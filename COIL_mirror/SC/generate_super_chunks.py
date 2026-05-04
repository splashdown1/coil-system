#!/usr/local/bin/python3
"""
COIL Super-Chunk Generator & Batch Uploader
TASK 005 — Dog-aligned: <4sH4s32sHH (hash at byte 10, matches server)
  - Groups every 20 x 256-byte chunks into one binary super-chunk (.scbin)
  - FIXED: Hash at byte 10 (4s gap with 0f56414a padding) — server-compatible
  - Appends super-chunks to COIL_mirror/SC/
  - Anchors to PHYSICAL DISK BYTES of COIL_MASTER_CHIP.json (34MB Dog)
  - Streams uploads to coil-sync-server in batches of 20
  - Calls /complete after all uploads confirm
"""
import json, struct, hashlib, os, sys, time, urllib.request, urllib.error, subprocess

WORKSPACE        = "/home/workspace"
MIRROR_DIR       = "/home/workspace/COIL_mirror"
SC_DIR           = "/home/workspace/COIL_mirror/SC"
MANIFEST_PATH    = "/home/workspace/COIL_MASTER_CHIP.json"
CHUNK_SIZE       = 256
SUPER_PER_BATCH  = 20
UPLOAD_BATCH     = 20
SERVER_BASE      = "http://localhost:3000"
CHIP_FILE        = "COIL_MASTER_CHIP.json"

# FIXED format: <4sH4s32sHH = 46 bytes
#   MAGIC(4s) VERSION(H) GAP_PADDING(4s) FILE_HASH(32s) NUM_CHUNKS(H) RESERVED(H)
#   Hash is at byte 10 (struct offsets 0,2,6 = gap bytes go at byte 6)
HEADER_FMT   = "<4sH4s32sHH"
HEADER_SIZE  = 46
GAP_VALUE    = b"\x0f\x56\x41\x4a"  # server-expected padding in the 4s gap

def build_super_chunk(super_id, chunk_data_list, file_hash_bytes):
    n = len(chunk_data_list)
    hashes = b"".join(hashlib.sha256(d).digest() for d in chunk_data_list)
    payload = b"".join(chunk_data_list)
    header = struct.pack(HEADER_FMT, b"COIL", 1, GAP_VALUE, file_hash_bytes, n, 0)
    return header + hashes + payload

def super_chunk_path(super_id):
    return os.path.join(SC_DIR, f"chip.sc.{super_id:06d}.bin")

# ─── Phase 1: Generate super-chunks ────────────────────────────────────────────
def generate_super_chunks():
    print("[PHASE 1] Generating super-chunks …")
    os.makedirs(SC_DIR, exist_ok=True)

    # ANCHOR TO PHYSICAL DISK BYTES
    raw_path = os.path.join(WORKSPACE, CHIP_FILE)
    disk_bytes = open(raw_path, "rb").read()
    physical_hash = hashlib.sha256(disk_bytes).hexdigest()
    physical_hash_bytes = bytes.fromhex(physical_hash)
    file_size = len(disk_bytes)
    print(f"  PHYSICAL hash: {physical_hash}")
    print(f"  PHYSICAL size: {file_size:,} bytes")

    num_full_chunks = file_size // CHUNK_SIZE
    remainder = file_size % CHUNK_SIZE
    # FIX: append raw remainder bytes WITHOUT zero-padding
    # The server reads exact bytes via totalExpected, no padding needed
    all_chunks = [disk_bytes[i*CHUNK_SIZE:(i+1)*CHUNK_SIZE] for i in range(num_full_chunks)]
    if remainder > 0:
        all_chunks.append(disk_bytes[num_full_chunks*CHUNK_SIZE:])
    num_total = len(all_chunks)
    num_super = (num_total + SUPER_PER_BATCH - 1) // SUPER_PER_BATCH
    print(f"  → {num_total:,} × {CHUNK_SIZE}B chunks → {num_super:,} super-chunks")

    super_entries = []
    for sid in range(num_super):
        start = sid * SUPER_PER_BATCH
        end   = min(start + SUPER_PER_BATCH, num_total)
        group = all_chunks[start:end]
        sc_data = build_super_chunk(sid, group, physical_hash_bytes)
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
    return super_entries, physical_hash, file_size, num_total

# ─── Phase 2: Update manifest ────────────────────────────────────────────────
def update_manifest(super_entries, source_hash, file_size, num_chunks):
    print("[PHASE 2] Updating manifest …")
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    chip_idx = next(i for i, e in enumerate(manifest["files"]) if e["filename"] == CHIP_FILE)
    manifest["files"][chip_idx] = {
        "filename":          CHIP_FILE,
        "size_bytes":        file_size,
        "file_hash_sha256":  source_hash,
        "chunk_count":       num_chunks,
        "chunk_size":        CHUNK_SIZE,
        "super_chunk_count": len(super_entries),
        "super_chunk_size":  SUPER_PER_BATCH,
        "sync_status":       "in_progress",
        "super_chunks":     super_entries,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  ✓ Manifest updated")

# ─── Phase 3: Upload ─────────────────────────────────────────────────────────
def upload_super_chunks(super_entries, batch_log_path):
    print("[PHASE 3] Uploading …")
    import subprocess as sub, json as j

    batch_log = j.load(open(batch_log_path)) if os.path.exists(batch_log_path) else []
    done_ids = {sid for b in batch_log if b.get("ok") for sid in b.get("super_ids", [])}
    pending = [e for e in super_entries if e["super_id"] not in done_ids]
    total_batches = (len(pending) + UPLOAD_BATCH - 1) // UPLOAD_BATCH
    print(f"  Pending: {len(pending):,} in {total_batches:,} batches")

    for bi in range(total_batches):
        bs = bi * UPLOAD_BATCH
        be = min(bs + UPLOAD_BATCH, len(pending))
        batch = pending[bs:be]
        all_ok = True
        for e in batch:
            sc_path = super_chunk_path(e["super_id"])
            cmd = [
                "curl", "-s", "--max-time", "20", "-X", "POST",
                "-H", f"x-file-id: {CHIP_FILE}",
                "-H", f"x-chunk-index: {e['super_id']}",
                "-H", f"x-hash: {e['sha256']}",
                "-H", "Content-Type: application/octet-stream",
                "--data-binary", f"@{sc_path}",
                f"{SERVER_BASE}/upload"
            ]
            try:
                r = sub.run(cmd, capture_output=True, text=True, timeout=25)
                resp = j.loads(r.stdout)
                if not resp.get("ok"):
                    all_ok = False
            except:
                all_ok = False

        batch_log.append({"batch": bi, "super_ids": [e["super_id"] for e in batch], "ok": all_ok,
                         "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
        with open(batch_log_path, "w") as f:
            j.dump(batch_log, f, indent=2)
        done = sum(1 for b in batch_log if b["ok"])
        print(f"  Batch {bi+1:,}/{total_batches:,} → {'✓' if all_ok else '✗'} | {done:,}/{len(super_entries):,}")

    done = sum(1 for b in batch_log if b["ok"])
    return batch_log, done == len(super_entries)

# ─── Phase 4: Complete ─────────────────────────────────────────────────────
def signal_complete():
    import subprocess as sub
    cmd = ["curl", "-s", "--max-time", "20", "-X", "POST",
           "-H", "Content-Type: application/json",
           "-H", f"x-file-id: {CHIP_FILE}",
           "-d", json.dumps({"originalExt": "json"}),
           f"{SERVER_BASE}/complete"]
    try:
        r = sub.run(cmd, capture_output=True, text=True, timeout=25)
        print(f"  /complete: {r.stdout}")
    except Exception as ex:
        print(f"  /complete error: {ex}")

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
        print(f"\n[DONE] {done:,}/{len(chip['super_chunks']):,} uploaded")
        if all_done:
            signal_complete()
        else:
            print(f"[WARNING] {len(chip['super_chunks']) - done:,} failed — re-run upload to retry")
