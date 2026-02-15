# 16 - Bayesian Rug Signal

## Purpose

Real-time probability detection for rug timing:
1. Event gap signal detection
2. Base probability curve by tick
3. Likelihood ratio updates
4. Bayesian probability fusion

## Dependencies

```python
from collections import deque
from dataclasses import dataclass
from typing import Optional
import time
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Bayesian Rug Signal System                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Event Stream Input                               │    │
│  │  gameStateUpdate → RugGapSignalDetector.on_event()                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Gap Detection                                     │    │
│  │                                                                      │    │
│  │  Normal:        <350ms interval  →  LR = 1.0x                       │    │
│  │  Warning:       350-450ms        →  LR = 1.5x                       │    │
│  │  High Alert:    450-500ms        →  LR = 3.0x                       │    │
│  │  Gap Detected:  >500ms           →  LR = 8.0x                       │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Bayesian Update                                   │    │
│  │                                                                      │    │
│  │  P_base = get_base_rug_probability(tick_count)                      │    │
│  │  odds_prior = P_base / (1 - P_base)                                 │    │
│  │  odds_posterior = odds_prior × likelihood_ratio × prior_mult        │    │
│  │  P_posterior = odds_posterior / (1 + odds_posterior)                │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Decision Output                                   │    │
│  │                                                                      │    │
│  │  P(rug) > 70% + sidebet window open → Consider betting              │    │
│  │  Gap signal provides 500ms (2 tick) early warning                   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Gap Signal Result

```python
# src/analysis/bayesian_rug_signal.py

from dataclasses import dataclass

@dataclass
class GapSignalResult:
    """Result of gap signal analysis."""
    gap_detected: bool
    gap_duration_ms: float
    confidence: float  # 0.0 to 1.0
    likelihood_ratio: float  # Multiply with base probability
```

### 2. Rug Gap Signal Detector

```python
class RugGapSignalDetector:
    """
    Detects the pre-rug event gap signal.

    Key findings from analysis of 1,132 rug events:
    - Normal: ~4 gameStateUpdate events per second (250ms intervals)
    - Pre-rug: Event rate drops ~50% in the 500-250ms before rug
    - At -250ms: Event rate drops ~95% (almost no events)

    This detector tracks inter-event timing and outputs a likelihood ratio
    for Bayesian probability updates.
    """

    # Empirical thresholds from analysis of 1,132 rug events
    NORMAL_INTERVAL_MS = 250  # Expected tick interval
    WARNING_THRESHOLD_MS = 350  # Gap suggesting potential rug (1.4x normal)
    HIGH_ALERT_THRESHOLD_MS = 450  # Strong rug signal (1.8x normal)

    # Likelihood ratios for Bayesian updates (empirically derived)
    # These multiply the base probability P(rug | tick_count)
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
        self.last_event_time: Optional[float] = None

    def on_event(self, event_type: str, timestamp: Optional[float] = None) -> GapSignalResult:
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
        if event_type != 'gameStateUpdate':
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

    def _evaluate_signal(self, interval_ms: float) -> GapSignalResult:
        """Evaluate the signal strength based on interval."""

        if interval_ms >= 500:
            # Strong gap signal - 95% of rugs show this at -250ms
            return self._make_result(
                gap_detected=True,
                gap_duration_ms=interval_ms,
                confidence=0.95,
                likelihood_ratio=self.LIKELIHOOD_GAP_DETECTED
            )
        elif interval_ms >= self.HIGH_ALERT_THRESHOLD_MS:
            # High alert - significant deviation from normal
            return self._make_result(
                gap_detected=True,
                gap_duration_ms=interval_ms,
                confidence=0.7,
                likelihood_ratio=self.LIKELIHOOD_HIGH_ALERT
            )
        elif interval_ms >= self.WARNING_THRESHOLD_MS:
            # Warning - moderate deviation
            return self._make_result(
                gap_detected=False,
                gap_duration_ms=interval_ms,
                confidence=0.4,
                likelihood_ratio=self.LIKELIHOOD_WARNING
            )
        else:
            # Normal operation
            return self._make_result(
                gap_detected=False,
                gap_duration_ms=interval_ms,
                confidence=0.1,
                likelihood_ratio=self.LIKELIHOOD_NORMAL
            )
```

### 3. Base Probability Curve

```python
# Base probability curve from rugs-expert knowledge base
# P(rug in next 40 ticks | current tick count)
BASE_PROBABILITY_CURVE = [
    (0, 0.15), (10, 0.18), (20, 0.22), (30, 0.25), (40, 0.28),
    (50, 0.32), (60, 0.35), (70, 0.38), (80, 0.42), (90, 0.45),
    (100, 0.50), (120, 0.55), (140, 0.60), (160, 0.65), (180, 0.70),
    (200, 0.74), (220, 0.77), (240, 0.80), (260, 0.83), (280, 0.86),
    (300, 0.88), (350, 0.91), (400, 0.93), (450, 0.95), (500, 0.96)
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
```

### 4. Bayesian Probability Computation

```python
def compute_bayesian_rug_probability(
    tick_count: int,
    gap_signal: GapSignalResult,
    prior_multiplier: float = 1.0
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
```

### 5. Rolling Statistics

```python
def get_rolling_stats(self) -> dict:
    """Get rolling statistics on tick intervals."""
    if len(self.recent_intervals) < 3:
        return {'mean': 250, 'std': 0, 'count': len(self.recent_intervals)}

    intervals = list(self.recent_intervals)
    mean = sum(intervals) / len(intervals)
    variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)
    std = variance ** 0.5

    return {
        'mean': mean,
        'std': std,
        'count': len(intervals),
        'min': min(intervals),
        'max': max(intervals)
    }

def check_current_gap(self, timestamp: Optional[float] = None) -> GapSignalResult:
    """
    Check if we're currently in a gap (no recent events).
    Call this on a timer to detect gaps even when no events arrive.

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
```

## Signal Thresholds

| Interval | Signal Level | Likelihood Ratio | Action |
|----------|--------------|------------------|--------|
| < 350ms | Normal | 1.0x | No change |
| 350-450ms | Warning | 1.5x | +50% rug probability |
| 450-500ms | High Alert | 3.0x | +200% rug probability |
| > 500ms | Gap Detected | 8.0x | Strong bet signal |

## Probability by Tick Count

| Tick | Base P(rug) | With 8x LR | Decision |
|------|-------------|------------|----------|
| 100 | 50% | 89% | Bet if gap |
| 150 | 62% | 93% | Bet if gap |
| 200 | 74% | 96% | Bet if gap |
| 250 | 81% | 97% | Bet if gap |
| 300 | 88% | 98% | Bet if gap |

## Integration Example

```python
# Real-time usage with WebSocket events
detector = RugGapSignalDetector()

def on_game_state_update(event: dict):
    """Called on each gameStateUpdate event."""
    result = detector.on_event('gameStateUpdate')

    # Compute Bayesian probability
    tick_count = event.get('tick', 0)
    prob = compute_bayesian_rug_probability(tick_count, result)

    # Decision logic
    if prob > 0.70 and sidebet_window_open:
        consider_placing_bet()

    if result.gap_detected:
        # 500ms warning before likely rug
        alert_imminent_rug(result.gap_duration_ms)

# Timer-based gap check (50ms interval)
def check_gaps():
    result = detector.check_current_gap()
    if result.gap_detected:
        # No events received - likely approaching rug
        handle_gap_signal(result)
```

## Gotchas

1. **Event Filtering**: Only `gameStateUpdate` events count for gap detection.

2. **Timer Required**: Call `check_current_gap()` on a timer (50ms) to detect gaps when no events arrive.

3. **Game Reset**: Call `detector.reset()` on game end/start to clear state.

4. **Probability Bounds**: Output is clamped to 0.05-0.99 to avoid numerical issues.

5. **Empirical Basis**: All thresholds derived from analysis of 1,132 rug events.

6. **Two-Tick Warning**: The 500ms gap provides approximately 2 ticks of warning before rug.

7. **Confidence vs Likelihood**: Confidence is for UI display; likelihood_ratio is for Bayesian math.
