#!/usr/bin/env python3
"""
TASK 015-A — LOGOS_EXPANSION_002 Upload
DISK_STRICT_VERIFICATION: count on-disk after every batch
Server: localhost:3000 (fsync'd, SC_STRIP_OFFSET=686 patched)
"""
import json, hashlib, os, sys, time, subprocess, struct

SC_DIR         = "/home/workspace/COIL_mirror/SC_002"
BATCH_LOG_PATH = "/home/workspace/COIL_mirror/SC_002/TASK015_BATCH_LOG.json"
LOCAL_LOG_PATH = "/home/workspace/COIL_mirror/SC_002/TASK015_SYNC_LOG.txt"
FILE_ID        = "LOGOS_EXPANSION_002"
ANCHOR         = "a8c5cac1fb537de94e740455e99f7b60499a984b65dba6237a4d45942fa1346c"
SERVER_BASE    = "http://localhost:3000"
UPLOAD_ENDPOINT = f"{SERVER_BASE}/upload"
BATCH_SIZE     = 20
MAX_WORKERS    = 1
TIMEOUT_SEC    = 30
TOTAL_SCS      = 20480
HEADER_SIZE    = 46

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

def disk_strict_count(super_ids):
    """Count how many of these super_ids are actually on disk (not server mem)."""
    disk_dir = f"/home/workspace/uploads/{FILE_ID}"
    return sum(1 for sid in super_ids if os.path.exists(os.path.join(disk_dir, f"{sid:08d}")))

def build_entries():
    entries = []
    for sid in range(TOTAL_SCS):
        sc_path = os.path.join(SC_DIR, f"chip.sc.{sid:06d}.bin")
        with open(sc_path, "rb") as f:
            hdr = f.read(HEADER_SIZE)
        magic, ver, s_id, fhash, nc, rsv = struct.unpack("<4sHI32sHH", hdr)
        if magic != b"COIL":
            log(f"FATAL: {sc_path} bad magic {magic}")
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
    for e in super_entries:
        sc_path = os.path.join(SC_DIR, e["file"])
        ok, err = upload_one(e["super_id"], e["sha256"], sc_path)
        results.append((e, ok, err))

    all_ok = all(ok for _, ok, _ in results)
    super_ids = [e["super_id"] for e in super_entries]

    log_entry = {
        "batch": batch_idx,
        "super_ids": super_ids,
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

    # DISK_STRICT_VERIFICATION: count actual on-disk chunks, not server mem
    disk_count = disk_strict_count(super_ids)
    expected = len(super_ids)
    if disk_count < expected:
        log(f"  ⚠ DISK LAG: {disk_count}/{expected} on disk — server may be dropping writes")

    return all_ok, log_entry

def main():
    log(f"TASK 015-A START — {FILE_ID} | {TOTAL_SCS} SCs | SERVER={SERVER_BASE}")

    src = "/home/workspace/LOGOS_EXPANSION_002.bin"
    with open(src, "rb") as f:
        src_hash = hashlib.sha256(f.read()).hexdigest()
    log(f"  Source anchor: {src_hash}")
    if src_hash != ANCHOR:
        log(f"  FATAL: Anchor mismatch! Expected {ANCHOR}")
        sys.exit(1)
    log("  ✓ Anchor hash locked")

    entries = build_entries()
    total = len(entries)

    batch_log = json.load(open(BATCH_LOG_PATH)) if os.path.exists(BATCH_LOG_PATH) else []
    done_ids = set()
    for b in batch_log:
        if b.get("ok"):
            done_ids.update(b.get("super_ids", []))
    pending = [e for e in entries if e["super_id"] not in done_ids]
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

    next_batch = (batch_log[-1]["batch"] + 1) if batch_log else 0
    log(f"Checkpoint: {len(batch_log)} batches | Done: {len(done_ids)}/{total} | Pending: {len(pending)} ({total_batches} batches)")
    if pending:
        log(f"Starting at batch {next_batch} → SC {pending[0]['super_id']}")
    else:
        log("All chunks already uploaded.")

    for bi in range(next_batch, total_batches):
        bs = bi * BATCH_SIZE
        be = min(bs + BATCH_SIZE, len(pending))
        batch = pending[bs:be]
        sid_start, sid_end = batch[0]["super_id"], batch[-1]["super_id"]

        log(f"--- BATCH {bi+1:,}/{total_batches:,} | SC {sid_start:06d}–{sid_end:06d} ---")
        t0 = time.time()
        all_ok, entry = run_batch(bi, batch)
        elapsed = time.time() - t0

        with open(BATCH_LOG_PATH) as f:
            cur_log = json.load(f)
        log_confirmed = sum(len(b.get("super_ids", [])) for b in cur_log if b.get("ok"))
        disk_confirmed = len(os.listdir(f"/home/workspace/uploads/{FILE_ID}"))
        log(f"  → {'✓' if all_ok else '✗'} | {elapsed:.1f}s | Log:{log_confirmed:,} Disk:{disk_confirmed:,}/{total:,}")
        if not all_ok:
            time.sleep(5)
        else:
            time.sleep(0.3)

    final_bl = json.load(open(BATCH_LOG_PATH))
    confirmed = sum(len(b.get("super_ids", [])) for b in final_bl if b.get("ok"))
    disk_final = len(os.listdir(f"/home/workspace/uploads/{FILE_ID}"))
    log(f"[COMPLETE] {confirmed:,}/{total:,} logged | {disk_final:,}/{total:,} on disk")
    print(f"\nDONE — {disk_final:,}/20,480 on disk")

if __name__ == "__main__":
    main()
