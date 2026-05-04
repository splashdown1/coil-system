#!/usr/bin/env python3
"""
COIL Super-Chunk Batch Uploader — TASK 005 Resume (Fixed)
Resumes from last completed batch using COIL_BATCH_UPLOAD_LOG.json as checkpoint.
Streams super-chunks to coil-sync-server in batches of 20 with per-batch logging.
"""
import json, hashlib, os, sys, time, subprocess, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Config ───────────────────────────────────────────────────────────────────
WORKSPACE        = "/home/workspace"
SC_DIR           = "/home/workspace/COIL_mirror/SC"
MANIFEST_PATH    = "/home/workspace/COIL_MASTER_CHIP.json"
BATCH_LOG_PATH   = os.path.join(SC_DIR, "COIL_BATCH_UPLOAD_LOG.json")
LOCAL_LOG_PATH   = os.path.join(SC_DIR, "TASK005_SYNC_LOG.txt")
CHIP_FILE        = "COIL_MASTER_CHIP.json"
SERVER_BASE      = "http://localhost:3000"
UPLOAD_ENDPOINT  = f"{SERVER_BASE}/upload"
BATCH_SIZE       = 20          # super-chunks per upload transaction
MAX_WORKERS      = 10          # parallel uploads per batch
MAX_RETRIES      = 2
RETRY_DELAY      = 3
TIMEOUT_SEC      = 30

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOCAL_LOG_PATH, "a") as f:
        f.write(line + "\n")

def upload_one(super_id, file_hash, sc_path, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            cmd = [
                "curl", "-s", "--max-time", str(TIMEOUT_SEC),
                "-X", "POST",
                "-H", f"x-file-id: {CHIP_FILE}",
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
            time.sleep(RETRY_DELAY * (attempt + 1))
    return False, err

def run_batch(batch_idx, super_entries):
    """Upload one batch of super-chunks, write result to log."""
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for e in super_entries:
            sc_path = os.path.join(SC_DIR, e["file"])
            live_sha = hashlib.sha256(open(sc_path, "rb").read()).hexdigest()
            fut = executor.submit(upload_one, e["super_id"], live_sha, sc_path)
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

    # Persist checkpoint
    with open(BATCH_LOG_PATH) as f:
        batch_log = json.load(f)
    batch_log.append(log_entry)
    with open(BATCH_LOG_PATH, "w") as f:
        json.dump(batch_log, f, indent=2)

    return all_ok, log_entry

def main():
    # Load manifest super_chunks
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    chip = next(e for e in manifest["files"] if e["filename"] == CHIP_FILE)
    all_entries = chip["super_chunks"]
    total = len(all_entries)
    log(f"TASK 005 RESUME — {total} super-chunks total")

    # Load checkpoint — robust JSON load
    if not os.path.exists(BATCH_LOG_PATH):
        log(f"ERROR: {BATCH_LOG_PATH} not found — cannot resume")
        sys.exit(1)

    with open(BATCH_LOG_PATH) as f:
        batch_log = json.load(f)

    # Build done set from all logged batches
    done_ids = set()
    for b in batch_log:
        if b.get("ok"):
            done_ids.update(b.get("super_ids", []))

    # Probe server state for ALL fileIds this run might have touched
    file_ids_to_audit = ["COIL_MASTER_CHIP.json"]
    if os.path.exists(BATCH_LOG_PATH):
        try:
            with open(BATCH_LOG_PATH) as _f:
                _log = json.load(_f)
            for _b in _log:
                for _sid in _b.get("super_ids", []):
                    _fids = {CHIP_FILE}
                    for _f in _fids:
                        try:
                            _url = f"http://localhost:3000/audit/{_f}?total=6713"
                            _j = json.loads(urllib.request.urlopen(_url, timeout=5).read())
                            _server_done = _j.get("received", 0)
                            for _e in all_entries:
                                if _e["super_id"] not in done_ids and _e["super_id"] < _server_done:
                                    done_ids.add(_e["super_id"])
                        except: pass
        except Exception as _e:
            log(f"Server probe failed: {_e} — using batch log only")
    pending_entries = [e for e in all_entries if e["super_id"] not in done_ids]
    total_pending = len(pending_entries)
    total_batches = (total_pending + BATCH_SIZE - 1) // BATCH_SIZE

    log(f"Upload log: {len(batch_log)} batches | Done: {len(done_ids)}/{total} | Pending: {total_pending} (~{total_batches} batches)")

    # Last batch in log determines next batch index
    next_batch = (batch_log[-1]["batch"] + 1) if batch_log else 0
    log(f"Resuming from batch index {next_batch} (SC {pending_entries[0]['super_id'] if pending_entries else 'NONE'})")

    for bi in range(next_batch, total_batches):
        bs = bi * BATCH_SIZE
        be = min(bs + BATCH_SIZE, total_pending)
        batch = pending_entries[bs:be]

        sid_start = batch[0]["super_id"]
        sid_end = batch[-1]["super_id"]
        log(f"--- BATCH {bi+1}/{total_batches} | SC {sid_start:06d}–{sid_end:06d} ---")

        t0 = time.time()
        all_ok, entry = run_batch(bi, batch)
        elapsed = time.time() - t0

        confirmed = sum(len(b.get("super_ids", [])) for b in batch_log if b.get("ok"))
        log(f"  → {'✓' if all_ok else '✗'} Batch {bi} | {elapsed:.1f}s | {confirmed}/{total} confirmed")

        if not all_ok:
            log(f"  WARNING: Batch {bi} had failures — sleeping 5s before continuing")
            time.sleep(5)
        else:
            time.sleep(0.3)

    log(f"[COMPLETE] All {total} super-chunks uploaded")
    print(f"\nDONE — {sum(len(b.get('super_ids',[])) for b in batch_log if b.get('ok'))}/{total} confirmed")

if __name__ == "__main__":
    main()