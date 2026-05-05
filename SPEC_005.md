# LOGOS_EXPANSION_005 — Index Layer Spec

## Purpose
005 is the first **referenceable** artifact — a map into the four data layers (001-004). Instead of storing new content, it stores pointers: `content_hash → artifact_id + chunk_index`. This transforms the system from dumb storage to queryable archive.

## Architecture

### Fixed 100MB Format (identical to 001-004)
- Total chunks: 20,480
- Chunk body: 5,120 bytes
- Total content: 104,857,600 bytes

### Layout
```
Chunks 0:          Master Header Index
Chunks 1–511:      Primary Index Table (511 chunks × 160 entries = 81,920 slots)
Chunks 512–20479: Reserved (19,968 chunks) — future use, zero-filled
```

### Entry Format (32 bytes each)
| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | artifact_id (uint32 LE: 1=001, 2=002, 3=003, 4=004) |
| 4 | 4 | chunk_index (uint32 LE, 0–20,479) |
| 8 | 32 | content_hash (SHA256, same as upload hash) |
| **Total** | **40 bytes** | |

### Entry Density
- 5,120 / 40 = **128 entries per chunk**
- 511 chunks × 128 entries = **65,408 index slots**
- 4 artifacts × 20,480 chunks = **81,920 total chunks to index**
- → Slots > entries → room for orphans, duplicates, reserved entries

### Master Header (Chunk 0, Bytes 0–511)
```
offset 0  (4):  magic = 0x0F56414A (GAP_VALUE)
offset 4  (2):  format_version = 5
offset 6  (4):  artifact_count = 4
offset 10 (4):  total_indexed_chunks = 81,920
offset 14 (4):  index_chunks_used = 511
offset 18 (4):  entries_total
offset 22 (4):  entries_filled
offset 26 (64): reserved (zero)
offset 90 (512): first 16 index entries (fallback bootstrap)
```

### Indexing Strategy
For each artifact (001–004):
1. Read chunk N (skip header = bytes 686 onward, 5,120 bytes)
2. Compute SHA256 of the 5,120-byte body
3. Write entry: {artifact_id, chunk_index, sha256_hash}

Entries sorted by content_hash (binary sort) for O(log n) lookup.

### Generation Pipeline
```
1. Iterate chunks 0–20,479 for each of 001, 002, 003, 004
2. Compute SHA256(body) for each chunk
3. Collect all 81,920 entries
4. Sort entries by content_hash
5. Write to 005 chunks 1–511 (128 per chunk)
6. Chunk 0 = master header
7. Remaining chunks (512–20479) = zero
```

### Verification
- Local: re-read 005, scan all entries, confirm each hash matches referenced artifact/chunk
- Server: upload as `LOGOS_EXPANSION_005.bin`, verify 20,480 chunks arrive

## Relationship to Prior Artifacts
- 001–004: data layers (what)
- 005: index layer (where)
- Future 006+: query layer / semantic overlay

## Server Upload
- File ID: `LOGOS_EXPANSION_005.bin`
- Expected chunks: 20,480
- Protocol: standard COIL (same as 001-004)