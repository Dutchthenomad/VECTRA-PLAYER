"""Tests for trade annotation (forced sell, liquidation, practice/real inference)."""

from src.models import Phase, Trade, TradeType
from src.trade_annotator import TradeAnnotator


class TestTokenClassification:
    """Test practice vs real token inference."""

    def setup_method(self):
        self.annotator = TradeAnnotator()

    def test_real_sol_trade(self):
        trade = Trade(
            id="t1",
            game_id="g1",
            player_id="p1",
            type=TradeType.BUY,
            amount=0.03,
            bonus_portion=0,
            real_portion=0.03,
        )
        self.annotator.annotate(trade, Phase.ACTIVE)
        assert trade.token_type == "real"
        assert trade.is_practice is False

    def test_practice_trade(self):
        trade = Trade(
            id="t2",
            game_id="g1",
            player_id="p1",
            type=TradeType.BUY,
            amount=0.794,
            bonus_portion=0.794,
            real_portion=0,
        )
        self.annotator.annotate(trade, Phase.ACTIVE)
        assert trade.token_type == "practice"
        assert trade.is_practice is True

    def test_mixed_trade_classified_as_real(self):
        """Position stacking can produce mixed portions."""
        trade = Trade(
            id="t3",
            game_id="g1",
            player_id="p1",
            type=TradeType.SELL,
            amount=1.0,
            bonus_portion=0.5,
            real_portion=0.5,
        )
        self.annotator.annotate(trade, Phase.ACTIVE)
        assert trade.token_type == "real"

    def test_unknown_when_no_portions(self):
        """Shorts may not have bonusPortion/realPortion."""
        trade = Trade(
            id="t4",
            game_id="g1",
            player_id="p1",
            type=TradeType.SHORT_OPEN,
            amount=0.2,
            bonus_portion=None,
            real_portion=None,
        )
        self.annotator.annotate(trade, Phase.ACTIVE)
        assert trade.token_type == "unknown"

    def test_zero_both_portions(self):
        trade = Trade(
            id="t5",
            game_id="g1",
            player_id="p1",
            type=TradeType.BUY,
            amount=0.0,
            bonus_portion=0.0,
            real_portion=0.0,
        )
        self.annotator.annotate(trade, Phase.ACTIVE)
        assert trade.token_type == "unknown"


class TestForcedSellDetection:
    """Test forced sell inference during rug."""

    def setup_method(self):
        self.annotator = TradeAnnotator()

    def test_sell_during_rug_is_forced(self):
        trade = Trade(
            id="t1",
            game_id="g1",
            player_id="p1",
            type=TradeType.SELL,
            amount=0.5,
            price=0.001784,
        )
        self.annotator.annotate(trade, Phase.RUGGED)
        assert trade.is_forced_sell is True

    def test_sell_during_active_is_voluntary(self):
        trade = Trade(
            id="t2",
            game_id="g1",
            player_id="p1",
            type=TradeType.SELL,
            amount=0.5,
            price=1.5,
        )
        self.annotator.annotate(trade, Phase.ACTIVE)
        assert trade.is_forced_sell is False

    def test_buy_during_rug_not_forced_sell(self):
        """Only sells can be forced."""
        trade = Trade(
            id="t3",
            game_id="g1",
            player_id="p1",
            type=TradeType.BUY,
            amount=0.1,
        )
        self.annotator.annotate(trade, Phase.RUGGED)
        assert trade.is_forced_sell is False

    def test_short_close_during_rug_not_flagged(self):
        """Forced sell flag only applies to type=sell."""
        trade = Trade(
            id="t4",
            game_id="g1",
            player_id="p1",
            type=TradeType.SHORT_CLOSE,
            amount=0.2,
        )
        self.annotator.annotate(trade, Phase.RUGGED)
        assert trade.is_forced_sell is False


class TestPracticeTokenUpdate:
    """Test updating practice token list from availableShitcoins."""

    def setup_method(self):
        self.annotator = TradeAnnotator()

    def test_update_from_available_shitcoins(self):
        coins = [
            {"address": "0xPractice", "ticker": "FREE", "name": "Practice SOL"},
        ]
        self.annotator.update_practice_tokens(coins)
        # The default "0xPractice" is already tracked, so this is a no-op
        assert "0xPractice" in self.annotator._practice_addresses

    def test_update_with_none(self):
        """Should handle None gracefully."""
        self.annotator.update_practice_tokens(None)

    def test_update_with_empty(self):
        """Should handle empty list gracefully."""
        self.annotator.update_practice_tokens([])
