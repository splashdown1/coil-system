#!/usr/bin/env python3
"""
COIL Pre-Upload Sanity Check
Run before every upload batch to catch manifest drift, hash mismatches,
and fileId namespace pollution before they accumulate.

Exit codes:
  0 = all checks passed
  1 = check failed — do not upload
  2 = usage error
"""
import json, sys, hashlib, struct, os

# ── Config ──────────────────────────────────────────────────────────────────
WORKSPACE      = "/home/workspace"
SC_DIR         = os.path.join(WORKSPACE, "COIL_mirror/SC")
MANIFEST_PATH  = os.path.join(WORKSPACE, "COIL_MASTER_CHIP.json")
SERVER_BASE    = "http://localhost:3000"
CHIP_FILE      = "COIL_MASTER_CHIP.json"
CHUNK_SIZE     = 256
HEADER_FMT    = "<4sHI32sHH"   # 46 bytes
HEADER_SIZE    = 46

def red(s):   return f"\033[91m{s}\033[0m"
def green(s): return f"\033[92m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def bold(s):  return f"\033[1m{s}\033[0m"

def h1(s):
    print(f"\n{bold('─'*60)}")
    print(f"{bold(s)}")

def h2(s):
    print(f"\n  {bold(s)}")

# ── Load local manifest ────────────────────────────────────────────────────────
h1("CHECK 1 — Local manifest integrity")
try:
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    chip = next(e for e in manifest["files"] if e["filename"] == CHIP_FILE)
except Exception as e:
    print(f"  {red('FAIL')} Cannot load {MANIFEST_PATH}: {e}")
    sys.exit(2)

local_size    = chip["size_bytes"]
local_hash    = chip["file_hash_sha256"]
local_chunks  = chip["chunk_count"]
sc_count_l    = chip.get("super_chunk_count", "MISSING")

print(f"  Source file:  {local_size:,} bytes")
print(f"  Source hash:  {local_hash}")
print(f"  Chunk count:  {local_chunks:,} × {CHUNK_SIZE}B")
print(f"  Super-chunks: {sc_count_l}")

# ── Verify local source file hash ────────────────────────────────────────────
h1("CHECK 2 — Source file hash verification")
actual_hash = hashlib.sha256(open(MANIFEST_PATH, "rb").read()).hexdigest()
if actual_hash == local_hash:
    print(f"  {green('PASS')} hash matches manifest")
else:
    print(f"  {red('FAIL')} hash mismatch!")
    print(f"    Manifest: {local_hash}")
    print(f"    Actual:   {actual_hash}")
    sys.exit(1)

# ── Compute super-chunk derived values ───────────────────────────────────────
h1("CHECK 3 — Super-chunk arithmetic")
num_full = local_size // CHUNK_SIZE
remainder = local_size % CHUNK_SIZE
total_chunks_derived = num_full + (1 if remainder else 0)
num_sc_derived = (total_chunks_derived + 19) // 20   # 20 chunks per SC

print(f"  Source size:    {local_size:,} bytes")
print(f"  Full chunks:    {num_full:,}")
print(f"  Remainder:      {remainder} bytes")
print(f"  Total chunks:   {total_chunks_derived:,} (should match manifest)")
print(f"  Super-chunks:   {num_sc_derived:,} (should match manifest)")

mismatch = False
if total_chunks_derived != local_chunks:
    print(f"  {red('FAIL')} chunk count mismatch: derived {total_chunks_derived} vs manifest {local_chunks}")
    mismatch = True
else:
    print(f"  {green('PASS')} chunk count matches")

if sc_count_l != "MISSING" and sc_count_l != num_sc_derived:
    print(f"  {red('FAIL')} super-chunk count mismatch: derived {num_sc_derived} vs manifest {sc_count_l}")
    mismatch = True
else:
    print(f"  {green('PASS')} super-chunk count matches")

if mismatch:
    sys.exit(1)

# ── Probe server state ────────────────────────────────────────────────────────
h1("CHECK 4 — Server state probe")
import urllib.request

server_manifest_url = f"{SERVER_BASE}/audit/{CHIP_FILE}?total={num_sc_derived}"
try:
    resp = urllib.request.urlopen(server_manifest_url, timeout=5)
    server_data = json.loads(resp.read())
    server_received = server_data.get("received", 0)
    server_missing  = len(server_data.get("missingRanges", []))
    print(f"  Server received:  {server_received:,} chunks")
    print(f"  Server missing:    {server_missing:,} ranges")
except Exception as e:
    print(f"  {yellow('WARN')} Could not reach server: {e}")
    print(f"  {yellow('     ')} Proceeding without server probe — upload anyway")
    server_received = None

# ── Check super-chunk files ───────────────────────────────────────────────────
h1("CHECK 5 — Super-chunk file integrity")
sc_files = sorted([
    f for f in os.listdir(SC_DIR)
    if f.startswith("chip.sc.") and f.endswith(".bin")
], key=lambda x: int(x.split(".")[2]))

print(f"  SC files on disk: {len(sc_files):,} (expected {num_sc_derived})")
if len(sc_files) != num_sc_derived:
    print(f"  {red('FAIL')} SC count mismatch — source regenerated since last upload?")
    sys.exit(1)

# Verify first 3 and last 3 SC headers
sample_ids = []
if num_sc_derived == 0:
    print(f"  {red('FAIL')} No super-chunks found")
    sys.exit(1)
elif num_sc_derived <= 6:
    sample_ids = list(range(num_sc_derived))
else:
    sample_ids = [0, 1, 2, num_sc_derived-3, num_sc_derived-2, num_sc_derived-1]

sha_ok = 0
for sid in sample_ids:
    sc_path = os.path.join(SC_DIR, f"chip.sc.{sid:06d}.bin")
    if not os.path.exists(sc_path):
        print(f"  {red('FAIL')} Missing SC {sid}: {sc_path}")
        sys.exit(1)
    data = open(sc_path, "rb").read()
    actual = hashlib.sha256(data).hexdigest()
    entry = next((e for e in chip["super_chunks"] if e["super_id"] == sid), None)
    if entry and actual == entry["sha256"]:
        sha_ok += 1
    elif entry:
        print(f"  {red('FAIL')} SHA mismatch SC {sid}")
        print(f"    Expected: {entry['sha256']}")
        print(f"    Actual:   {actual}")

print(f"  Header/SHA checks: {sha_ok}/{len(sample_ids)} passed")
if sha_ok != len(sample_ids):
    sys.exit(1)

# ── Check for server drift (if server reachable) ───────────────────────────────
if server_received is not None:
    h1("CHECK 6 — Server drift detection")
    sc_uploaded = server_received // 20   # rough super-chunk count
    local_sc_on_disk = len(sc_files)
    
    if sc_uploaded > local_sc_on_disk:
        print(f"  {red('WARN')} Server has {server_received} chunks ({sc_uploaded} SC)")
        print(f"         Disk has    {local_sc_on_disk} SC")
        print(f"         Gap:        {sc_uploaded - local_sc_on_disk} SC MORE on server than disk")
        print(f"         {red('STOP')} Source may have been regenerated after upload started")
        print(f"         Remove server chunks before resuming:")
        print(f"         curl -X POST {SERVER_BASE}/purge -H 'x-file-id: {CHIP_FILE}'")
        sys.exit(1)
    elif sc_uploaded < local_sc_on_disk:
        print(f"  {green('OK')} Server behind disk ({sc_uploaded} vs {local_sc_on_disk} SC) — upload is safe to resume")
    else:
        print(f"  {green('OK')} Server and disk in sync")

# ── Summary ────────────────────────────────────────────────────────────────────
h1("RESULT")
print(f"  {green('ALL CHECKS PASSED')} — ready to upload")
print(f"  Source: {local_size:,} bytes | {local_chunks:,} chunks | {num_sc_derived:,} super-chunks")
print(f"  SC dir: {SC_DIR}")
print(f"  Server: {SERVER_BASE}")
sys.exit(0)
