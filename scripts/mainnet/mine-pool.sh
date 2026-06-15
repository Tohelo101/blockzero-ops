#!/usr/bin/env bash
# BLOZ pool miner (Linux / macOS) — mines on pool.bloz.org
set -euo pipefail

POOL_URL="${POOL_URL:-wss://pool.bloz.org/stratum}"
POOL_REPO="${POOL_REPO:-Rexemre/blockzero-pool}"
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
    say "Either pass one:    ./mine-pool.sh bz1YOURADDRESS"
    say "Or create a wallet first, then re-run ./mine-pool.sh"
    exit 1
fi

case "$ADDRESS" in
    bz1*) ;;
    *) die "Payout address must start with bz1 (got: $ADDRESS)" ;;
esac

if [[ "$ADDRESS" == bz1*.* ]]; then
    parsed_rig="${ADDRESS#*.}"
    ADDRESS="${ADDRESS%%.*}"
    say "Note: pass only your bz1 address — the script adds the rig name."
    say "      Using rig name \"$parsed_rig\" from your argument (override with WORKER=…)."
    WORKER="$parsed_rig"
fi

# ---------- platform ----------
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Linux)
        case "$ARCH" in
            x86_64|amd64) ASSET="bz-pool-miner-linux-x64.tar.gz" ;;
            aarch64|arm64) ASSET="bz-pool-miner-linux-arm64.tar.gz" ;;
            *) die "No prebuilt Linux binary for $ARCH." ;;
        esac
        ;;
    Darwin)
        [ "$ARCH" = "arm64" ] || die "Prebuilt macOS binary is Apple Silicon only."
        ASSET="bz-pool-miner-macos-arm64.tar.gz"
        ;;
    *)
        die "Unsupported OS: $OS"
        ;;
esac

# ---------- install / update miner ----------
download_miner() {
    say "Looking up latest pool miner release..."
    # Muutettu hakemaan suoraan /releases/latest vakauden varmistamiseksi
    local api="https://api.github.com/repos/$REPO/releases/latest"
    local url
    url="$(curl -fsSL "$api" \
        | grep -o "\"browser_download_url\": *\"[^\"]*$ASSET\"" \
        | head -n1 | sed 's/.*"\(https[^"]*\)"/\1/')"
    [ -n "$url" ] || die "No $ASSET found in $REPO latest release."

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

# KORJAUS: Testataan kirjastoyhteensopivuus ldd:llä/tiedostomuodolla ilman ohjelman virheellistä käynnistämistä
needs_python_miner() {
    [ "$OS" = "Darwin" ] && return 1 # macOS ei käytä GLIBC:tä tässä muodossa
    if command -v ldd >/dev/null 2>&1; then
        ldd "$BIN" 2>&1 | grep -qE 'not found|GLIBC_' && return 0
    fi
    return 1
}

ensure_python_miner() {
    local py_dir="$INSTALL_DIR/python-miner"
    if [ ! -f "$py_dir/miner/blockzero-miner.py" ]; then
        say "Setting up Python pool miner (compatible with older Linux)..."
        mkdir -p "$py_dir"
        curl -fsSL "https://codeload.github.com/$POOL_REPO/tar.gz/refs/heads/main" \
            | tar -xz -C "$py_dir" --strip-components=1
    fi
    if ! python3 -c "import randomx, websocket" 2>/dev/null; then
        say "Installing Python deps (randomx, websocket-client)..."
        python3 -m pip install --user -q -r "$py_dir/requirements.txt" \
            || python3 -m pip install -q -r "$py_dir/requirements.txt"
    fi
}

run_python_miner() {
    ensure_python_miner
    python3 "$INSTALL_DIR/python-miner/miner/blockzero-miner.py" \
        -o "$POOL_URL" -u "$FULL_WORKER" -t "$THREADS"
}

USE_PYTHON=0
if needs_python_miner; then
    say ""
    say "Prebuilt bz-pool-miner needs a newer system libc. Switching to Python miner..."
    USE_PYTHON=1
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
say "Pool:      $POOL_URL"
say "Worker:    $FULL_WORKER"
say "Threads:   $THREADS"
say "Dashboard: https://pool.bloz.org"
say "Press Ctrl+C to stop."
say ""

trap 'exit 0' INT TERM
while true; do
    if [ "$USE_PYTHON" = "1" ]; then
        run_python_miner && break
    else
        # Suoritetaan binääri. Jos se kaatuu, tarkistetaan johtuiko se puuttuvista kirjastoista
        if ! "$BIN" -o "$POOL_URL" -u "$FULL_WORKER" -Threads "$THREADS"; then
            if needs_python_miner; then
                say "Switching to Python miner (GLIBC/GLIBCXX too old)..."
                USE_PYTHON=1
                continue
            fi
            say "Miner exited unexpectedly - restarting in 10s (Ctrl+C to stop)..."
            sleep 10
            continue
        fi
        break
    fi
done
