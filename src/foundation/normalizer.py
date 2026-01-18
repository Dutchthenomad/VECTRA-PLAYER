"""Event normalizer for Foundation Service."""

import time
from dataclasses import dataclass, field


@dataclass
class NormalizedEvent:
    """Normalized event in Foundation format."""

    type: str
    ts: int  # Unix timestamp (ms)
    game_id: str | None
    seq: int  # Sequence number
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transmission."""
        return {
            "type": self.type,
            "ts": self.ts,
            "gameId": self.game_id,
            "seq": self.seq,
            "data": self.data,
        }


class EventNormalizer:
    """
    Transforms raw rugs.fun WebSocket events to Foundation normalized format.

    Input: Raw event dicts from CDP interception
    Output: NormalizedEvent with unified type names and structure
    """

    # Event type mapping: rugs.fun -> Foundation
    EVENT_MAP = {
        "gameStateUpdate": "game.tick",
        "playerUpdate": "player.state",
        "usernameStatus": "connection.authenticated",
        "playerLeaderboardPosition": "player.leaderboard",
        "standard/newTrade": "player.trade",
        "currentSidebet": "sidebet.placed",
        "currentSidebetResult": "sidebet.result",
    }

    def __init__(self):
        self._seq = 0
        self._current_game_id: str | None = None

    def normalize(self, raw: dict) -> NormalizedEvent:
        """
        Normalize a raw event to Foundation format.

        Args:
            raw: Dict with 'event' and 'data' keys from CDP interception

        Returns:
            NormalizedEvent ready for broadcasting
        """
        event_name = raw.get("event", "unknown")
        data = raw.get("data") or {}  # Handle None explicitly

        # Increment sequence
        self._seq += 1

        # Map event type
        event_type = self.EVENT_MAP.get(event_name, f"raw.{event_name}")

        # Extract game_id (update tracker for gameStateUpdate)
        game_id = data.get("gameId", self._current_game_id)
        if event_name == "gameStateUpdate" and game_id:
            self._current_game_id = game_id

        # Build normalized data based on event type
        normalized_data = self._normalize_data(event_name, data)

        return NormalizedEvent(
            type=event_type,
            ts=int(time.time() * 1000),
            game_id=game_id,
            seq=self._seq,
            data=normalized_data,
        )

    def _normalize_data(self, event_name: str, data: dict) -> dict:
        """Normalize event data based on event type."""
        if event_name == "gameStateUpdate":
            return self._normalize_game_state(data)
        elif event_name == "playerUpdate":
            return self._normalize_player_update(data)
        elif event_name == "usernameStatus":
            return self._normalize_username_status(data)
        elif event_name == "standard/newTrade":
            return self._normalize_trade(data)
        else:
            return data  # Pass through unknown events

    def _normalize_game_state(self, data: dict) -> dict:
        """Normalize gameStateUpdate data."""
        phase = self._detect_phase(data)
        return {
            "active": data.get("active", False),
            "rugged": data.get("rugged", False),
            "price": data.get("price", 1.0),
            "tickCount": data.get("tickCount", 0),
            "cooldownTimer": data.get("cooldownTimer", 0),
            "allowPreRoundBuys": data.get("allowPreRoundBuys", False),
            "tradeCount": data.get("tradeCount", 0),
            "phase": phase,
            "gameHistory": data.get("gameHistory"),
            "leaderboard": data.get("leaderboard"),
        }

    def _normalize_player_update(self, data: dict) -> dict:
        """Normalize playerUpdate data."""
        return {
            "cash": data.get("cash", 0),
            "positionQty": data.get("positionQty", 0),
            "avgCost": data.get("avgCost", 0),
            "cumulativePnL": data.get("cumulativePnL", 0),
            "totalInvested": data.get("totalInvested", 0),
        }

    def _normalize_username_status(self, data: dict) -> dict:
        """Normalize usernameStatus data."""
        return {
            "player_id": data.get("id"),
            "username": data.get("username"),
            "hasUsername": data.get("hasUsername", False),
        }

    def _normalize_trade(self, data: dict) -> dict:
        """Normalize standard/newTrade data."""
        return {
            "username": data.get("username"),
            "type": data.get("type"),  # "buy" or "sell"
            "qty": data.get("qty"),
            "price": data.get("price"),
            "playerId": data.get("playerId"),
        }

    def _detect_phase(self, data: dict) -> str:
        """
        Detect game phase from gameStateUpdate data.

        Phase detection logic per rugs-expert spec:
        - COOLDOWN: cooldownTimer > 0
        - PRESALE: allowPreRoundBuys=True, active=False
        - ACTIVE: active=True, rugged=False
        - RUGGED: rugged=True
        """
        if data.get("cooldownTimer", 0) > 0:
            return "COOLDOWN"
        elif data.get("rugged", False):
            return "RUGGED"
        elif data.get("allowPreRoundBuys", False) and not data.get("active", False):
            return "PRESALE"
        elif data.get("active", False) and not data.get("rugged", False):
            return "ACTIVE"
        else:
            return "UNKNOWN"
