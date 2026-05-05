# TRU / COIL System

## What This Is

TRU is Joe's resident intelligence — a sharp, skeptical agent persona ("Dry Truth, Steady Nudge") running in a Zo Computer workspace. COIL is the underlying data sync/transfer protocol that moves binary chip artifacts between the local mirror and the remote sync server.

## Core Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Root agent memory — long-term goals, project context, workspace guidance |
| `SOUL.md` | TRU's personality and behavioral identity |
| `tru_core.py` | TRU's core execution engine |
| `tru_shield.py` | Defensive layer — guards against injection, corruption, coherence drift |
| `tru_control_center.py` | Orchestration hub for TRU operations |
| `COIL_MASTER_CHIP.json` | Master manifest of all chip artifacts — hashes, sizes, sync state |
| `COIL_mirror/` | Local mirror of sync server assets |
| `tru_optim/` | TRU's optimization output and reports |
| `Tru_Knowledge_Bank.json` | Structured knowledge base TRU operates from |
| `Knowledge Bank/` | Raw knowledge assets |

## COIL Sync Architecture

```
Local Filesystem → COIL_mirror/ → [sync daemon] → coil-sync-server
                                        ↑
                              coil_sync.py (uploader)
```

- **Supper-chunks**: binary chip files (`chip.sc.*.bin`) packed from mirror assets
- **Sync daemon**: file-watch daemon that mirrors filesystem changes
- **Upload**: `task005_batch_uploader.py` / `task005_safe_uploader.py` — uploads in batches of 20
- **Server endpoint**: `https://coil-sync-server-splashdown.zocomputer.io`
- **Verification**: `POST /complete` triggers server-side reconstruction; verify SHA256 + size

## Known Friction Points

- `/complete` reconstruction has historically produced corrupted output — verify hashes post-stitch
- Server tunnel/edge 403s on uploads — uploads via `http://localhost:3000` work; direct external URL may not
- Chunk delivery gaps ("Only 16 of 1834 chunks arrived") — use batched retry logic, track in `COIL_BATCH_UPLOAD_LOG.json`
- "Tru is silent" frontend reliability issues — homepage fetch timeout logic needs careful tuning

## Active Projects

- **COIL_UNBOUND Task 005**: Super-chunk sync + server-side stitching (active sync pipeline)
- **Tru-centric web dashboard**: Node/Express dashboard bridging to Zo backend (`coil_unbound/`)
- **Tru Optim**: TRU's own optimization loop output

## Preserving This System

1. **AGENTS.md** is the living memory — keep it current after any structural change
2. **COIL_MASTER_CHIP.json** is the source of truth for sync state — never delete it mid-sync
3. The git repo (`/home/workspace/.git`) tracks `coil_unbound/` dashboard code and core TRU modules — commit meaningful changes
4. All other assets are filesystem-resident and NOT in git — they persist on the server disk

## Git Workflow

```bash
# Workspace is a git repo (branch: main)
git add <files>
git commit -m "<descriptive message>"
git push
```

Last pushed: `efc4bee` — Dynamic Chunk Indexer + /api/health + EncryptionWrapper (Red Line)
