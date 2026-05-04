#!/usr/bin/env python3
"""
COIL + JSON Patch End-to-End Test
Run while COIL_Server.js is running in the background on port 3000

Tests the full pipeline:
  1. Upload v1 JSON file
  2. Upload v1 via COIL chunks
  3. Diff v1 vs v2 → generate patch ops
  4. Send only the ops via /diff
  5. Server applies patch → reconstructed v2 matches local v2
"""
import os
import json
import hashlib
import base64
import requests

BASE = "http://localhost:3000"
FILE_ID = "test-patch-001"

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def clean():
    import shutil
    for d in ["./uploads", "./manifests", "./data", "./patches"]:
        folder = os.path.join(d, FILE_ID)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(d, exist_ok=True)
        for f in [f"{FILE_ID}.json", f"{FILE_ID}.json.orig", f"{FILE_ID}.json.patch"]:
            p = os.path.join(d, f)
            if os.path.exists(p): os.remove(p)

def diff_json(old_obj, new_obj, path=""):
    ops = []
    # Removed keys
    for key in old_obj:
        if key not in new_obj:
            ops.append({"op": "remove", "path": f"{path}/{key}"})
    # Added or replaced keys
    for key in new_obj:
        new_path = f"{path}/{key}" if path else f"/{key}"
        if key not in old_obj:
            ops.append({"op": "add", "path": new_path, "value": new_obj[key]})
        elif old_obj[key] != new_obj[key]:
            if isinstance(old_obj[key], dict) and isinstance(new_obj[key], dict):
                ops.extend(diff_json(old_obj[key], new_obj[key], new_path))
            else:
                ops.append({"op": "replace", "path": new_path, "value": new_obj[key]})
    return ops

def apply_patch(obj, ops):
    result = json.loads(json.dumps(obj))
    for op in ops:
        keys = [k for k in op["path"].split("/") if k]
        target = result
        for key in keys[:-1]:
            target = target[key]
        last = keys[-1]
        if op["op"] == "remove":
            del target[last]
        elif op["op"] in ("replace", "add"):
            target[last] = op["value"]
    return result

def test():
    clean()

    # ── v1 ──────────────────────────────────────────────────────────────────
    v1 = {
        "version": 1,
        "name": "Training_Set_Batch_1",
        "entries": [
            {"id": 0, "value": 10},
            {"id": 1, "value": 20},
            {"id": 2, "value": 30},
            {"id": 3, "value": 40},
        ]
    }
    v1_bytes = json.dumps(v1, separators=(",", ":")).encode()
    v1_hash = sha256(v1_bytes)
    print(f"[v1] JSON size: {len(v1_bytes)}B, SHA256: {v1_hash[:16]}...")

    # ── Step 1: Upload v1 via COIL chunks ───────────────────────────────────
    print("\n[STEP 1] Upload v1 via COIL chunks")
    chunk_size = 200
    chunks = [v1_bytes[i:i+chunk_size] for i in range(0, len(v1_bytes), chunk_size)]
    for i, chunk in enumerate(chunks):
        h = sha256(chunk)
        r = requests.post(f"{BASE}/upload", headers={
            "x-file-id": FILE_ID,
            "x-chunk-index": str(i),
            "x-hash": h,
            "x-version": "1"
        }, data=chunk)
        if not r.ok:
            print(f"  Chunk {i}: ❌ HTTP {r.status_code} — {r.text}")
            return
        else:
            print(f"  Chunk {i}: ✅ HTTP {r.status_code}")

    # ── Step 2: Complete v1 ────────────────────────────────────────────────
    print("\n[STEP 2] Complete v1")
    r = requests.post(f"{BASE}/complete", headers={"x-file-id": FILE_ID}, json={
        "fileId": FILE_ID,
        "originalExt": "json",
        "totalExpected": len(chunks)
    })
    print(f"  /complete: HTTP {r.status_code} — {r.json()}")

    # ── v2 (local diff) ─────────────────────────────────────────────────────
    v2 = {
        "version": 2,
        "name": "Training_Set_Batch_1",
        "entries": [
            {"id": 0, "value": 10},
            {"id": 1, "value": 99},       # replaced
            {"id": 2, "value": 30},
            # id 3 removed
            {"id": 4, "value": 50},       # added
        ]
    }
    v2_bytes = json.dumps(v2, separators=(",", ":")).encode()
    v2_hash = sha256(v2_bytes)
    print(f"\n[v2] JSON size: {len(v2_bytes)}B, SHA256: {v2_hash[:16]}...")

    # ── Step 3: Generate ops via diffJSON ───────────────────────────────────
    print("\n[STEP 3] diffJSON(v1, v2)")
    ops = diff_json(v1, v2)
    ops_bytes = json.dumps(ops, separators=(",", ":")).encode()
    ops_hash = sha256(ops_bytes)
    print(f"  Ops: {len(ops)} patch operations")
    for op in ops:
        print(f"    {op}")
    print(f"  Ops size: {len(ops_bytes)}B vs full file {len(v2_bytes)}B → "
          f"{100 - round(len(ops_bytes)/len(v2_bytes)*100)}% saved")

    # ── Step 4: Send ops via /diff ──────────────────────────────────────────
    print("\n[STEP 4] POST /diff")
    r = requests.post(f"{BASE}/diff", json={
        "fileId": FILE_ID,
        "baseVersion": 1,
        "newVersion": 2,
        "ops": ops
    })
    if not r.ok:
        print(f"  /diff: ❌ HTTP {r.status_code} — {r.text}")
        return
    resp = r.json()
    print(f"  /diff: ✅ HTTP {r.status_code}")
    print(f"  Response: {resp}")

    # ── Step 5: Verify reconstructed v2 matches local v2 ─────────────────────
    print("\n[STEP 5] Verify")
    reconstructed_path = f"./data/{FILE_ID}.json"
    if os.path.exists(reconstructed_path):
        with open(reconstructed_path) as f:
            reconstructed_v2 = json.load(f)
        # Normalise for comparison
        reconstructed_normalised = json.dumps(reconstructed_v2, sort_keys=True)
        local_normalised = json.dumps(v2, sort_keys=True)
        match = reconstructed_normalised == local_normalised
        print(f"  Reconstructed v2 matches local v2: {'✅' if match else '❌'}")
        print(f"  Reconstructed: {json.dumps(reconstructed_v2, indent=2)[:300]}")
    else:
        print(f"  ❌ Reconstructed file not found at {reconstructed_path}")

    # ── Patch audit trail ───────────────────────────────────────────────────
    patch_file = f"./patches/{FILE_ID}.json.patch"
    if os.path.exists(patch_file):
        with open(patch_file) as f:
            audit = json.load(f)
        print(f"\n[PATCH AUDIT] {json.dumps(audit, indent=2)}")

    # Check patches dir for patch file
    if os.path.exists(f"./patches"):
        for f in os.listdir("./patches"):
            if FILE_ID in f:
                print(f"\n[PATCH FILE] ./{f}")
                with open(f"./patches/{f}") as pf:
                    print(pf.read()[:500])

    clean()
    print("\n[PATCH] Test complete")

if __name__ == "__main__":
    test()
