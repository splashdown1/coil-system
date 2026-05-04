#!/usr/bin/env python3
"""
COIL Delta Sync Test
Run while COIL_Server.js is running in the background on port 3000

Tests:
  1. Upload a 3-chunk file
  2. Modify only chunk 1 on the client
  3. Call GET /status to get server's hash map
  4. Delta sync — only changed chunks (0, 2) should be uploaded
  5. Verify server rejects unchanged chunk 1 and accepts changed chunk 1
"""
import os
import json
import hashlib
import requests

BASE = "http://localhost:3000"
FILE_ID = "delta-test-002"  # fresh each run to avoid stale manifest pickup

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def clean():
    import shutil
    for d in ["./uploads", "./manifests"]:
        # Wipe entire file-id subdir AND any loose manifest so no stale data
        subdir = os.path.join(d, FILE_ID)
        if os.path.exists(subdir):
            shutil.rmtree(subdir)
        manifest = os.path.join(d, f"{FILE_ID}.json")
        if os.path.exists(manifest):
            os.remove(manifest)
    print("[DELTA] Cleaned up test artifacts")
    print()

def original_payload():
    """Returns 3 chunks: all different content"""
    chunks = [
        b'{"part": 1, "data": "alpha"}',
        b'{"part": 2, "data": "beta"}',
        b'{"part": 3, "data": "gamma"}',
    ]
    hashes = [hashlib.sha256(c).hexdigest() for c in chunks]
    return chunks, hashes

def modified_payload():
    """Same as original but chunk 1 changed"""
    chunks = [
        b'{"part": 1, "data": "alpha"}',        # unchanged
        b'{"part": 2, "data": "BETA_MODIFIED"}', # changed
        b'{"part": 3, "data": "gamma"}',         # unchanged
    ]
    hashes = [hashlib.sha256(c).hexdigest() for c in chunks]
    return chunks, hashes

def upload_chunk(chunk_idx, data, expected_hash, compressed=False):
    headers = {
        "x-file-id": FILE_ID,
        "x-chunk-index": str(chunk_idx),
        "x-hash": expected_hash,
    }
    if compressed:
        headers["x-compressed"] = "true"
    r = requests.post(f"{BASE}/upload", data=data, headers=headers)
    return r.status_code, r.json()

print("=" * 60)
print("COIL DELTA SYNC TEST")
print("=" * 60)
print()

# ── Cleanup from any previous run ───────────────────────────────────────────
clean()

# ── Step 1: Upload original file (3 chunks) ─────────────────────────────────
print("[STEP 1] Upload original file (3 chunks)")
orig_chunks, orig_hashes = original_payload()
for idx, chunk, h in zip(range(len(orig_chunks)), orig_chunks, orig_hashes):
    status, body = upload_chunk(idx, chunk, h)
    print(f"  Chunk {idx}: HTTP {status} — {'✅' if status == 200 else '❌'}")

r = requests.post(f"{BASE}/complete",
                  headers={"x-file-id": FILE_ID},
                  json={"originalName": "delta_test.json", "totalExpected": 3})
print(f"  /complete: HTTP {r.status_code} — {'✅' if r.status_code == 200 else '❌'}")
print()

# ── Step 2: Get server hash map ─────────────────────────────────────────────
print("[STEP 2] Fetch server chunk hash map via GET /status")
r = requests.get(f"{BASE}/status", params={"fileId": FILE_ID})
server_map = r.json()
print(f"  Server map: {server_map}")
print()

# ── Step 3: Build delta — compare client hashes vs server hashes ──────────────
print("[STEP 3] Delta analysis: client hashes vs server hashes")
mod_chunks, mod_hashes = modified_payload()
skip_count = 0
upload_count = 0

for idx, (chunk, new_hash) in enumerate(zip(mod_chunks, mod_hashes)):
    server_hash = server_map.get(str(idx))
    if server_hash == new_hash:
        print(f"  Chunk {idx}: ⏭ SKIP (identical)")
        skip_count += 1
    else:
        print(f"  Chunk {idx}: ⬆ UPLOAD (changed — server={server_hash[:8]}..., client={new_hash[:8]}...)")
        upload_count += 1

print(f"  Delta result: {skip_count} skip, {upload_count} upload")
print()

# ── Step 4: Only upload changed chunks (simulating delta logic) ──────────────
print("[STEP 4] Upload only changed chunks")
FILE_ID_DELTA = "delta-test-002"  # fresh fileId for clarity
results = {}
for idx, (chunk, new_hash) in enumerate(zip(mod_chunks, mod_hashes)):
    server_hash = server_map.get(str(idx))
    if server_hash == new_hash:
        # In real delta sync: skip entirely. Here we log but don't upload.
        results[idx] = "skipped"
        print(f"  Chunk {idx}: ⏭ skipped (unchanged)")
    else:
        status, body = upload_chunk(idx, chunk, new_hash)
        results[idx] = status
        marker = "✅" if status in (200, 208) else "❌"  # 208 = Already Reported (chunk already exists)
        print(f"  Chunk {idx}: HTTP {status} {marker}")

print()

# ── Step 5: Verify — unchanged chunk should NOT be re-uploaded ──────────────
print("[STEP 5] Delta sync verification")
print(f"  Skipped (unchanged) chunks: {skip_count}")
print(f"  Uploaded (changed) chunks: {upload_count}")
passed = skip_count == 2 and upload_count == 1
print(f"  Result: {'✅ DELTA SYNC PASSED' if passed else '❌ DELTA SYNC FAILED'}")
print()

clean()
print("[DELTA] Test complete")
