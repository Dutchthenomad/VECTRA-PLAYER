"""Tests for Bayesian rug signal module."""


class TestBayesianRugSignal:
    """Tests for Bayesian rug signal detector."""

    def test_gap_detector_initialization(self):
        """Gap detector should initialize with default thresholds."""
        from src.analyzers.bayesian import RugGapSignalDetector

        detector = RugGapSignalDetector()

        assert detector.NORMAL_INTERVAL_MS == 250
        assert detector.WARNING_THRESHOLD_MS == 350
        assert detector.HIGH_ALERT_THRESHOLD_MS == 450

    def test_on_event_returns_gap_signal_result(self):
        """on_event should return GapSignalResult dataclass."""
        from src.analyzers.bayesian import GapSignalResult, RugGapSignalDetector

        detector = RugGapSignalDetector()
        result = detector.on_event("gameStateUpdate", timestamp=0.0)

        assert isinstance(result, GapSignalResult)
        assert hasattr(result, "gap_detected")
        assert hasattr(result, "likelihood_ratio")

    def test_gap_detection_on_500ms_gap(self):
        """500ms gap should trigger gap detection."""
        from src.analyzers.bayesian import RugGapSignalDetector

        detector = RugGapSignalDetector()

        # First event sets baseline
        detector.on_event("gameStateUpdate", timestamp=0.0)

        # 500ms gap - should trigger detection
        result = detector.on_event("gameStateUpdate", timestamp=0.5)

        assert result.gap_detected is True
        assert result.likelihood_ratio == 8.0

    def test_get_base_rug_probability(self):
        """Base probability should increase with tick count."""
        from src.analyzers.bayesian import get_base_rug_probability

        prob_50 = get_base_rug_probability(50)
        prob_200 = get_base_rug_probability(200)
        prob_400 = get_base_rug_probability(400)

        assert prob_50 < prob_200 < prob_400
        assert 0.0 < prob_50 < 1.0

    def test_compute_bayesian_rug_probability(self):
        """Bayesian update should apply likelihood ratio."""
        from src.analyzers.bayesian import (
            RugGapSignalDetector,
            compute_bayesian_rug_probability,
        )

        detector = RugGapSignalDetector()
        detector.on_event("gameStateUpdate", timestamp=0.0)
        signal = detector.on_event("gameStateUpdate", timestamp=0.5)  # 500ms gap

        prob = compute_bayesian_rug_probability(tick_count=200, gap_signal=signal)

        # With 8x likelihood ratio, probability should be higher than base
        assert prob > 0.5
        assert prob < 1.0
