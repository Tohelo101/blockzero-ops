#!/usr/bin/env python3
"""Convert the miner VPS into a real pool worker (bz-pool-miner via wss).

Builds bz-pool-miner from the public blockzero-ops repo on the VPS,
stops solo mining, and runs the worker as a systemd service.
"""
import os
import sys

import paramiko

HOST = os.environ.get("MINER_VPS_HOST", "217.160.64.206")
PW = os.environ.get("MINER_VPS_PASSWORD", "")

SETUP = r"""
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== 1) Build deps ==="
apt-get update -qq
apt-get install -y -qq cmake g++ git libssl-dev ca-certificates >/dev/null

echo "=== 2) Fetch blockzero-ops (public) ==="
if [ -d /opt/blockzero-ops/.git ]; then
  git -C /opt/blockzero-ops fetch --depth 1 origin main
  git -C /opt/blockzero-ops reset --hard origin/main
else
  git clone --depth 1 https://github.com/Rexemre/blockzero-ops.git /opt/blockzero-ops
fi

echo "=== 3) Build bz-pool-miner ==="
cmake -S /opt/blockzero-ops/pool/native -B /opt/blockzero-ops/build -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build /opt/blockzero-ops/build --target bz-pool-miner -j"$(nproc)" 2>&1 | tail -3
install -m 0755 /opt/blockzero-ops/build/bz-pool-miner /usr/local/bin/bz-pool-miner
/usr/local/bin/bz-pool-miner --help 2>&1 | head -2 || true

echo "=== 4) Stop solo mining (pool worker replaces it) ==="
systemctl stop blockzero-miner.service 2>/dev/null || true
systemctl disable blockzero-miner.service 2>/dev/null || true
systemctl stop blockzero-pool-worker.service 2>/dev/null || true
pkill -f 'g[e]neratetoaddress' 2>/dev/null || true  # bracket avoids matching this script itself

echo "=== 5) Payout address ==="
ADDR_FILE=/root/.blockzero-mainnet/mining-address.txt
if [ ! -f "$ADDR_FILE" ]; then
  echo "ERROR: $ADDR_FILE missing"; exit 1
fi
BZ1=$(tr -d '[:space:]' < "$ADDR_FILE")
echo "payout: $BZ1"

CORES=$(nproc)
if [ "$CORES" -gt 4 ]; then THREADS=$((CORES-1)); else THREADS=$CORES; fi
echo "threads: $THREADS (of $CORES cores)"

echo "=== 6) systemd service ==="
cat >/etc/systemd/system/blockzero-pool-worker.service <<UNIT
[Unit]
Description=Block Zero pool worker (bz-pool-miner on pool.bloz.org)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/bz-pool-miner -o wss://pool.bloz.org/stratum -u ${BZ1}.vps -Threads ${THREADS}
Restart=always
RestartSec=15
Nice=10

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable blockzero-pool-worker
systemctl restart blockzero-pool-worker
sleep 8
echo "=== STATUS ==="
systemctl is-active blockzero-pool-worker
journalctl -u blockzero-pool-worker -n 15 --no-pager
free -h | head -2
"""


def main():
    if not PW:
        sys.exit("Set MINER_VPS_PASSWORD")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", password=PW, timeout=30)
    _, o, e = c.exec_command(SETUP, timeout=1800, get_pty=True)
    for line in iter(o.readline, ""):
        print(line, end="")
    code = o.channel.recv_exit_status()
    err = e.read().decode().strip()
    if err:
        print("STDERR:", err)
    c.close()
    print(f"\nexit={code}")


if __name__ == "__main__":
    main()
