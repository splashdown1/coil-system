#!/usr/bin/env python3
"""
COIL Compression Test
Run while COIL_Server.js is running in the background on port 3000

Tests:
  1. Chunk + compress + upload compressed chunk
  2. Server decompresses before SHA-256 verify
  3. Reconstructed file hash matches original
"""
import os
import json
import hashlib
import requests
import zlib

FILE_ID = "test-compress-001"
BASE = "http://localhost:3000"
ORIG_PATH = "/tmp/test_coil_payload.json"
CHUNK_SIZE = 32 * 1024  # bytes — 32KB

def clean():
    for d in [f"./uploads/{FILE_ID}", f"./manifests/{FILE_ID}.json"]:
        try: os.remove(d)
        except: pass

def test():
    clean()
    print("============================================================")
    print("COIL COMPRESSION TEST")
    print("============================================================\n")

    # ── Step 1: Load original ────────────────────────────────────────────────
    with open(ORIG_PATH, "rb") as f:
        raw = f.read()
    original_hash = hashlib.sha256(raw).digest()
    print(f"[COMPRESS] Original: {len(raw)} bytes, SHA256: {original_hash.hex()}\n")

    # ── Step 2: Chunk + compress ──────────────────────────────────────────────
    chunks = []
    for i in range(0, len(raw), CHUNK_SIZE):
        chunk_data = raw[i : i + CHUNK_SIZE]
        # Use zlib.compress (zlib format RFC 1950) — matches server's zlib.decompress()
        compressed = zlib.compress(chunk_data)
        chunk_hash = hashlib.sha256(chunk_data).digest()  # hash ORIGINAL bytes
        chunks.append((chunk_data, compressed, chunk_hash))
        print(f"  Chunk {i//CHUNK_SIZE}: raw={len(chunk_data)}B → "
              f"compressed={len(compressed)}B "
              f"({100*len(compressed)/max(len(chunk_data),1):.0f}% ratio)")

    print()

    # ── Step 3: Upload compressed chunks ─────────────────────────────────────
    print("[STEP 1] Upload compressed chunks")
    for idx, (chunk_data, compressed, chunk_hash) in enumerate(chunks):
        headers = {
            "x-file-id": FILE_ID,
            "x-chunk-index": str(idx),
            "x-hash": chunk_hash.hex(),
            "x-compressed": "true",
            "x-original-size": str(len(chunk_data)),
            "Content-Type": "application/octet-stream",
        }
        r = requests.post(f"{BASE}/upload", headers=headers, data=compressed)
        print(f"  Chunk {idx}: HTTP {r.status_code} — {'✅' if r.status_code == 200 else '❌'}")

    # ── Step 4: Check manifest has compressed flag ───────────────────────────
    r = requests.get(f"{BASE}/status/{FILE_ID}")
    manifest = r.json()
    print(f"\n[STEP 2] Manifest status: {manifest.get('status')}")
    # receivedChunks is an array of indices from /status/:fileId
    print(f"  Total chunks received: {manifest.get('totalReceived')}")

    # ── Step 5: Complete + reconstruct ───────────────────────────────────────
    print(f"\n[STEP 3] Complete + reconstruct")
    r = requests.post(
        f"{BASE}/complete",
        headers={"x-file-id": FILE_ID},
        json={"originalName": "test_compressed.json", "totalExpected": len(chunks)},
    )
    print(f"  /complete: HTTP {r.status_code} — {'✅' if r.status_code == 200 else '❌'}")
    result = r.json()
    print(f"  Result: {result}")

    reconstructed_path = f"./uploads/{FILE_ID}.bin"
    if os.path.exists(reconstructed_path):
        with open(reconstructed_path, "rb") as f:
            reconstructed = f.read()
        reconstructed_hash = hashlib.sha256(reconstructed).digest()
        match = reconstructed_hash == original_hash
        print(f"\n[STEP 4] Reconstruction verification")
        print(f"  Original hash:      {original_hash.hex()}")
        print(f"  Reconstructed hash: {reconstructed_hash.hex()}")
        print(f"  Match: {'✅ COMPRESSION TEST PASSED' if match else '❌ MISMATCH'}")
    else:
        print(f"\n[STEP 4] ❌ File not reconstructed")

    clean()
    print("\n[COMPRESS] Test complete")

if __name__ == "__main__":
    test()
