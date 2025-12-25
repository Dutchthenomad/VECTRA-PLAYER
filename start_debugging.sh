#!/bin/bash
# Start WebSocket Debugging Workflow
# Usage: ./start_debugging.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   WebSocket Debugging Workflow Startup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Kill existing Chrome instances
echo "🔄 Step 1: Cleaning up existing Chrome instances..."
pkill chrome 2>/dev/null || true
sleep 1

# Step 2: Start Chrome with CDP
echo "🌐 Step 2: Starting Chrome with CDP on port 9222..."
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/nomad/.gamebot/chrome_profiles/rugs_bot \
  --no-first-run \
  "https://rugs.fun" &> /tmp/chrome_debug.log &

CHROME_PID=$!
echo "   Chrome PID: $CHROME_PID"

# Wait for Chrome to start
sleep 3

# Step 3: Verify CDP
echo "🔍 Step 3: Verifying CDP connection..."
if curl -s http://localhost:9222/json/version | jq .Browser > /dev/null 2>&1; then
    echo "   ✅ CDP is responding"
    curl -s http://localhost:9222/json/version | jq -r '"   Browser: " + .Browser'
else
    echo "   ❌ CDP is not responding"
    echo "   Check /tmp/chrome_debug.log for errors"
    exit 1
fi

# Step 4: Launch VECTRA-PLAYER
echo "🚀 Step 4: Launching VECTRA-PLAYER..."
echo "   (UI will open in a few seconds)"
./run.sh &> /tmp/vectra_player.log &
VECTRA_PID=$!
echo "   VECTRA-PLAYER PID: $VECTRA_PID"

sleep 2

# Step 5: Final instructions
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ✅ Debugging Workflow Started"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next Steps (Manual):"
echo ""
echo "1. In VECTRA-PLAYER UI:"
echo "   • Menu → Browser → Connect to Live Browser"
echo "   • Wait for '🟢 Connected' status"
echo ""
echo "2. Enable Live Feed:"
echo "   • Menu → Sources → Live WebSocket Feed"
echo ""
echo "3. Play the game:"
echo "   • Navigate to https://rugs.fun in Chrome window"
echo "   • Events will appear in real-time"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Process IDs:"
echo "   Chrome: $CHROME_PID"
echo "   VECTRA-PLAYER: $VECTRA_PID"
echo ""
echo "Logs:"
echo "   Chrome: /tmp/chrome_debug.log"
echo "   VECTRA-PLAYER: /tmp/vectra_player.log"
echo ""
echo "To stop all processes:"
echo "   kill $CHROME_PID $VECTRA_PID"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
