#!/usr/bin/env bash
set -e

# Start the mock relay in the background
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PID_FILE="/tmp/mock_relay.pid"

# Activate venv if specified
if [ -n "$VENV_PATH" ]; then
    PYTHON="$VENV_PATH/bin/python"
else
    PYTHON="python3"
fi

echo "Starting mock relay with $PYTHON..."

# Start the relay in the background with output to both stderr and log file
cd "$TESTS_DIR"

# Create a named pipe for output
PIPE="/tmp/mock_relay_pipe"
rm -f "$PIPE"
mkfifo "$PIPE"

# Start tee in background to read from pipe
tee /tmp/mock_relay.log < "$PIPE" &
TEE_PID=$!

# Start relay with output to the pipe, get its PID
"$PYTHON" -u mock_relay.py > "$PIPE" 2>&1 &
RELAY_PID=$!

# Save the relay PID (not tee's PID)
echo $RELAY_PID > "$PID_FILE"

echo "Mock relay started with PID $RELAY_PID (tee PID: $TEE_PID)"
echo "Relay output is being logged to /tmp/mock_relay.log and stderr"
echo ""

# Wait for relay to be ready (max 10 seconds)
for i in {1..20}; do
    if grep -q "Mock relay listening" /tmp/mock_relay.log 2>/dev/null; then
        echo "✅ Mock relay is ready!"
        echo ""
        exit 0
    fi
    sleep 0.5
done

echo "❌ ERROR: Mock relay failed to start within 10 seconds"
echo "Last lines from relay log:"
tail -20 /tmp/mock_relay.log 2>/dev/null || echo "(log file not found)"
exit 1
