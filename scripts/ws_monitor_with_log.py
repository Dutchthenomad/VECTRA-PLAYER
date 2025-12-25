#!/usr/bin/env python3
"""
WebSocket Monitor with File Logging
Outputs to terminal AND /tmp/rugs_ws_feed.log

Usage:
    python3 scripts/ws_monitor_with_log.py

    # In another terminal, Claude can read:
    tail -f /tmp/rugs_ws_feed.log
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import websockets
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

try:
    import httpx
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

LOG_FILE = Path("/tmp/rugs_ws_feed.log")


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


def log_and_print(msg: str, plain_msg: str = None):
    """Print to terminal (with colors) and log to file (plain)."""
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(
            (
                plain_msg
                or msg.replace("\033[0m", "")
                .replace("\033[1m", "")
                .replace("\033[91m", "")
                .replace("\033[92m", "")
                .replace("\033[93m", "")
                .replace("\033[94m", "")
                .replace("\033[95m", "")
                .replace("\033[96m", "")
                .replace("\033[90m", "")
            )
            + "\n"
        )


def format_event(data: dict, direction: str = "RX") -> tuple[str, str]:
    """Format event for terminal (colored) and log (plain)."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    event_type = "unknown"
    payload = data

    if isinstance(data, dict):
        event_type = data.get("event", data.get("type", "unknown"))
    elif isinstance(data, list) and len(data) >= 2:
        event_type = data[0]
        payload = data[1] if len(data) > 1 else {}

    color = EVENT_COLORS.get(event_type, Colors.RESET)
    dir_color = Colors.GREEN if direction == "RX" else Colors.BLUE
    dir_sym = "◀" if direction == "RX" else "▶"

    # Colored version
    header_colored = f"{Colors.GRAY}{timestamp}{Colors.RESET} {dir_color}{dir_sym}{Colors.RESET} {color}{event_type}{Colors.RESET}"
    # Plain version
    header_plain = f"{timestamp} {dir_sym} {event_type}"

    detail = ""
    if isinstance(payload, dict):
        if event_type == "gameStateUpdate":
            tick = payload.get("tickIndex", "?")
            price = payload.get("currentPrice", "?")
            phase = payload.get("phase", "?")
            detail = f" tick={tick} price={price} phase={phase}"
        elif event_type == "playerUpdate":
            cash = payload.get("cash", "?")
            pos = payload.get("positionQty", "?")
            pnl = payload.get("cumulativePnL", "?")
            short = payload.get("shortPosition")
            short_str = f" SHORT={json.dumps(short)}" if short else ""
            detail = f" cash={cash} pos={pos} pnl={pnl}{short_str}"
        elif event_type == "newTrade":
            action = payload.get("action", "?")
            amount = payload.get("amount", "?")
            price = payload.get("price", "?")
            detail = f" {action} amount={amount} @ {price}"
        elif event_type in ("currentSidebet", "currentSidebetResult"):
            bet_type = payload.get("type", "?")
            amount = payload.get("betAmount", "?")
            won = payload.get("won", "")
            won_str = f" WON={won}" if won != "" else ""
            detail = f" type={bet_type} amount={amount}{won_str}"
        else:
            payload_str = json.dumps(payload)
            if len(payload_str) > 100:
                payload_str = payload_str[:97] + "..."
            detail = f" {payload_str}"

    return header_colored + detail, header_plain + detail


async def get_ws_debugger_url() -> str:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://localhost:9222/json")
            pages = resp.json()
            for page in pages:
                if "rugs.fun" in page.get("url", ""):
                    return page["webSocketDebuggerUrl"]
            if pages:
                return pages[0]["webSocketDebuggerUrl"]
            raise Exception("No pages found")
        except httpx.ConnectError:
            raise Exception("Chrome CDP not available on port 9222")


async def monitor_websockets():
    # Clear log file
    LOG_FILE.write_text("")

    log_and_print(f"\n{Colors.BOLD}━━━ WebSocket Monitor (with logging) ━━━{Colors.RESET}")
    log_and_print(f"{Colors.GRAY}Log file: {LOG_FILE}{Colors.RESET}")

    try:
        ws_url = await get_ws_debugger_url()
        log_and_print(f"{Colors.GREEN}✓ Connected to Chrome CDP{Colors.RESET}")
    except Exception as e:
        log_and_print(f"{Colors.RED}✗ {e}{Colors.RESET}")
        log_and_print(f"\n{Colors.YELLOW}Start Chrome:{Colors.RESET}")
        log_and_print("  google-chrome --remote-debugging-port=9222 https://rugs.fun")
        return

    async with websockets.connect(ws_url, max_size=None) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        await ws.recv()

        log_and_print(f"{Colors.GREEN}✓ Monitoring WebSocket traffic{Colors.RESET}")
        log_and_print(f"\n{Colors.GRAY}{'─' * 60}{Colors.RESET}\n")

        ws_request_ids = set()

        async for message in ws:
            try:
                msg = json.loads(message)
                method = msg.get("method", "")
                params = msg.get("params", {})

                if method == "Network.webSocketCreated":
                    url = params.get("url", "")
                    if "socket.io" in url or "rugs" in url:
                        ws_request_ids.add(params.get("requestId"))
                        log_and_print(f"{Colors.GREEN}🔌 WebSocket: {url[:50]}...{Colors.RESET}")

                elif method == "Network.webSocketFrameReceived":
                    request_id = params.get("requestId")
                    if request_id in ws_request_ids or not ws_request_ids:
                        payload = params.get("response", {}).get("payloadData", "")
                        if payload.startswith("42"):
                            try:
                                data = json.loads(payload[2:])
                                colored, plain = format_event(data, "RX")
                                log_and_print(colored, plain)
                            except json.JSONDecodeError:
                                pass

                elif method == "Network.webSocketFrameSent":
                    request_id = params.get("requestId")
                    if request_id in ws_request_ids or not ws_request_ids:
                        payload = params.get("response", {}).get("payloadData", "")
                        if payload.startswith("42"):
                            try:
                                data = json.loads(payload[2:])
                                colored, plain = format_event(data, "TX")
                                log_and_print(colored, plain)
                            except json.JSONDecodeError:
                                pass

                elif method == "Network.webSocketClosed":
                    request_id = params.get("requestId")
                    if request_id in ws_request_ids:
                        ws_request_ids.discard(request_id)
                        log_and_print(f"{Colors.RED}🔌 Disconnected{Colors.RESET}")

            except Exception as e:
                pass


def main():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║         rugs.fun WebSocket Monitor + Logger              ║
║                                                          ║
║  Terminal 1: This window (live colored feed)             ║
║  Terminal 2: Claude reads /tmp/rugs_ws_feed.log          ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
""")
    try:
        asyncio.run(monitor_websockets())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stopped{Colors.RESET}")


if __name__ == "__main__":
    main()
