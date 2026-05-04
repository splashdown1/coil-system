#!/bin/bash
DELAY=1.5
SERVER="https://coil-sync-server-splashdown.zocomputer.io"
LOG="/home/workspace/COIL_mirror/SC/COIL_BATCH_UPLOAD_LOG.json"
SC_DIR="/home/workspace/COIL_mirror/SC"
MANIFEST="/home/workspace/COIL_MASTER_CHIP.json"

echo "[$(date -u +%T)] Safe sync started" >> /home/workspace/COIL_mirror/SC/safe_sync.log

# Run the Python uploader inline
python3 << PYEOF
import json, time, subprocess, os

entries = json.load(open('$MANIFEST'))['files'][1]['super_chunks']
total = len(entries)
done = 0

for bi in range(0, total, 20):
    batch = entries[bi:bi+20]
    all_ok = True
    for e in batch:
        path = os.path.join('$SC_DIR', e['file'])
        sha  = e['sha256']
        idx  = e['super_id']
        r = subprocess.run(['curl','-s','--max-time','15','-X','POST',
            '-H','x-file-id: COIL_MASTER_CHIP.json',
            '-H','x-chunk-index: %d' % idx,
            '-H','x-hash: %s' % sha,
            '-H','Content-Type: application/octet-stream',
            '--data-binary','@'+path,
            '$SERVER/upload'],
            capture_output=True, text=True, timeout=20)
        try: ok = json.loads(r.stdout).get('ok',False)
        except: ok = False
        if not ok: all_ok = False
        time.sleep($DELAY)

    with open('$LOG') as f: log = json.load(f)
    log.append({'batch':bi//20,'super_ids':[e['super_id'] for e in batch],'ok':all_ok,
                 'ts':time.strftime('%Y-%m-%dT%H:%M:%SZ')})
    json.dump(log, open('$LOG','w'), indent=2)
    done += len(batch)
    print("[%s] %d/%d (%.1f%%) | Batch %d %s" % (
        time.strftime('%H:%M:%S'), done, total, 100*done/total, bi//20+1, 'OK' if all_ok else 'FAIL'))
    time.sleep($DELAY)

# Mark manifest mirrored
m = json.load(open('$MANIFEST'))
for e in m['files']:
    if e['filename']=='COIL_MASTER_CHIP.json': e['sync_status']='mirrored'
json.dump(m, open('$MANIFEST','w'), indent=2)

# Call /complete
r = subprocess.run(['curl','-s','-X','POST','-H','x-file-id: COIL_MASTER_CHIP.json',
    '-H','Content-Type: application/json','-d','{"originalExt":"json"}',
    '$SERVER/complete'], capture_output=True, text=True, timeout=30)
print("/complete:", r.stdout)
print("DONE")
PYEOF
