"""
Enhanced authentication waiter with event-driven detection and exponential backoff.

This module provides:
- AuthenticationState: Tracks authentication progress
- AuthenticationWaiter: Waits for player identity from WebSocket events

The system monitors multiple event sources to extract player identity:
1. connection.authenticated - Direct auth event (from usernameStatus)
   - Raw field: "id" -> player_id
   - Raw field: "username" -> username
2. game.tick leaderboard - Match by wallet or active trades (fallback)

NOTE: player.state (playerUpdate) does NOT contain identity - only balance/position.

Features:
- 60 second maximum timeout (configurable)
- Exponential backoff: starts at 0.5s, grows to 5s max
- Graceful degradation: read-only mode if game data present but no player identity
- Early exit when authentication succeeds
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuthenticationState:
    """
    Tracks authentication progress.

    Fields:
        username: Player's display name
        player_id: Player's unique identifier (e.g., did:privy:...)
        game_id: Current game ID
        wallet_address: For matching player in leaderboard
    """

    username: str | None = None
    player_id: str | None = None
    game_id: str | None = None
    wallet_address: str | None = None

    @property
    def is_fully_authenticated(self) -> bool:
        """Check if we have complete player identity."""
        return self.username is not None and self.player_id is not None

    @property
    def has_game_data(self) -> bool:
        """Check if we have at least game activity."""
        return self.game_id is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "username": self.username,
            "player_id": self.player_id,
            "game_id": self.game_id,
            "wallet_address": self.wallet_address,
        }


class AuthenticationWaiter:
    """
    Waits for player authentication by monitoring WebSocket events.
    Uses exponential backoff to reduce overhead while remaining responsive.
    """

    def __init__(
        self,
        max_wait_seconds: float = 60.0,
        initial_check_interval: float = 0.5,
        max_check_interval: float = 5.0,
        backoff_multiplier: float = 1.5,
    ):
        """
        Initialize authentication waiter.

        Args:
            max_wait_seconds: Maximum time to wait before timeout (default: 60s)
            initial_check_interval: Initial check interval in seconds (default: 0.5s)
            max_check_interval: Maximum check interval in seconds (default: 5.0s)
            backoff_multiplier: Multiplier for exponential backoff (default: 1.5x)
        """
        self.max_wait = max_wait_seconds
        self.initial_interval = initial_check_interval
        self.max_interval = max_check_interval
        self.backoff_multiplier = backoff_multiplier

        self.state = AuthenticationState()
        self._event_received = asyncio.Event()

    def _extract_player_from_event(self, event: dict[str, Any]) -> tuple[str | None, str | None]:
        """
        Extract username and player_id from various event types.

        Args:
            event: Event dictionary from WebSocket

        Returns:
            Tuple of (username, player_id) or (None, None)
        """
        event_type = event.get("type", "")
        data = event.get("data", {})

        # Debug: Log all events for troubleshooting
        logger.debug(
            f"[AuthWaiter] Processing event type={event_type}, data_keys={list(data.keys()) if data else []}"
        )

        # Method 1: Direct authentication event (from usernameStatus)
        # Raw data has "id", normalized data has "player_id"
        if event_type == "connection.authenticated":
            username = data.get("username")
            # Check both raw field "id" and normalized field "player_id"
            player_id = data.get("id") or data.get("player_id") or data.get("playerId")
            logger.debug(
                f"[AuthWaiter] connection.authenticated: username={username}, player_id={player_id}"
            )
            if username and player_id:
                logger.info(f"Authentication event received: {username} (ID: {player_id})")
                return username, player_id
            elif username:
                logger.warning(
                    f"[AuthWaiter] Got username={username} but no player_id in data: {data}"
                )
            elif player_id:
                logger.warning(
                    f"[AuthWaiter] Got player_id={player_id} but no username in data: {data}"
                )

        # NOTE: player.state (playerUpdate) does NOT contain identity - only balance/position
        # Do NOT check player.state for identity extraction

        # Method 2: playerLeaderboardPosition - contains YOUR identity in playerEntry
        # This is a backup auth event that fires once on connection
        if event_type == "player.leaderboard":
            player_entry = data.get("playerEntry")
            if isinstance(player_entry, dict):
                username = player_entry.get("username")
                player_id = player_entry.get("playerId")
                logger.debug(
                    f"[AuthWaiter] player.leaderboard: username={username}, player_id={player_id}"
                )
                if username and player_id:
                    logger.info(
                        f"Authentication from playerLeaderboardPosition: {username} (ID: {player_id})"
                    )
                    return username, player_id

        # Method 3: Find ourselves in game.tick leaderboard - ONLY with wallet matching
        # WARNING: Do NOT use hasActiveTrades fallback - it picks ANY player, not YOUR player
        if event_type == "game.tick":
            leaderboard = data.get("leaderboard")
            if isinstance(leaderboard, list) and self.state.wallet_address:
                for player in leaderboard:
                    username = player.get("username")
                    player_id = player.get("id")

                    # ONLY match if we have wallet address and it matches
                    if player_id and self.state.wallet_address in player_id:
                        logger.info(
                            f"Player matched in leaderboard by wallet: {username} (ID: {player_id})"
                        )
                        return username, player_id

        return None, None

    def _update_state_from_event(self, event: dict[str, Any]) -> None:
        """
        Update authentication state from event data.

        Args:
            event: Event dictionary from WebSocket
        """
        # Extract game ID if present
        game_id = event.get("gameId")
        if game_id and not self.state.game_id:
            self.state.game_id = game_id
            logger.info(f"Game ID detected: {game_id}")

        # Try to extract player identity
        username, player_id = self._extract_player_from_event(event)

        if username and player_id:
            self.state.username = username
            self.state.player_id = player_id
            self._event_received.set()  # Signal that we got what we need

    def set_wallet_address(self, address: str) -> None:
        """
        Set wallet address for matching player in leaderboard.

        Args:
            address: Wallet address (e.g., Solana public key)
        """
        self.state.wallet_address = address
        logger.debug(f"Wallet address set for player matching: {address[:8]}...")

    async def wait_for_authentication(self) -> AuthenticationState:
        """
        Wait for authentication with exponential backoff checking.

        Returns:
            AuthenticationState with player identity (or partial state)

        Raises:
            TimeoutError: If no game activity detected within max_wait_seconds
        """
        start_time = time.time()
        check_interval = self.initial_interval
        last_log_time = start_time
        log_interval = 5.0  # Log progress every 5 seconds

        logger.info(f"Waiting for authentication (max: {self.max_wait}s)...")
        logger.info("Monitoring WebSocket events for player identity...")

        while True:
            elapsed = time.time() - start_time

            # Check if we've exceeded max wait time
            if elapsed >= self.max_wait:
                break

            # Check if we have complete authentication
            if self.state.is_fully_authenticated:
                logger.info(
                    f"Authentication complete in {elapsed:.1f}s: "
                    f"{self.state.username} (ID: {self.state.player_id})"
                )
                return self.state

            # Periodic progress logging
            if time.time() - last_log_time >= log_interval:
                if self.state.has_game_data:
                    logger.info(
                        f"[{elapsed:.1f}s] Game activity detected (ID: {self.state.game_id}), "
                        f"waiting for player identity..."
                    )
                else:
                    logger.info(f"[{elapsed:.1f}s] Waiting for game activity...")
                last_log_time = time.time()

            # Wait with exponential backoff
            wait_time = min(check_interval, self.max_wait - elapsed)
            try:
                # Use asyncio.wait_for to allow early exit if event received
                await asyncio.wait_for(self._event_received.wait(), timeout=wait_time)
                self._event_received.clear()
            except TimeoutError:
                pass  # Normal timeout, continue loop

            # Increase check interval (exponential backoff)
            check_interval = min(
                check_interval * self.backoff_multiplier,
                self.max_interval,
            )

        # Timeout reached - determine what we have
        elapsed = time.time() - start_time

        if self.state.is_fully_authenticated:
            # Got it just before timeout
            logger.info(
                f"Authentication complete at timeout: "
                f"{self.state.username} (ID: {self.state.player_id})"
            )
            return self.state

        elif self.state.has_game_data:
            # Partial success - have game data but no player identity
            logger.warning(
                f"Partial authentication after {elapsed:.1f}s: "
                f"Game ID {self.state.game_id} detected but no player identity"
            )
            logger.warning(
                "Running in READ-ONLY mode - monitoring game state without player context"
            )
            return self.state

        else:
            # Complete failure
            logger.error(f"Authentication timeout after {elapsed:.1f}s - no game activity detected")
            raise TimeoutError(
                f"No game activity detected after {self.max_wait}s. "
                "Ensure rugs.fun is loaded and player is connected."
            )
