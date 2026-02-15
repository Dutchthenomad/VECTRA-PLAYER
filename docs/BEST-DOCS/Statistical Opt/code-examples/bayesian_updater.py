"""
Bayesian Rug Signal Updater

Real-time probability update based on WebSocket event frequency analysis.
Detects pre-rug event gaps that provide ~500ms early warning.

Usage:
    from bayesian_updater import (
        RugGapSignalDetector,
        compute_bayesian_rug_probability,
        get_base_rug_probability,
    )

    detector = RugGapSignalDetector()

    def on_game_tick(event):
        signal = detector.on_event('gameStateUpdate')
        prob = compute_bayesian_rug_probability(tick_count=event['tick'], gap_signal=signal)
        if prob > 0.70:
            consider_placing_bet()
"""

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class GapSignalResult:
    """Result of gap signal analysis."""

    gap_detected: bool
    gap_duration_ms: float
    confidence: float  # 0.0 to 1.0
    likelihood_ratio: float  # Multiply with base probability


class RugGapSignalDetector:
    """
    Detects the pre-rug event gap signal.

    Key findings from analysis of 1,132 rug events:
    - Normal: ~4 gameStateUpdate events per second (250ms intervals)
    - Pre-rug: Event rate drops ~50% in the 500-250ms before rug
    - At -250ms: Event rate drops ~95% (almost no events)

    This provides a 2-tick (500ms) early warning signal.

    Example:
        detector = RugGapSignalDetector()

        # Process incoming events
        for event in websocket_stream:
            result = detector.on_event('gameStateUpdate')
            if result.gap_detected:
                print(f"GAP! Likelihood: {result.likelihood_ratio}x")

        # Or check current gap on timer
        result = detector.check_current_gap()
    """

    # Empirical thresholds from analysis of 1,132 rug events
    NORMAL_INTERVAL_MS = 250  # Expected tick interval
    WARNING_THRESHOLD_MS = 350  # Gap suggesting potential rug (1.4x normal)
    HIGH_ALERT_THRESHOLD_MS = 450  # Strong rug signal (1.8x normal)

    # Likelihood ratios for Bayesian updates (empirically derived)
    LIKELIHOOD_NORMAL = 1.0  # No change to base probability
    LIKELIHOOD_WARNING = 1.5  # 50% increase in rug probability
    LIKELIHOOD_HIGH_ALERT = 3.0  # 3x increase in rug probability
    LIKELIHOOD_GAP_DETECTED = 8.0  # Strong signal when >500ms gap

    def __init__(self, window_size: int = 20):
        """
        Initialize detector.

        Args:
            window_size: Number of recent intervals to track for variance calc
        """
        self.window_size = window_size
        self.recent_intervals: deque = deque(maxlen=window_size)
        self.last_event_time: float | None = None

    def on_event(self, event_type: str, timestamp: float | None = None) -> GapSignalResult:
        """
        Process an incoming WebSocket event.

        Args:
            event_type: The event type (e.g., 'gameStateUpdate')
            timestamp: Event timestamp in seconds (defaults to now)

        Returns:
            GapSignalResult with current signal state
        """
        now = timestamp or time.time()

        # Only track gameStateUpdate for the primary signal
        if event_type != "gameStateUpdate":
            return self._make_result(False, 0, 0.0, self.LIKELIHOOD_NORMAL)

        if self.last_event_time is None:
            self.last_event_time = now
            return self._make_result(False, 0, 0.0, self.LIKELIHOOD_NORMAL)

        # Calculate interval since last gameStateUpdate
        interval_ms = (now - self.last_event_time) * 1000
        self.last_event_time = now

        # Track for rolling statistics
        self.recent_intervals.append(interval_ms)

        # Determine signal level
        return self._evaluate_signal(interval_ms)

    def check_current_gap(self, timestamp: float | None = None) -> GapSignalResult:
        """
        Check if we're currently in a gap (no recent events).

        Call this on a timer (50ms) to detect gaps even when no events arrive.

        Args:
            timestamp: Current time in seconds (defaults to now)

        Returns:
            GapSignalResult with current gap state
        """
        now = timestamp or time.time()

        if self.last_event_time is None:
            return self._make_result(False, 0, 0.0, self.LIKELIHOOD_NORMAL)

        gap_ms = (now - self.last_event_time) * 1000
        return self._evaluate_signal(gap_ms)

    def _evaluate_signal(self, interval_ms: float) -> GapSignalResult:
        """Evaluate the signal strength based on interval."""

        if interval_ms >= 500:
            # Strong gap signal - 95% of rugs show this at -250ms
            return self._make_result(
                gap_detected=True,
                gap_duration_ms=interval_ms,
                confidence=0.95,
                likelihood_ratio=self.LIKELIHOOD_GAP_DETECTED,
            )
        elif interval_ms >= self.HIGH_ALERT_THRESHOLD_MS:
            # High alert - significant deviation from normal
            return self._make_result(
                gap_detected=True,
                gap_duration_ms=interval_ms,
                confidence=0.7,
                likelihood_ratio=self.LIKELIHOOD_HIGH_ALERT,
            )
        elif interval_ms >= self.WARNING_THRESHOLD_MS:
            # Warning - moderate deviation
            return self._make_result(
                gap_detected=False,
                gap_duration_ms=interval_ms,
                confidence=0.4,
                likelihood_ratio=self.LIKELIHOOD_WARNING,
            )
        else:
            # Normal operation
            return self._make_result(
                gap_detected=False,
                gap_duration_ms=interval_ms,
                confidence=0.1,
                likelihood_ratio=self.LIKELIHOOD_NORMAL,
            )

    def _make_result(
        self, gap_detected: bool, gap_duration_ms: float, confidence: float, likelihood_ratio: float
    ) -> GapSignalResult:
        return GapSignalResult(
            gap_detected=gap_detected,
            gap_duration_ms=gap_duration_ms,
            confidence=confidence,
            likelihood_ratio=likelihood_ratio,
        )

    def get_rolling_stats(self) -> dict:
        """Get rolling statistics on tick intervals."""
        if len(self.recent_intervals) < 3:
            return {"mean": 250, "std": 0, "count": len(self.recent_intervals)}

        intervals = list(self.recent_intervals)
        mean = sum(intervals) / len(intervals)
        variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)
        std = variance**0.5

        return {
            "mean": mean,
            "std": std,
            "count": len(intervals),
            "min": min(intervals),
            "max": max(intervals),
        }

    def reset(self):
        """Reset detector state (call on game end/start)."""
        self.recent_intervals.clear()
        self.last_event_time = None


# Base probability curve from rugs-expert knowledge base
# P(rug in next 40 ticks | current tick count)
BASE_PROBABILITY_CURVE = [
    (0, 0.15),
    (10, 0.18),
    (20, 0.22),
    (30, 0.25),
    (40, 0.28),
    (50, 0.32),
    (60, 0.35),
    (70, 0.38),
    (80, 0.42),
    (90, 0.45),
    (100, 0.50),
    (120, 0.55),
    (140, 0.60),
    (160, 0.65),
    (180, 0.70),
    (200, 0.74),
    (220, 0.77),
    (240, 0.80),
    (260, 0.83),
    (280, 0.86),
    (300, 0.88),
    (350, 0.91),
    (400, 0.93),
    (450, 0.95),
    (500, 0.96),
]


def get_base_rug_probability(tick_count: int) -> float:
    """
    Get base probability of rug in next 40 ticks given current tick count.

    Uses linear interpolation between empirical data points.

    Args:
        tick_count: Current game tick

    Returns:
        Probability between 0.15 and 0.96
    """
    if tick_count < 0:
        return 0.10
    if tick_count > 500:
        return 0.96

    # Linear interpolation
    for i in range(len(BASE_PROBABILITY_CURVE) - 1):
        tick1, prob1 = BASE_PROBABILITY_CURVE[i]
        tick2, prob2 = BASE_PROBABILITY_CURVE[i + 1]

        if tick1 <= tick_count <= tick2:
            ratio = (tick_count - tick1) / (tick2 - tick1)
            return prob1 + (prob2 - prob1) * ratio

    return 0.96


def compute_bayesian_rug_probability(
    tick_count: int, gap_signal: GapSignalResult, prior_multiplier: float = 1.0
) -> float:
    """
    Compute Bayesian probability of rug in next 40 ticks.

    Uses odds form of Bayes' theorem:
        odds_posterior = odds_prior × likelihood_ratio

    Args:
        tick_count: Current game tick
        gap_signal: Signal from RugGapSignalDetector
        prior_multiplier: Additional prior adjustment (e.g., from other features)

    Returns:
        Updated probability (clamped to 0.05-0.99)

    Example:
        detector = RugGapSignalDetector()
        signal = detector.on_event('gameStateUpdate')
        prob = compute_bayesian_rug_probability(150, signal)
        print(f"P(rug in 40 ticks): {prob:.1%}")
    """
    base_prob = get_base_rug_probability(tick_count)

    # Apply likelihood ratio from gap signal
    # Using odds form: odds_posterior = odds_prior * likelihood_ratio
    odds_prior = base_prob / (1 - base_prob)
    odds_posterior = odds_prior * gap_signal.likelihood_ratio * prior_multiplier

    # Convert back to probability
    prob_posterior = odds_posterior / (1 + odds_posterior)

    # Clamp to reasonable bounds
    return max(0.05, min(0.99, prob_posterior))


class BayesianSidebetAdvisor:
    """
    Advisory system combining gap signal with tick-based probability.

    Provides actionable recommendations for sidebet timing.
    """

    def __init__(self, bet_threshold: float = 0.70):
        """
        Initialize advisor.

        Args:
            bet_threshold: Minimum probability to recommend betting
        """
        self.detector = RugGapSignalDetector()
        self.bet_threshold = bet_threshold

    def update(self, tick_count: int, event_type: str = "gameStateUpdate") -> dict:
        """
        Update with new event and get recommendation.

        Args:
            tick_count: Current game tick
            event_type: WebSocket event type

        Returns:
            Dict with recommendation and analysis
        """
        signal = self.detector.on_event(event_type)
        prob = compute_bayesian_rug_probability(tick_count, signal)

        # Decision logic
        in_optimal_zone = tick_count >= 200
        should_bet = prob >= self.bet_threshold and in_optimal_zone

        return {
            "tick": tick_count,
            "base_probability": get_base_rug_probability(tick_count),
            "gap_signal": {
                "detected": signal.gap_detected,
                "duration_ms": signal.gap_duration_ms,
                "likelihood_ratio": signal.likelihood_ratio,
                "confidence": signal.confidence,
            },
            "posterior_probability": prob,
            "in_optimal_zone": in_optimal_zone,
            "recommendation": "BET" if should_bet else "WAIT",
            "edge": prob - (1 / 6) if prob > (1 / 6) else 0,  # Edge over breakeven
        }

    def reset(self):
        """Reset for new game."""
        self.detector.reset()


# Example usage
if __name__ == "__main__":
    print("Bayesian Rug Signal Demo")
    print("=" * 50)

    detector = RugGapSignalDetector()

    # Simulate normal game ticks
    print("\nSimulating normal game (250ms intervals):")
    t = 0
    for i in range(10):
        result = detector.on_event("gameStateUpdate", t)
        if i > 0:
            prob = compute_bayesian_rug_probability(tick_count=100 + i, gap_signal=result)
            print(
                f"  Tick {100 + i}: interval={result.gap_duration_ms:.0f}ms, "
                f"LR={result.likelihood_ratio:.1f}x, P(rug)={prob:.1%}"
            )
        t += 0.250  # 250ms intervals

    # Simulate pre-rug gap
    print("\nSimulating pre-rug gap (500ms then rug):")
    t += 0.500  # 500ms gap
    result = detector.on_event("gameStateUpdate", t)
    prob = compute_bayesian_rug_probability(tick_count=110, gap_signal=result)
    print(
        f"  GAP DETECTED: interval={result.gap_duration_ms:.0f}ms, "
        f"LR={result.likelihood_ratio:.1f}x, P(rug)={prob:.1%}"
    )
    print(f"  Signal: gap_detected={result.gap_detected}, confidence={result.confidence:.0%}")

    # Show probability curve
    print("\nBase probability curve (no gap signal):")
    for tick in [50, 100, 150, 200, 250, 300, 400]:
        base = get_base_rug_probability(tick)
        print(f"  Tick {tick}: {base:.1%}")
