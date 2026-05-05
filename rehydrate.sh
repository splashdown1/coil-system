#!/bin/bash
# LOGOS_PHOENIX: Rehydrate tru-core on every server restart
# Pull latest git state, then restart the tru-core service

set -e

WORKSPACE="/home/workspace"
SERVICE_LABEL="tru-core"

echo "[PHOENIX] Rehydrating at $(date -Iseconds)"

# Pull latest from git
cd "$WORKSPACE"
git pull origin main

# Restart tru-core service (managed by Zo)
echo "[PHOENIX] Pull complete. Service restart is handled by Zo's supervisor."