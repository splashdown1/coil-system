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

## Verified Binaries
| File | SHA256 | Size |
|---|---|---|
| LOGOS_EXPANSION_004.bin | `bee5e6ee480054b98a7c8c15221ea45adc59864e03fffcfe70ba8e2def6d600f` | 104,857,600 |
