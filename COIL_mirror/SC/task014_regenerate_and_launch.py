#!/usr/bin/env python3
"""
TASK 014 — 100MB Stress Test: Regenerate SCs from LOGOS_EXPANSION_001.bin
Then launch uploader in background.
"""
import struct, hashlib, os, sys, time, json, subprocess

WORKSPACE     = "/home/workspace"
SC_DIR        = "/home/workspace/COIL_mirror/SC"
MANIFEST_PATH = "/home/workspace/COIL_MASTER_CHIP.json"
SOURCE_FILE   = "LOGOS_EXPANSION_001.bin"
CHUNK_SIZE    = 256
SUPER_PER_BATCH = 20

HEADER_FMT  = "<4sHI32sHH"
HEADER_SIZE = 46

def build_super_chunk(super_id, chunk_data_list, file_hash_bytes):
    n = len(chunk_data_list)
    hashes = b"".join(hashlib.sha256(d).digest() for d in chunk_data_list)
    payload = b"".join(chunk_data_list)
    header = struct.pack(HEADER_FMT, b"COIL", 1, super_id, file_hash_bytes, n, 0)
    return header + hashes + payload

def super_chunk_path(super_id):
    return os.path.join(SC_DIR, f"chip.sc.{super_id:06d}.bin")

def main():
    source_path = os.path.join(WORKSPACE, SOURCE_FILE)
    print(f"[IGNITION] Reading {source_path}")
    with open(source_path, "rb") as f:
        raw = f.read()

    file_size = len(raw)
    num_full_chunks = file_size // CHUNK_SIZE
    remainder = file_size % CHUNK_SIZE

    all_chunks = [raw[i*CHUNK_SIZE:(i+1)*CHUNK_SIZE] for i in range(num_full_chunks)]
    if remainder > 0:
        padded = raw[num_full_chunks*CHUNK_SIZE:] + b"\x00" * (CHUNK_SIZE - remainder)
        all_chunks.append(padded)

    num_total = len(all_chunks)
    num_super = (num_total + SUPER_PER_BATCH - 1) // SUPER_PER_BATCH
    source_hash = hashlib.sha256(raw).hexdigest()
    source_hash_bytes = bytes.fromhex(source_hash)

    print(f"  Source: {file_size:,} bytes | Hash: {source_hash}")
    print(f"  Chunks: {num_total:,} | Super-chunks: {num_super:,}")

    # Clear old SCs
    existing = sorted([f for f in os.listdir(SC_DIR) if f.startswith("chip.sc.")])
    print(f"  Clearing {len(existing):,} stale SC files …")
    for f in existing:
        os.remove(os.path.join(SC_DIR, f))

    # Generate new SCs
    print("  Generating new SCs …")
    super_entries = []
    for sid in range(num_super):
        start = sid * SUPER_PER_BATCH
        end   = min(start + SUPER_PER_BATCH, num_total)
        group = all_chunks[start:end]
        sc_data = build_super_chunk(sid, group, source_hash_bytes)
        with open(super_chunk_path(sid), "wb") as f:
            f.write(sc_data)
        super_entries.append({
            "super_id":    sid,
            "file":        f"chip.sc.{sid:06d}.bin",
            "size_bytes":  len(sc_data),
            "sha256":      hashlib.sha256(sc_data).hexdigest(),
            "num_chunks":  len(group),
            "chunk_range": [start, end - 1],
        })
        if sid > 0 and sid % 5000 == 0:
            print(f"    … {sid:,}/{num_super:,}")

    print(f"  ✓ {num_super:,} SCs written")

    # Verify SC[0]
    sc0_path = super_chunk_path(0)
    with open(sc0_path, "rb") as f:
        sc0_data = f.read()
    sc0_hash = hashlib.sha256(sc0_data).hexdigest()
    print(f"\n[VERIFY] SC[0] path: {sc0_path}")
    print(f"  Size: {len(sc0_data):,} bytes")
    print(f"  SHA256: {sc0_hash}")

    # Update manifest — point COIL_MASTER_CHIP.json to new source
    print("\n[MANIFEST] Updating COIL_MASTER_CHIP.json …")
    chip_file = "COIL_MASTER_CHIP.json"
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    chip_idx = next(i for i, e in enumerate(manifest["files"]) if e["filename"] == chip_file)
    old = manifest["files"][chip_idx]
    manifest["files"][chip_idx] = {
        "filename":          chip_file,
        "size_bytes":        file_size,
        "file_hash_sha256":  source_hash,
        "chunk_count":       num_total,
        "chunk_size":        CHUNK_SIZE,
        "super_chunk_count": num_super,
        "super_chunk_size":  SUPER_PER_BATCH,
        "delta_sync_id":     old.get("delta_sync_id", "ds-" + source_hash[:12]),
        "sync_status":       "in_progress",
        "sync_server":       "coil-sync-server-splashdown.zocomputer.io",
        "super_chunks":      super_entries,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  ✓ Manifest updated with {num_super:,} SCs")

    # Launch uploader
    print("\n[UPLOADER] Launching task014_safe_uploader.py …")
    upload_script = os.path.join(SC_DIR, "task014_safe_uploader.py")
    log_path = os.path.join(SC_DIR, "TASK014_UPLOAD.log")

    with open(upload_script, "w") as f:
        f.write(f'''#!/usr/bin/env python3
"""TASK 014 Safe Uploader — background process"""
import json, os, sys, time, subprocess

SC_DIR        = "{SC_DIR}"
MANIFEST_PATH = "{MANIFEST_PATH}"
UPLOAD_BATCH  = 20
SERVER_BASE   = "https://coil-sync-server-splashdown.zocomputer.io"
LOG_PATH      = "{log_path}"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{{ts}}] {{msg}}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\\n")

def main():
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    chip = next(e for e in manifest["files"] if e["filename"] == "COIL_MASTER_CHIP.json")
    scs = chip["super_chunks"]
    done_ids = set()

    log(f"START — {{len(scs):,}} SCs to upload")

    for bi in range(0, len(scs), UPLOAD_BATCH):
        batch = scs[bi:bi+UPLOAD_BATCH]
        all_ok = True
        for e in batch:
            sc_path = os.path.join(SC_DIR, e["file"])
            cmd = [
                "curl", "-s", "--max-time", "20",
                "-X", "POST",
                "-H", f"x-file-id: COIL_MASTER_CHIP.json",
                "-H", f"x-chunk-index: {{e['super_id']}}",
                "-H", f"x-hash: {{e['sha256']}}",
                "-H", "Content-Type: application/octet-stream",
                "--data-binary", f"@{{sc_path}}",
                f"{{SERVER_BASE}}/upload"
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
                resp = json.loads(r.stdout)
                ok = resp.get("ok", False)
            except Exception as ex:
                log(f"SC{{e['super_id']}} ERROR: {{ex}}")
                ok = False
            if not ok:
                all_ok = False

        done = sum(1 for b in done_ids)
        log(f"Batch {{bi//UPLOAD_BATCH+1}} → {{'OK' if all_ok else 'FAIL'}} | {{len(done_ids):,}}/{{len(scs):,}}")

    log(f"COMPLETE — {{len(done_ids):,}}/{{len(scs):,}} SCs uploaded")

if __name__ == "__main__":
    main()
''')

    os.chmod(upload_script, 0o755)
    log(f"UPLOADER SCRIPT written to {upload_script}")

    # Run in background
    pid = subprocess.Popen(
        ["python3", upload_script],
        stdout=open(log_path, "w"),
        stderr=subprocess.STDOUT,
        cwd=SC_DIR
    ).pid

    print(f"\n[LAUNCH] uploader PID={pid} | log: {log_path}")
    print(f"  Monitor: tail -f {log_path}")

if __name__ == "__main__":
    main()