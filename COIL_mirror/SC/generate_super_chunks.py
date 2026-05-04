#!/usr/local/bin/python3
"""
COIL Super-Chunk Generator & Batch Uploader
TASK 005 — Fixed: uses localhost to avoid 403 tunnel errors
  - Groups every 20 x 256-byte chunks into one binary super-chunk (.scbin)
  - Appends super-chunks to COIL_mirror/SC/
  - Updates COIL_MASTER_CHIP.json manifest
  - Streams uploads to coil-sync-server in batches of 20
  - Calls /complete after all uploads confirm
"""
import json, struct, hashlib, os, sys, time, urllib.request, urllib.error, subprocess
# ─── Config ───────────────────────────────────────────────────────────────────
WORKSPACE        = "/home/workspace"
MIRROR_DIR       = "/home/workspace/COIL_mirror"
SC_DIR          = "/home/workspace/COIL_mirror/SC"
MANIFEST_PATH   = "/home/workspace/COIL_MASTER_CHIP.json"
CHUNK_SIZE      = 256          # bytes per input chunk
SUPER_PER_BATCH = 20           # chunks per super-chunk
UPLOAD_BATCH    = 20           # super-chunks per upload transaction
SERVER_BASE     = "http://localhost:3000"   # ← fixed: localhost avoids 403 tunnel errors
UPLOAD_ENDPOINT = f"{SERVER_BASE}/upload"
COMPLETE_ENDPOINT = f"{SERVER_BASE}/complete"
MAX_RETRIES     = 3
RETRY_DELAY     = 2            # seconds
CHIP_FILE       = "COIL_MASTER_CHIP.json"

# Super-chunk binary format (all little-endian, 46 header bytes):
#   MAGIC(4s) VERSION(H) SUPER_ID(I) FILE_HASH(32s) NUM_CHUNKS(H) RESERVED(H)
HEADER_FMT = "<4sHI32sHH"  # 46 bytes: 4+2+4+32+2+2
HEADER_SIZE = 46  # 4+2+4+32+2+2

def build_super_chunk(super_id, chunk_data_list, file_hash_bytes):
    n = len(chunk_data_list)
    hashes = b"".join(hashlib.sha256(d).digest() for d in chunk_data_list)
    payload = b"".join(chunk_data_list)
    header = struct.pack(HEADER_FMT,
        b"COIL",
        1,
        super_id,
        file_hash_bytes,
        n,
        0
    )
    return header + hashes + payload

def super_chunk_path(super_id):
    return os.path.join(SC_DIR, f"chip.sc.{super_id:06d}.bin")

# ─── Phase 1: Generate super-chunks ────────────────────────────────────────────
def generate_super_chunks():
    print("[PHASE 1] Generating super-chunks from COIL_MASTER_CHIP.json …")
    os.makedirs(SC_DIR, exist_ok=True)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    chip_entry = next(e for e in manifest["files"] if e["filename"] == CHIP_FILE)
    source_hash = chip_entry["file_hash_sha256"]
    source_hash_bytes = bytes.fromhex(source_hash)

    raw = open(os.path.join(WORKSPACE, CHIP_FILE), "rb").read()
    file_size = len(raw)
    num_full_chunks = file_size // CHUNK_SIZE
    remainder = file_size % CHUNK_SIZE

    all_chunks = [raw[i*CHUNK_SIZE:(i+1)*CHUNK_SIZE] for i in range(num_full_chunks)]
    if remainder > 0:
        padded = raw[num_full_chunks*CHUNK_SIZE:] + b"\x00" * (CHUNK_SIZE - remainder)
        all_chunks.append(padded)
    num_total = len(all_chunks)
    num_super = (num_total + SUPER_PER_BATCH - 1) // SUPER_PER_BATCH

    print(f"  Source: {file_size:,} bytes → {num_total:,} × {CHUNK_SIZE}B chunks → {num_super:,} super-chunks")

    super_entries = []
    for sid in range(num_super):
        start = sid * SUPER_PER_BATCH
        end   = min(start + SUPER_PER_BATCH, num_total)
        group = all_chunks[start:end]
        sc_data = build_super_chunk(sid, group, source_hash_bytes)
        with open(super_chunk_path(sid), "wb") as f:
            f.write(sc_data)
        super_entries.append({
            "super_id":   sid,
            "file":       f"chip.sc.{sid:06d}.bin",
            "size_bytes": len(sc_data),
            "sha256":     hashlib.sha256(sc_data).hexdigest(),
            "num_chunks": len(group),
            "chunk_range": [start, end - 1],
        })
        if sid > 0 and sid % 1000 == 0:
            print(f"  … {sid:,}/{num_super:,} written")
    print(f"  ✓ {num_super:,} super-chunks → {SC_DIR}/")
    return super_entries, source_hash, file_size, num_total

# ─── Phase 2: Update manifest ────────────────────────────────────────────────
def update_manifest(super_entries, source_hash, file_size, num_chunks):
    print("[PHASE 2] Updating COIL_MASTER_CHIP.json …")
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    chip_idx = next(i for i, e in enumerate(manifest["files"]) if e["filename"] == CHIP_FILE)
    old = manifest["files"][chip_idx]
    manifest["files"][chip_idx] = {
        "filename":          CHIP_FILE,
        "size_bytes":        file_size,
        "file_hash_sha256":  source_hash,
        "chunk_count":       num_chunks,
        "chunk_size":        CHUNK_SIZE,
        "super_chunk_count": len(super_entries),
        "super_chunk_size":  SUPER_PER_BATCH,
        "delta_sync_id":     old.get("delta_sync_id", "ds-" + source_hash[:12]),
        "sync_status":       "in_progress",
        "sync_server":       "coil-sync-server-splashdown.zocomputer.io",
        "super_chunks":     super_entries,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  ✓ Manifest saved with {len(super_entries):,} super-chunks")

# ─── Phase 3: Upload (curl, localhost, batch confirmation) ──────────────────
def upload_super_chunks(super_entries, batch_log_path):
    print("[PHASE 3] Uploading super-chunks to server …")
    import subprocess, json as _json

    batch_log = _json.load(open(batch_log_path)) if os.path.exists(batch_log_path) else []
    done_ids = set()
    for b in batch_log:
        if b.get("ok"):
            for sid in b.get("super_ids", []):
                done_ids.add(sid)

    pending = [e for e in super_entries if e["super_id"] not in done_ids]
    total_batches = (len(pending) + UPLOAD_BATCH - 1) // UPLOAD_BATCH
    print(f"  Pending: {len(pending):,} super-chunks in {total_batches:,} batches | Already done: {len(done_ids):,}")

    for bi in range(total_batches):
        bs = bi * UPLOAD_BATCH
        be = min(bs + UPLOAD_BATCH, len(pending))
        batch = pending[bs:be]

        all_ok = True
        for e in batch:
            sc_path = super_chunk_path(e["super_id"])
            sha = e["sha256"]
            idx = e["super_id"]
            cmd = [
                "curl", "-s", "--max-time", "20",
                "-X", "POST",
                "-H", f"x-file-id: {CHIP_FILE}",
                "-H", f"x-chunk-index: {idx}",
                "-H", f"x-hash: {sha}",
                "-H", "Content-Type: application/octet-stream",
                "--data-binary", f"@{sc_path}",
                f"{SERVER_BASE}/upload"
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
                resp = _json.loads(result.stdout)
                ok = resp.get("ok", False)
            except Exception as ex:
                print(f"  Batch {bi} SC{e['super_id']} error: {ex}")
                ok = False
            if not ok:
                all_ok = False

        batch_log.append({
            "batch":     bi,
            "super_ids": [e["super_id"] for e in batch],
            "files":     [e["file"] for e in batch],
            "ok":        all_ok,
            "ts":        time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        with open(batch_log_path, "w") as f:
            _json.dump(batch_log, f, indent=2)

        done = sum(1 for b in batch_log if b["ok"])
        print(f"  Batch {bi+1:,}/{total_batches:,} → {'✓' if all_ok else '✗'} | {done:,}/{len(super_entries):,} confirmed")

    done = sum(1 for b in batch_log if b["ok"])
    return batch_log, done == len(super_entries)

# ─── Phase 4: Signal complete ───────────────────────────────────────────────
def signal_complete():
    print("[PHASE 4] Signaling /complete to server …")
    cmd = [
        "curl", "-s", "--max-time", "20",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", f"x-file-id: {CHIP_FILE}",
        "-d", json.dumps({"originalExt": "json", "totalExpected": 1}),
        f"{SERVER_BASE}/complete"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        resp = json.loads(result.stdout)
        print(f"  /complete response: {resp}")
        return resp.get("ok", False)
    except Exception as ex:
        print(f"  /complete error: {ex}")
        return False

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    batch_log_path = os.path.join(SC_DIR, "COIL_BATCH_UPLOAD_LOG.json")

    if phase in ("all", "generate"):
        se, sh, fs, nc = generate_super_chunks()
        update_manifest(se, sh, fs, nc)

    if phase in ("all", "upload"):
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        chip = next(e for e in manifest["files"] if e["filename"] == CHIP_FILE)
        bl, all_done = upload_super_chunks(chip["super_chunks"], batch_log_path)
        done = sum(1 for b in bl if b["ok"])
        print(f"\n[DONE] {done:,}/{len(chip['super_chunks']):,} super-chunks uploaded")

        if all_done:
            signal_complete()
        else:
            print(f"[WARNING] {len(chip['super_chunks']) - done:,} batches failed. Re-run upload to retry.")
