"""Socket.IO frame parser for CDP WebSocket interception."""

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SocketIOFrame:
    """Parsed Socket.IO frame."""

    type: str  # "connect", "disconnect", "event", "ping", "pong", "error"
    event_name: str | None = None
    data: Any | None = None
    raw: str = ""


# Socket.IO Engine.IO packet types
PACKET_TYPES = {
    "0": "connect",
    "1": "disconnect",
    "2": "ping",
    "3": "pong",
    "4": "message",
    "5": "upgrade",
    "6": "noop",
}

# Socket.IO packet types (after Engine.IO '4' message)
SOCKETIO_TYPES = {
    "0": "connect",
    "1": "disconnect",
    "2": "event",
    "3": "ack",
    "4": "error",
    "5": "binary_event",
    "6": "binary_ack",
}


def parse_socketio_frame(raw: str) -> SocketIOFrame | None:
    """
    Parse a Socket.IO frame from raw WebSocket data.

    Socket.IO uses Engine.IO as transport layer:
    - Engine.IO packet: <packet_type><data>
    - For message (type 4): 4<socketio_type>[<data>]

    Common patterns:
    - "0{...}" - Engine.IO connect
    - "2" - Engine.IO ping
    - "3" - Engine.IO pong
    - "42[...]" - Engine.IO message (4) + Socket.IO event (2)

    Args:
        raw: Raw WebSocket frame data

    Returns:
        Parsed SocketIOFrame or None if invalid
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Get Engine.IO packet type
    engine_type = raw[0]

    if engine_type not in PACKET_TYPES:
        return None

    packet_type = PACKET_TYPES[engine_type]

    # Handle simple packets (ping/pong)
    if packet_type in ("ping", "pong", "noop", "upgrade"):
        return SocketIOFrame(type=packet_type, raw=raw)

    # Handle connect packet
    if packet_type == "connect":
        data = None
        if len(raw) > 1:
            try:
                data = json.loads(raw[1:])
            except json.JSONDecodeError as e:
                # Truncate payload for logging
                truncated = raw[1:200] if len(raw) > 200 else raw[1:]
                logger.warning(f"Invalid JSON in connect packet: {e}. Payload: {truncated}...")
        return SocketIOFrame(type="connect", data=data, raw=raw)

    # Handle disconnect
    if packet_type == "disconnect":
        return SocketIOFrame(type="disconnect", raw=raw)

    # Handle message packet (contains Socket.IO data)
    if packet_type == "message":
        return _parse_socketio_message(raw[1:], raw)

    return None


def _parse_socketio_message(data: str, raw: str) -> SocketIOFrame | None:
    """Parse Socket.IO message payload."""
    if not data:
        return None

    # Get Socket.IO packet type
    sio_type = data[0]

    if sio_type not in SOCKETIO_TYPES:
        return None

    sio_packet_type = SOCKETIO_TYPES[sio_type]

    # Handle event (type 2)
    if sio_packet_type == "event":
        return _parse_event(data[1:], raw)

    # Handle other types
    return SocketIOFrame(type=sio_packet_type, raw=raw)


def _parse_event(data: str, raw: str) -> SocketIOFrame | None:
    """Parse Socket.IO event from JSON array.

    Supports:
    - 42["event", {...}]
    - 42123["event", {...}] (ack id)
    - 42/namespace,["event", {...}] (namespace)
    - 42/namespace,123["event", {...}] (namespace + ack id)
    """
    if not data:
        return None

    # Strip optional namespace prefix: /ns,
    if data.startswith("/"):
        comma_idx = data.find(",")
        if comma_idx == -1:
            return None
        data = data[comma_idx + 1 :]

    # Skip optional ack id digits before JSON
    bracket_idx = data.find("[")
    if bracket_idx == -1:
        return None

    json_payload = data[bracket_idx:]

    try:
        parsed = json.loads(json_payload)
    except json.JSONDecodeError as e:
        # Truncate payload for logging
        truncated = json_payload[:200] if len(json_payload) > 200 else json_payload
        logger.warning(f"Invalid JSON in message packet: {e}. Payload: {truncated}...")
        return None

    if isinstance(parsed, list) and len(parsed) >= 1:
        event_name = parsed[0]
        event_data = parsed[1] if len(parsed) > 1 else None

        return SocketIOFrame(type="event", event_name=event_name, data=event_data, raw=raw)

    return None

    try:
        # Event format: ["eventName", data]
        parsed = json.loads(data)

        if isinstance(parsed, list) and len(parsed) >= 1:
            event_name = parsed[0]
            event_data = parsed[1] if len(parsed) > 1 else None

            return SocketIOFrame(type="event", event_name=event_name, data=event_data, raw=raw)
    except json.JSONDecodeError as e:
        # Truncate payload for logging
        truncated = data[:200] if len(data) > 200 else data
        logger.warning(f"Invalid JSON in event packet: {e}. Payload: {truncated}...")

    return None
