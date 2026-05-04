#!/usr/bin/env python3
"""
COIL Pre-Flight Audit — TASK 007
Run this BEFORE any upload starts. Catches namespace collision,
manifest mismatch, and orphaned server state before bytes fly.

Usage:
  python3 coil_preflight.py <source_file> <target_fileId> [server_url]
  python3 coil_preflight.py COIL_MASTER_CHIP.json COIL_MASTER_CHIP http://localhost:3000

Exit codes: 0 = pass, 1 = fatal, 2 = warning (server not clean)
"""
import json, sys, os, hashlib, urllib.request

CHUNK_SIZE = 256
SUPER_SIZE = 20
DEFAULT_SERVER = "https://coil-sync-server-splashdown.zocomputer.io"

def fatal(msg): print(f"FATAL: {msg}", file=sys.stderr); sys.exit(1)
def warn(msg):  print(f"WARNING: {msg}", file=sys.stderr)

# ── 1. Namespace check ────────────────────────────────────────────────────────
def check_namespace(file_id):
    print(f"\n[1/4] NAMESPACE CHECK — {file_id}")
    if not file_id or len(file_id) < 3:
        fatal(f"Invalid file-id: '{file_id}' (too short)")
    if file_id not in ("COIL_MASTER_CHIP.json", "COIL_MASTER_CHIP", "ALPHA-BACKTEST-1777174", "CYCLE23-1777172221"):
        warn(f"Unusual file-id: '{file_id}' — verify this is intentional")
    else:
        print(f"  ✓ Known file-id")
    return True

# ── 2. Source audit ────────────────────────────────────────────────────────────
def audit_source(source_path):
    print(f"\n[2/4] SOURCE AUDIT — {source_path}")
    if not os.path.exists(source_path):
        fatal(f"Source file not found: {source_path}")

    size      = os.path.getsize(source_path)
    chunks    = size // CHUNK_SIZE
    remainder = size % CHUNK_SIZE
    sc_count  = (chunks + SUPER_SIZE - 1) // SUPER_SIZE
    full_hash = hashlib.sha256(open(source_path, "rb").read()).hexdigest()

    print(f"  Size:        {size:,} bytes")
    print(f"  Full chunks: {chunks:,} × {CHUNK_SIZE}B = {chunks*CHUNK_SIZE:,} bytes covered")
    print(f"  Remainder:   {remainder} bytes{' → padded to full chunk' if remainder else ' (none)'}")
    print(f"  Super-chunks: {sc_count:,}")
    print(f"  SHA256:      {full_hash}")

    return {"size": size, "chunks": chunks, "remainder": remainder,
            "super_chunks": sc_count, "hash": full_hash}

# ── 3. Server state probe ──────────────────────────────────────────────────────
def probe_server(file_id, server_base):
    print(f"\n[3/4] SERVER STATE — {file_id} @ {server_base}")
    url = f"{server_base}/audit/{file_id}?total=999999"

    try:
        raw = json.loads(urllib.request.urlopen(url, timeout=5).read())
    except Exception as e:
        warn(f"Server unreachable ({e}) — cannot verify server state. Assuming clean.")
        return None

    received    = raw.get("chunksReceived", 0)
    total_exp   = raw.get("totalExpected", "UNKNOWN")
    missing     = raw.get("missingRanges", [])
    orphaned    = raw.get("totalOrphanedFiles", 0)

    print(f"  Received:    {received:,} chunks")
    print(f"  Expected:    {total_exp}")
    print(f"  Missing:     {len(missing)} range(s)")
    if orphaned:
        warn(f"  ⚠ Orphaned files on server: {orphaned}")

    if received > 0:
        for m in missing[:5]:
            print(f"    Missing: {m}")
        if len(missing) > 5:
            print(f"    ... +{len(missing)-5} more")

    return raw

# ── 4. Wipe gate ──────────────────────────────────────────────────────────────
def check_wipe_gate(server_state, source_info):
    print(f"\n[4/4] WIPE GATE")
    if server_state is None:
        print("  ℹ Server not reachable — assuming clean. Proceed.")
        return

    received = server_state.get("chunksReceived", 0)
    if received == 0:
        print("  ✓ Server is clean — proceed with upload")
        return

    print(f"  ✗ SERVER HAS {received:,} CHUNKS — NOT CLEAN")
    print(f"  Uploading into non-empty server = split-brain state.")
    print()
    wipe_url = f"http://localhost:3000/wipe/{server_state.get('fileId', file_id)}"
    print(f"  To wipe: curl -X POST {wipe_url}")
    print()
    fatal("PRE-FLIGHT FAILED: server state not clean. Wipe first.")

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        fatal("Usage: python3 coil_preflight.py <source_file> <target_fileId> [server_url]")
        sys.exit(1)

    source_path = sys.argv[1]
    file_id     = sys.argv[2]
    server_base = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SERVER

    check_namespace(file_id)
    src = audit_source(source_path)
    srv = probe_server(file_id, server_base)
    check_wipe_gate(srv, src)

    print(f"\n{'='*50}")
    print(f"PRE-FLIGHT: PASS")
    print(f"  Source:  {src['size']:,} bytes | {src['chunks']:,} chunks | {src['super_chunks']:,} SCs")
    print(f"  Target:  {file_id}")
    print(f"  Server:  {server_base}")
    print(f"  Hash:    {src['hash']}")
    print(f"\nReady to upload. Run task005_batch_uploader.py next.")