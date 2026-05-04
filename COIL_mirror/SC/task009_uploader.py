#!/usr/bin/env python3
"""
TASK 009 — Clean Uploader (localhost-only, no retry spam)
"""
import json, struct, hashlib, os, time, subprocess

WORKSPACE    = "/home/workspace"
SC_DIR       = f"{WORKSPACE}/COIL_mirror/SC"
CHIP_FILE    = "COIL_MASTER_CHIP.json"
SERVER       = "http://localhost:3000"
BATCH_LOG    = f"{SC_DIR}/COIL_BATCH_UPLOAD_LOG.json"
LOCAL_LOG    = f"{SC_DIR}/TASK009_SYNC_LOG.txt"
BATCH_SIZE   = 20

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOCAL_LOG, "a") as f:
        f.write(line + "\n")

def upload_one(sc_id, sha, sc_path):
    cmd = [
        "curl", "-s", "--max-time", "12",
        "-X", "POST",
        "-H", f"x-file-id: {CHIP_FILE}",
        "-H", f"x-chunk-index: {sc_id}",
        "-H", f"x-hash: {sha}",
        "-H", "Content-Type: application/octet-stream",
        "--data-binary", f"@{sc_path}",
        f"{SERVER}/upload"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    try:
        return json.loads(r.stdout).get("ok", False)
    except:
        return False

def run():
    # Load manifest
    manifest = json.load(open(f"{WORKSPACE}/COIL_MASTER_CHIP.json"))
    chip = next(e for e in manifest["files"] if e["filename"] == CHIP_FILE)
    entries = chip["super_chunks"]
    total = len(entries)
    log(f"TASK 009 START — {total} SCs")

    # Load checkpoint
    batch_log = json.load(open(BATCH_LOG)) if os.path.exists(BATCH_LOG) else []
    done = set()
    for b in batch_log:
        if b.get("ok"):
            done.update(b.get("super_ids", []))

    pending = [e for e in entries if e["super_id"] not in done]
    pending_count = len(pending)
    total_batches = (pending_count + BATCH_SIZE - 1) // BATCH_SIZE
    log(f"Done: {len(done)}/{total} | Pending: {pending_count} (~{total_batches} batches)")

    next_batch = (batch_log[-1]["batch"] + 1) if batch_log else 0

    for bi in range(next_batch, total_batches):
        bs = bi * BATCH_SIZE
        be = min(bs + BATCH_SIZE, pending_count)
        batch = pending[bs:be]
        sid_start = batch[0]["super_id"]
        sid_end = batch[-1]["super_id"]
        log(f"--- BATCH {bi+1}/{total_batches} | SC {sid_start:06d}–{sid_end:06d} ---")

        t0 = time.time()
        results = []
        for e in batch:
            ok = upload_one(e["super_id"], e["sha256"], f"{SC_DIR}/chip.sc.{e['super_id']:06d}.bin")
            results.append((e["super_id"], ok))

        elapsed = time.time() - t0
        ok_ids = [sid for sid, ok in results if ok]
        all_ok = len(ok_ids) == len(batch)
        ok_count = len(ok_ids)

        batch_record = {"batch": bi, "super_ids": [e["super_id"] for e in batch], "ok": all_ok, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        batch_log.append(batch_record)
        with open(BATCH_LOG, "w") as f:
            json.dump(batch_log, f, indent=2)

        rate = ok_count / elapsed if elapsed > 0 else 0
        log(f"  → {'✓' if all_ok else '✗'} {ok_count}/{len(batch)} | {elapsed:.1f}s ({rate:.1f} SC/s)")
        time.sleep(0.5)

    total_done = sum(len(b.get("super_ids", [])) for b in batch_log if b.get("ok"))
    log(f"[COMPLETE] {total_done}/{total} SCs confirmed")

if __name__ == "__main__":
    run()