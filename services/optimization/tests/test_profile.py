"""Tests for Strategy Profile producer."""

from datetime import datetime

import numpy as np
import pytest


class TestStrategyProfile:
    """Tests for strategy profile generation."""

    def test_profile_dataclass_creation(self):
        """Profile dataclass should be creatable with required fields."""
        from src.profiles.models import StrategyProfile

        profile = StrategyProfile(
            profile_id="test-001",
            created_at=datetime.utcnow(),
            kelly_variant="quarter",
            min_edge_threshold=0.02,
            optimal_entry_tick=200,
            expected_return=0.15,
            probability_profit=0.65,
            probability_ruin=0.05,
            var_95=0.08,
            sharpe_ratio=1.2,
        )

        assert profile.profile_id == "test-001"
        assert profile.kelly_variant == "quarter"
        assert profile.games_played == 0  # Default

    def test_profile_to_dict(self):
        """Profile should serialize to dict."""
        from src.profiles.models import StrategyProfile

        profile = StrategyProfile(
            profile_id="test-002",
            created_at=datetime.utcnow(),
            kelly_variant="half",
            min_edge_threshold=0.02,
            optimal_entry_tick=200,
            expected_return=0.20,
            probability_profit=0.70,
            probability_ruin=0.03,
            var_95=0.06,
            sharpe_ratio=1.5,
        )

        data = profile.to_dict()

        assert isinstance(data, dict)
        assert data["profile_id"] == "test-002"
        assert data["kelly_variant"] == "half"


class TestProfileProducer:
    """Tests for profile producer."""

    @pytest.fixture
    def sample_games(self):
        """Sample completed games for testing."""
        # Simulate 100 games with durations
        np.random.seed(42)
        return [
            {"game_id": f"game-{i}", "duration": int(np.random.lognormal(5.0, 0.6))}
            for i in range(100)
        ]

    def test_producer_generates_profile(self, sample_games):
        """Producer should generate valid profile from games."""
        from src.profiles.producer import ProfileProducer

        producer = ProfileProducer()
        profile = producer.generate_profile(sample_games)

        assert profile is not None
        assert profile.profile_id is not None
        assert profile.optimal_entry_tick > 0
        assert 0 < profile.probability_profit < 1
