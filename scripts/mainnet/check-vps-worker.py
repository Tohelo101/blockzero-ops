#!/usr/bin/env python3
"""Quick health check of the VPS pool worker."""
import os
import sys
import time

import paramiko

wait = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if wait:
    time.sleep(wait)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("217.160.64.206", username="root", password=os.environ["MINER_VPS_PASSWORD"], timeout=30)
_, o, _ = c.exec_command(
    "journalctl -u blockzero-pool-worker --since '5 min ago' --no-pager "
    "| grep -E 'Fast mode|Hashrate|Share|dataset|job' | tail -14; free -h | head -2",
    timeout=30,
)
print(o.read().decode())
c.close()
