#!/bin/bash
set -euo pipefail
echo "== site paths =="
ls -d /opt/sites/blockzero /opt/blockzero-pool/web /opt/blockzero-bridge/web /opt/sites/blockzero-pool 2>/dev/null || true
find /opt -maxdepth 4 -path '*/web/index.html' 2>/dev/null | grep -E 'pool|bridge|blockzero' | head -10
