#!/bin/bash
# Recording Service - Local Startup Script
#
# Usage:
#   ./start.sh           # Start service in foreground
#   ./start.sh --daemon  # Start service in background
#
# Prerequisites:
#   - Foundation Service running on port 9000
#   - Python virtual environment activated

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/../../.venv"
LOG_FILE="/tmp/recording-service.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           VECTRA Recording Service Starter                ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"

# Check for Foundation Service
echo -e "\n${YELLOW}Checking prerequisites...${NC}"
if curl -s http://localhost:9000/health > /dev/null 2>&1; then
    echo -e "  ✓ Foundation Service running on port 9000"
else
    echo -e "  ${RED}✗ Foundation Service not responding on port 9000${NC}"
    echo -e "    Start Foundation first: python -m foundation.launcher"
    exit 1
fi

# Check if port 9010 is available
if lsof -i :9010 > /dev/null 2>&1; then
    echo -e "  ${YELLOW}! Port 9010 in use - killing existing process${NC}"
    pkill -f "python.*src.main.*9010" 2>/dev/null || true
    sleep 2
fi
echo -e "  ✓ Port 9010 available"

# Set environment variables for local development
export STORAGE_PATH="${HOME}/rugs_recordings/raw_captures"
export DEDUP_PATH="${SCRIPT_DIR}/config/seen_games.json"
export FOUNDATION_WS_URL="ws://localhost:9000/feed"
export PORT=9010

# Ensure storage directory exists
mkdir -p "${STORAGE_PATH}"
echo -e "  ✓ Storage path: ${STORAGE_PATH}"

# Change to service directory
cd "${SCRIPT_DIR}"

# Activate venv if available
if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
    echo -e "  ✓ Virtual environment activated"
fi

echo -e "\n${GREEN}Starting Recording Service...${NC}"
echo -e "  API:        http://localhost:9010"
echo -e "  Health:     http://localhost:9010/health"
echo -e "  Foundation: ${FOUNDATION_WS_URL}"

# Start service
if [ "$1" == "--daemon" ] || [ "$1" == "-d" ]; then
    echo -e "\n${YELLOW}Running in daemon mode. Logs: ${LOG_FILE}${NC}"
    nohup python -m src.main > "${LOG_FILE}" 2>&1 &
    PID=$!
    echo -e "  PID: ${PID}"
    sleep 3

    # Check health
    if curl -s http://localhost:9010/health | grep -q '"status":"healthy"'; then
        echo -e "\n${GREEN}✓ Recording Service started successfully${NC}"
        curl -s http://localhost:9010/health | python3 -m json.tool
    else
        echo -e "\n${RED}✗ Service failed to start. Check logs: tail -f ${LOG_FILE}${NC}"
        exit 1
    fi
else
    echo -e "\n${YELLOW}Running in foreground. Press Ctrl+C to stop.${NC}\n"
    python -m src.main
fi
