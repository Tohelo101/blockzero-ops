#!/usr/bin/env python3
"""Deploy pool web dashboard (and optionally engine) to the pool VPS."""
import os
import sys

import paramiko

HOST = "217.154.169.211"
PW = os.environ.get("POOL_VPS_PASSWORD", "")
LOCAL = os.path.join(os.path.dirname(__file__), "..", "..", "..", "blockzero-pool")

FILES = [
    ("web/index.html", "/opt/blockzero-pool/web/index.html"),
    ("web/assets/app.css", "/opt/blockzero-pool/web/assets/app.css"),
    ("web/assets/app.js", "/opt/blockzero-pool/web/assets/app.js"),
    ("engine/status_server.py", "/opt/blockzero-pool/engine/status_server.py"),
    ("engine/pplns.py", "/opt/blockzero-pool/engine/pplns.py"),
    ("engine/stratum_server.py", "/opt/blockzero-pool/engine/stratum_server.py"),
]


def main():
    if not PW:
        sys.exit("Set POOL_VPS_PASSWORD")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", password=PW, timeout=30)
    s = c.open_sftp()

    c.exec_command("mkdir -p /opt/blockzero-pool/web/assets")[1].read()

    for rel, remote in FILES:
        local = os.path.normpath(os.path.join(LOCAL, rel))
        if not os.path.isfile(local):
            print(f"skip (missing): {rel}")
            continue
        print(f"upload {rel} -> {remote}")
        s.put(local, remote)

    s.close()
    print("restart services...")
    _, o, e = c.exec_command(
        "systemctl restart blockzero-pool-api blockzero-pool-stratum; sleep 2; "
        "systemctl is-active blockzero-pool-api blockzero-pool-stratum; "
        "curl -s https://pool.bloz.org/api/status | head -c 400",
        timeout=60,
    )
    print(o.read().decode())
    err = e.read().decode().strip()
    if err:
        print("STDERR:", err)
    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
