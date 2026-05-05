# AGENTS.md — TRU Workspace Memory

## Identity
TRU (Dry Truth, Steady Nudge) — resident AI for splashdown.zo.computer.

## Workspace Rules
- **NEVER** overwrite `splashdown.zo.space` homepage (`/`) — it's the live production site
- New work goes to fresh routes or new zo.space sites only
- All uploads use `http://localhost:3000` (not the public sync URL) to avoid 403 tunnel errors
- On `/complete` reconstruction failure: wipe server chunks + manifest, delete local done-log, restart from 0

## Friction Points (history)
- 403 tunnel errors on direct sync server uploads → work-around: `http://localhost:3000`
- `/complete` reconstruction produced wrong file sizes → required manual server chunk cleanup
- Uploader stalls requiring resume from later batch
- **LOGOS_EXPANSION_004 corruption loop**: chip.sc files (4040-7158) were split from CORRUPTED server reconstruction, not the original. When in doubt, copy original directly — never re-upload from corrupted chips.
- **delta.zo.space** sleeps on cold start — route density (23 routes) keeps it warm

## ZO.SPACE SITE LOCK
**https://splashdown.zo.space/** is LOCKED. Homepage never gets modified.

## COIL_SYNC Protocol
- Chunk size: 5120 bytes (body after 686-byte COIL header stripped)
- Upload endpoint: `POST http://localhost:3000/upload`
- Required headers: `x-chunk-index`, `x-file-id`, `x-hash`, `x-size`
- Status: `GET http://localhost:3000/status/<file_id>`
- Complete: `POST http://localhost:3000/complete`

## Pipeline Recovery
- Orphan threshold: manifests with ≤4 chunks and `in_progress` status are orphans → safe to delete
- `POST /api/sync-reset` — wipes orphan manifests, verifies server health, logs task summary
- Known orphans: `ALPHA-BACKTEST-1777174120`, `TASK010`, `TASK010_FIXED`, `TASK010_TEST`, `enc-test`, `tru-optim-report`, `COIL_MASTER_CHIP`
- tru-core is supervised by zo/supervisord — if it restarts repeatedly, check `/dev/shm/tru-core_err.log` for module import errors
- zo.space site: `splashdown.zo.space` | Routes: `/` (chat), `/timeline`, `/stocks`, `/api/status`, `/api/sync-reset`, `/api/tru-ask`, `/api/zo-ask`

## Canonical Artifacts (6/6)
| ID | Chunks | Status |
|---|---|---|
| LOGOS_EXPANSION_001.bin | 20,480 | complete |
| LOGOS_EXPANSION_002 | 20,480 | complete |
| LOGOS_EXPANSION_003 | 20,480 | complete |
| LOGOS_EXPANSION_004 | 20,480 | complete |
| TASK006 | 20,480 | complete |
| TASK007 | 20,480 | complete |

**Note:** TASK008 exists on server (20,480 chunks) but is a duplicate/orphan from a prior run — NOT canonical. Server shows 7 total, canonical count is 6.

## Verified Binaries
| File | SHA256 | Size |
|---|---|---|
| LOGOS_EXPANSION_004.bin | `bee5e6ee480054b98a7c8c15221ea45adc59864e03fffcfe70ba8e2def6d600f` | 104,857,600 |

## Tru Knowledge Bank
**File:** `file 'Tru_Knowledge_Bank.json'` — persistent institutional memory for TRU
- Loaded at tru-core startup via `logos_verify` layer
- Contains verified_facts, anomalies_log, preferences, pipeline_state
- Anomalies: ghost hash (VF-003), inotify loop (VF-004), header format mismatch (ANOM-003), /complete strip bug (ANOM-004)
- All facts verified by LOGOS before storage — no speculation, no anecdote

## Critical Pipeline Rules (proven by debug session)
1. **Kill daemon before chip generation** — `coil-mirror-sync-daemon` modifies COIL_MASTER_CHIP.json → inotify loop → hash oscillation
2. **Anchor to git HEAD** — if disk hash vs manifest hash disagree, restore from `git checkout HEAD -- COIL_MASTER_CHIP.json`
3. **Never trust local log** — server response is the only source of truth
4. **Header format must be `<4sH4s32sHH`** — GAP_VALUE=b'\x0f\x56\x41\x4a' at byte 6
5. **Server /complete must STRIP=686** before concat — 46 header + 640 hash table per chunk

## Active Anomalies (watch list)
- ~~LOGOS_EXPANSION_001 in_progress~~ — RESOLVED: server shows 20,480 chunks, complete
- ~~TASK005 not showing in dashboard~~ — RESOLVED: wiped, not worth restoring
- ~~COIL_MASTER_CHIP-1777394476~~ — REMOVED: ghost, 0 chunks on server
- TASK008: on server with 20,480 chunks, orphan/duplicate, NOT canonical
- CANONICAL_ARTIFACTS: 6/6 confirmed live at server (4 LOGOS + TASK006 + TASK007)
- 6,713 legacy chip.sc.*.bin files: **WIPED** from COIL_mirror/SC — 41MB freed, no longer needed