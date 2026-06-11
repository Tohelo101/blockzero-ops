# Pool mining quickstart

Mine BLOZ on **pool.bloz.org** — Windows, Linux and macOS.

Dashboard: https://pool.bloz.org (live stats, copy-paste setup, your earnings)

## Windows

```powershell
git clone https://github.com/Rexemre/blockzero-ops.git
cd blockzero-ops\scripts\mainnet
.\install-windows.ps1
.\mine-mainnet.ps1 -Pool
```

First run: installs binaries, creates wallet + `bz1` address, downloads pool miner, starts mining.
Later runs: uses your existing BlockZero wallet automatically.

## Linux / macOS

```bash
git clone https://github.com/Rexemre/blockzero-ops.git
cd blockzero-ops/scripts/mainnet
chmod +x mine-pool.sh
./mine-pool.sh bz1YOURADDRESS        # or just ./mine-pool.sh if you have a local wallet
```

The script downloads the prebuilt miner (Linux x64 / macOS arm64) from
[blockzero-ops releases](https://github.com/Rexemre/blockzero-ops/releases) and auto-restarts on crashes.

Options (env vars): `THREADS=8 ./mine-pool.sh` · `WORKER=rig2 ./mine-pool.sh` · `FORCE=1` re-downloads the miner.

No local wallet yet? The address is read from `~/.blockzero-mainnet/mining-address.txt` if present;
otherwise pass your `bz1` address as the first argument.

## Commands (Windows)

| Command | What it does |
|---------|----------------|
| `.\mine-mainnet.ps1 -Pool` | Pool mine (recommended) |
| `.\mine-mainnet.ps1 -Pool -Threads 4` | Pool mine, 4 CPU threads |
| `.\mine-pool.bat` | Same as `-Pool` (double-click) |
| `.\mine-mainnet.ps1 -Status` | Solo node status + wallet balance |
| `.\mine-pool-mainnet.ps1 -Status` | Pool height, fee, stratum, pool hashrate |

## Files

| Path | Purpose |
|------|---------|
| `%LOCALAPPDATA%\BlockZeroMainnet\mining-address.txt` | Your `bz1` payout address (Windows) |
| `~/.blockzero-mainnet/mining-address.txt` | Same (Linux/macOS) |
| `%LOCALAPPDATA%\BlockZero\pool\miner.conf` | Pool miner settings (threads, worker name) |
| `~/.blockzero/pool/bin/bz-pool-miner` | Pool miner binary (Linux/macOS, auto-downloaded) |

## Solo vs pool

| | Solo | Pool (`-Pool` / `mine-pool.sh`) |
|--|--|--|
| Node sync | Required | Not for mining (wallet setup once) |
| Wallet | BlockZero | Same wallet |
| Payout | Direct | PPLNS (2% fee, min 0.5 BLOZ) |

## Pool settings

| Setting | Value |
|---------|-------|
| Dashboard | https://pool.bloz.org |
| Stratum | `wss://pool.bloz.org/stratum` |
| Worker | `bz1YOURADDRESS.rigname` (rig name = any label) |
| Password | none (`x` by convention, ignored) |
| Threads | auto = all cores − 1; max 64 |

## Miner behavior (v0.6+)

- Survives connection drops: reconnects and re-subscribes automatically
- RandomX cache reused across jobs within an epoch (no re-init stall)
- Reports total hashrate + accepted/rejected shares every 30s
- Thread count is clamped (never a hard error)

## Troubleshooting

- **No wallet (Windows)** — run `.\mine-mainnet.ps1 -Pool` (creates wallet on first run)
- **No hashrate on the dashboard** — wait 2-5 min after the first `Share accepted`; the estimate needs a few shares
- **Change threads** — Windows: `-Threads 8` · Linux/macOS: `THREADS=8 ./mine-pool.sh`
- **Pool connection error** — check firewall; the pool uses WSS on port 443
- **macOS blocks the binary** — System Settings → Privacy & Security → Allow
