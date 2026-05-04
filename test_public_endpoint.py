#!/usr/bin/env python3
"""
COIL Public Endpoint Full Verification
Tests against the live public endpoint:
  https://coil-sync-server-splashdown.zocomputer.io
"""
import os, time, requests, json, hashlib, shutil

BASE_URL = "https://coil-sync-server-splashdown.zocomputer.io"
FILE_ID = f"pub-test-{int(time.time())}"

def clean():
    for d in ["./uploads", "./manifests"]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def log(msg):
    print(f"  {msg}")

print("\n==============================================")
print("COIL PUBLIC ENDPOINT VERIFICATION")
print("==============================================\n")

# ── Step 1: Health / reachability ───────────────────────────────────────────
print(f"[STEP 1] Server reachability")
r = requests.get(f"{BASE_URL}/status/ping")
log(f"GET /status/ping → {r.status_code} | {r.elapsed.total_seconds()*1000:.1f}ms")
r = requests.get(f"{BASE_URL}/status/{FILE_ID}")
log(f"GET /status/{{fileId}} → {r.status_code} | body: {r.json()}")

# ── Step 2: Upload 3-chunk file ──────────────────────────────────────────────
print(f"\n[STEP 2] Full upload (3 chunks)")
payload = b'A' * 300 + b'B' * 200 + b'C' * 150
log(f"Payload: {len(payload)} bytes, SHA256: {sha256(payload)[:16]}…")

chunk_size = 256
chunks = []
for i in range(0, len(payload), chunk_size):
    chunks.append(payload[i:i+chunk_size])

orig_hashes = [sha256(c) for c in chunks]
uploaded_indices = []

t0 = time.time()
for idx, chunk_data in enumerate(chunks):
    r = requests.post(f"{BASE_URL}/upload",
        headers={
            "x-file-id": FILE_ID,
            "x-chunk-index": str(idx),
            "x-hash": orig_hashes[idx],
            "x-compressed": "false",
            "x-original-size": str(len(chunk_data))
        },
        data=chunk_data
    )
    uploaded_indices.append(idx)
    log(f"  Chunk {idx}: {len(chunk_data)}B → HTTP {r.status_code}")

log(f"Upload time: {(time.time()-t0)*1000:.0f}ms")

# ── Step 3: Confirm chunks received ─────────────────────────────────────────
print(f"\n[STEP 3] Confirm chunks received")
r = requests.get(f"{BASE_URL}/status/{FILE_ID}")
body = r.json()
log(f"GET /status/{FILE_ID} → status={body.get('status')}")
log(f"Received chunks: {sorted(body.get('receivedChunks', []))}")

# ── Step 4: Delta re-upload (same chunks + 1 changed) ─────────────────────────
print(f"\n[STEP 4] Delta re-upload")
changed_chunk_data = b'A' * 300 + b'B' * 200 + b'C' * 250  # chunk 2 slightly changed
changed_hash = sha256(changed_chunk_data)

r = requests.get(f"{BASE_URL}/status?fileId={FILE_ID}")
server_map = r.json() if r.ok else {}
log(f"Server hash map: {json.dumps(server_map)[:80]}…")

t0 = time.time()
delta_skipped = 0
for idx, chunk_data in enumerate([payload[:256], payload[256:456], changed_chunk_data]):
    h = sha256(chunk_data)
    if server_map.get(str(idx)) == h:
        log(f"  Chunk {idx}: ⏭ SKIP (identical)")
        delta_skipped += 1
    else:
        r = requests.post(f"{BASE_URL}/upload",
            headers={
                "x-file-id": FILE_ID,
                "x-chunk-index": str(idx),
                "x-hash": h,
                "x-compressed": "false",
                "x-original-size": str(len(chunk_data))
            },
            data=chunk_data
        )
        log(f"  Chunk {idx}: ⬆ UPLOAD (changed) → HTTP {r.status_code}")

log(f"Delta time: {(time.time()-t0)*1000:.0f}ms | Skipped: {delta_skipped}/{len(chunks)}")

# ── Step 5: Complete + reconstruct + verify ──────────────────────────────────
print(f"\n[STEP 5] Complete + reconstruct")
r = requests.post(f"{BASE_URL}/complete",
    headers={"x-file-id": FILE_ID},
    data=json.dumps({
        "originalName": "public-test.txt",
        "totalExpected": len(chunks) + 1
    })
)
log(f"POST /complete → HTTP {r.status_code}")

time.sleep(1)
r = requests.get(f"{BASE_URL}/data/{FILE_ID}.json")
log(f"GET /data/{FILE_ID}.json → HTTP {r.status_code} | {len(r.content)} bytes")
if r.ok and r.content:
    try:
        result = json.loads(r.text)
        reconstructed = result.get("data", result.get("", "")).encode() if isinstance(result.get("data"), str) else result.get("data", b"")
        if isinstance(reconstructed, str): reconstructed = reconstructed.encode()
        reconstructed_hash = sha256(reconstructed)
    except:
        # Not JSON — raw binary
        reconstructed = r.content
        reconstructed_hash = sha256(reconstructed)
        result = {}
    expected_hash = sha256(payload[:256] + payload[256:456] + changed_chunk_data)
    match = reconstructed_hash == expected_hash
    log(f"Reconstructed: {len(reconstructed)}B")
    log(f"Hash match: {'✅' if match else '❌'}")
    log(f"  Expected: {expected_hash[:16]}…")
    log(f"  Got:      {reconstructed_hash[:16]}…")
else:
    log(f"Response: {r.text[:200]}")

clean()
print(f"\n==============================================")
print("VERIFICATION COMPLETE")
print("==============================================\n")
