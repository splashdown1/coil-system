#!/usr/bin/env python3
"""
COIL Encryption Test
Run while COIL_Server.js is running in the background on port 3000

Tests:
  1. Generate AES-256-GCM key + IV
  2. Encrypt chunk payload with AES-GCM
  3. Upload encrypted (ciphertext + IV + auth tag)
  4. Server stores as opaque binary
  5. Reconstruct + decrypt + verify
  6. Hash matches original
"""
import os
import json
import hashlib
import requests
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FILE_ID = "test-encrypt-001"
BASE = "http://localhost:3000"
ORIG_PATH = "/tmp/test_coil_payload.json"
CHUNK_SIZE = 20  # bytes — small to force multiple chunks
KEY_BYTES = 32   # AES-256
IV_BYTES = 12    # AESGCM standard IV

def clean():
    for d in [f"./uploads/{FILE_ID}", f"./manifests/{FILE_ID}.json"]:
        try: os.remove(d)
        except: pass

def test():
    clean()
    print("============================================================")
    print("COIL ENCRYPTION TEST")
    print("============================================================\n")

    # ── Step 1: Load original ────────────────────────────────────────────────
    with open(ORIG_PATH, "rb") as f:
        raw = f.read()
    original_hash = hashlib.sha256(raw).digest()
    print(f"[ENCRYPT] Original: {len(raw)} bytes, SHA256: {original_hash.hex()}\n")

    # ── Step 2: Encrypt each chunk ───────────────────────────────────────────
    chunks = []
    for i in range(0, len(raw), CHUNK_SIZE):
        chunk_data = raw[i : i + CHUNK_SIZE]
        key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(key)
        iv = os.urandom(IV_BYTES)
        # AESGCM.encrypt returns ciphertext + tag concatenated
        ciphertext_with_tag = aesgcm.encrypt(iv, chunk_data, None)
        chunk_hash = hashlib.sha256(chunk_data).digest()
        # Server stores: [IV (12B)][ciphertext+tag]
        stored = iv + ciphertext_with_tag
        chunks.append((chunk_data, stored, chunk_hash, key, iv))
        print(f"  Chunk {i//CHUNK_SIZE}: raw={len(chunk_data)}B → "
              f"stored={len(stored)}B ({100*len(stored)/max(len(chunk_data),1):.0f}% overhead)")

    print()

    # ── Step 3: Upload encrypted chunks ─────────────────────────────────────
    print("[STEP 1] Upload encrypted chunks")
    for idx, (chunk_data, stored, chunk_hash, key, iv) in enumerate(chunks):
        headers = {
            "x-file-id": FILE_ID,
            "x-chunk-index": str(idx),
            "x-hash": chunk_hash.hex(),
            "x-encrypted": "true",
            "x-original-size": str(len(chunk_data)),
            "Content-Type": "application/octet-stream",
        }
        r = requests.post(f"{BASE}/upload", headers=headers, data=stored)
        ok = r.status_code == 200
        print(f"  Chunk {idx}: HTTP {r.status_code} — {'✅' if ok else '❌'}")
        if not ok:
            print(f"    {r.text}")

    # ── Step 4: Complete + reconstruct ───────────────────────────────────────
    print(f"\n[STEP 2] Complete + reconstruct")
    keys_info = {
        str(idx): {
            "key": base64.b64encode(key).decode(),
            "iv": base64.b64encode(iv).decode()
        }
        for idx, (_, _, _, key, iv) in enumerate(chunks)
    }
    r = requests.post(
        f"{BASE}/complete",
        headers={"x-file-id": FILE_ID},
        json={
            "originalName": "test_encrypted.json",
            "totalExpected": len(chunks),
            "encrypted": True,
            "keys": keys_info
        },
    )
    print(f"  /complete: HTTP {r.status_code} — {'✅' if r.status_code == 200 else '❌'}")
    result = r.json()
    print(f"  Result: {result}")

    # ── Step 5: Decrypt reconstructed chunks ────────────────────────────────
    reconstructed_path = f"./uploads/{FILE_ID}.bin"
    if os.path.exists(reconstructed_path):
        with open(reconstructed_path, "rb") as f:
            reconstructed_data = f.read()

        # Split back into IV + ciphertext+tag per chunk
        decrypted_chunks = []
        offset = 0
        for idx, (chunk_data, _, _, key, iv) in enumerate(chunks):
            stored_len = len(iv) + len(chunk_data) + 16  # IV + ciphertext + AESGCM tag
            stored = reconstructed_data[offset : offset + stored_len]
            offset += stored_len
            received_iv = stored[:IV_BYTES]
            received_ct_with_tag = stored[IV_BYTES:]
            aesgcm = AESGCM(key)
            try:
                decrypted = aesgcm.decrypt(received_iv, received_ct_with_tag, None)
                decrypted_chunks.append(decrypted)
            except Exception as e:
                print(f"  ❌ Decrypt failed for chunk {idx}: {e}")
                clean()
                return

        reconstructed = b"".join(decrypted_chunks)
        reconstructed_hash = hashlib.sha256(reconstructed).digest()
        match = reconstructed_hash == original_hash
        print(f"\n[STEP 3] Decryption + verification")
        print(f"  Original hash:      {original_hash.hex()}")
        print(f"  Reconstructed hash: {reconstructed_hash.hex()}")
        print(f"  Match: {'✅ ENCRYPTION TEST PASSED' if match else '❌ MISMATCH'}")
    else:
        print(f"\n[STEP 3] ❌ File not reconstructed")

    clean()
    print("\n[ENCRYPT] Test complete")

if __name__ == "__main__":
    test()
