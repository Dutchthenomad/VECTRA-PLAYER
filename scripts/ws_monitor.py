#!/usr/bin/env python3
"""
Standalone WebSocket Monitor for rugs.fun
Connects to Chrome via CDP and prints WebSocket events to terminal.

Usage:
    python3 scripts/ws_monitor.py

Requirements:
    - Chrome running with --remote-debugging-port=9222
    - Navigate to rugs.fun in Chrome
"""

import asyncio
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


# ANSI colors for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


# Event type colors
EVENT_COLORS = {
    "gameStateUpdate": Colors.GREEN,
    "playerUpdate": Colors.CYAN,
    "newTrade": Colors.YELLOW,
    "currentSidebet": Colors.MAGENTA,
    "currentSidebetResult": Colors.MAGENTA,
    "priceUpdate": Colors.GRAY,
    "gameStart": Colors.GREEN + Colors.BOLD,
    "gameEnd": Colors.RED + Colors.BOLD,
    "rug": Colors.RED + Colors.BOLD,
}


def format_event(data, direction: str = "RX") -> str:
    """Format a WebSocket event for terminal display."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    # Parse Socket.IO array format: ["eventName", {payload}]
    event_type = "unknown"
    payload = {}

    if isinstance(data, list) and len(data) >= 1:
        event_type = data[0]
        payload = data[1] if len(data) > 1 else {}
    elif isinstance(data, dict):
        event_type = data.get("event", data.get("type", "unknown"))
        payload = data

    # Get color for event type
    color = EVENT_COLORS.get(event_type, Colors.RESET)

    # Direction indicator
    dir_color = Colors.GREEN if direction == "RX" else Colors.BLUE
    dir_str = f"{dir_color}◀{Colors.RESET}" if direction == "RX" else f"{dir_color}▶{Colors.RESET}"

    # Format output
    header = f"{Colors.GRAY}{timestamp}{Colors.RESET} {dir_str} {color}{event_type}{Colors.RESET}"

    # Compact payload display
    if isinstance(payload, dict):
        # Show key fields for common events
        if event_type == "gameStateUpdate":
            # Check for cooldown state (between games)
            if "cooldownTimer" in payload:
                timer = payload.get("cooldownTimer", "?")
                return f"{header} COOLDOWN timer={timer}"

            # Active game state
            tick = payload.get("tickIndex") or payload.get("tick") or payload.get("currentTick")
            price = payload.get("currentPrice") or payload.get("price")
            phase = payload.get("phase") or payload.get("gamePhase") or payload.get("status")

            if isinstance(price, (int, float)):
                price = f"{price:.2f}"
            return f"{header} tick={tick} price={price} phase={phase}"

        elif event_type == "gameStatePlayerUpdate":
            # This has nested game state info
            game_id = payload.get("gameId", "?")[:20]
            rugpool = payload.get("rugpool", {})
            rp_amount = rugpool.get("rugpoolAmount", "?")
            if isinstance(rp_amount, (int, float)):
                rp_amount = f"{rp_amount:.3f}"
            return f"{header} game={game_id} rugpool={rp_amount}"

        elif event_type == "playerUpdate":
            cash = payload.get("cash", "?")
            pos = payload.get("positionQty", "?")
            pnl = payload.get("cumulativePnL", "?")
            if isinstance(cash, (int, float)):
                cash = f"{cash:.4f}"
            if isinstance(pnl, (int, float)):
                pnl = f"{pnl:.4f}"
            short = payload.get("shortPosition")
            short_str = " SHORT" if short else ""
            return f"{header} cash={cash} pos={pos} pnl={pnl}{short_str}"

        elif event_type == "standard/newTrade":
            # Show raw payload keys for debugging if key fields missing
            action = payload.get("action") or payload.get("side") or payload.get("type")
            amount = payload.get("amount") or payload.get("qty") or payload.get("solAmount")
            price = payload.get("price") or payload.get("multiplier")
            player = (payload.get("playerId") or payload.get("userId") or "")[:8]
            if action or amount:
                return f"{header} {action} amt={amount} @{price} {player}"
            # Show first few keys if parsing failed
            keys = list(payload.keys())[:4]
            return f"{header} keys={keys}"

        elif event_type in ("currentSidebet", "currentSidebetResult"):
            bet_type = payload.get("type", "?")
            amount = payload.get("betAmount", "?")
            won = payload.get("won")
            won_str = f" WON={won}" if won is not None else ""
            return f"{header} type={bet_type} amt={amount}{won_str}"

        elif event_type in ("pinpointPartyEventUpdate", "goldenHourUpdate", "diddyPartyUpdate"):
            # Mini-game updates - just show event type
            return f"{header}"

        # Default: show truncated JSON
        payload_str = json.dumps(payload)
        if len(payload_str) > 80:
            payload_str = payload_str[:77] + "..."
        return f"{header} {payload_str}"

    return f"{header} {payload}"


async def get_ws_debugger_url() -> str:
    """Get the WebSocket debugger URL from Chrome CDP."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://localhost:9222/json")
            pages = resp.json()

            # Find rugs.fun page
            for page in pages:
                if "rugs.fun" in page.get("url", ""):
                    return page["webSocketDebuggerUrl"]

            # Fallback to first page
            if pages:
                print(
                    f"{Colors.YELLOW}⚠ rugs.fun not found, using first page: {pages[0]['url']}{Colors.RESET}"
                )
                return pages[0]["webSocketDebuggerUrl"]

            raise Exception("No pages found in Chrome")
        except httpx.ConnectError:
            raise Exception(
                "Cannot connect to Chrome CDP. Is Chrome running with --remote-debugging-port=9222?"
            )


async def monitor_websockets():
    """Monitor WebSocket traffic via Chrome CDP."""
    print(f"\n{Colors.BOLD}━━━ WebSocket Monitor for rugs.fun ━━━{Colors.RESET}\n")

    # Get debugger URL
    print(f"{Colors.GRAY}Connecting to Chrome CDP...{Colors.RESET}")
    try:
        ws_url = await get_ws_debugger_url()
        print(f"{Colors.GREEN}✓ Connected to CDP{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}✗ {e}{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Start Chrome with:{Colors.RESET}")
        print("  google-chrome --remote-debugging-port=9222 https://rugs.fun")
        return

    # Connect to CDP WebSocket
    async with websockets.connect(ws_url, max_size=None) as ws:
        # Enable Network domain for WebSocket monitoring
        await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        await ws.recv()  # Wait for response

        print(f"{Colors.GREEN}✓ Network monitoring enabled{Colors.RESET}")
        print(f"\n{Colors.GRAY}Waiting for WebSocket events... (Ctrl+C to stop){Colors.RESET}\n")
        print(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}\n")

        # Track WebSocket request IDs to filter
        ws_request_ids = set()

        async for message in ws:
            try:
                msg = json.loads(message)
                method = msg.get("method", "")
                params = msg.get("params", {})

                # Track WebSocket connections
                if method == "Network.webSocketCreated":
                    url = params.get("url", "")
                    if "socket.io" in url or "rugs" in url:
                        ws_request_ids.add(params.get("requestId"))
                        print(f"{Colors.GREEN}🔌 WebSocket connected: {url[:60]}...{Colors.RESET}")

                # WebSocket frame received
                elif method == "Network.webSocketFrameReceived":
                    request_id = params.get("requestId")
                    if request_id in ws_request_ids or not ws_request_ids:
                        payload = params.get("response", {}).get("payloadData", "")

                        # Parse Socket.IO format
                        if payload.startswith("42"):
                            try:
                                data = json.loads(payload[2:])
                                print(format_event(data, "RX"))
                            except json.JSONDecodeError:
                                pass
                        elif payload.startswith("0") or payload.startswith("40"):
                            # Connection/handshake messages - skip
                            pass
                        elif payload and payload not in ("2", "3"):  # Skip ping/pong
                            print(f"{Colors.GRAY}◀ {payload[:80]}{Colors.RESET}")

                # WebSocket frame sent
                elif method == "Network.webSocketFrameSent":
                    request_id = params.get("requestId")
                    if request_id in ws_request_ids or not ws_request_ids:
                        payload = params.get("response", {}).get("payloadData", "")

                        if payload.startswith("42"):
                            try:
                                data = json.loads(payload[2:])
                                print(format_event(data, "TX"))
                            except json.JSONDecodeError:
                                pass
                        elif payload and payload not in ("2", "3"):
                            print(f"{Colors.BLUE}▶ {payload[:80]}{Colors.RESET}")

                # WebSocket closed
                elif method == "Network.webSocketClosed":
                    request_id = params.get("requestId")
                    if request_id in ws_request_ids:
                        ws_request_ids.discard(request_id)
                        print(f"{Colors.RED}🔌 WebSocket disconnected{Colors.RESET}")

            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.RESET}")


def main():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║           rugs.fun WebSocket Monitor                     ║
║                                                          ║
║  This tool monitors WebSocket traffic from Chrome CDP    ║
║  Run in one terminal, discuss in another with Claude     ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
""")

    try:
        asyncio.run(monitor_websockets())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stopped by user{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")


if __name__ == "__main__":
    main()
