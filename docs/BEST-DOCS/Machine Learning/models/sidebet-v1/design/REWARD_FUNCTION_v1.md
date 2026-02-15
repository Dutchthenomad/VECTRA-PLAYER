# Sidebet RL Reward Function v1.0

**Date:** January 10, 2026
**Status:** AUDITED - Ready for Implementation
**Strategy:** Sniper (single late bet)

---

## Design Principles

| Mechanic | Validated Value | Source |
|----------|-----------------|--------|
| Payout ratio | 5:1 (400% profit + original) | rugs-expert |
| Window | 40 ticks (inclusive) | Protocol spec |
| Breakeven win rate | 20% (1/5 for 5x payout) | Mathematical |
| Cooldown | ~5 ticks minimum between bets | Empirical |
| Optimal zone | Tick 200+ (18-21% win rate) | Training data analysis |
| Median rug point | Tick 138-145 | Training data analysis |

---

## Strategic Zones

| Zone | Tick Range | Empirical Win Rate | vs Breakeven |
|------|------------|-------------------|--------------|
| Very Early | 0-49 | 17.6% | -2.4% |
| Dead Zone | 50-99 | 16.0% | -4.0% |
| Marginal Early | 100-149 | 17.4% | -2.6% |
| Marginal Late | 150-199 | 15.9% | -4.1% |
| **Optimal** | **200-299** | **18.5%** | **-1.5%** |
| **Extended Optimal** | **300+** | **19.2%** | **-0.8%** |

**Note:** Win rates from 35,023 sidebets across 888 games.

---

## Reward Components

### 1. Win Rewards (Graduated by Timing Quality)

```python
WIN_REWARDS = {
    "optimal_zone":   +4.0,   # Tick 200-500: Best empirical win rate
    "marginal_late":  +3.0,   # Tick 150-199: Above median, marginal rate
    "marginal_early": +2.5,   # Tick 100-149: Some signal, marginal rate
    "dead_zone":      +2.0,   # Tick 50-99: Won despite poor timing
    "very_early":     +1.5,   # Tick 0-49: Blind luck territory
}
```

**Rationale:** All wins are positive, but timing quality matters. The model learns that *when* you win matters for consistent profitability.

### 2. Loss Penalties (Graduated by Timing Quality)

```python
LOSS_PENALTIES = {
    "optimal_zone":   -0.75,  # Tick 200+: Expected to lose some
    "marginal_late":  -0.85,  # Tick 150-199: Dead zone entry
    "marginal_early": -0.90,  # Tick 100-149: Also marginal
    "dead_zone":      -1.00,  # Tick 50-99: Worst zone - full penalty
    "very_early":     -0.50,  # Tick 0-49: Low probability anyway
}
```

**Rationale:** Losing in dead zones is penalized more heavily than losing in optimal zones.

### 3. Skip Penalties (POST-AUDIT REVISED)

```python
def calculate_skip_penalty(game_duration_ticks: int) -> float:
    """
    Penalty for not placing any bet during a game.

    CRITICAL: Must be worse than expected loss in equivalent zones
    to prevent passive strategy exploitation.
    """
    if game_duration_ticks < 40:
        return 0.0       # Unplayable - physically impossible
    elif game_duration_ticks < 90:
        return -0.30     # 1 window max
    elif game_duration_ticks < 200:
        return -0.60     # Playable
    elif game_duration_ticks < 300:
        return -1.20     # Optimal zone - MUST be worse than betting
    else:
        return -1.75     # Extended - multiple missed opportunities
```

**Rationale:**
- 18.5% of games are unplayable - **no penalty** for skipping
- Penalty scales with how many betting opportunities were missed
- CRITICAL: Skipping in optimal zone (-1.20) must be worse than betting (E[bet] = +0.13)

### 4. Near-Miss Bonus (Reward Shaping)

```python
def calculate_near_miss_bonus(ticks_to_rug: int) -> float:
    """
    Bonus for losses that were close to winning.
    Helps model understand it was on the right track.
    """
    if ticks_to_rug <= 10:      # Rug within 10 ticks of window end
        return +0.15
    elif ticks_to_rug <= 20:    # Rug within 20 ticks
        return +0.08
    else:
        return 0.0
```

**Rationale:** A bet that missed by 5 ticks is qualitatively different from one that missed by 200 ticks.

---

## Complete Implementation

```python
import math
from typing import Optional

# === CONSTANTS ===
WIN_REWARDS = {
    "optimal_zone":   +4.0,
    "marginal_late":  +3.0,
    "marginal_early": +2.5,
    "dead_zone":      +2.0,
    "very_early":     +1.5,
}

LOSS_PENALTIES = {
    "optimal_zone":   -0.75,
    "marginal_late":  -0.85,
    "marginal_early": -0.90,
    "dead_zone":      -1.00,
    "very_early":     -0.50,
}

# === HELPER FUNCTIONS ===
def categorize_tick(tick: int) -> str:
    """Categorize entry tick into strategic zone."""
    if tick >= 200:
        return "optimal_zone"
    elif tick >= 150:
        return "marginal_late"
    elif tick >= 100:
        return "marginal_early"
    elif tick >= 50:
        return "dead_zone"
    else:
        return "very_early"

def calculate_skip_penalty(game_duration_ticks: int) -> float:
    """Penalty for not placing any bet during a game."""
    if game_duration_ticks < 40:
        return 0.0
    elif game_duration_ticks < 90:
        return -0.30
    elif game_duration_ticks < 200:
        return -0.60
    elif game_duration_ticks < 300:
        return -1.20
    else:
        return -1.75

def calculate_near_miss_bonus(ticks_to_rug: int) -> float:
    """Bonus for losses that were close to winning."""
    if ticks_to_rug <= 10:
        return +0.15
    elif ticks_to_rug <= 20:
        return +0.08
    else:
        return 0.0

# === MAIN REWARD FUNCTION ===
def calculate_sidebet_reward(
    action: int,                         # 0=HOLD, 1=BET
    entry_tick: Optional[int],           # Tick when bet was placed (if any)
    game_duration: int,                  # Total ticks when game rugged
    bet_won: Optional[bool] = None,      # Did rug happen in window?
    ticks_to_rug: Optional[int] = None,  # Ticks from window end to rug
) -> float:
    """
    Calculate reward for sidebet RL agent.

    Args:
        action: 0 for HOLD (no bet), 1 for BET
        entry_tick: Tick when bet was placed (None if no bet)
        game_duration: Total game length in ticks
        bet_won: True if rug occurred within 40-tick window
        ticks_to_rug: For losses, how many ticks after window end did rug occur

    Returns:
        Float reward value
    """

    # === NO BET PLACED ===
    if action == 0 or entry_tick is None:
        return calculate_skip_penalty(game_duration)

    # === BET PLACED ===
    tick_zone = categorize_tick(entry_tick)

    if bet_won:
        return WIN_REWARDS[tick_zone]
    else:
        base_penalty = LOSS_PENALTIES[tick_zone]
        near_miss = calculate_near_miss_bonus(ticks_to_rug or 999)
        return base_penalty + near_miss
```

---

## Expected Value Analysis

| Zone | Win Rate | Win Reward | Loss Penalty | E[Reward] |
|------|----------|------------|--------------|-----------|
| Optimal (200+) | 18.5% | +4.0 | -0.75 | **+0.13** |
| Marginal Late | 15.9% | +3.0 | -0.85 | -0.24 |
| Marginal Early | 17.4% | +2.5 | -0.90 | -0.31 |
| Dead Zone | 16.0% | +2.0 | -1.00 | -0.52 |
| Very Early | 17.6% | +1.5 | -0.50 | -0.15 |

**The model should learn:** Only the optimal zone has positive expected reward.

---

## Reward Hacking Audit Results

| Vector | Severity | Status |
|--------|----------|--------|
| Skip penalty exploitation | CRITICAL | FIXED - penalties increased |
| Boundary gaming | MEDIUM | Accepted for v1 |
| Near-miss bonus | LOW | Safe - cannot create profit |
| Terminal exploitation | MEDIUM | Verified safe |
| Passive strategy | CRITICAL | FIXED - skip > loss in optimal |
| Early termination | LOW | Current design safe |
| Information leakage | LOW | Features are historical only |
| Multi-bet gaming | DEFERRED | v1 is single-bet only |

### Critical Fix Applied

**Original skip penalty (optimal zone):** -0.50
**Revised skip penalty (optimal zone):** -1.20

**Validation:**
- E[bet in optimal] = +0.13
- E[skip in optimal] = -1.20
- Difference: +1.33 in favor of betting

---

## Action Masking

```python
def get_valid_actions(state: np.ndarray) -> np.ndarray:
    """Mask invalid actions to prevent impossible exploits."""
    mask = np.ones(2, dtype=bool)  # [HOLD, BET]

    tick = int(state[0])
    active = bool(state[2])
    sidebet_active = bool(state[25])

    if not active:
        mask[1] = False  # Cannot bet if game not active

    if sidebet_active:
        mask[1] = False  # Cannot bet if already have active sidebet

    if tick < 0:
        mask[1] = False  # Cannot bet in presale

    return mask
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-10 | Initial design with reward hacking audit |

---

*Collaboratively designed: Human + Claude*
*Session: 2026-01-10*
