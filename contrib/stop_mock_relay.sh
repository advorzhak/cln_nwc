#!/usr/bin/env bash

# Stop the mock relay
PID_FILE="/tmp/mock_relay.pid"
LOG_FILE="/tmp/mock_relay.log"
PIPE="/tmp/mock_relay_pipe"

if [ -f "$PID_FILE" ]; then
    RELAY_PID=$(cat "$PID_FILE")
    echo "Stopping mock relay (PID $RELAY_PID)..."
    
    if kill -0 "$RELAY_PID" 2>/dev/null; then
        kill "$RELAY_PID"
        # Wait for it to exit
        for i in {1..10}; do
            if ! kill -0 "$RELAY_PID" 2>/dev/null; then
                echo "Mock relay stopped"
                break
            fi
            sleep 0.5
        done
        
        # Force kill if still running
        if kill -0 "$RELAY_PID" 2>/dev/null; then
            echo "Force killing mock relay..."
            kill -9 "$RELAY_PID" 2>/dev/null || true
        fi
    else
        echo "Mock relay process not running"
    fi
    
    rm -f "$PID_FILE"
else
    echo "No PID file found, relay may not be running"
fi

# Clean up any tee processes that might be attached to the log
pkill -f "tee /tmp/mock_relay.log" 2>/dev/null || true

# Clean up named pipe
rm -f "$PIPE"

# Show last few lines of log if it exists
if [ -f "$LOG_FILE" ]; then
    echo ""
    echo "Last 20 lines of mock relay log:"
    tail -20 "$LOG_FILE"
    rm -f "$LOG_FILE"
fi
