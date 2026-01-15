#!/bin/bash
# VECTRA Recording Dashboard - Startup Script
#
# Usage: ./scripts/record.sh [OPTIONS]
#
# If Chrome is running (with main UI connected), the dashboard opens
# as a new tab in the SAME browser window. Otherwise, access manually.
#
# Options:
#   -n, --no-browser    Don't auto-open in Chrome
#   -p, --port PORT     Use custom port (default: 5000)
#   -h, --help          Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"

# Parse arguments
EXTRA_ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--no-browser)
            EXTRA_ARGS="$EXTRA_ARGS --no-browser"
            shift
            ;;
        -p|--port)
            EXTRA_ARGS="$EXTRA_ARGS --port $2"
            shift 2
            ;;
        -h|--help)
            head -14 "$0" | tail -13
            exit 0
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Check for virtual environment
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# Check dependencies
python -c "import flask" 2>/dev/null || {
    echo "Installing Flask..."
    pip install flask
}

python -c "import duckdb" 2>/dev/null || {
    echo "Installing DuckDB..."
    pip install duckdb
}

# Run the dashboard
cd "$SRC_DIR"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        VECTRA Recording Dashboard                          ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  If Chrome/main UI is running → opens as new tab           ║"
echo "║  Otherwise → access manually at http://localhost:5000      ║"
echo "║                                                            ║"
echo "║  Press Ctrl+C to stop                                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

python -m recording_ui $EXTRA_ARGS
