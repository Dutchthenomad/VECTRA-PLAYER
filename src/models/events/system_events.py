"""
System Event Schemas - Issue #8

System lifecycle events for connection management, authentication,
and session tracking.

Socket.IO Protocol:
- Connection events use Engine.IO protocol (0, 40, etc.)
- Custom events use Socket.IO protocol (42, 43)

Schema Version: 1.0.0
GitHub Issue: #8
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SystemEventType(str, Enum):
    """System event type enumeration."""
    CONNECT = 'connect'
    DISCONNECT = 'disconnect'
    RECONNECT = 'reconnect'
    AUTH_SUCCESS = 'auth_success'
    AUTH_FAILURE = 'auth_failure'
    ERROR = 'error'
    PING = 'ping'
    PONG = 'pong'
    SESSION_START = 'session_start'
    SESSION_END = 'session_end'
    GAME_START = 'game_start'
    GAME_END = 'game_end'


class SystemEvent(BaseModel):
    """
    Generic system event for lifecycle tracking.

    Captures connection status, authentication, errors, and
    session boundaries for debugging and analytics.

    Example usage:
    - Connection established/lost
    - Authentication success/failure
    - Recording session start/end
    - Game lifecycle events
    """

    event_type: SystemEventType = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")

    # Connection info
    socket_id: Optional[str] = Field(None, description="Socket.IO session ID")
    transport: Optional[Literal['websocket', 'polling']] = Field(None, description="Transport method")

    # Error info
    error_code: Optional[str] = Field(None, description="Error code if applicable")
    error_message: Optional[str] = Field(None, description="Error message if applicable")

    # Ingestion metadata
    meta_ts: Optional[datetime] = Field(None)
    meta_seq: Optional[int] = Field(None)
    meta_source: Optional[Literal['cdp', 'public_ws', 'replay', 'ui']] = Field(None)
    meta_session_id: Optional[str] = Field(None)

    class Config:
        extra = 'allow'
        use_enum_values = True

    @property
    def is_error(self) -> bool:
        return self.event_type in (SystemEventType.ERROR, SystemEventType.AUTH_FAILURE)

    @property
    def is_connection_event(self) -> bool:
        return self.event_type in (
            SystemEventType.CONNECT,
            SystemEventType.DISCONNECT,
            SystemEventType.RECONNECT,
        )


class ConnectionEvent(SystemEvent):
    """Specialized event for connection state changes."""

    event_type: SystemEventType = Field(
        default=SystemEventType.CONNECT,
        description="Connection event type"
    )
    url: Optional[str] = Field(None, description="Server URL")
    latency_ms: Optional[int] = Field(None, description="Connection latency")
    retry_count: Optional[int] = Field(None, description="Reconnection attempt count")


class AuthEvent(SystemEvent):
    """Specialized event for authentication state changes."""

    event_type: SystemEventType = Field(
        default=SystemEventType.AUTH_SUCCESS,
        description="Auth event type"
    )
    player_id: Optional[str] = Field(None, description="Authenticated player ID")
    username: Optional[str] = Field(None, description="Authenticated username")
    wallet_address: Optional[str] = Field(None, description="Wallet address")


class GameLifecycleEvent(SystemEvent):
    """Specialized event for game start/end tracking."""

    event_type: SystemEventType = Field(
        default=SystemEventType.GAME_START,
        description="Game lifecycle event type"
    )
    game_id: str = Field(..., description="Game identifier")
    tick_count: Optional[int] = Field(None, description="Tick count at event")
    price: Optional[Decimal] = Field(None, description="Price at event")
    rugged: Optional[bool] = Field(None, description="Whether game rugged")


class SessionEvent(SystemEvent):
    """Specialized event for recording session boundaries."""

    event_type: SystemEventType = Field(
        default=SystemEventType.SESSION_START,
        description="Session event type"
    )
    session_id: str = Field(..., description="Recording session ID")
    recording_path: Optional[str] = Field(None, description="Output file path")
    event_count: Optional[int] = Field(None, description="Events in session")
    duration_seconds: Optional[float] = Field(None, description="Session duration")
