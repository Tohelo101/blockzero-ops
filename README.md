# BLOCK ZERO · Ops

**Modern BTC code. A second chance at Genesis.**

Infrastructure, release tooling, and runbooks for the Block Zero network.

Fair launch. Proof-of-work. No presale. No insiders.

---

## Mine testnet in one command

| Platform | Script |
|----------|--------|
| **Windows** | [`install-windows.ps1`](scripts/testnet/install-windows.ps1) → [`resync-testnet.ps1`](scripts/testnet/resync-testnet.ps1) → [`mine-testnet.ps1`](scripts/testnet/mine-testnet.ps1) |
| **Linux / macOS** | [`scripts/testnet/install-unix.sh`](scripts/testnet/install-unix.sh) → [`mine-testnet.sh`](scripts/testnet/mine-testnet.sh) |

Downloads prebuilt binaries from [blockzero-core Releases](https://github.com/Rexemre/blockzero-core/releases).  
**Use native Windows binaries for mining** — WSL2 RandomX is ~10× slower.

Full walkthrough: [blockzero-docs/quickstart-mining.md](https://github.com/Rexemre/blockzero-docs/blob/main/quickstart-mining.md)

---

## Runbooks

- [Testnet Seed Node](runbooks/testnet-seed-node.md) — run a persistent, reachable testnet peer
- [`scripts/wsl-portproxy.ps1`](scripts/wsl-portproxy.ps1) — Windows→WSL port proxy (dev only)

---

## Scope

- Public seed nodes and network bootstrap
- Release checklists and CI
- Monitoring, incident response, postmortems

---

## Repositories

| Repo | Purpose |
|------|---------|
| [blockzero-core](https://github.com/Rexemre/blockzero-core) | Node & chain |
| [blockzero-docs](https://github.com/Rexemre/blockzero-docs) | Documentation |
| **blockzero-ops** (here) | Scripts & infrastructure |
| [blockzero-wallet](https://github.com/Rexemre/blockzero-wallet) | Wallet (in development) |
