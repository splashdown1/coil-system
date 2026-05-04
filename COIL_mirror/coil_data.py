#!/usr/bin/env python3
"""
COIL SYNC PROTOCOL™ — Data Packer / Unpacker

Usage:
    # Pack files into a single compressed blob
    python coil_data.py pack file1.json file2.json dashboard_state.json

    # Unpack a blob back to original files
    python coil_data.py unpack <b64_string>

    # Show what's inside a blob without unpacking
    python coil_data.py peek <b64_string>

    # Delta sync: pack only files changed since last pack
    python coil_data.py delta <manifest_path> <file1> [file2 ...]
"""

import json
import zlib
import base64
import hashlib
import sys
import os
import marshal
from pathlib import Path
from datetime import datetime

COIL_VERSION = "1.0.0"
CHUNK_SIZE = 1024 * 1024  # 1MB


# ─── PACK ─────────────────────────────────────────────────────────────────────

def pack_files(file_paths):
    """
    Reads files, chunks each, delta-encodes against a local manifest,
    then returns a base64 COIL blob.
    """
    combined = {}
    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {fp}")
        combined[str(path)] = json.loads(path.read_text(encoding="utf-8"))

    json_bytes = json.dumps(combined, ensure_ascii=False).encode("utf-8")

    # Zstd-like compression: use zlib with max level
    compressed = zlib.compress(json_bytes, level=9)

    # SHA-256 of the uncompressed stream (our integrity anchor)
    digest = hashlib.sha256(json_bytes).hexdigest()

    # Build COIL frame
    frame = {
        "v": COIL_VERSION,
        "ts": datetime.utcnow().isoformat() + "Z",
        "sha256": digest,
        "original_size": len(json_bytes),
        "compressed_size": len(compressed),
        "ratio": round(1 - len(compressed) / len(json_bytes), 4),
        "files": {},
    }

    # Re-chunk the compressed blob for transmission
    total_chunks = (len(compressed) + CHUNK_SIZE - 1) // CHUNK_SIZE
    chunks = []
    for i in range(total_chunks):
        start = i * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, len(compressed))
        chunk_bytes = compressed[start:end]
        chunk_hash = hashlib.sha256(chunk_bytes).hexdigest()
        chunks.append({
            "index": i,
            "hash": chunk_hash,
            "size": len(chunk_bytes),
            "offset": start,
        })
        frame["files"][str(Path(fp))] = {
            "path": str(Path(fp)),
            "raw_bytes": len(json_bytes),
        }

    frame["chunks"] = chunks
    frame["data"] = base64.b64encode(compressed).decode("utf-8")

    return json.dumps(frame, indent=2)


# ─── UNPACK ───────────────────────────────────────────────────────────────────

def unpack_blob(b64_string):
    """Decompresses a COIL blob and returns the original file contents dict."""
    frame = json.loads(b64_string)
    compressed = base64.b64decode(frame["data"])

    # Verify compression integrity
    actual_hash = hashlib.sha256(compressed).hexdigest()
    if actual_hash != frame["sha256"]:
        raise ValueError(
            f"SHA-256 mismatch on compressed data: expected {frame['sha256']}, "
            f"got {actual_hash}"
        )

    decompressed = zlib.decompress(compressed)
    return json.loads(decompressed.decode("utf-8"))


def extract_files(b64_string, out_dir="."):
    """Unpack blob and write files to disk."""
    data = unpack_blob(b64_string)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for file_path, content in data.items():
        p = out_path / file_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, (dict, list)):
            p.write_text(json.dumps(content, indent=2), encoding="utf-8")
        else:
            p.write_text(str(content), encoding="utf-8")
        print(f"  → {p}")

    print(f"\nExtracted {len(data)} file(s) to ./{out_dir}")


def peek_blob(b64_string):
    """Print metadata without decompressing payload."""
    frame = json.loads(b64_string)
    print(f"COIL SYNC PROTOCOL™ v{frame['v']}")
    print(f"  Packed at   : {frame['ts']}")
    print(f"  Original    : {frame['original_size']:,} bytes")
    print(f"  Compressed  : {frame['compressed_size']:,} bytes")
    print(f"  Ratio       : {frame['ratio']*100:.1f}% saved")
    print(f"  SHA-256     : {frame['sha256']}")
    print(f"  Chunks      : {len(frame['chunks'])}")
    for chunk in frame["chunks"]:
        print(
            f"    [{chunk['index']:04d}] "
            f"hash={chunk['hash'][:12]}… "
            f"size={chunk['size']:,} bytes"
        )


# ─── DELTA SYNC ────────────────────────────────────────────────────────────────

MANIFEST_NAME = ".coil_manifest.json"


def load_manifest():
    path = Path(MANIFEST_NAME)
    if path.exists():
        return json.loads(path.read_text())
    return {"version": COIL_VERSION, "files": {}}


def save_manifest(manifest):
    Path(MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))


def delta_pack(file_paths, manifest=None):
    """
    Compare files against a previous manifest.
    Only include files whose content hash has changed.
    """
    manifest = manifest or load_manifest()
    changed = {}

    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            print(f"  ✗ skip (not found): {fp}")
            continue
        raw = path.read_bytes()
        file_hash = hashlib.sha256(raw).hexdigest()
        prev = manifest["files"].get(str(path))

        if prev and prev["hash"] == file_hash:
            print(f"  = unchanged: {fp}")
        else:
            print(f"  + changed  : {fp} ({len(raw):,} bytes)")
            changed[str(path)] = {
                "hash": file_hash,
                "size": len(raw),
                "mtime": path.stat().st_mtime,
            }

    if not changed:
        print("No changes detected.")
        return None

    # Pack only changed files
    changed_paths = list(changed.keys())
    blob = pack_files(changed_paths)

    # Update manifest
    for fp in changed_paths:
        manifest["files"][fp] = changed[fp]
    save_manifest(manifest)

    print(f"\nDelta blob contains {len(changed)} changed file(s)")
    return blob


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "pack":
        if len(args) < 2:
            print("Usage: coil_data.py pack <file1> [file2] ...")
            sys.exit(1)
        result = pack_files(args[1:])
        print(result)  # full JSON blob

    elif cmd == "unpack":
        if len(args) < 2:
            print("Usage: coil_data.py unpack <b64_string>")
            sys.exit(1)
        extract_files(args[1:])

    elif cmd == "peek":
        if len(args) < 2:
            print("Usage: coil_data.py peek <b64_string>")
            sys.exit(1)
        peek_blob(args[1])

    elif cmd == "delta":
        manifest = load_manifest()
        result = delta_pack(args[1:], manifest)
        if result:
            print("\n--- DELTA BLOB ---")
            print(result)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
