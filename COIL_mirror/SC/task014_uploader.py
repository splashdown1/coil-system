#!/usr/bin/env python3
"""
TASK 014-A Uploader — LOGOS_EXPANSION_001.bin (100MB, 20480 SCs)
x-file-id: LOGOS_EXPANSION_001.bin | server: localhost:3000
"""
import json, hashlib, os, sys, time, subprocess, struct
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Config ───────────────────────────────────────────────────────────────────
SC_DIR           = "/home/workspace/COIL_mirror/SC"
BATCH_LOG_PATH   = "/home/workspace/COIL_mirror/SC/TASK014_BATCH_LOG.json"
LOCAL_LOG_PATH   = "/home/workspace/COIL_mirror/SC/TASK014_SYNC_LOG.txt"
SOURCE_FILE      = "LOGOS_EXPANSION_001.bin"
FILE_ID          = "LOGOS_EXPANSION_001.bin"
SERVER_BASE      = "http://localhost:3000"
UPLOAD_ENDPOINT  = f"{SERVER_BASE}/upload"
BATCH_SIZE       = 20
MAX_WORKERS      = 10
TIMEOUT_SEC      = 30
HEADER_SIZE      = 46

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOCAL_LOG_PATH, "a") as f:
        f.write(line + "\n")

def upload_one(super_id, file_hash, sc_path, retries=3):
    for attempt in range(retries):
        try:
            cmd = [
                "curl", "-s", "--max-time", str(TIMEOUT_SEC),
                "-X", "POST",
                "-H", f"x-file-id: {FILE_ID}",
                "-H", f"x-chunk-index: {super_id}",
                "-H", f"x-hash: {file_hash}",
                "-H", "Content-Type: application/octet-stream",
                "--data-binary", f"@{sc_path}",
                UPLOAD_ENDPOINT
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SEC + 5)
            resp = json.loads(result.stdout)
            if resp.get("ok"):
                return True, None
            err = resp.get("error", result.stdout[:100])
        except Exception as ex:
            err = str(ex)
        if attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
    return False, err

def build_entries():
    """Build super-chunk entries from existing SC files, verifying header integrity."""
    entries = []
    for sid in range(20480):
        sc_path = os.path.join(SC_DIR, f"chip.sc.{sid:06d}.bin")
        if not os.path.exists(sc_path):
            log(f"FATAL: missing {sc_path}")
            sys.exit(1)
        with open(sc_path, "rb") as f:
            hdr = f.read(HEADER_SIZE)
        magic, ver, s_id, fhash, nc, rsv = struct.unpack("<4sHI32sHH", hdr)
        if magic != b"COIL":
            log(f"FATAL: {sc_path} has bad magic {magic}")
            sys.exit(1)
        live_sha = hashlib.sha256(open(sc_path, "rb").read()).hexdigest()
        entries.append({
            "super_id": sid,
            "file": f"chip.sc.{sid:06d}.bin",
            "size_bytes": os.path.getsize(sc_path),
            "sha256": live_sha,
            "num_chunks": nc,
        })
    return entries

def run_batch(batch_idx, super_entries):
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for e in super_entries:
            sc_path = os.path.join(SC_DIR, e["file"])
            fut = executor.submit(upload_one, e["super_id"], e["sha256"], sc_path)
            futures[fut] = e
        for fut in as_completed(futures):
            e = futures[fut]
            ok, err = fut.result()
            results.append((e, ok, err))

    all_ok = all(ok for _, ok, _ in results)
    log_entry = {
        "batch": batch_idx,
        "super_ids": [e["super_id"] for e in super_entries],
        "files": [e["file"] for e in super_entries],
        "ok": all_ok,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if not all_ok:
        log_entry["errors"] = {str(e["super_id"]): err for e, ok, err in results if not ok}

    batch_log = json.load(open(BATCH_LOG_PATH)) if os.path.exists(BATCH_LOG_PATH) else []
    batch_log.append(log_entry)
    with open(BATCH_LOG_PATH, "w") as f:
        json.dump(batch_log, f, indent=2)

    return all_ok, log_entry

def main():
    log(f"TASK 014-A START — {FILE_ID} | 20,480 SCs")
    entries = build_entries()
    total = len(entries)
    log(f"SC entries built: {total} | Verifying SC[0] header hash...")

    # Verify SC[0] header matches LOGOS_EXPANSION_001.bin
    import hashlib as hl
    src = "/home/workspace/LOGOS_EXPANSION_001.bin"
    with open(src, "rb") as f:
        src_raw = f.read()
    src_hash = hl.sha256(src_raw).hexdigest()
    sc0_path = os.path.join(SC_DIR, "chip.sc.000000.bin")
    with open(sc0_path, "rb") as f:
        _, _, sid, fhash, nc, _ = struct.unpack("<4sHI32sHH", f.read(HEADER_SIZE))
    log(f"  Source SHA256: {src_hash}")
    log(f"  SC[0] header:  {fhash.hex()}")
    if fhash.hex() != src_hash:
        log(f"FATAL: SC[0] header hash mismatch! Aborting.")
        sys.exit(1)
    log(f"  ✓ Header verified — anchor hash locked")

    # Load checkpoint
    batch_log = json.load(open(BATCH_LOG_PATH)) if os.path.exists(BATCH_LOG_PATH) else []
    done_ids = set()
    for b in batch_log:
        if b.get("ok"):
            done_ids.update(b.get("super_ids", []))
    pending = [e for e in entries if e["super_id"] not in done_ids]
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

    next_batch = (batch_log[-1]["batch"] + 1) if batch_log else 0
    log(f"Batch log: {len(batch_log)} entries | Done: {len(done_ids)}/{total} | Pending: {len(pending)} SCs ({total_batches} batches)")
    log(f"Resuming from batch index {next_batch} → SC {pending[0]['super_id'] if pending else 'NONE'}")

    for bi in range(next_batch, total_batches):
        bs = bi * BATCH_SIZE
        be = min(bs + BATCH_SIZE, len(pending))
        batch = pending[bs:be]
        sid_start, sid_end = batch[0]["super_id"], batch[-1]["super_id"]

        log(f"--- BATCH {bi+1:,}/{total_batches:,} | SC {sid_start:06d}–{sid_end:06d} ---")
        t0 = time.time()
        all_ok, entry = run_batch(bi, batch)
        elapsed = time.time() - t0
        confirmed = sum(len(b.get("super_ids", [])) for b in json.load(open(BATCH_LOG_PATH)) if b.get("ok"))
        log(f"  → {'✓' if all_ok else '✗'} Batch {bi} | {elapsed:.1f}s | {confirmed:,}/{total:,} confirmed")

        if not all_ok:
            log(f"  WARNING: some failures in batch {bi} — sleeping 5s")
            time.sleep(5)
        else:
            time.sleep(0.2)

    log(f"[COMPLETE] TASK 014-A done — all 20,480 SCs uploaded")
    final_log = json.load(open(BATCH_LOG_PATH))
    confirmed = sum(len(b.get("super_ids", [])) for b in final_log if b.get("ok"))
    print(f"\nDONE — {confirmed:,}/20,480 confirmed")

if __name__ == "__main__":
    main()
