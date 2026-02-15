"""
WebSocket Interception Pattern

Demonstrates how to intercept and parse Socket.IO WebSocket messages
from rugs.fun game streams.

Usage:
    from websocket_intercept import SocketIOParser, WebSocketInterceptor

    parser = SocketIOParser()
    interceptor = WebSocketInterceptor(cdp_session)

    for event in interceptor.listen():
        parsed = parser.parse(event)
        print(f"Event: {parsed['event_name']}")
"""

import json
import re
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedEvent:
    """Parsed Socket.IO event."""

    event_name: str
    data: dict
    raw_payload: str
    packet_type: int


class SocketIOParser:
    """
    Parser for Socket.IO protocol messages.

    Socket.IO uses Engine.IO underneath with specific packet types:
    - 0: open
    - 1: close
    - 2: ping
    - 3: pong
    - 4: message (contains Socket.IO events)

    Socket.IO packet format: 42["event_name", {...data...}]
    - 4 = Engine.IO message
    - 2 = Socket.IO event
    """

    # Regex to extract event name and JSON data
    EVENT_PATTERN = re.compile(r'^42\["([^"]+)",(.+)\]$', re.DOTALL)

    def parse(self, raw_message: str) -> ParsedEvent | None:
        """
        Parse a raw WebSocket message.

        Args:
            raw_message: Raw WebSocket frame data

        Returns:
            ParsedEvent or None if not a valid Socket.IO event
        """
        # Handle ping/pong (Engine.IO)
        if raw_message == "2":  # ping
            return ParsedEvent("ping", {}, raw_message, 2)
        if raw_message == "3":  # pong
            return ParsedEvent("pong", {}, raw_message, 3)

        # Parse Socket.IO event (42["event", {...}])
        match = self.EVENT_PATTERN.match(raw_message)
        if match:
            event_name = match.group(1)
            try:
                data = json.loads(match.group(2))
            except json.JSONDecodeError:
                data = {"raw": match.group(2)}

            return ParsedEvent(
                event_name=event_name, data=data, raw_payload=raw_message, packet_type=42
            )

        # Unknown format
        return None

    def is_game_event(self, event: ParsedEvent) -> bool:
        """Check if event is a game-related event."""
        game_events = {
            "gameStateUpdate",
            "playerUpdate",
            "currentSidebet",
            "currentSidebetResult",
            "standard/newTrade",
            "gameEnded",
            "gameStarted",
        }
        return event.event_name in game_events


class WebSocketInterceptor:
    """
    Intercepts WebSocket messages via CDP Network domain.

    Uses Chrome DevTools Protocol to capture WebSocket frames
    without needing to proxy the connection.
    """

    def __init__(self, cdp_session: Any):
        """
        Initialize interceptor.

        Args:
            cdp_session: CDP session with execute() method
        """
        self.cdp = cdp_session
        self._enabled = False

    def enable(self):
        """Enable WebSocket monitoring."""
        self.cdp.execute("Network.enable")
        self._enabled = True

    def disable(self):
        """Disable WebSocket monitoring."""
        if self._enabled:
            self.cdp.execute("Network.disable")
            self._enabled = False

    def listen(self) -> Generator[dict, None, None]:
        """
        Listen for WebSocket frames.

        Yields:
            Dict with frame data including:
            - requestId: WebSocket connection ID
            - timestamp: Frame timestamp
            - response: Received payload (for received frames)
            - request: Sent payload (for sent frames)

        Note: This is a simplified example. Real implementation would
        use CDP event subscription.
        """
        if not self._enabled:
            self.enable()

        # In real implementation, would subscribe to:
        # - Network.webSocketFrameReceived
        # - Network.webSocketFrameSent
        #
        # Example event structure:
        # {
        #     "method": "Network.webSocketFrameReceived",
        #     "params": {
        #         "requestId": "123",
        #         "timestamp": 1234567.89,
        #         "response": {
        #             "opcode": 1,
        #             "mask": false,
        #             "payloadData": "42[\"gameStateUpdate\",{...}]"
        #         }
        #     }
        # }
        pass


def extract_game_state(event: ParsedEvent) -> dict | None:
    """
    Extract normalized game state from gameStateUpdate event.

    Args:
        event: Parsed Socket.IO event

    Returns:
        Normalized game state dict or None
    """
    if event.event_name != "gameStateUpdate":
        return None

    data = event.data

    return {
        "game_id": data.get("gameId"),
        "tick": data.get("tick", 0),
        "price": data.get("price", 1.0),
        "multiplier": data.get("multiplier", 1.0),
        "phase": data.get("phase", "unknown"),
        "timestamp": data.get("timestamp"),
        "connected_players": data.get("connectedPlayers", 0),
    }


def extract_sidebet_result(event: ParsedEvent) -> dict | None:
    """
    Extract sidebet result from currentSidebetResult event.

    Args:
        event: Parsed Socket.IO event

    Returns:
        Sidebet result dict or None
    """
    if event.event_name != "currentSidebetResult":
        return None

    data = event.data

    return {
        "won": data.get("won", False),
        "payout": data.get("payout", 0),
        "bet_amount": data.get("betAmount", 0),
        "result_price": data.get("resultPrice"),
        "bet_price": data.get("betPrice"),
    }


# Example usage
if __name__ == "__main__":
    parser = SocketIOParser()

    # Test parsing
    test_messages = [
        '42["gameStateUpdate",{"gameId":"abc123","tick":150,"price":2.5}]',
        '42["currentSidebetResult",{"won":true,"payout":0.05}]',
        "2",  # ping
        "3",  # pong
    ]

    for msg in test_messages:
        event = parser.parse(msg)
        if event:
            print(f"Event: {event.event_name}")
            if event.event_name == "gameStateUpdate":
                state = extract_game_state(event)
                print(f"  Game state: {state}")
