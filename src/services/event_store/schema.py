"""
Event Store Schema - Canonical event envelope and doc types

Schema Version: 1.0.0
"""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class DocType(str, Enum):
    """Document types for partitioning"""

    WS_EVENT = "ws_event"  # Raw WebSocket events
    GAME_TICK = "game_tick"  # Price/tick stream
    PLAYER_ACTION = "player_action"  # Human/bot trading actions
    BUTTON_EVENT = "button_event"  # Human button presses for RL training (Phase B)
    BBC_ROUND = "bbc_round"  # BBC sidegame rounds
    CANDLEFLIP_ROUND = "candleflip_round"  # Candleflip sidegame rounds
    SHORT_POSITION = "short_position"  # Short position snapshots
    SERVER_STATE = "server_state"  # Server-authoritative snapshots
    SYSTEM_EVENT = "system_event"  # Connection/disconnect/errors


class EventSource(str, Enum):
    """Event source identifiers"""

    CDP = "cdp"  # Chrome DevTools Protocol interception
    PUBLIC_WS = "public_ws"  # Public WebSocket connection
    REPLAY = "replay"  # Replayed from recording
    UI = "ui"  # User interface action


class Direction(str, Enum):
    """Event direction"""

    RECEIVED = "received"  # Received from server
    SENT = "sent"  # Sent to server


@dataclass
class EventEnvelope:
    """
    Canonical event envelope for all doc types.

    Common columns stored in Parquet:
    - ts: Event timestamp (UTC)
    - source: Event source (cdp, public_ws, replay, ui)
    - doc_type: Document type
    - session_id: Recording session UUID
    - game_id: Game identifier (optional)
    - player_id: Player DID (optional)
    - username: Player display name (optional)
    - seq: Sequence number within session
    - direction: received or sent
    - raw_json: Full original payload (string)
    """

    ts: datetime
    source: EventSource
    doc_type: DocType
    session_id: str
    seq: int
    direction: Direction
    raw_json: str

    # Optional fields
    game_id: str | None = None
    player_id: str | None = None
    username: str | None = None

    # Type-specific extracted fields (for efficient queries)
    event_name: str | None = None  # For ws_event
    price: Decimal | None = None  # For game_tick
    tick: int | None = None  # For game_tick
    action_type: str | None = None  # For player_action
    cash: Decimal | None = None  # For server_state
    position_qty: Decimal | None = None  # For server_state

    # Button event fields (Phase B - RL training)
    button_id: str | None = None  # For button_event (BUY, SELL, INC_01, etc.)
    button_category: str | None = None  # For button_event (action, bet_adjust, percentage)
    sequence_id: str | None = None  # For button_event (action sequence grouping)
    sequence_position: int | None = None  # For button_event (position in sequence)

    @classmethod
    def from_ws_event(
        cls,
        event_name: str,
        data: dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: str | None = None,
        player_id: str | None = None,
        username: str | None = None,
    ) -> "EventEnvelope":
        """Create envelope from WebSocket event"""
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.WS_EVENT,
            session_id=session_id,
            seq=seq,
            direction=Direction.RECEIVED,
            raw_json=json.dumps({"event": event_name, "data": data}),
            game_id=game_id,
            player_id=player_id,
            username=username,
            event_name=event_name,
        )

    @classmethod
    def from_game_tick(
        cls,
        tick: int,
        price: Decimal,
        data: dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: str,
    ) -> "EventEnvelope":
        """Create envelope from game tick"""
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.GAME_TICK,
            session_id=session_id,
            seq=seq,
            direction=Direction.RECEIVED,
            raw_json=json.dumps(data),
            game_id=game_id,
            tick=tick,
            price=price,
        )

    @classmethod
    def from_player_action(
        cls,
        action_type: str,
        data: dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: str | None = None,
        player_id: str | None = None,
        username: str | None = None,
    ) -> "EventEnvelope":
        """Create envelope from player action"""
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.PLAYER_ACTION,
            session_id=session_id,
            seq=seq,
            direction=Direction.SENT,
            raw_json=json.dumps(data),
            game_id=game_id,
            player_id=player_id,
            username=username,
            action_type=action_type,
        )

    @classmethod
    def from_server_state(
        cls,
        data: dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: str,
        player_id: str,
        username: str | None = None,
        cash: Decimal | None = None,
        position_qty: Decimal | None = None,
    ) -> "EventEnvelope":
        """Create envelope from server state update"""
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.SERVER_STATE,
            session_id=session_id,
            seq=seq,
            direction=Direction.RECEIVED,
            raw_json=json.dumps(data),
            game_id=game_id,
            player_id=player_id,
            username=username,
            cash=cash,
            position_qty=position_qty,
        )

    @classmethod
    def from_system_event(
        cls,
        event_type: str,
        data: dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
    ) -> "EventEnvelope":
        """Create envelope from system event"""
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.SYSTEM_EVENT,
            session_id=session_id,
            seq=seq,
            direction=Direction.RECEIVED,
            raw_json=json.dumps({"type": event_type, "data": data}),
            event_name=event_type,
        )

    @classmethod
    def from_button_event(
        cls,
        button_id: str,
        button_category: str,
        data: dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: str | None = None,
        player_id: str | None = None,
        username: str | None = None,
        tick: int | None = None,
        price: Decimal | None = None,
        sequence_id: str | None = None,
        sequence_position: int | None = None,
    ) -> "EventEnvelope":
        """
        Create envelope from button event (Phase B - RL training).

        Args:
            button_id: Button identifier (BUY, SELL, INC_01, etc.)
            button_category: Button category (action, bet_adjust, percentage)
            data: Full ButtonEvent data as dict
            source: Event source (typically UI)
            session_id: Recording session UUID
            seq: Sequence number
            game_id: Game identifier
            player_id: Player DID
            username: Player display name
            tick: Game tick when button was pressed
            price: Price when button was pressed
            sequence_id: ActionSequence grouping ID
            sequence_position: Position within sequence
        """
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.BUTTON_EVENT,
            session_id=session_id,
            seq=seq,
            direction=Direction.SENT,
            raw_json=json.dumps(data),
            game_id=game_id,
            player_id=player_id,
            username=username,
            tick=tick,
            price=price,
            button_id=button_id,
            button_category=button_category,
            sequence_id=sequence_id,
            sequence_position=sequence_position,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Parquet serialization"""
        return {
            "ts": self.ts.isoformat(),
            "source": self.source.value,
            "doc_type": self.doc_type.value,
            "session_id": self.session_id,
            "seq": self.seq,
            "direction": self.direction.value,
            "raw_json": self.raw_json,
            "game_id": self.game_id,
            "player_id": self.player_id,
            "username": self.username,
            "event_name": self.event_name,
            "price": str(self.price) if self.price is not None else None,
            "tick": self.tick,
            "action_type": self.action_type,
            "cash": str(self.cash) if self.cash is not None else None,
            "position_qty": str(self.position_qty) if self.position_qty is not None else None,
            # Button event fields (Phase B)
            "button_id": self.button_id,
            "button_category": self.button_category,
            "sequence_id": self.sequence_id,
            "sequence_position": self.sequence_position,
        }


# Schema version for migrations
SCHEMA_VERSION = "1.0.0"
