"""
Event Store Schema - Canonical event envelope and doc types

Schema Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
import json
import uuid


class DocType(str, Enum):
    """Document types for partitioning"""
    WS_EVENT = 'ws_event'           # Raw WebSocket events
    GAME_TICK = 'game_tick'         # Price/tick stream
    PLAYER_ACTION = 'player_action' # Human/bot trading actions
    SERVER_STATE = 'server_state'   # Server-authoritative snapshots
    SYSTEM_EVENT = 'system_event'   # Connection/disconnect/errors


class EventSource(str, Enum):
    """Event source identifiers"""
    CDP = 'cdp'               # Chrome DevTools Protocol interception
    PUBLIC_WS = 'public_ws'   # Public WebSocket connection
    REPLAY = 'replay'         # Replayed from recording
    UI = 'ui'                 # User interface action


class Direction(str, Enum):
    """Event direction"""
    RECEIVED = 'received'     # Received from server
    SENT = 'sent'             # Sent to server


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
    game_id: Optional[str] = None
    player_id: Optional[str] = None
    username: Optional[str] = None

    # Type-specific extracted fields (for efficient queries)
    event_name: Optional[str] = None  # For ws_event
    price: Optional[Decimal] = None   # For game_tick
    tick: Optional[int] = None        # For game_tick
    action_type: Optional[str] = None # For player_action
    cash: Optional[Decimal] = None    # For server_state
    position_qty: Optional[Decimal] = None  # For server_state

    @classmethod
    def from_ws_event(
        cls,
        event_name: str,
        data: Dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: Optional[str] = None,
        player_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> 'EventEnvelope':
        """Create envelope from WebSocket event"""
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.WS_EVENT,
            session_id=session_id,
            seq=seq,
            direction=Direction.RECEIVED,
            raw_json=json.dumps({'event': event_name, 'data': data}),
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
        data: Dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: str,
    ) -> 'EventEnvelope':
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
        data: Dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: Optional[str] = None,
        player_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> 'EventEnvelope':
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
        data: Dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
        game_id: str,
        player_id: str,
        username: Optional[str] = None,
        cash: Optional[Decimal] = None,
        position_qty: Optional[Decimal] = None,
    ) -> 'EventEnvelope':
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
        data: Dict[str, Any],
        source: EventSource,
        session_id: str,
        seq: int,
    ) -> 'EventEnvelope':
        """Create envelope from system event"""
        return cls(
            ts=datetime.utcnow(),
            source=source,
            doc_type=DocType.SYSTEM_EVENT,
            session_id=session_id,
            seq=seq,
            direction=Direction.RECEIVED,
            raw_json=json.dumps({'type': event_type, 'data': data}),
            event_name=event_type,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Parquet serialization"""
        return {
            'ts': self.ts.isoformat(),
            'source': self.source.value,
            'doc_type': self.doc_type.value,
            'session_id': self.session_id,
            'seq': self.seq,
            'direction': self.direction.value,
            'raw_json': self.raw_json,
            'game_id': self.game_id,
            'player_id': self.player_id,
            'username': self.username,
            'event_name': self.event_name,
            'price': str(self.price) if self.price is not None else None,
            'tick': self.tick,
            'action_type': self.action_type,
            'cash': str(self.cash) if self.cash is not None else None,
            'position_qty': str(self.position_qty) if self.position_qty is not None else None,
        }


# Schema version for migrations
SCHEMA_VERSION = '1.0.0'
