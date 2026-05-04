#!/usr/bin/env python3
"""COIL 50MB upload + delta sync demo"""
import hashlib, time, json, requests

BASE = "https://coil-sync-server-splashdown.zocomputer.io"
FILE = "/home/workspace/Cycle23_Training_Dummy.bin"

with open(FILE, "rb") as f:
    data = f.read()

size = len(data)
print(f"File: {size:,} bytes ({size/1024/1024:.1f} MB)")

# Check baseline hash from established mirror
expected_hash = "cb30c4bcd40647e0b1415769112df5bf10d546770ce7518250bff34a7d077a17"
actual_hash = hashlib.sha256(data).digest().hex()
print(f"Full hash: {actual_hash}")
print(f"Baseline:  {expected_hash}")
print(f"Match: {'✅' if actual_hash == expected_hash else '❌'}")

# Upload via COIL
CHUNK = 512 * 1024
file_id = f"CYCLE23-{int(time.time())}"

print(f"\nUploading as {file_id}...")
t0 = time.time()

chunks_sent = 0
for i in range(0, size, CHUNK):
    chunk = data[i:i+CHUNK]
    h = hashlib.sha256(chunk).hexdigest()
    r = requests.post(f"{BASE}/upload",
        headers={"x-file-id": file_id, "x-chunk-index": str(i//CHUNK),
                 "x-hash": h, "x-compressed": "false", "x-encrypted": "false",
                 "x-original-size": str(len(chunk))},
        data=chunk, timeout=30)
    if r.ok:
        chunks_sent += 1
        pct = min(100, (i+CHUNK)*100//size)
        print(f"\r  Chunk {chunks_sent}: ✅ {pct}%", end="", flush=True)
    else:
        print(f"\n  Chunk {i//CHUNK} failed: {r.status_code} {r.text}")
        break

t1 = time.time()
elapsed = t1 - t0
mb_per_s = (size/1024/1024) / elapsed if elapsed > 0 else 0

print(f"\n\nUploaded {chunks_sent} chunks in {elapsed:.1f}s")
print(f"Throughput: {mb_per_s:.1f} MB/s")
print(f"Rate: {chunks_sent/elapsed:.1f} chunks/s" if elapsed > 0 else "")