#!/usr/bin/env python3
"""
COIL end-to-end test script
Run while COIL_Server.js is running in the background on port 3000
"""
import os
import json
import hashlib
import requests
import zlib
import base64

FILE_ID = "test-e2e-001"
BASE = "http://localhost:3000"
ORIG_PATH = "/tmp/test_coil_payload.json"

def clean():
    import shutil
    shutil.rmtree("./uploads/test-e2e-001", ignore_errors=True)
    shutil.rmtree("./manifests/test-e2e-001.json", ignore_errors=True)

# ── Step 1: Create test payload ─────────────────────────────────────────────
with open(ORIG_PATH, "wb") as f:
    f.write(b'{"test": "COIL_SYNC_protocol_v1", "data": [1,2,3,4,5]}')

with open(ORIG_PATH, "rb") as f:
    raw_bytes = f.read()

original_hash = hashlib.sha256(raw_bytes).hexdigest()
original_size = len(raw_bytes)
print(f"[TEST] Original: {original_size} bytes, SHA256: {original_hash}")

# ── Step 2: Compress (not needed for basic test — upload raw) ──────────────
# compressed = zlib.compress(raw_bytes)
# compressed_size = len(compressed)

# ── Step 3: Chunk raw bytes directly (no compression — server stores as-is) ──
CHUNK_SIZE = 32
chunks = []
for i in range(0, len(raw_bytes), CHUNK_SIZE):
    chunk_bytes = raw_bytes[i:i+CHUNK_SIZE]
    chunk_hash = hashlib.sha256(chunk_bytes).hexdigest()
    chunks.append((i // CHUNK_SIZE, chunk_bytes, chunk_hash))

print(f"[TEST] {len(chunks)} chunks")

# ── Step 4: Upload raw binary (no multipart) ─────────────────────────────────
for idx, chunk_data, chunk_hash in chunks:
    headers = {
        "x-file-id": FILE_ID,
        "x-chunk-index": str(idx),
        "x-hash": chunk_hash,
        "x-compressed": "false"
    }
    r = requests.post(
        f"{BASE}/upload",
        data=chunk_data,          # raw bytes — no multipart encoding
        headers=headers
    )
    print(f"[TEST] Chunk {idx:03d} → HTTP {r.status_code}")

# ── Step 5: Check /status ────────────────────────────────────────────────────
r = requests.get(f"{BASE}/status/{FILE_ID}")
print(f"[TEST] /status → {r.json()}")

# ── Step 6: Complete (fileId goes in HEADER, not body) ─────────────────────
r = requests.post(
    f"{BASE}/complete",
    headers={"x-file-id": FILE_ID},
    json={"originalName": "test_payload.json"}  # body still OK
)
print(f"[TEST] /complete → {r.json()}")

# ── Step 7: Verify ──────────────────────────────────────────────────────────
# Server outputs as {fileId}.bin (no originalExt was provided to /complete)
reconstructed_path = f"./uploads/{FILE_ID}.bin"
if os.path.exists(reconstructed_path):
    with open(reconstructed_path, "rb") as f:
        reconstructed = f.read()
    reconstructed_hash = hashlib.sha256(reconstructed).hexdigest()
    print(f"[TEST] Reconstructed hash: {reconstructed_hash}")
    print(f"[TEST] Match: {'✅' if reconstructed_hash == original_hash else '❌'}")
else:
    print("[TEST] ❌ File not reconstructed")

clean()
print("[TEST] Done")