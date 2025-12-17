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
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SystemEventType(str, Enum):
    """System event type enumeration."""

    CONNECT = "connect"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    GAME_START = "game_start"
    GAME_END = "game_end"


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
    details: dict[str, Any] = Field(default_factory=dict, description="Event details")

    # Connection info
    socket_id: str | None = Field(None, description="Socket.IO session ID")
    transport: Literal["websocket", "polling"] | None = Field(None, description="Transport method")

    # Error info
    error_code: str | None = Field(None, description="Error code if applicable")
    error_message: str | None = Field(None, description="Error message if applicable")

    # Ingestion metadata
    meta_ts: datetime | None = Field(None)
    meta_seq: int | None = Field(None)
    meta_source: Literal["cdp", "public_ws", "replay", "ui"] | None = Field(None)
    meta_session_id: str | None = Field(None)

    class Config:
        extra = "allow"
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
        default=SystemEventType.CONNECT, description="Connection event type"
    )
    url: str | None = Field(None, description="Server URL")
    latency_ms: int | None = Field(None, description="Connection latency")
    retry_count: int | None = Field(None, description="Reconnection attempt count")


class AuthEvent(SystemEvent):
    """Specialized event for authentication state changes."""

    event_type: SystemEventType = Field(
        default=SystemEventType.AUTH_SUCCESS, description="Auth event type"
    )
    player_id: str | None = Field(None, description="Authenticated player ID")
    username: str | None = Field(None, description="Authenticated username")
    wallet_address: str | None = Field(None, description="Wallet address")


class GameLifecycleEvent(SystemEvent):
    """Specialized event for game start/end tracking."""

    event_type: SystemEventType = Field(
        default=SystemEventType.GAME_START, description="Game lifecycle event type"
    )
    game_id: str = Field(..., description="Game identifier")
    tick_count: int | None = Field(None, description="Tick count at event")
    price: Decimal | None = Field(None, description="Price at event")
    rugged: bool | None = Field(None, description="Whether game rugged")


class SessionEvent(SystemEvent):
    """Specialized event for recording session boundaries."""

    event_type: SystemEventType = Field(
        default=SystemEventType.SESSION_START, description="Session event type"
    )
    session_id: str = Field(..., description="Recording session ID")
    recording_path: str | None = Field(None, description="Output file path")
    event_count: int | None = Field(None, description="Events in session")
    duration_seconds: float | None = Field(None, description="Session duration")
