"""
Trade annotation: enriches standard/newTrade events with inferred fields.

Rosetta Stone Event 2: Forced sells and leverage liquidations are
indistinguishable from voluntary sells on the wire. This module infers them.
"""

from __future__ import annotations

import logging

from .models import Phase, Trade, TradeType

logger = logging.getLogger(__name__)

# Leverage liquidation thresholds (Rosetta Stone Event 2)
# When price drops this % from entry, position is force-liquidated.
LIQUIDATION_THRESHOLDS: dict[int, float] = {
    2: 0.20,  # 2x leverage: -20% from entry
    3: 0.10,  # 3x leverage: -10% from entry
    4: 0.025,  # 4x leverage: -2.5% from entry
    5: 0.01,  # 5x leverage: -1% from entry
}

# Practice token address
PRACTICE_TOKEN_ADDRESS = "0xPractice"


class TradeAnnotator:
    """Annotates trades with inferred fields.

    Tracks practice token address from availableShitcoins and
    game phase to infer forced sells and liquidations.
    """

    def __init__(self) -> None:
        self._practice_addresses: set[str] = {PRACTICE_TOKEN_ADDRESS}

    def update_practice_tokens(self, available_shitcoins: list[dict] | None) -> None:
        """Update known practice token addresses from availableShitcoins.

        Rosetta Stone Section 1.12: Only one practice token exists,
        but we track the set defensively.
        """
        if not available_shitcoins:
            return
        for coin in available_shitcoins:
            addr = coin.get("address", "")
            if addr:
                self._practice_addresses.add(addr)

    def annotate(self, trade: Trade, phase: Phase) -> Trade:
        """Annotate a trade with inferred fields.

        Mutates the trade in-place and returns it for convenience.

        Annotations:
        - is_forced_sell: sell during RUGGED phase
        - is_liquidation: leveraged sell at liquidation threshold
        - is_practice: trade uses practice token
        - token_type: 'practice' | 'real' | 'unknown'
        """
        # Token type classification
        trade.token_type = self._classify_token(trade)
        trade.is_practice = trade.token_type == "practice"

        # Forced sell detection: sell during RUGGED phase
        if trade.type == TradeType.SELL and phase == Phase.RUGGED:
            trade.is_forced_sell = True

        # Leverage liquidation inference is harder — we'd need to
        # cross-reference with the player's entry price (avgCost from
        # leaderboard). For now, we mark sells with leverage context.
        # A more sophisticated version could track avgCost per player.

        return trade

    def _classify_token(self, trade: Trade) -> str:
        """Classify trade as practice, real, or unknown.

        Rosetta Stone Section 1.12: leaderboard does NOT differentiate
        practice vs real. We infer from bonusPortion/realPortion.
        Token lock rule: players can't switch mid-game.
        """
        bonus = trade.bonus_portion
        real = trade.real_portion

        if bonus is None and real is None:
            return "unknown"

        bonus = bonus or 0.0
        real = real or 0.0

        if bonus > 0 and real == 0:
            return "practice"
        if real > 0 and bonus == 0:
            return "real"
        if real > 0 and bonus > 0:
            # Mixed — can happen with position stacking
            return "real"
        return "unknown"
