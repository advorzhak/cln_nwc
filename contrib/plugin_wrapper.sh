#!/usr/bin/env bash
# Wrapper script to run the NWC plugin with Python venv activated
# This ensures the plugin has access to required Python dependencies

set -e

# Find the project root (where venv should be)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/venv}"

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Run the plugin
exec python3 "$PROJECT_ROOT/src/nwc.py" "$@"
