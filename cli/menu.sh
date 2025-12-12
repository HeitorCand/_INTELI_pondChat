#!/usr/bin/env bash
# cli/menu.sh
# Simple wrapper to run the Python menu

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Use virtual environment Python if it exists
if [ -f "$WORKSPACE_DIR/.venv/bin/python" ]; then
    PYTHON="$WORKSPACE_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

# Run the Python menu
cd "$WORKSPACE_DIR"
$PYTHON cli/run.py "$@"
