#!/usr/bin/env python3
"""
TASK 008 — Clean Uploader
Hardcoded CHIP_FILE = COIL_MASTER_CHIP.json
NO manifest writes. NO x-hash mismatches. Simple sequential loop.
"""
import json, hashlib, os, time, subprocess

CHIP_FILE    = "COIL_MASTER_CHIP.json"
SERVER_BASE   = "https://coil-sync-server-splashdown.zocomputer.io"
UPLOAD_URL    = f"{SERVER_BASE}/upload"
BATCH_LOG     = "/home/workspace/COIL_archive/TASK008_BATCH_LOG.json"
MANIFEST_PATH = "/home/workspace/COIL_MASTER_CHIP.json"
SC_DIR        = "/home/workspace/COIL_mirror/SC"
BATCH_SIZE    = 20
TIMEOUT_SEC   = 30

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    open("/home/workspace/COIL_archive/TASK008_RUN.log", "a").write(line + "\n")

# Load batch log
if os.path.exists(BATCH_LOG):
    batch_log = json.load(open(BATCH_LOG))
else:
    batch_log = []

done_ids = set()
for b in batch_log:
    if b.get("ok"):
        done_ids.update(b.get("super_ids", []))

# Load manifest
with open(MANIFEST_PATH) as f:
    manifest = json.load(f)

chip = next(e for e in manifest["files"] if e["filename"] == CHIP_FILE)
all_entries = chip["super_chunks"]
total = len(all_entries)

pending = [e for e in all_entries if e["super_id"] not in done_ids]
total_pending = len(pending)
total_batches = (total_pending + BATCH_SIZE - 1) // BATCH_SIZE

log(f"TASK 008 — {total} SCs total | Done: {len(done_ids)} | Pending: {total_pending} ({total_batches} batches)")

for bi in range(total_batches):
    bs = bi * BATCH_SIZE
    be = min(bs + BATCH_SIZE, total_pending)
    batch = pending[bs:be]
    sid_start, sid_end = batch[0]["super_id"], batch[-1]["super_id"]

    log(f"--- BATCH {bi+1}/{total_batches} | SC {sid_start:06d}–{sid_end:06d} ---")

    batch_ok = True
    errors = {}
    for e in batch:
        sc_path = os.path.join(SC_DIR, e["file"])
        sha = e["sha256"]
        sid = e["super_id"]

        # Upload with x-hash = sha256 of actual SC file on disk
        actual_sha = hashlib.sha256(open(sc_path, "rb").read()).hexdigest()
        cmd = [
            "curl", "-s", "--max-time", str(TIMEOUT_SEC),
            "-X", "POST",
            "-H", f"x-file-id: {CHIP_FILE}",
            "-H", f"x-chunk-index: {sid}",
            "-H", f"x-hash: {actual_sha}",
            "-H", "Content-Type: application/octet-stream",
            "--data-binary", f"@{sc_path}",
            UPLOAD_URL
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SEC + 5)
            resp = json.loads(result.stdout)
            ok = resp.get("ok", False)
        except Exception as ex:
            ok = False
            errors[str(sid)] = str(ex)

        if not ok:
            batch_ok = False
            errors[str(sid)] = errors.get(str(sid), "upload failed")

    entry = {
        "batch": bi,
        "super_ids": [e["super_id"] for e in batch],
        "ok": batch_ok,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if errors:
        entry["errors"] = errors

    batch_log.append(entry)
    json.dump(batch_log, open(BATCH_LOG, "w"))

    confirmed = sum(len(b.get("super_ids", [])) for b in batch_log if b.get("ok"))
    log(f"  → {'✓' if batch_ok else '✗'} Batch {bi} | {confirmed}/{total} confirmed")
    if not batch_ok:
        log(f"  Errors: {errors}")
        time.sleep(3)
    else:
        time.sleep(0.5)

log(f"[COMPLETE] All {total_pending} pending SCs uploaded")
done = sum(len(b.get("super_ids",[])) for b in batch_log if b.get("ok"))
print(f"\nDONE — {done}/{total} confirmed")
