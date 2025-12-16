"""
UsernameStatus Event Schema - Issue #3

Player identity confirmation event sent once on connection.
Used to identify "our" player in leaderboard arrays.

Socket.IO Format: 42["usernameStatus", {trace}, {...}]
Auth Required: YES - Only sent to authenticated clients

CRITICAL: If this event is NOT received, the connection is NOT authenticated.
Use presence of this event to confirm wallet connection.

Schema Version: 1.0.0
GitHub Issue: #3
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class UsernameStatus(BaseModel):
    """
    Player identity confirmation event.

    Sent once on connection when wallet is authenticated.
    Absence of this event indicates unauthenticated session.

    Socket.IO Format: 42["usernameStatus", {trace}, {...}]
    Auth Required: YES

    Example payload:
    {
        "id": "did:privy:cmaibr7rt0094jp0mc2mbpfu4",
        "hasUsername": true,
        "username": "Dutch"
    }
    """

    # ==========================================================================
    # IDENTITY FIELDS
    # ==========================================================================
    id: str = Field(..., description="Unique player ID (Privy DID)")
    username: Optional[str] = Field(None, description="Display name (null if not set)")
    hasUsername: bool = Field(False, description="Whether username is set")

    # ==========================================================================
    # TRACING FIELDS (internal, may be present)
    # Note: Server sends __trace but Pydantic doesn't allow leading underscores
    # ==========================================================================
    trace_enabled: Optional[bool] = Field(None, alias="__trace", description="Tracing enabled")
    traceparent: Optional[str] = Field(None, description="OpenTelemetry trace ID")

    # ==========================================================================
    # INGESTION METADATA (added by VECTRA-PLAYER, not from socket)
    # ==========================================================================
    meta_ts: Optional[datetime] = Field(None, description="Ingestion timestamp (UTC)")
    meta_seq: Optional[int] = Field(None, description="Sequence number within session")
    meta_source: Optional[Literal['cdp', 'public_ws', 'replay', 'ui']] = Field(None, description="Event source")
    meta_session_id: Optional[str] = Field(None, description="Recording session UUID")

    class Config:
        """Pydantic model configuration."""
        extra = 'allow'
        use_enum_values = True
        populate_by_name = True  # Allow field aliases

    @property
    def is_authenticated(self) -> bool:
        """True if this event represents a valid authenticated session."""
        return bool(self.id)

    @property
    def display_name(self) -> str:
        """Return username or 'Anonymous' if not set."""
        return self.username if self.username else "Anonymous"
