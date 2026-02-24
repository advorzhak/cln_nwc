#!/usr/bin/env bash
# Setup minimal regtest environment for CI testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
BITCOIN_DIR="${BITCOIN_DIR:-$HOME/.bitcoin-regtest}"
LIGHTNING_DIR="${LIGHTNING_DIR:-$PROJECT_ROOT/tests/.lightning_nodes}"
NETWORK="regtest"

echo "=== Setting up Bitcoin regtest environment ==="
mkdir -p "$BITCOIN_DIR"

# Start bitcoind if not running
if ! bitcoin-cli -datadir="$BITCOIN_DIR" -regtest getblockchaininfo >/dev/null 2>&1; then
    echo "Starting bitcoind in regtest mode..."
    bitcoind -datadir="$BITCOIN_DIR" -regtest -daemon \
        -txindex=1 \
        -fallbackfee=0.00000253 \
        -zmqpubrawblock=tcp://127.0.0.1:28332 \
        -zmqpubrawtx=tcp://127.0.0.1:28333
    
    # Wait for bitcoind to start
    for i in {1..30}; do
        if bitcoin-cli -datadir="$BITCOIN_DIR" -regtest getblockchaininfo >/dev/null 2>&1; then
            echo "✅ bitcoind started"
            break
        fi
        echo "Waiting for bitcoind to start... ($i/30)"
        sleep 1
    done
fi

# Create and load default wallet
if ! bitcoin-cli -datadir="$BITCOIN_DIR" -regtest listwallets | grep -q "default"; then
    echo "Creating default wallet..."
    bitcoin-cli -datadir="$BITCOIN_DIR" -regtest createwallet "default" >/dev/null 2>&1 || true
fi

# Mine some blocks if needed
BLOCK_COUNT=$(bitcoin-cli -datadir="$BITCOIN_DIR" -regtest getblockcount)
if [ "$BLOCK_COUNT" -lt 101 ]; then
    echo "Mining initial blocks..."
    ADDRESS=$(bitcoin-cli -datadir="$BITCOIN_DIR" -regtest getnewaddress)
    bitcoin-cli -datadir="$BITCOIN_DIR" -regtest generatetoaddress 101 "$ADDRESS" >/dev/null
fi

echo "=== Setting up Lightning nodes ==="
mkdir -p "$LIGHTNING_DIR"

# Determine if we should load the NWC plugin
# Default to true for integration tests to work
LOAD_PLUGIN="${LOAD_NWC_PLUGIN:-true}"

# For CI, do a clean start by removing old data
CLEAN_START="${CLEAN_START:-true}"

# Setup node configurations
for NODE in 1 2; do
    NODE_DIR="$LIGHTNING_DIR/l$NODE"
    
    # For clean start, remove old directory completely
    if [ "$CLEAN_START" = "true" ] && [ -d "$NODE_DIR" ]; then
        echo "Cleaning up old data for l$NODE..."
        rm -rf "$NODE_DIR"
    fi
    
    mkdir -p "$NODE_DIR/$NETWORK"
    
    PORT=$((7070 + NODE * 101))
    
    # Clean up any stale files from previous runs
    rm -f "$NODE_DIR/$NETWORK/lightningd-$NETWORK.pid"
    rm -f "$NODE_DIR/$NETWORK/.lightningd.lock"
    
    # Create config file
    cat > "$NODE_DIR/config" <<EOF
network=$NETWORK
log-level=debug
log-file=$NODE_DIR/$NETWORK/log
addr=localhost:$PORT
allow-deprecated-apis=false
developer
dev-fast-gossip
dev-bitcoind-poll=5
database-upgrade=true
disable-plugin=cln-grpc
EOF
    
    # Add plugin if requested (uses wrapper script to activate Python venv)
    if [ "$LOAD_PLUGIN" = "true" ]; then
        echo "plugin=$PROJECT_ROOT/contrib/plugin_wrapper.sh" >> "$NODE_DIR/config"
    fi
    
    # Check if node is already running
    if lightning-cli --lightning-dir="$NODE_DIR" getinfo >/dev/null 2>&1; then
        echo "✅ Lightning node l$NODE already running"
        continue
    fi
    
    # Start lightning node
    echo "Starting Lightning node l$NODE..."
    echo "Config file:"
    cat "$NODE_DIR/config"
    echo ""
    
    # Start lightningd (daemon mode returns immediately)
    echo "Executing: lightningd --lightning-dir=$NODE_DIR --bitcoin-datadir=$BITCOIN_DIR --daemon"
    if ! lightningd --lightning-dir="$NODE_DIR" \
                    --bitcoin-datadir="$BITCOIN_DIR" \
                    --daemon; then
        echo "❌ lightningd command failed for l$NODE (exit code: $?)"
        echo "Last 50 lines of log:"
        tail -n 50 "$NODE_DIR/$NETWORK/log" 2>/dev/null || echo "No log file found"
        exit 1
    fi
    
    echo "lightningd started, waiting for RPC to be ready..."
    # Give it a moment to initialize before checking
    sleep 1
    
    # Wait for node to be ready
    STARTED=false
    echo -n "Waiting for RPC to be ready"
    for i in {1..60}; do
        if lightning-cli --lightning-dir="$NODE_DIR" getinfo >/dev/null 2>&1; then
            echo ""
            echo "✅ Lightning node l$NODE started (took ${i}s)"
            STARTED=true
            break
        fi
        
        # Check if process crashed
        if [ -f "$NODE_DIR/$NETWORK/lightningd-$NETWORK.pid" ]; then
            PID=$(cat "$NODE_DIR/$NETWORK/lightningd-$NETWORK.pid")
            if ! kill -0 "$PID" 2>/dev/null; then
                echo ""
                echo "❌ Lightning node l$NODE process died (PID: $PID)"
                STARTED=false
                break
            fi
        fi
        
        # Show progress
        echo -n "."
        sleep 1
    done
    echo ""
    
    # Check if node failed to start
    if [ "$STARTED" = "false" ]; then
        echo "❌ Failed to start Lightning node l$NODE"
        echo ""
        echo "=== Config file ==="
        cat "$NODE_DIR/config"
        echo ""
        echo "=== Last 50 lines of log ==="
        tail -n 50 "$NODE_DIR/$NETWORK/log" 2>/dev/null || echo "No log file found"
        echo ""
        echo "=== Directory contents ==="
        ls -la "$NODE_DIR/$NETWORK/" 2>/dev/null || echo "Directory not found"
        exit 1
    fi
    
    # Small delay between starting nodes to avoid race conditions
    sleep 1
done

# Export environment variables for tests
echo ""
echo "=== Environment variables for tests ==="
echo "export LIGHTNING_DIR_L1=$LIGHTNING_DIR/l1"
echo "export LIGHTNING_DIR_L2=$LIGHTNING_DIR/l2"
echo "export BITCOIN_DIR=$BITCOIN_DIR"

# Create env file for CI
cat > "$PROJECT_ROOT/tests/.test_env" <<EOF
LIGHTNING_DIR_L1=$LIGHTNING_DIR/l1
LIGHTNING_DIR_L2=$LIGHTNING_DIR/l2
BITCOIN_DIR=$BITCOIN_DIR
EOF

echo ""
echo "✅ Regtest environment ready!"
