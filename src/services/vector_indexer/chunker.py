"""Event chunker for vector indexing.

Converts raw event dictionaries into text chunks suitable for embedding.
"""

import json
from typing import Any


def chunk_event(event: dict[str, Any]) -> dict[str, Any]:
    """Convert an event into a searchable text chunk.

    Args:
        event: Raw event dictionary from Parquet

    Returns:
        Chunk dict with 'text', 'metadata', and 'id' fields
    """
    doc_type = event.get("doc_type", "unknown")

    # Generate unique ID
    chunk_id = f"{event.get('session_id', 'unknown')}_{event.get('seq', 0)}"

    # Generate text representation based on doc_type
    if doc_type == "ws_event":
        text = _chunk_ws_event(event)
    elif doc_type == "game_tick":
        text = _chunk_game_tick(event)
    elif doc_type == "player_action":
        text = _chunk_player_action(event)
    elif doc_type == "server_state":
        text = _chunk_server_state(event)
    elif doc_type == "system_event":
        text = _chunk_system_event(event)
    else:
        text = _chunk_generic(event)

    return {
        "id": chunk_id,
        "text": text,
        "metadata": {
            "doc_type": doc_type,
            "session_id": event.get("session_id"),
            "game_id": event.get("game_id"),
            "ts": str(event.get("ts")),
        },
    }


def _chunk_ws_event(event: dict) -> str:
    """Format WebSocket event as searchable text."""
    direction = event.get("direction", "unknown")
    game_id = event.get("game_id", "unknown")

    # AUDIT FIX: Use default=str to handle Decimals, datetimes, etc.
    raw_json = event.get("raw_json", "{}")
    if isinstance(raw_json, dict):
        raw_json = json.dumps(raw_json, indent=2, default=str)

    return f"""WebSocket Event ({direction})
Game: {game_id}
Timestamp: {event.get('ts')}

Payload:
{raw_json}
"""


def _chunk_game_tick(event: dict) -> str:
    """Format game tick as searchable text."""
    game_id = event.get("game_id", "unknown")

    # AUDIT FIX: Use default=str to handle Decimals, datetimes, etc.
    raw_json = event.get("raw_json", "{}")
    if isinstance(raw_json, dict):
        raw_json = json.dumps(raw_json, indent=2, default=str)

    return f"""Game Tick
Game: {game_id}
Timestamp: {event.get('ts')}

Data:
{raw_json}
"""


def _chunk_player_action(event: dict) -> str:
    """Format player action as searchable text."""
    game_id = event.get("game_id", "unknown")
    player_id = event.get("player_id", "unknown")

    # AUDIT FIX: Use default=str to handle Decimals, datetimes, etc.
    raw_json = event.get("raw_json", "{}")
    if isinstance(raw_json, dict):
        raw_json = json.dumps(raw_json, indent=2, default=str)

    return f"""Player Action
Game: {game_id}
Player: {player_id}
Timestamp: {event.get('ts')}

Action:
{raw_json}
"""


def _chunk_server_state(event: dict) -> str:
    """Format server state update as searchable text."""
    game_id = event.get("game_id", "unknown")

    # AUDIT FIX: Use default=str to handle Decimals, datetimes, etc.
    raw_json = event.get("raw_json", "{}")
    if isinstance(raw_json, dict):
        raw_json = json.dumps(raw_json, indent=2, default=str)

    return f"""Server State Update
Game: {game_id}
Timestamp: {event.get('ts')}

State:
{raw_json}
"""


def _chunk_system_event(event: dict) -> str:
    """Format system event as searchable text."""
    # AUDIT FIX: Use default=str to handle Decimals, datetimes, etc.
    raw_json = event.get("raw_json", "{}")
    if isinstance(raw_json, dict):
        raw_json = json.dumps(raw_json, indent=2, default=str)

    return f"""System Event
Timestamp: {event.get('ts')}
Source: {event.get('source', 'unknown')}

Event:
{raw_json}
"""


def _chunk_generic(event: dict) -> str:
    """Format unknown event type as searchable text."""
    # AUDIT FIX: Use default=str to handle Decimals, datetimes, etc.
    return f"""Event
Type: {event.get('doc_type', 'unknown')}
Timestamp: {event.get('ts')}

Data:
{json.dumps(event, indent=2, default=str)}
"""
