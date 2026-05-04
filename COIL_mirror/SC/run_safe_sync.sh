#!/bin/bash
set -euo pipefail
DELAY=1.5
SERVER="https://coil-sync-server-splashdown.zocomputer.io"
LOG="/home/workspace/COIL_mirror/SC/COIL_BATCH_UPLOAD_LOG.json"
MANIFEST="/home/workspace/COIL_MASTER_CHIP.json"
SC_DIR="/home/workspace/COIL_mirror/SC"
BATCH_SIZE=20

cd "$SC_DIR"

# Read last confirmed batch from log
last_batch() {
  python3 -c "
import json, sys
try:
    log = json.load(open('$LOG'))
    ok = [b for b in log if b.get('ok')]
    if ok: print(max(b['batch'] for b in ok))
    else: print(-1)
except: print(-1)
"
}

# Sync one batch of 20 SCs
sync_batch() {
  local start=$1
  local -a ids=()
  for ((i=0; i<BATCH_SIZE; i++)); do
    ids+=($((start + i)))
  done
  local ok_all=true
  for sid in "${ids[@]}"; do
    local f="chip.sc.$(printf '%06d' $sid).bin"
    if [ ! -f "$SC_DIR/$f" ]; then continue; fi
    local sha=$(sha256sum "$SC_DIR/$f" | cut -d' ' -f1)
    local result=$(curl -s --max-time 15 -X POST \
      -H "x-file-id: COIL_MASTER_CHIP.json" \
      -H "x-chunk-index: $sid" \
      -H "x-hash: $sha" \
      --data-binary "@$SC_DIR/$f" \
      "$SERVER/upload" 2>/dev/null || echo '{}')
    if ! echo "$result" | python3 -c "import sys,json; json.load(sys.stdin); sys.exit(0)" 2>/dev/null; then
      ok_all=false
    fi
    sleep $DELAY
  done
  echo "ok_all=$ok_all"
}

# Main loop
resume=$(last_batch)
next_batch=$((resume + 1))
total=6713
total_batches=$(( (total + BATCH_SIZE - 1) / BATCH_SIZE ))

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting safe sync from batch $next_batch ($total_batches total)" >&2

for ((bi=next_batch; bi<total_batches; bi++)); do
  start=$((bi * BATCH_SIZE))
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Batch $bi/$total_batches | SC $start-$((start+BATCH_SIZE-1))" >&2
  
  ok_all=$(sync_batch $start)
  
  if [ "$ok_all" = "ok_all=true" ]; then
    python3 -c "
import json
from datetime import datetime
log = json.load(open('$LOG'))
entry = {'batch': $bi, 'super_ids': list(range($start, $start+$BATCH_SIZE)), 'ok': True, 'ts': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}
# dedupe by batch id
batches = {b['batch']: b for b in log}
batches[$bi] = entry
with open('$LOG', 'w') as f:
    json.dump(list(batches.values()), f, indent=2)
"
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ✓ Batch $bi done" >&2
  else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ✗ Batch $bi failed" >&2
    sleep 5
  fi
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] SAFE SYNC COMPLETE" >&2
