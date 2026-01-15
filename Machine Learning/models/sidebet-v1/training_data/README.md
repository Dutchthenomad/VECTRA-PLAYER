# Sidebet RL Training Data

**Generated:** 2026-01-10
**Source:** ~/rugs_data/events_parquet/doc_type=complete_game/

---

## Data Files

### games_with_prices.parquet (PRIMARY - For RL Training)

**943 unique games** with real tick-by-tick price arrays

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | string | Unique game identifier (YYYYMMDD-uuid) |
| `timestamp` | int | Unix timestamp (ms) when game ended |
| `duration_ticks` | int | Total game length in ticks |
| `prices` | list[float] | **Real tick-by-tick multipliers** |
| `peak_multiplier` | float | Highest price reached |
| `peak_tick` | int | Tick when peak occurred |
| `ticks_after_peak` | int | Ticks from peak to rug |
| `final_price` | float | Price at rug |
| `is_unplayable` | bool | True if duration < 40 ticks |
| `game_version` | string | Protocol version |

**Usage:**
```python
import pandas as pd
games = pd.read_parquet('games_with_prices.parquet')

# Access tick-by-tick prices for first game
prices = games.iloc[0]['prices']
print(f"Game duration: {len(prices)} ticks")
print(f"First 5 prices: {prices[:5]}")
```

---

### games_deduplicated.parquet (Summary Stats Only)

**888 unique games** (deduplicated by gameId from 11,130 raw records)

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | string | Unique game identifier (YYYYMMDD-uuid) |
| `timestamp` | int | Unix timestamp (ms) when game ended |
| `duration_ticks` | int | Total game length in ticks |
| `peak_multiplier` | float | Highest price reached |
| `peak_tick` | int | Tick when peak occurred |
| `ticks_after_peak` | int | Ticks from peak to rug |
| `final_price` | float | Price at rug |
| `sidebet_count` | int | Number of sidebets in this game |
| `game_version` | string | Protocol version |
| `is_unplayable` | bool | True if duration < 40 ticks |
| `betting_windows_possible` | int | Max consecutive bets possible |

### sidebets_deduplicated.parquet

**35,023 unique sidebets** across all games

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | string | Game this bet was placed in |
| `game_duration` | int | Duration of the game (ticks) |
| `player_id` | string | Player who placed the bet |
| `username` | string | Player username |
| `bet_amount` | float | SOL wagered |
| `x_payout` | int | Payout multiplier (5 or 10) |
| `start_tick` | int | Tick when bet was placed |
| `end_tick` | int | Tick when window closes (start + 40) |
| `price_at_bet` | float | Price when bet was placed |
| `timestamp` | int | Unix timestamp (ms) |
| `type` | string | Event type (placed/payout) |
| `bet_won` | bool | **True if game rugged within window** |
| `ticks_to_rug` | int | Positive = ticks before window end, Negative = ticks after |
| `was_near_miss` | bool | Lost but rug within 10 ticks of window |
| `bet_in_optimal_zone` | bool | Entry tick >= 200 |

---

## Key Statistics

### Game Duration Distribution
```
Median:  144 ticks
Mean:    199.5 ticks
Min:     2 ticks
Max:     1,815 ticks
```

### Percentiles
```
 5th:   10 ticks
10th:   20 ticks
25th:   55 ticks
50th:  144 ticks (median)
75th:  285 ticks
90th:  453 ticks
95th:  572 ticks
99th:  875 ticks
```

### Unplayable Games
- **18.5%** of games rug before tick 40 (no betting window possible)
- **20.7%** rug before tick 45 (no 2nd bet possible)

### Overall Sidebet Win Rate
- **17.6%** win rate (above 16.67% breakeven for 5x payout)

### Win Rate by Entry Tick

| Tick Range | Win Rate | vs Breakeven | Sample Size |
|------------|----------|--------------|-------------|
| 0-50 | 17.6% | +0.9% | 22,456 |
| 50-100 | 16.0% | -0.7% | 2,723 |
| 100-150 | 17.4% | +0.7% | 2,161 |
| 150-200 | 15.9% | -0.8% | 1,646 |
| **200-250** | **18.6%** | +1.9% | 1,469 |
| **250-300** | **18.5%** | +1.8% | 1,109 |
| **300-400** | **19.6%** | +2.9% | 1,476 |
| **400-500** | **18.5%** | +1.8% | 886 |
| **500+** | **20.8%** | +4.1% | 1,029 |

**Optimal betting zone: Tick 200+** (consistently above breakeven)

---

## Strategic Zones (Cross-Reference)

### For Sidebet RL (THIS MODEL)
- **Dead zones (avoid sidebets):** Ticks 50-100, 150-200 (below 16.67% breakeven)
- **Optimal zones (place sidebets):** Tick 200+ (18-21% win rate)

### For Future Trading RL (SEPARATE MODEL - NOT YET)
- **Safe zones (hold for 2x gains):** Ticks 50-100, 150-200
  - Lower rug probability = safer to hold trading positions
  - These are the INVERSE of sidebet optimal zones
- **Danger zones (exit positions):** Tick 200+ (higher rug probability)

**NOTE:** We are training the SIDEBET model first. Trading model comes later once we've validated the training methodology prevents reward hacking and ensures the model actually learns to play.

---

## Execution Architecture

The trained model will play through the existing tkinter UI like a "player piano":
- Uses `BotActionInterface` (Phase 6 complete)
- Interacts with real game via button clicks
- No direct API access - must play like a human would
- This prevents reward hacking and ensures realistic behavior

---

## Deduplication Notes

The raw `complete_game` Parquet files contain duplicates because:

1. **Rolling 10-game window**: Each `gameStateUpdate` includes the last 10 completed games
2. **Dual-broadcast on rug**: Server sends 2 events within 500ms on game end

**Deduplication ratio:** 12.5x (11,130 raw → 888 unique)

Always use `game_id` as the primary key for deduplication.

---

## Usage

```python
import pandas as pd

# Load data
games = pd.read_parquet('games_deduplicated.parquet')
sidebets = pd.read_parquet('sidebets_deduplicated.parquet')

# Filter to playable games
playable = games[~games['is_unplayable']]

# Filter to winning bets
winners = sidebets[sidebets['bet_won']]

# Win rate in optimal zone
optimal = sidebets[sidebets['bet_in_optimal_zone']]
print(f"Optimal zone win rate: {optimal['bet_won'].mean():.1%}")
```

---

## Source Data Location

Raw (with duplicates):
```
~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet
```

This deduplicated data:
```
/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/training_data/
```
