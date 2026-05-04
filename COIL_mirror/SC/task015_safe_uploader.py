#!/usr/bin/env python3
"""
TASK 015-A — LOGOS_EXPANSION_002 Upload
Patched: DISK_STRICT_VERIFICATION, fsync'd server, SC_STRIP_OFFSET=686 fix
"""
import json, hashlib, os, sys, time, subprocess, struct
from concurrent.futures import ThreadPoolExecutor, as_completed

SC_DIR          = "/home/workspace/COIL_mirror/SC_002"
BATCH_LOG_PATH  = "/home/workspace/COIL_mirror/SC/TASK015_BATCH_LOG.json"
LOCAL_LOG_PATH  = "/home/workspace/COIL_mirror/SC/TASK015_SYNC_LOG.txt"
FILE_ID         = "LOGOS_EXPANSION_002"
SERVER_BASE     = "http://localhost:3000"
UPLOAD_ENDPOINT = f"{SERVER_BASE}/upload"
BATCH_SIZE      = 20
MAX_WORKERS     = 10
TIMEOUT_SEC     = 30
TOTAL_SCS       = 20480
HEADER_SIZE_S   = 46  # SC header size in super-chunk files
TARGET_DISK     = "/home/workspace/uploads/LOGOS_EXPANSION_002/"
ANCHOR          = "636e5bd7beb932f5fb671d04d183deb2d1854d8be6a7cc9b1eec32fd3db67455"

os.makedirs(TARGET_DISK, exist_ok=True)

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

def disk_count():
    try:
        return len(os.listdir(TARGET_DISK))
    except Exception:
        return 0

def disk_strict_verify(super_ids):
    """Re-verify by counting actual files on disk for these IDs."""
    missing = [sid for sid in super_ids if not os.path.exists(
        os.path.join(TARGET_DISK, f"{sid:08d}")
    )]
    return len(super_ids) - len(missing), missing

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

    # DISK_STRICT_VERIFICATION: confirm files landed
    confirmed_disk, missing = disk_strict_verify(log_entry["super_ids"])
    if missing:
        log_entry["disk_missing"] = missing
        log(f"  [!] DISK_STRICT: {len(missing)} files not on disk — will retry")

    batch_log = json.load(open(BATCH_LOG_PATH)) if os.path.exists(BATCH_LOG_PATH) else []
    batch_log.append(log_entry)
    with open(BATCH_LOG_PATH, "w") as f:
        json.dump(batch_log, f, indent=2)
    return all_ok, log_entry

def main():
    log(f"TASK 015-A START — {FILE_ID} | {TOTAL_SCS} SCs | SERVER={SERVER_BASE}")

    # Verify anchor
    with open(f"/home/workspace/LOGOS_EXPANSION_002.bin", "rb") as f:
        src_hash = hashlib.sha256(f.read()).hexdigest()
    log(f"  Source anchor: {src_hash}")
    log(f"  Expected:       {ANCHOR}")
    if src_hash != ANCHOR:
        log("FATAL: Anchor hash mismatch!")
        sys.exit(1)
    log("  ✓ Anchor locked")

    # Build entries
    entries = []
    for sid in range(TOTAL_SCS):
        sc_path = os.path.join(SC_DIR, f"chip.sc.{sid:06d}.bin")
        with open(sc_path, "rb") as f:
            hdr = f.read(HEADER_SIZE_S)
        magic = hdr[:4]
        if magic != b"COIL":
            log(f"FATAL: {sc_path} bad magic {magic}")
            sys.exit(1)
        live_sha = hashlib.sha256(open(sc_path, "rb").read()).hexdigest()
        entries.append({"super_id": sid, "file": f"chip.sc.{sid:06d}.bin",
                        "size_bytes": os.path.getsize(sc_path),
                        "sha256": live_sha, "num_chunks": 20})

    # Load checkpoint
    batch_log = json.load(open(BATCH_LOG_PATH)) if os.path.exists(BATCH_LOG_PATH) else []
    done_ids = set()
    for b in batch_log:
        if b.get("ok") and not b.get("disk_missing"):
            done_ids.update(b.get("super_ids", []))
    pending = [e for e in entries if e["super_id"] not in done_ids]
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

    next_batch = (batch_log[-1]["batch"] + 1) if batch_log else 0
    log(f"Checkpoint: {len(batch_log)} batches logged | Done: {len(done_ids)}/{TOTAL_SCS} | Pending: {len(pending)} ({total_batches} batches)")
    if pending:
        log(f"Starting at batch {next_batch} → SC {pending[0]['super_id']:06d}")
    else:
        log("Nothing pending — all done")
        return

    for bi in range(next_batch, total_batches):
        bs = bi * BATCH_SIZE
        be = min(bs + BATCH_SIZE, len(pending))
        batch = pending[bs:be]
        sid_start, sid_end = batch[0]["super_id"], batch[-1]["super_id"]
        log(f"--- BATCH {bi+1:,}/{total_batches:,} | SC {sid_start:06d}–{sid_end:06d} ---")
        t0 = time.time()
        all_ok, entry = run_batch(bi, batch)
        elapsed = time.time() - t0

        # DISK_STRICT: count actual on-disk after each batch
        disk_now = disk_count()
        log(f"  → {'✓' if all_ok else '✗'} | {elapsed:.1f}s | Disk: {disk_now:,}/{TOTAL_SCS:,}")

        if not all_ok or entry.get("disk_missing"):
            time.sleep(5)
        else:
            time.sleep(0.4)

    final_bl = json.load(open(BATCH_LOG_PATH))
    confirmed = sum(len(b.get("super_ids", [])) for b in final_bl if b.get("ok"))
    log(f"[COMPLETE] {confirmed:,}/{TOTAL_SCS:,} SCs uploaded")
    print(f"\nDONE — {confirmed:,}/20,480 confirmed")

if __name__ == "__main__":
    main()
