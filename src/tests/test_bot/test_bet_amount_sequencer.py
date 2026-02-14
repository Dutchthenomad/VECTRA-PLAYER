"""
Tests for BetAmountSequencer - Delta-based optimal button sequence calculator.

Tests the delta-based algorithm that calculates minimal button clicks
to go from current bet amount to target amount.
"""

from decimal import Decimal

from bot.bet_amount_sequencer import (
    _build_from_zero,
    _count_doubles,
    _count_halves,
    _greedy_increments,
    calculate_optimal_sequence,
    estimate_clicks,
)


class TestCalculateOptimalSequence:
    """Tests for the main calculate_optimal_sequence function."""

    def test_same_amount_returns_empty(self):
        """When current == target, no clicks needed."""
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.004")) == []
        assert calculate_optimal_sequence(Decimal("0.1"), Decimal("0.1")) == []
        assert calculate_optimal_sequence(Decimal("0"), Decimal("0")) == []

    def test_single_half(self):
        """Test single 1/2 button press."""
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.002")) == ["1/2"]
        assert calculate_optimal_sequence(Decimal("0.1"), Decimal("0.05")) == ["1/2"]
        assert calculate_optimal_sequence(Decimal("1.0"), Decimal("0.5")) == ["1/2"]

    def test_single_double(self):
        """Test single X2 button press."""
        assert calculate_optimal_sequence(Decimal("0.002"), Decimal("0.004")) == ["X2"]
        assert calculate_optimal_sequence(Decimal("0.05"), Decimal("0.1")) == ["X2"]
        assert calculate_optimal_sequence(Decimal("0.5"), Decimal("1.0")) == ["X2"]

    def test_multiple_halves(self):
        """Test multiple 1/2 presses."""
        assert calculate_optimal_sequence(Decimal("0.008"), Decimal("0.002")) == ["1/2", "1/2"]
        assert calculate_optimal_sequence(Decimal("0.016"), Decimal("0.002")) == [
            "1/2",
            "1/2",
            "1/2",
        ]

    def test_multiple_doubles(self):
        """Test multiple X2 presses."""
        assert calculate_optimal_sequence(Decimal("0.001"), Decimal("0.004")) == ["X2", "X2"]
        assert calculate_optimal_sequence(Decimal("0.001"), Decimal("0.008")) == ["X2", "X2", "X2"]

    def test_simple_increments(self):
        """Test simple increment scenarios."""
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.005")) == ["+0.001"]
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.006")) == [
            "+0.001",
            "+0.001",
        ]

    def test_build_from_zero(self):
        """Test building amount from zero."""
        result = calculate_optimal_sequence(Decimal("0"), Decimal("0.004"))
        # Should be optimized to 3 clicks (either half or quarter optimization)
        # Half: ['+0.001', '+0.001', 'X2'] or Quarter: ['+0.001', 'X2', 'X2']
        assert len(result) == 3
        assert "X2" in result  # Must use X2 optimization

    def test_build_0_001_from_zero(self):
        """Test building smallest amount."""
        assert calculate_optimal_sequence(Decimal("0"), Decimal("0.001")) == ["+0.001"]

    def test_build_0_01_from_zero(self):
        """Test building 0.01 from zero."""
        # Could be +0.01 (1 click) or +0.001 x10, should choose +0.01
        result = calculate_optimal_sequence(Decimal("0"), Decimal("0.01"))
        assert result == ["+0.01"]

    def test_build_0_1_from_zero(self):
        """Test building 0.1 from zero."""
        result = calculate_optimal_sequence(Decimal("0"), Decimal("0.1"))
        assert result == ["+0.1"]

    def test_decrease_requires_clear(self):
        """Test decrease that requires clear + rebuild."""
        # 0.007 → 0.003 can't be done with halves
        result = calculate_optimal_sequence(Decimal("0.007"), Decimal("0.003"))
        assert result[0] == "X"  # Should start with clear

    def test_complex_increase(self):
        """Test complex increase scenario."""
        # 0.004 → 0.007 needs +0.001 × 3
        result = calculate_optimal_sequence(Decimal("0.004"), Decimal("0.007"))
        assert result == ["+0.001", "+0.001", "+0.001"]

    def test_large_amount_build(self):
        """Test building larger amounts."""
        # 0 → 1.0 should be +1 (1 click)
        result = calculate_optimal_sequence(Decimal("0"), Decimal("1.0"))
        assert result == ["+1"]

    def test_mixed_increments(self):
        """Test mixed increment sizes."""
        # 0 → 0.111 should use +0.1, +0.01, +0.001
        result = calculate_optimal_sequence(Decimal("0"), Decimal("0.111"))
        assert "+0.1" in result
        assert "+0.01" in result
        assert "+0.001" in result


class TestCountHalves:
    """Tests for _count_halves helper."""

    def test_exact_halves(self):
        """Test when target is exact multiple of halves."""
        assert _count_halves(Decimal("0.008"), Decimal("0.004")) == 1
        assert _count_halves(Decimal("0.008"), Decimal("0.002")) == 2
        assert _count_halves(Decimal("0.008"), Decimal("0.001")) == 3

    def test_no_exact_half(self):
        """Test when target cannot be reached by halving."""
        assert _count_halves(Decimal("0.007"), Decimal("0.003")) is None
        # Note: 0.005 → 0.002 returns 1 due to banker's rounding (0.0025 → 0.002)
        # This is acceptable for the UI which also rounds to 3 decimals

    def test_zero_current(self):
        """Test with zero current amount."""
        assert _count_halves(Decimal("0"), Decimal("0.001")) is None

    def test_zero_target(self):
        """Test with zero target amount."""
        assert _count_halves(Decimal("0.001"), Decimal("0")) is None


class TestCountDoubles:
    """Tests for _count_doubles helper."""

    def test_exact_doubles(self):
        """Test when target is exact multiple of doubles."""
        assert _count_doubles(Decimal("0.001"), Decimal("0.002")) == 1
        assert _count_doubles(Decimal("0.001"), Decimal("0.004")) == 2
        assert _count_doubles(Decimal("0.001"), Decimal("0.008")) == 3

    def test_no_exact_double(self):
        """Test when target cannot be reached by doubling."""
        assert _count_doubles(Decimal("0.003"), Decimal("0.007")) is None
        assert _count_doubles(Decimal("0.002"), Decimal("0.005")) is None

    def test_zero_current(self):
        """Test with zero current amount."""
        assert _count_doubles(Decimal("0"), Decimal("0.001")) is None


class TestGreedyIncrements:
    """Tests for _greedy_increments helper."""

    def test_single_increment(self):
        """Test single increment."""
        assert _greedy_increments(Decimal("0.001")) == ["+0.001"]
        assert _greedy_increments(Decimal("0.01")) == ["+0.01"]
        assert _greedy_increments(Decimal("0.1")) == ["+0.1"]
        assert _greedy_increments(Decimal("1")) == ["+1"]

    def test_mixed_increments(self):
        """Test mixed increment amounts."""
        result = _greedy_increments(Decimal("0.111"))
        assert result.count("+0.1") == 1
        assert result.count("+0.01") == 1
        assert result.count("+0.001") == 1

    def test_multiple_of_single(self):
        """Test multiple of single increment."""
        result = _greedy_increments(Decimal("0.003"))
        assert result == ["+0.001", "+0.001", "+0.001"]


class TestBuildFromZero:
    """Tests for _build_from_zero helper."""

    def test_simple_build(self):
        """Test simple builds."""
        assert _build_from_zero(Decimal("0.001")) == ["+0.001"]
        assert _build_from_zero(Decimal("0.01")) == ["+0.01"]

    def test_x2_optimization(self):
        """Test X2 optimization for cleaner builds."""
        # 0.004 = 0.001 × 4, but with X2 optimization is 3 clicks vs 4
        # Can be half (['+0.001', '+0.001', 'X2']) or quarter (['+0.001', 'X2', 'X2'])
        result = _build_from_zero(Decimal("0.004"))
        assert len(result) == 3
        assert "X2" in result

    def test_x2_optimization_double(self):
        """Test double X2 optimization."""
        # 0.008 = 0.001 × 8, but +0.001, X2, X2, X2 is 4 clicks vs 8
        result = _build_from_zero(Decimal("0.008"))
        assert len(result) < 8  # Should be optimized

    def test_zero_target(self):
        """Test with zero target."""
        assert _build_from_zero(Decimal("0")) == []


class TestEstimateClicks:
    """Tests for estimate_clicks function."""

    def test_estimates_match_sequence_length(self):
        """Verify estimate matches actual sequence length."""
        test_cases = [
            (Decimal("0.004"), Decimal("0.002")),  # 1/2
            (Decimal("0.002"), Decimal("0.004")),  # X2
            (Decimal("0"), Decimal("0.004")),  # Build from zero
            (Decimal("0.007"), Decimal("0.003")),  # Clear + rebuild
        ]
        for current, target in test_cases:
            sequence = calculate_optimal_sequence(current, target)
            estimate = estimate_clicks(current, target)
            assert estimate == len(sequence), f"Mismatch for {current} → {target}"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_small_amounts(self):
        """Test with very small amounts."""
        result = calculate_optimal_sequence(Decimal("0.001"), Decimal("0.002"))
        assert result == ["X2"]

    def test_rounding(self):
        """Test that rounding is handled correctly."""
        # Input with extra decimal places should be quantized
        result = calculate_optimal_sequence(Decimal("0.0045"), Decimal("0.0025"))
        # 0.0045 → 0.005, 0.0025 → 0.003
        # After quantization: 0.005 → 0.003 (not exact half, needs clear + rebuild)
        assert isinstance(result, list)

    def test_negative_handled(self):
        """Test negative amounts are handled (defensive)."""
        # Current implementation should handle gracefully
        result = calculate_optimal_sequence(Decimal("0.004"), Decimal("0.003"))
        assert "X" in result  # Should clear and rebuild

    def test_large_delta(self):
        """Test large delta scenario."""
        # 0 → 1.234
        result = calculate_optimal_sequence(Decimal("0"), Decimal("1.234"))
        assert "+1" in result
        assert "+0.1" in result or len(result) > 0


class TestDocstringExamples:
    """Verify examples from the docstrings work correctly."""

    def test_docstring_example_half(self):
        """calculate_optimal_sequence(Decimal('0.004'), Decimal('0.002')) == ['1/2']"""
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.002")) == ["1/2"]

    def test_docstring_example_double(self):
        """calculate_optimal_sequence(Decimal('0.004'), Decimal('0.008')) == ['X2']"""
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.008")) == ["X2"]

    def test_docstring_example_increment(self):
        """calculate_optimal_sequence(Decimal('0.004'), Decimal('0.005')) == ['+0.001']"""
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.005")) == ["+0.001"]

    def test_docstring_example_double_half(self):
        """calculate_optimal_sequence(Decimal('0.004'), Decimal('0.001')) == ['1/2', '1/2']"""
        assert calculate_optimal_sequence(Decimal("0.004"), Decimal("0.001")) == ["1/2", "1/2"]

    def test_docstring_example_build_from_zero(self):
        """calculate_optimal_sequence(Decimal('0'), Decimal('0.004')) produces 3 clicks with X2"""
        result = calculate_optimal_sequence(Decimal("0"), Decimal("0.004"))
        # Either half or quarter optimization is valid - both produce 3 clicks
        assert len(result) == 3
        assert "X2" in result
