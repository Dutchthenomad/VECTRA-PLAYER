#!/bin/bash
# VECTRA Unified Control Panel - Single Command Startup
#
# Usage: ./scripts/start.sh [OPTIONS]
#
# This script starts everything needed for VECTRA:
#   1. Chrome browser with rugs_bot profile (CDP enabled on port 9222)
#   2. Flask recording dashboard on port 5000
#   3. Opens dashboard in Chrome tab
#
# The dashboard provides:
#   - Chrome browser connection (CONNECT button)
#   - Trading controls (BUY/SELL/SIDEBET)
#   - Bet amount controls
#   - Recording toggle
#   - Game state display
#
# Options:
#   -n, --no-browser    Don't auto-open Chrome tab
#   -c, --no-chrome     Don't launch Chrome (assumes already running)
#   -p, --port PORT     Use custom dashboard port (default: 5000)
#   -h, --help          Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"

# Configuration
DASHBOARD_PORT=5000
CDP_PORT=9222
# MUST match CDPBrowserManager.profile_path: ~/.gamebot/chrome_profiles/rugs_bot
CHROME_PROFILE_PATH="$HOME/.gamebot/chrome_profiles/rugs_bot"
RUGS_URL="https://rugs.fun"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Flags
LAUNCH_CHROME=true
OPEN_TAB=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--no-browser)
            OPEN_TAB=false
            shift
            ;;
        -c|--no-chrome)
            LAUNCH_CHROME=false
            shift
            ;;
        -p|--port)
            DASHBOARD_PORT=$2
            shift 2
            ;;
        -h|--help)
            head -25 "$0" | tail -24
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

DASHBOARD_URL="http://localhost:${DASHBOARD_PORT}"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}           ${GREEN}VECTRA Unified Control Panel${NC}                     ${CYAN}║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Dashboard: ${YELLOW}${DASHBOARD_URL}${NC}                        ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Chrome CDP: ${YELLOW}port ${CDP_PORT}${NC}                                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Profile: ${YELLOW}rugs_bot${NC}                                   ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check/activate virtual environment
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    echo -e "${GREEN}✓${NC} Virtual environment activated"
fi

# Check dependencies
python -c "import flask" 2>/dev/null || {
    echo -e "${YELLOW}Installing Flask...${NC}"
    pip install flask flask-socketio
}

# Function to check if Chrome is running with CDP
chrome_cdp_running() {
    lsof -i:${CDP_PORT} > /dev/null 2>&1
}

# Launch Chrome if needed
if [ "$LAUNCH_CHROME" = true ]; then
    if chrome_cdp_running; then
        echo -e "${GREEN}✓${NC} Chrome already running with CDP on port ${CDP_PORT}"
    else
        echo -e "${YELLOW}→${NC} Launching Chrome with rugs_bot profile..."

        # Use same format as CDPBrowserManager: --user-data-dir=<full_profile_path>
        google-chrome \
            --user-data-dir="$CHROME_PROFILE_PATH" \
            --remote-debugging-port=${CDP_PORT} \
            --start-maximized \
            --new-window \
            --no-first-run \
            --no-default-browser-check \
            "$RUGS_URL" 2>/dev/null &

        CHROME_PID=$!

        # Wait for Chrome to be ready
        echo -e "${YELLOW}  Waiting for Chrome CDP...${NC}"
        for i in {1..20}; do
            if chrome_cdp_running; then
                echo -e "${GREEN}✓${NC} Chrome ready with CDP on port ${CDP_PORT}"
                break
            fi
            sleep 0.5
        done

        if ! chrome_cdp_running; then
            echo -e "${RED}✗${NC} Chrome failed to start with CDP"
            exit 1
        fi
    fi
fi

# Gracefully stop any existing process on dashboard port
if lsof -ti:${DASHBOARD_PORT} > /dev/null 2>&1; then
    echo -e "${YELLOW}→${NC} Stopping existing dashboard on port ${DASHBOARD_PORT}..."
    # First try graceful shutdown (SIGTERM)
    lsof -ti:${DASHBOARD_PORT} | xargs -r kill -15 2>/dev/null || true
    sleep 2
    # If still running, force kill (SIGKILL)
    if lsof -ti:${DASHBOARD_PORT} > /dev/null 2>&1; then
        echo -e "${YELLOW}  Process didn't stop gracefully, forcing...${NC}"
        lsof -ti:${DASHBOARD_PORT} | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi
fi

# Start Flask dashboard
echo -e "${GREEN}→${NC} Starting Flask dashboard on port ${DASHBOARD_PORT}..."
cd "$SRC_DIR"

if [ "$OPEN_TAB" = true ]; then
    python -m recording_ui.app --port ${DASHBOARD_PORT} &
else
    python -m recording_ui.app --port ${DASHBOARD_PORT} --no-browser &
fi

FLASK_PID=$!

# Wait for Flask to be ready
echo -e "${YELLOW}  Waiting for dashboard...${NC}"
for i in {1..20}; do
    if curl -s "${DASHBOARD_URL}/api/status" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Dashboard ready at ${DASHBOARD_URL}"
        break
    fi
    sleep 0.5
done

if ! curl -s "${DASHBOARD_URL}/api/status" > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Dashboard failed to start"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}                    ${CYAN}READY!${NC}                                   ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  1. Open ${YELLOW}${DASHBOARD_URL}${NC} in browser               ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  2. Click ${CYAN}CONNECT${NC} to connect to Chrome/rugs.fun        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  3. Use trading buttons to control the game              ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  Keyboard shortcuts:                                       ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}    ${CYAN}C${NC} - Connect/Disconnect    ${CYAN}R${NC} - Toggle Recording        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}    ${CYAN}B${NC} - Buy    ${CYAN}S${NC} - Sell    ${CYAN}D${NC} - Sidebet                   ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  Press ${RED}Ctrl+C${NC} to stop                                    ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Wait for Flask process (keeps script running)
wait $FLASK_PID
