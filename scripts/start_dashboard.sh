#!/bin/bash
#
# start_dashboard.sh - Launch the ML Models Dashboard
#
# Usage:
#   1. Start VECTRA-PLAYER first: ./run.sh
#   2. Then run this script: ./scripts/start_dashboard.sh
#
# This script:
#   - Kills any existing process on port 5000
#   - Starts the Flask dashboard server
#   - Opens the Models page in the rugs_bot Chrome profile
#

set -e

# Config
PORT=5000
PROJECT_DIR="/home/devops/Desktop/VECTRA-PLAYER"
CHROME_PROFILE_DIR="$HOME/.gamebot/chrome_profiles"
CHROME_PROFILE="rugs_bot"
DASHBOARD_URL="http://localhost:${PORT}/models"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== VECTRA ML Dashboard Launcher ===${NC}"

# Change to project directory
cd "$PROJECT_DIR"

# Kill any existing process on port
echo -e "${YELLOW}Checking port ${PORT}...${NC}"
if lsof -ti:${PORT} > /dev/null 2>&1; then
    echo -e "${YELLOW}Killing existing process on port ${PORT}${NC}"
    lsof -ti:${PORT} | xargs -r kill -9 2>/dev/null || true
    sleep 1
fi

# Start Flask server in background
echo -e "${GREEN}Starting Flask dashboard on port ${PORT}...${NC}"
.venv/bin/python -m src.recording_ui.app --no-browser --port ${PORT} &
FLASK_PID=$!

# Wait for server to be ready
echo -e "${YELLOW}Waiting for server to start...${NC}"
for i in {1..10}; do
    if curl -s "http://localhost:${PORT}/api/models/runs" > /dev/null 2>&1; then
        echo -e "${GREEN}Server is ready!${NC}"
        break
    fi
    sleep 0.5
done

# Open in Chrome with rugs_bot profile
echo -e "${GREEN}Opening dashboard in Chrome (${CHROME_PROFILE} profile)...${NC}"

# Check if Chrome is already running with CDP
if pgrep -f "chrome.*remote-debugging-port" > /dev/null 2>&1; then
    # Chrome is running, open new tab
    google-chrome \
        --profile-directory="$CHROME_PROFILE" \
        --user-data-dir="$CHROME_PROFILE_DIR" \
        "$DASHBOARD_URL" 2>/dev/null &
else
    echo -e "${YELLOW}Note: VECTRA-PLAYER Chrome not detected. Opening standalone Chrome.${NC}"
    google-chrome \
        --profile-directory="$CHROME_PROFILE" \
        --user-data-dir="$CHROME_PROFILE_DIR" \
        "$DASHBOARD_URL" 2>/dev/null &
fi

echo ""
echo -e "${GREEN}Dashboard running at: ${DASHBOARD_URL}${NC}"
echo -e "${YELLOW}Flask PID: ${FLASK_PID}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Wait for Flask process (keeps script running)
wait $FLASK_PID
