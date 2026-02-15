# Sidebet RL Design Session - January 10, 2026

## Session Summary

This document captures the findings from our collaborative design session for the sidebet RL training system.

---

## Training Data Created

**Location:** `/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/training_data/`

| File | Records | Description |
|------|---------|-------------|
| `games_deduplicated.parquet` | 888 games | Unique games by gameId |
| `sidebets_deduplicated.parquet` | 35,023 bets | All player sidebets with outcomes |

**Deduplication:** Raw 11,130 records → 888 unique (12.5x ratio due to rolling window)

---

## Key Statistics

### Game Duration
- **Median:** 144 ticks
- **Mean:** 199.5 ticks
- **Range:** 2 - 1,815 ticks
- **Unplayable (<40 ticks):** 18.5%

### Win Rate by Entry Tick
| Tick Range | Win Rate | vs 16.67% Breakeven |
|------------|----------|---------------------|
| 0-50 | 17.6% | +0.9% ✅ |
| 50-100 | 16.0% | -0.7% ❌ DEAD ZONE |
| 100-150 | 17.4% | +0.7% ✅ |
| 150-200 | 15.9% | -0.8% ❌ DEAD ZONE |
| 200-300 | 18.5% | +1.8% ✅ |
| 300-500 | 19.2% | +2.5% ✅ |

**Dead zones (50-100, 150-200):** Below breakeven for sidebets, but SAFE for trading positions.

---

## Player Behavior Analysis

### Volume Distribution
- **64% of all bets placed at tick 0-50**
- Players use martingale-like sequential betting
- **NO players exclusively bet late** - everyone who bets at 200+ also bets early

### Martingale Success Rates
| Bets per Game | Win ≥1 | Notes |
|---------------|--------|-------|
| 1 bet | 43.1% | Single attempt |
| 3 bets | 50.6% | Cover more ground |
| 5 bets | 55.1% | Good coverage |
| 7 bets | 63.9% | High coverage |

### Player Segments
- **Winning players (>20%):** 69 players, avg entry tick 86
- **Losing players (<15%):** 100 players, avg entry tick 101
- **Key insight:** Winning players are MORE CONSISTENT (lower std dev)

---

## Two Viable Strategies

### Strategy A: "Sniper" (TRAIN FIRST)
- Wait until tick 200-300
- Place ONE bet
- 18-20% individual win rate
- Simpler reward function
- No bankroll management needed

### Strategy B: "Martingale" (TRAIN LATER)
- Start at tick 0-50
- Sequential bets with 45-tick gaps
- 40-60% per-game success rate
- Requires bankroll state tracking

**Decision:** Train Strategy A first to validate methodology, then evolve to B.

---

## Strategic Zones Cross-Reference

| Zone | Sidebet Strategy | Trading Strategy |
|------|------------------|------------------|
| Tick 0-50 | Marginal (17.6%) | Risky |
| Tick 50-100 | AVOID (16.0%) | SAFE for 2x |
| Tick 100-150 | Marginal (17.4%) | Moderate |
| Tick 150-200 | AVOID (15.9%) | SAFE for 2x |
| Tick 200-300 | OPTIMAL (18.5%) | Exit positions |
| Tick 300+ | EXCELLENT (19%+) | High risk |

**Inverse relationship:** Dead zones for sidebets = safe zones for trading.

---

## Reward Function Design (PENDING)

To be completed collaboratively. Key considerations:
1. Unplayable games (18.5%) - no penalty for skipping
2. Graduated rewards for 1st/2nd/3rd/4th bet success
3. Escalating penalty for refusing to play playable games
4. Use Bayesian priors for reward shaping

---

## Execution Architecture

Model plays through existing tkinter UI ("player piano"):
- Uses `BotActionInterface` (Phase 6 complete)
- No direct API access
- Must click buttons like a human
- Prevents reward hacking

---

## Next Steps

1. Complete reward function design (collaborative)
2. Define observation space
3. Create Gymnasium environment
4. Train Strategy A baseline
5. Evaluate and iterate

---

## Open Research Questions (Tangential Study)

These patterns are noted for future investigation but NOT included in v1 model:

1. **Cross-game correlations:** Long/high games → short following games?
2. **Active player count effects:** More players → different rug timing?
3. **Final tick remainder:** Non-zero final price - pattern in PRNG?
4. **Server treasury management:** 53% house edge enforcement?

See: `PRNG_EXPLORATION_SESSION.md` (if created)

---

*Session Date: January 10, 2026*
*Participants: Human + Claude*
