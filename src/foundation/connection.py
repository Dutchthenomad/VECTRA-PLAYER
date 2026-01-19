"""Connection state machine for Foundation Service."""

import time
from dataclasses import dataclass
from enum import Enum


class ConnectionStatus(Enum):
    """Connection status states."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    AUTHENTICATED = "AUTHENTICATED"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    ERROR = "ERROR"


@dataclass
class ConnectionState:
    """
    Tracks Foundation connection state.

    State machine:
        DISCONNECTED -> CONNECTING -> AUTHENTICATED
                                   -> UNAUTHENTICATED (timeout)
                                   -> ERROR
    """

    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    username: str | None = None
    player_id: str | None = None
    error_message: str | None = None
    connected_at: float | None = None
    authenticated_at: float | None = None

    def set_connecting(self) -> None:
        """Transition to CONNECTING state."""
        self.status = ConnectionStatus.CONNECTING
        self.connected_at = time.time()
        self.username = None
        self.player_id = None
        self.error_message = None

    def set_authenticated(self, username: str, player_id: str) -> None:
        """Transition to AUTHENTICATED state."""
        self.status = ConnectionStatus.AUTHENTICATED
        self.username = username
        self.player_id = player_id
        self.authenticated_at = time.time()
        self.error_message = None

    def set_unauthenticated(self) -> None:
        """Transition to UNAUTHENTICATED state (auth timeout)."""
        self.status = ConnectionStatus.UNAUTHENTICATED
        self.error_message = "Authentication timeout - no usernameStatus received"

    def set_error(self, message: str) -> None:
        """Transition to ERROR state."""
        self.status = ConnectionStatus.ERROR
        self.error_message = message

    def set_disconnected(self) -> None:
        """Transition to DISCONNECTED state."""
        self.status = ConnectionStatus.DISCONNECTED
        self.username = None
        self.player_id = None
        self.connected_at = None
        self.authenticated_at = None

    def to_dict(self) -> dict:
        """Serialize state to dictionary."""
        return {
            "status": self.status.value,
            "username": self.username,
            "player_id": self.player_id,
            "error_message": self.error_message,
            "connected_at": self.connected_at,
            "authenticated_at": self.authenticated_at,
        }
