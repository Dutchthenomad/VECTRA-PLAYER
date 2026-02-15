"""Tests for game phase detection state machine."""

from src.models import Phase
from src.phase_detector import PhaseDetector

# ---------------------------------------------------------------------------
# Phase detection (stateless, single-event)
# ---------------------------------------------------------------------------


class TestDetectPhase:
    """Test the priority-ordered phase detection logic."""

    def setup_method(self):
        self.detector = PhaseDetector()

    def test_active_game(self):
        data = {"active": True, "rugged": False, "cooldownTimer": 0}
        assert self.detector.detect(data) == Phase.ACTIVE

    def test_rugged_game(self):
        """rugged=True takes priority even when active=True (the overlap window)."""
        data = {"active": True, "rugged": True, "cooldownTimer": 0}
        assert self.detector.detect(data) == Phase.RUGGED

    def test_rugged_after_active_false(self):
        data = {"active": False, "rugged": True, "cooldownTimer": 0}
        assert self.detector.detect(data) == Phase.RUGGED

    def test_cooldown_settlement(self):
        """Timer > 10000 without allowPreRoundBuys = settlement buffer."""
        data = {"cooldownTimer": 14900, "allowPreRoundBuys": False}
        assert self.detector.detect(data) == Phase.COOLDOWN

    def test_presale_with_timer(self):
        """Timer <= 10000 with allowPreRoundBuys = presale countdown."""
        data = {"cooldownTimer": 8500, "allowPreRoundBuys": True}
        assert self.detector.detect(data) == Phase.PRESALE

    def test_presale_near_zero_timer(self):
        """allowPreRoundBuys=True with timer=0 edge case (superposition boundary)."""
        data = {"cooldownTimer": 0, "allowPreRoundBuys": True}
        assert self.detector.detect(data) == Phase.PRESALE

    def test_unknown_no_signals(self):
        data = {}
        assert self.detector.detect(data) == Phase.UNKNOWN

    def test_unknown_all_false(self):
        data = {
            "active": False,
            "rugged": False,
            "cooldownTimer": 0,
            "allowPreRoundBuys": False,
        }
        assert self.detector.detect(data) == Phase.UNKNOWN

    def test_active_priority_over_timer(self):
        """active=True takes priority over cooldownTimer > 0."""
        data = {"active": True, "rugged": False, "cooldownTimer": 5000}
        assert self.detector.detect(data) == Phase.ACTIVE

    def test_rugged_priority_over_everything(self):
        """rugged=True takes priority over ALL other signals."""
        data = {
            "active": True,
            "rugged": True,
            "cooldownTimer": 5000,
            "allowPreRoundBuys": True,
        }
        assert self.detector.detect(data) == Phase.RUGGED


# ---------------------------------------------------------------------------
# State transitions (stateful, multi-event sequences)
# ---------------------------------------------------------------------------


class TestPhaseTransitions:
    """Test the stateful game lifecycle tracking."""

    def setup_method(self):
        self.detector = PhaseDetector()

    def test_full_game_lifecycle(self):
        """Simulate: COOLDOWN -> PRESALE -> ACTIVE -> RUGGED -> COOLDOWN (new game)."""
        game_id = "20260206-game1"
        next_game_id = "20260206-game2"

        # COOLDOWN (settlement buffer)
        t1 = self.detector.process(
            {
                "gameId": game_id,
                "cooldownTimer": 14900,
                "allowPreRoundBuys": False,
            }
        )
        assert t1 is not None  # First event always transitions from UNKNOWN
        assert t1.new_phase == Phase.COOLDOWN
        assert self.detector.current_phase == Phase.COOLDOWN

        # PRESALE (timer drops, buys enabled)
        t2 = self.detector.process(
            {
                "gameId": game_id,
                "cooldownTimer": 9500,
                "allowPreRoundBuys": True,
            }
        )
        assert t2 is not None
        assert t2.previous_phase == Phase.COOLDOWN
        assert t2.new_phase == Phase.PRESALE
        assert t2.is_new_game is False

        # ACTIVE (game starts)
        t3 = self.detector.process(
            {
                "gameId": game_id,
                "active": True,
                "rugged": False,
                "cooldownTimer": 0,
                "tickCount": 0,
            }
        )
        assert t3 is not None
        assert t3.new_phase == Phase.ACTIVE
        assert t3.is_new_game is False

        # Still ACTIVE (no transition)
        t4 = self.detector.process(
            {
                "gameId": game_id,
                "active": True,
                "rugged": False,
                "cooldownTimer": 0,
                "tickCount": 50,
            }
        )
        assert t4 is None  # No transition

        # RUGGED (first rug-transition broadcast with seed reveal)
        t5 = self.detector.process(
            {
                "gameId": game_id,
                "active": True,
                "rugged": True,
                "cooldownTimer": 0,
                "provablyFair": {
                    "serverSeedHash": "abc123",
                    "serverSeed": "revealed_seed_here",
                    "version": "v3",
                },
            }
        )
        assert t5 is not None
        assert t5.new_phase == Phase.RUGGED
        assert t5.is_seed_reveal is True
        assert t5.is_new_game is False
        assert self.detector.rug_count == 1

        # COOLDOWN with NEW game ID (second rug-transition broadcast)
        t6 = self.detector.process(
            {
                "gameId": next_game_id,
                "cooldownTimer": 15000,
                "allowPreRoundBuys": False,
                "provablyFair": {
                    "serverSeedHash": "new_hash_for_game2",
                    "version": "v3",
                },
            }
        )
        assert t6 is not None
        assert t6.new_phase == Phase.COOLDOWN
        assert t6.is_new_game is True
        assert t6.previous_game_id == game_id
        assert t6.new_game_id == next_game_id
        assert self.detector.games_seen == 1

    def test_no_transition_on_repeated_phase(self):
        """Multiple ACTIVE ticks should not produce transitions."""
        self.detector.process(
            {
                "gameId": "game1",
                "active": True,
                "rugged": False,
            }
        )
        # Second active tick
        result = self.detector.process(
            {
                "gameId": "game1",
                "active": True,
                "rugged": False,
            }
        )
        assert result is None

    def test_rug_without_seed_reveal(self):
        """Rug event without serverSeed should not flag is_seed_reveal."""
        self.detector.process(
            {
                "gameId": "game1",
                "active": True,
                "rugged": False,
            }
        )
        t = self.detector.process(
            {
                "gameId": "game1",
                "active": True,
                "rugged": True,
                "provablyFair": {
                    "serverSeedHash": "hash",
                    "version": "v3",
                },
            }
        )
        assert t is not None
        assert t.is_seed_reveal is False
        assert self.detector.rug_count == 1

    def test_game_id_change_detected(self):
        """Game ID change should be flagged even without phase change."""
        self.detector.process(
            {
                "gameId": "game1",
                "cooldownTimer": 14000,
            }
        )
        t = self.detector.process(
            {
                "gameId": "game2",
                "cooldownTimer": 15000,
            }
        )
        assert t is not None
        assert t.is_new_game is True
        assert self.detector.games_seen == 1

    def test_stats(self):
        self.detector.process(
            {
                "gameId": "game1",
                "active": True,
                "rugged": False,
            }
        )
        stats = self.detector.get_stats()
        assert stats["current_phase"] == "ACTIVE"
        assert stats["current_game_id"] == "game1"
        assert stats["rug_count"] == 0
        assert stats["games_seen"] == 0
