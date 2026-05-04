# COIL SYNC PROTOCOL™ — Specification
**Version 1.0.0**

---

## Core Features

| Feature | Status |
|---|---|
| Chunked transfer | ✓ |
| Hash-based delta sync | ✓ |
| Optional compression | ✓ |
| Optional encryption | ✓ |
| Resume via checkpointing | ✓ |

---

## Headers

| Header | Purpose |
|---|---|
| `x-file-id` | Unique upload session identifier |
| `x-chunk-index` | Sequential chunk number |
| `x-hash` | SHA-256 of original (pre-compression) chunk |
| `x-compressed` | `true` if chunk body is gzip-deflated |
| `x-original-size` | Uncompressed size (for integrity sanity check) |
| `x-version` | Protocol version (`COIL-SYNC/1.0`) |

---

## Endpoints

### `POST /upload`
**Purpose:** Receive a single chunk

**Required headers:** `x-file-id`, `x-chunk-index`, `x-hash`

**Optional headers:** `x-compressed`, `x-original-size`, `x-version`

**Body:** Raw chunk bytes (optionally gzip-compressed)

**Response:** `200 { ok, chunkIndex, hashVerified, size }`

---

### `POST /complete`
**Purpose:** Finalize upload and reconstruct the file

**Required headers:** `x-file-id`

**Body (JSON):** `{ originalName?, originalExt?, totalExpected? }`

**Response:** `200 { ok, fileId, finalHash, outPath, chunksReconstructed }`

---

### `GET /status?fileId=<id>`
**Purpose:** Delta sync — fetch server's known chunk hashes

**Response:** `{ "00000000": "sha256hash", "00000001": "sha256hash", ... }`

---

## Protocol Flow

```
Client                          Server
  │                               │
  ├─ POST /upload (chunk 0) ─────►│
  │◄── 200 { hashVerified } ──────┤
  ├─ POST /upload (chunk 1) ─────►│
  │◄── 200 { hashVerified } ──────┤
  │         ...                    │
  │                               │
  ├─ GET /status?fileId=X ───────►│  ← delta check
  │◄── { index: hash } ───────────┤
  │                               │
  ├─ POST /upload (new only) ─────►│  ← skip existing
  │         ...                    │
  │                               │
  ├─ POST /complete ─────────────►│
  │◄── 200 { finalHash } ──────────┤
```

---

## Security Considerations

- `x-hash` verifies chunk integrity at upload time (SHA-256 of **original**, before compression)
- `x-original-size` provides a secondary sanity check post-decompression
- Server rejects compressed chunks that fail to decompress (422)
- Server rejects chunks with hash mismatch (415)
- Encryption (`encryptChunk`) is client-side only — server never sees plaintext; key management is out-of-band

---

## Extensions (future)

- `x-encrypted: true` + `iv` + exported key for E2E encryption
- `x-zstd: true` for Zstd compression (higher ratio, faster)
- `GET /status/:fileId` — richer manifest response with timestamps
