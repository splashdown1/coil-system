#!/usr/local/bin/python3
"""
COIL Flat Uploader — Clean Slate
Sends raw 5120-byte slices via temp files. No COIL header. No struct math.
Server does: Buffer.concat + size/hash verify on /complete.
"""
import json, hashlib, os, sys, time, subprocess, tempfile

WORKSPACE      = "/home/workspace"
SC_DIR         = "/home/workspace/COIL_mirror/SC"
CHIP_FILE      = "COIL_MASTER_CHIP.json"
CHUNK_SIZE     = 5120          # 20 × 256 bytes per slice
UPLOAD_BATCH   = 20
SERVER_BASE    = "http://localhost:3000"
CHUNK_LOG      = os.path.join(SC_DIR, "COIL_CHUNK_LOG.json")

def source_slices(path):
    raw = open(path, "rb").read()
    for i in range(0, len(raw), CHUNK_SIZE):
        yield i // CHUNK_SIZE, raw[i:i+CHUNK_SIZE]

def upload_all(fileId, source_path, log_path):
    log = json.load(open(log_path)) if os.path.exists(log_path) else []
    done = {c["idx"] for c in log if c.get("ok")}
    slices = list(source_slices(source_path))
    total = len(slices)
    pending = [s for s in slices if s[0] not in done]
    print(f"[UPLOAD] {len(pending)}/{total} pending")

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, raw in pending:
            sha = hashlib.sha256(raw).hexdigest()
            tmpfile = os.path.join(tmpdir, f"chunk_{idx}")
            open(tmpfile, "wb").write(raw)

            cmd = [
                "curl", "-s", "--max-time", "20", "-X", "POST",
                "-H", f"x-file-id: {fileId}",
                "-H", f"x-chunk-index: {idx}",
                "-H", f"x-hash: {sha}",
                "-H", f"x-size: {len(raw)}",
                "-H", "Content-Type: application/octet-stream",
                "--data-binary", f"@{tmpfile}",
                f"{SERVER_BASE}/upload"
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
                resp = json.loads(r.stdout)
                ok = resp.get("ok", False)
            except:
                ok = False

            log.append({"idx": idx, "sha": sha, "ok": ok, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
            with open(log_path, "w") as f:
                json.dump(log, f, indent=2)
            done_count = sum(1 for c in log if c.get("ok"))
            print(f"  [{done_count}/{total}] {'✓' if ok else '✗'} idx={idx}")

    ok_total = sum(1 for c in log if c.get("ok"))
    return ok_total == total

def signal_complete(fileId, expected_hash, expected_size):
    body = {"originalExt": "json", "expectedHash": expected_hash, "expectedSize": expected_size}
    cmd = [
        "curl", "-s", "--max-time", "30", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", f"x-file-id: {fileId}",
        "-d", json.dumps(body),
        f"{SERVER_BASE}/complete"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        print(f"  /complete → {r.stdout}")
        return json.loads(r.stdout).get("ok", False)
    except Exception as ex:
        print(f"  /complete error: {ex}")
        return False

if __name__ == "__main__":
    source = os.path.join(WORKSPACE, CHIP_FILE)
    disk_hash = hashlib.sha256(open(source, "rb").read()).hexdigest()
    disk_size = os.path.getsize(source)
    print(f"SOURCE: {disk_size:,} bytes SHA256={disk_hash}")

    os.makedirs(SC_DIR, exist_ok=True)
    ok = upload_all(CHIP_FILE, source, CHUNK_LOG)
    if ok:
        signal_complete(CHIP_FILE, disk_hash, disk_size)
    else:
        print("[DONE] partial — re-run to retry")
