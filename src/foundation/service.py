# src/foundation/service.py
"""Foundation Service - Main orchestrator."""

import logging
from collections.abc import Callable

from foundation.broadcaster import WebSocketBroadcaster
from foundation.config import FoundationConfig
from foundation.connection import ConnectionState, ConnectionStatus
from foundation.normalizer import EventNormalizer

logger = logging.getLogger(__name__)


class FoundationService:
    """
    Main Foundation Service orchestrator.

    Responsibilities:
    - Manages connection state
    - Normalizes incoming events
    - Broadcasts to subscribers
    - Provides status/health endpoints
    """

    def __init__(self, config: FoundationConfig | None = None):
        self.config = config or FoundationConfig()
        self.connection_state = ConnectionState()
        self.normalizer = EventNormalizer()
        self.broadcaster = WebSocketBroadcaster(
            host=self.config.host,
            port=self.config.port,
        )

        # Callbacks
        self.on_connection_change: Callable[[ConnectionStatus], None] | None = None

        logger.info(f"FoundationService initialized (port={self.config.port})")

    def on_raw_event(self, raw: dict) -> None:
        """
        Process a raw event from CDP interception.

        1. Normalizes the event
        2. Updates connection state if auth event
        3. Broadcasts to subscribers
        """
        event_name = raw.get("event", "unknown")

        # Normalize
        normalized = self.normalizer.normalize(raw)

        # Handle auth events
        if event_name == "usernameStatus":
            self._handle_auth_event(raw)

        # Broadcast
        self.broadcaster.broadcast(normalized)

        logger.debug(f"Processed event: {event_name} -> {normalized.type}")

    def _handle_auth_event(self, raw: dict) -> None:
        """Handle authentication event (usernameStatus)."""
        data = raw.get("data") or {}  # Handle None explicitly
        username = data.get("username")
        player_id = data.get("id")

        if username and player_id:
            self.connection_state.set_authenticated(username, player_id)
            logger.info(f"Authenticated as {username} ({player_id})")

            if self.on_connection_change:
                self.on_connection_change(ConnectionStatus.AUTHENTICATED)

    def set_connecting(self) -> None:
        """Mark connection as connecting."""
        self.connection_state.set_connecting()
        if self.on_connection_change:
            self.on_connection_change(ConnectionStatus.CONNECTING)

    def set_error(self, message: str) -> None:
        """Mark connection as error."""
        self.connection_state.set_error(message)
        if self.on_connection_change:
            self.on_connection_change(ConnectionStatus.ERROR)

    def set_disconnected(self) -> None:
        """Mark connection as disconnected."""
        self.connection_state.set_disconnected()
        if self.on_connection_change:
            self.on_connection_change(ConnectionStatus.DISCONNECTED)

    def get_status(self) -> dict:
        """Get complete service status."""
        return {
            "connection": self.connection_state.to_dict(),
            "broadcaster": self.broadcaster.get_stats(),
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "chrome_profile": self.config.chrome_profile,
                "ws_url": self.config.ws_url,
            },
        }

    def is_authenticated(self) -> bool:
        """Check if connection is authenticated."""
        return self.connection_state.status == ConnectionStatus.AUTHENTICATED
