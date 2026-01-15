#!/bin/bash
# Stop bot services - kills Flask and Chrome
#
# Usage: ./scripts/stop_bot.sh

set -e

echo "Stopping bot services..."

# Kill Flask on port 5005
FLASK_PID=$(lsof -ti :5005 2>/dev/null || true)
if [ -n "$FLASK_PID" ]; then
    echo "Stopping Flask (PID: $FLASK_PID)..."
    kill "$FLASK_PID" 2>/dev/null || true
    echo "✓ Flask stopped"
else
    echo "✓ Flask was not running"
fi

# Kill Chrome CDP on port 9222
# Note: This kills the Chrome process, not just CDP
CHROME_PID=$(lsof -ti :9222 2>/dev/null || true)
if [ -n "$CHROME_PID" ]; then
    echo "Stopping Chrome CDP (PID: $CHROME_PID)..."
    kill "$CHROME_PID" 2>/dev/null || true
    echo "✓ Chrome stopped"
else
    echo "✓ Chrome CDP was not running"
fi

echo ""
echo "All bot services stopped."
