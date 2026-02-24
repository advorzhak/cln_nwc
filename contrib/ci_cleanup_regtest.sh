#!/usr/bin/env bash
# Cleanup regtest environment after CI testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BITCOIN_DIR="${BITCOIN_DIR:-$HOME/.bitcoin-regtest}"
LIGHTNING_DIR="${LIGHTNING_DIR:-$PROJECT_ROOT/tests/.lightning_nodes}"

echo "=== Cleaning up regtest environment ==="

# Stop Lightning nodes
for NODE in 1 2; do
    NODE_DIR="$LIGHTNING_DIR/l$NODE"
    if [ -d "$NODE_DIR" ]; then
        echo "Stopping Lightning node l$NODE..."
        lightning-cli --lightning-dir="$NODE_DIR" stop 2>/dev/null || true
        sleep 2
    fi
done

# Stop bitcoind
if [ -d "$BITCOIN_DIR" ]; then
    echo "Stopping bitcoind..."
    bitcoin-cli -datadir="$BITCOIN_DIR" -regtest stop 2>/dev/null || true
    sleep 2
fi

echo "✅ Regtest environment cleaned up"
