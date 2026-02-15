"""Tests for survival analysis module."""

import numpy as np
import pytest


class TestSurvivalAnalysis:
    """Tests for survival analysis functions."""

    @pytest.fixture
    def sample_durations(self):
        """Sample game durations for testing."""
        # Realistic game durations (ticks)
        return np.array([100, 150, 200, 180, 250, 300, 120, 175, 220, 280])

    def test_compute_survival_curve_returns_dict(self, sample_durations):
        """Survival curve should return dict with expected keys."""
        from src.analyzers.survival import compute_survival_curve

        result = compute_survival_curve(sample_durations)

        assert isinstance(result, dict)
        assert "times" in result
        assert "survival" in result
        assert "n_at_risk" in result

    def test_survival_curve_decreases_monotonically(self, sample_durations):
        """Survival probability should decrease over time."""
        from src.analyzers.survival import compute_survival_curve

        result = compute_survival_curve(sample_durations)

        # Survival should never increase
        for i in range(1, len(result["survival"])):
            assert result["survival"][i] <= result["survival"][i - 1]

    def test_conditional_probability_returns_array(self, sample_durations):
        """Conditional probability should return numpy array."""
        from src.analyzers.survival import compute_conditional_probability

        result = compute_conditional_probability(sample_durations, window_size=40)

        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_find_optimal_entry_window(self, sample_durations):
        """Should find optimal entry window with edge."""
        from src.analyzers.survival import find_optimal_entry_window

        result = find_optimal_entry_window(sample_durations)

        assert isinstance(result, dict)
        assert "optimal_entry_tick" in result
