"""Tests for Kelly criterion sizing module."""

import pytest


class TestKellyCriterion:
    """Tests for Kelly criterion calculations."""

    def test_kelly_criterion_with_edge(self):
        """Kelly should return positive fraction when edge exists."""
        from src.analyzers.kelly import kelly_criterion

        # 20% win rate, 5:1 payout (breakeven is 16.67%)
        fraction = kelly_criterion(win_rate=0.20, payout=5.0)

        assert fraction > 0
        assert fraction < 1.0

    def test_kelly_criterion_no_edge(self):
        """Kelly should return 0 when no edge."""
        from src.analyzers.kelly import kelly_criterion

        # 15% win rate, 5:1 payout (below 16.67% breakeven)
        fraction = kelly_criterion(win_rate=0.15, payout=5.0)

        assert fraction == 0.0

    def test_fractional_kelly(self):
        """Fractional Kelly should reduce bet size."""
        from src.analyzers.kelly import fractional_kelly, kelly_criterion

        full = kelly_criterion(win_rate=0.20, payout=5.0)
        quarter = fractional_kelly(win_rate=0.20, fraction=0.25, payout=5.0)

        assert quarter == pytest.approx(full * 0.25, rel=0.01)

    def test_calculate_edge(self):
        """Edge calculation should return expected metrics."""
        from src.analyzers.kelly import calculate_edge

        edge = calculate_edge(win_rate=0.20, payout=5.0)

        assert isinstance(edge, dict)
        assert "expected_value" in edge
        assert "breakeven_win_rate" in edge
        assert edge["edge_exists"] is True
        assert edge["breakeven_win_rate"] == pytest.approx(1 / 6, rel=0.01)

    def test_recommend_bet_size(self):
        """Bet recommendation should cap at 5% of bankroll."""
        from src.analyzers.kelly import recommend_bet_size

        result = recommend_bet_size(
            win_rate=0.50,  # Very high edge
            bankroll=0.1,
            payout=5.0,
            risk_tolerance="moderate",
        )

        assert isinstance(result, dict)
        assert result["recommended_bet_size"] <= 0.1 * 0.05  # Max 5%
        assert result["capped"] is True  # Should be capped
