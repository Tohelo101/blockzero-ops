#!/usr/bin/env bash
# BLOZ pool miner (Linux / macOS) — mines on pool.bloz.org
#
# Usage:
#   ./mine-pool.sh                      # auto: address from BlockZero wallet
#   ./mine-pool.sh bz1YOURADDRESS      # explicit payout address
#   THREADS=8 ./mine-pool.sh            # custom thread count
#   WORKER=rig2 ./mine-pool.sh          # custom rig name
#
# First time? Create a wallet address with a local node:
#   bitcoind -datadir=~/.blockzero-mainnet -daemon
#   bitcoin-cli -datadir=~/.blockzero-mainnet createwallet mining
#   bitcoin-cli -datadir=~/.blockzero-mainnet -rpcwallet=mining getnewaddress > ~/.blockzero-mainnet/mining-address.txt
set -euo pipefail

POOL_URL="${POOL_URL:-wss://pool.bloz.org/stratum}"
REPO="${REPO:-Rexemre/blockzero-ops}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.blockzero/pool}"
DATA_DIR="${DATA_DIR:-$HOME/.blockzero-mainnet}"
WORKER="${WORKER:-$(hostname -s 2>/dev/null || echo rig1)}"
THREADS="${THREADS:-0}"

ADDRESS="${1:-}"
BIN="$INSTALL_DIR/bin/bz-pool-miner"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# ---------- payout address ----------
if [ -z "$ADDRESS" ] && [ -f "$DATA_DIR/mining-address.txt" ]; then
    ADDRESS="$(tr -d '[:space:]' < "$DATA_DIR/mining-address.txt")"
    say "Using BlockZero wallet address from $DATA_DIR/mining-address.txt"
fi

if [ -z "$ADDRESS" ]; then
    say ""
    say "No payout address found."
    say "Either pass one:   ./mine-pool.sh bz1YOURADDRESS"
    say "Or create a wallet first (see header of this script),"
    say "then re-run ./mine-pool.sh"
    exit 1
fi

case "$ADDRESS" in
    bz1*) ;;
    *) die "Payout address must start with bz1 (got: $ADDRESS)" ;;
esac

# ---------- platform ----------
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Linux)
        [ "$ARCH" = "x86_64" ] || die "Prebuilt Linux binary is x86_64 only (got $ARCH). Build from source: pool/native in $REPO"
        ASSET="bz-pool-miner-linux-x64.tar.gz"
        ;;
    Darwin)
        [ "$ARCH" = "arm64" ] || die "Prebuilt macOS binary is Apple Silicon only (got $ARCH). Build from source: pool/native in $REPO"
        ASSET="bz-pool-miner-macos-arm64.tar.gz"
        ;;
    *)
        die "Unsupported OS: $OS"
        ;;
esac

# ---------- install / update miner ----------
download_miner() {
    say "Looking up latest pool miner release..."
    local api="https://api.github.com/repos/$REPO/releases"
    local url
    url="$(curl -fsSL "$api" \
        | grep -o "\"browser_download_url\": *\"[^\"]*$ASSET\"" \
        | head -n1 | sed 's/.*"\(https[^"]*\)"/\1/')"
    [ -n "$url" ] || die "No $ASSET found in $REPO releases (pool-miner-v* tag). Try again later or build from source."

    say "Downloading $ASSET ..."
    mkdir -p "$INSTALL_DIR/bin"
    local tmp
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/$ASSET" "$url"
    tar -xzf "$tmp/$ASSET" -C "$INSTALL_DIR/bin"
    chmod +x "$BIN"
    rm -rf "$tmp"
    say "Installed: $BIN"
}

if [ ! -x "$BIN" ] || [ "${FORCE:-0}" = "1" ]; then
    download_miner
fi

# ---------- threads ----------
if [ "$THREADS" -le 0 ] 2>/dev/null; then
    if [ "$OS" = "Darwin" ]; then
        CORES="$(sysctl -n hw.ncpu 2>/dev/null || echo 4)"
    else
        CORES="$(nproc 2>/dev/null || echo 4)"
    fi
    if [ "$CORES" -gt 4 ]; then THREADS=$((CORES - 1)); else THREADS="$CORES"; fi
fi

FULL_WORKER="$ADDRESS.$WORKER"

say ""
say "Pool:    $POOL_URL"
say "Worker:  $FULL_WORKER"
say "Threads: $THREADS"
say "Dashboard: https://pool.bloz.org  (enter your bz1 address under 'Your stats')"
say "Press Ctrl+C to stop."
say ""

# Auto-restart on crash; clean exit (Ctrl+C) stops the loop.
trap 'exit 0' INT TERM
while true; do
    "$BIN" -o "$POOL_URL" -u "$FULL_WORKER" -Threads "$THREADS" && break
    say "Miner exited unexpectedly - restarting in 10s (Ctrl+C to stop)..."
    sleep 10
done
