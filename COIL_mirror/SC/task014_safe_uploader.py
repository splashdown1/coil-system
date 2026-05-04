#!/usr/bin/env python3
"""
TASK 014-A Safe Uploader — LOGOS_EXPANSION_001.bin (100MB, 20480 SCs)
Fixed: uploads to LOGOS_EXPANSION_001.bin (not COIL_MASTER_CHIP.json)
Uses existing chip.sc.*.bin files — does NOT regenerate
"""
import json, hashlib, os, sys, time, subprocess, struct
from concurrent.futures import ThreadPoolExecutor, as_completed

SC_DIR         = "/home/workspace/COIL_mirror/SC"
BATCH_LOG_PATH = "/home/workspace/COIL_mirror/SC/TASK014_BATCH_LOG.json"
LOCAL_LOG_PATH = "/home/workspace/COIL_mirror/SC/TASK014_SYNC_LOG.txt"
FILE_ID        = "LOGOS_EXPANSION_001.bin"
SERVER_BASE    = "http://localhost:3000"
UPLOAD_ENDPOINT = f"{SERVER_BASE}/upload"
BATCH_SIZE     = 20
MAX_WORKERS    = 10
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

def disk_count_for_batch(super_ids):
    """Count how many of these super_ids have a chunk file on disk (server-side upload dir)."""
    chunk_dir = f"/home/workspace/uploads/{FILE_ID}"
    return sum(1 for sid in super_ids if os.path.exists(os.path.join(chunk_dir, f"{sid:08d}")))

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

    # ── DISK STRICT VERIFICATION ──────────────────────────────────────────
    # Trust no HTTP response. Trust the filesystem.
    super_ids = [e["super_id"] for e in super_entries]
    disk_count = disk_count_for_batch(super_ids)
    if disk_count < len(super_ids):
        missing = [sid for sid in super_ids if not os.path.exists(
            os.path.join(f"/home/workspace/uploads/{FILE_ID}", f"{sid:08d}"))]
        log(f"  ⚠ Disk short — expected {len(super_ids)}, got {disk_count}. Re-sending {len(missing)} missing.")
        for e in super_entries:
            if e["super_id"] in missing:
                sc_path = os.path.join(SC_DIR, e["file"])
                ok, err = upload_one(e["super_id"], e["sha256"], sc_path)
                if ok:
                    disk_count += 1
                else:
                    log(f"  ⚠ Re-send failed for SC {e['super_id']}: {err}")
        # Final check
        disk_count = disk_count_for_batch(super_ids)
        all_ok = disk_count == len(super_ids)
    # ── END DISK VERIFICATION ─────────────────────────────────────────────

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

    return all_ok, log_entry

def main():
    log(f"TASK 014-A START — {FILE_ID} | {TOTAL_SCS} SCs | SERVER={SERVER_BASE}")

    # Anchor hash verification
    src = "/home/workspace/LOGOS_EXPANSION_001.bin"
    with open(src, "rb") as f:
        src_hash = hashlib.sha256(f.read()).hexdigest()
    sc0_path = os.path.join(SC_DIR, "chip.sc.000000.bin")
    with open(sc0_path, "rb") as f:
        _, _, _, fhash, _, _ = struct.unpack("<4sHI32sHH", f.read(HEADER_SIZE))
    log(f"  Anchor: {src_hash}")
    log(f"  SC[0] header: {fhash.hex()}")
    if fhash.hex() != src_hash:
        log("FATAL: Anchor hash mismatch!")
        sys.exit(1)
    log("  ✓ Anchor hash locked")

    entries = build_entries()
    total = len(entries)

    # Load checkpoint
    batch_log = json.load(open(BATCH_LOG_PATH)) if os.path.exists(BATCH_LOG_PATH) else []
    done_ids = set()
    for b in batch_log:
        if b.get("ok"):
            done_ids.update(b.get("super_ids", []))
    pending = [e for e in entries if e["super_id"] not in done_ids]
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

    next_batch = (batch_log[-1]["batch"] + 1) if batch_log else 0
    log(f"Checkpoint: {len(batch_log)} batches logged | Done: {len(done_ids)}/{total} | Pending: {len(pending)} ({total_batches} batches)")
    log(f"Starting at batch {next_batch} → SC {pending[0]['super_id'] if pending else 'ALL DONE'}")

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
        confirmed = sum(len(b.get("super_ids", [])) for b in cur_log if b.get("ok"))
        log(f"  → {'✓' if all_ok else '✗'} | {elapsed:.1f}s | {confirmed:,}/{total:,} confirmed")

        if not all_ok:
            time.sleep(5)
        else:
            time.sleep(0.2)

    final_bl = json.load(open(BATCH_LOG_PATH))
    confirmed = sum(len(b.get("super_ids", [])) for b in final_bl if b.get("ok"))
    log(f"[COMPLETE] {confirmed:,}/{total:,} SCs uploaded")
    print(f"\nDONE — {confirmed:,}/20,480 confirmed")

if __name__ == "__main__":
    main()
