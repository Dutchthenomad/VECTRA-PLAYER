#!/bin/bash
# Unified bot launcher - one command to start everything
#
# Usage: ./scripts/start_bot.sh
#
# This script:
# 1. Starts Flask dashboard (if not running)
# 2. Starts Chrome with rugs_bot profile (if not running)
# 3. Opens the Control Window
#
# When you close the Control Window, Flask and Chrome keep running.
# Use ./scripts/stop_bot.sh to stop everything.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Run the Python launcher
exec .venv/bin/python -c "
import sys
sys.path.insert(0, 'src')
from scripts.bot_launcher import main
main()
"
