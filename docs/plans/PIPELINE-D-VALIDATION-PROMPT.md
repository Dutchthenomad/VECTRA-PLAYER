# Pipeline D Validation & Planning Session

**Date:** 2025-12-28
**Purpose:** Validate Pipeline A-C implementation before building Pipeline D Training Data Pipeline
**Method:** Record 5 real games, verify data capture, refine Pipeline D design

---

## Project Context

**VECTRA-PLAYER** is a rugs.fun game viewer and RL training data capture system. The goal is to capture human gameplay (button presses, game state, player state) and generate training data for reinforcement learning bots.

### Repository
- **Location:** `/home/nomad/Desktop/VECTRA-PLAYER`
- **Tests:** 1149 passing
- **Data Store:** Parquet files at `~/rugs_data/events_parquet/`

### Key Files
- `CLAUDE.md` - Project overview
- `.claude/scratchpad.md` - Session state
- `docs/plans/GLOBAL-DEVELOPMENT-PLAN.md` - Master development plan
- `scripts/FLOW-CHARTS/observation-space-design.md` - 36-feature observation space spec

---

## What Has Been Built (Pipelines A-C)

### Pipeline A: Server State Validation ✅
- Validated 22 server state features against WebSocket protocol
- Fields: tick, price, game_phase, rugpool, session stats, connected_players
- Source events: `gameStateUpdate`, `playerUpdate`

### Pipeline B: ButtonEvent Capture ✅
- Human button presses captured with full game context
- ButtonEvent dataclass: `src/models/events/button_event.py`
- Stored as `doc_type=button_event` in Parquet
- 204 ButtonEvents captured so far

### Pipeline C: Player Action Features ✅ (2025-12-28)
- Implemented `time_in_position` tracking in LiveStateProvider
- Added execution tracking fields to ButtonEvent:
  - `execution_tick`, `execution_price`, `trade_id`
  - `client_timestamp`, `latency_ms`
  - `time_in_position`
- 11 new tests, 1149 total passing

---

## Observation Space Schema (36 Features)

### Category 1: Game State (9 features)
| Field | Source | Status |
|-------|--------|--------|
| tick | gameStateUpdate.tickCount | ✅ |
| price | gameStateUpdate.price | ✅ |
| game_phase | Derived (0-3) | ✅ |
| cooldown_timer_ms | gameStateUpdate.cooldownTimer | ✅ |
| allow_pre_round_buys | gameStateUpdate.allowPreRoundBuys | ✅ |
| active | gameStateUpdate.active | ✅ |
| rugged | gameStateUpdate.rugged | ✅ |
| connected_players | gameStateUpdate.connectedPlayers | ✅ |
| game_id | gameStateUpdate.gameId | ✅ |

### Category 2: Player State (5 features) - AUTH REQUIRED
| Field | Source | Status |
|-------|--------|--------|
| balance | playerUpdate.cash | ✅ |
| position_qty | playerUpdate.positionQty | ✅ |
| avg_entry_price | playerUpdate.avgCost | ✅ |
| cumulative_pnl | playerUpdate.cumulativePnL | ✅ |
| total_invested | playerUpdate.totalInvested | ✅ |

### Category 3: Rugpool (3 features)
| Field | Source | Status |
|-------|--------|--------|
| rugpool_amount | gameStateUpdate.rugpool.rugpoolAmount | ✅ |
| rugpool_threshold | gameStateUpdate.rugpool.threshold | ✅ |
| instarug_count | gameStateUpdate.rugpool.instarugCount | ✅ |

### Category 4: Session Stats (6 features)
| Field | Source | Status |
|-------|--------|--------|
| average_multiplier | gameStateUpdate.averageMultiplier | ✅ |
| count_2x | gameStateUpdate.count2x | ✅ |
| count_10x | gameStateUpdate.count10x | ✅ |
| count_50x | gameStateUpdate.count50x | ✅ |
| count_100x | gameStateUpdate.count100x | ✅ |
| highest_today | gameStateUpdate.highestToday | ✅ |

### Category 5: Derived (6 features)
| Field | Formula | Status |
|-------|---------|--------|
| price_velocity | (price[t] - price[t-1]) / dt | ⚠️ Needs validation |
| price_acceleration | (vel[t] - vel[t-1]) / dt | ⚠️ Needs validation |
| unrealized_pnl | (price - avgCost) * positionQty | ⚠️ Needs validation |
| position_pnl_pct | (price - avgCost) / avgCost | ⚠️ Needs validation |
| rugpool_ratio | rugpoolAmount / threshold | ⚠️ Needs validation |
| balance_at_risk_pct | positionQty / (balance + value) | ⚠️ Needs validation |

### Category 6: Player Action (3 features)
| Field | Source | Status |
|-------|--------|--------|
| time_in_position | LiveStateProvider.time_in_position | ✅ Implemented, needs validation |
| ticks_since_last_action | ButtonEvent tracking | ✅ Validated (range 1-517) |
| bet_amount | UI state | ✅ Validated (17/20 nonzero) |

### Category 7: Execution Tracking (5 features)
| Field | Source | Status |
|-------|--------|--------|
| execution_tick | standard/newTrade.tickIndex | ✅ Implemented, needs validation |
| execution_price | standard/newTrade.price | ✅ Implemented, needs validation |
| trade_id | standard/newTrade.id | ✅ Implemented, needs validation |
| client_timestamp | Local timestamp | ✅ Implemented, needs validation |
| latency_ms | server_ts - client_timestamp | ✅ Implemented, needs validation |

---

## Current Data in Parquet

```
Data inventory:
  ws_event:      31,744 events
  button_event:     204 events
  player_action:      2 events
  server_state:       1 event
  game_tick:          1 event

Existing games (top 10):
  20251228-84337efe6f9541c6: 2,136 events
  20251228-af0af8a572c04048: 1,444 events
  20251228-91f15109e4af4ca7: 1,024 events
  20251221-26c57824c8dd4476: 941 events
  20251228-777127b1a11f4a63: 876 events
  ...

WS Event types:
  gameStateUpdate:      13,596
  gameStatePlayerUpdate: 13,566
  ping:                  2,239
  standard/newTrade:       910
  playerUpdate:            225
  buyOrder:                 33
```

---

## What Needs Validation

### Critical Questions Before Pipeline D

1. **Are ButtonEvents capturing all Pipeline C fields?**
   - Is `time_in_position` being populated?
   - Is `execution_tick` being filled from server response?
   - Is `latency_ms` being calculated correctly?

2. **Is player state (balance, position_qty) available at each tick?**
   - Only 225 `playerUpdate` events vs 13,596 `gameStateUpdate`
   - How do we interpolate player state between updates?

3. **Are execution tracking fields being populated?**
   - When a BUY button is pressed, do we capture the matching `standard/newTrade`?
   - Is `trade_id` linking ButtonEvent to the broadcast trade?

4. **Is episode boundary detection working?**
   - Can we detect game start/end from `game_id` changes?
   - Can we detect rug events (rugged=True)?

5. **Are derived features calculated correctly?**
   - price_velocity, price_acceleration need price history
   - unrealized_pnl needs position and current price
   - rugpool_ratio needs rugpool data

---

## Validation Plan

### Step 1: Record 5 Games
```bash
cd /home/nomad/Desktop/VECTRA-PLAYER
./run.sh
# Play 5 complete games, pressing BUY/SELL buttons
```

### Step 2: Verify ButtonEvent Capture
```python
import duckdb, json
result = duckdb.query("""
    SELECT raw_json
    FROM read_parquet('/home/nomad/rugs_data/events_parquet/doc_type=button_event/**/*.parquet')
    ORDER BY ts DESC LIMIT 10
""").fetchall()
for r in result:
    d = json.loads(r[0])
    print(f"Button: {d.get('button_id')}")
    print(f"  time_in_position: {d.get('time_in_position')}")
    print(f"  execution_tick: {d.get('execution_tick')}")
    print(f"  latency_ms: {d.get('latency_ms')}")
```

### Step 3: Verify Game State Capture
```python
import duckdb, json
# Check if all fields are present in gameStateUpdate
result = duckdb.query("""
    SELECT raw_json
    FROM read_parquet('/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet')
    WHERE event_name = 'gameStateUpdate'
    ORDER BY ts DESC LIMIT 1
""").fetchone()
data = json.loads(result[0])['data']
required_fields = ['tickCount', 'price', 'active', 'rugged', 'cooldownTimer',
                   'allowPreRoundBuys', 'connectedPlayers', 'gameId', 'rugpool',
                   'averageMultiplier', 'count2x', 'count10x', 'count50x',
                   'count100x', 'highestToday']
for f in required_fields:
    print(f"{f}: {'✅' if f in data else '❌ MISSING'}")
```

### Step 4: Verify Player State Capture
```python
# Check playerUpdate frequency
result = duckdb.query("""
    SELECT game_id, COUNT(*) as player_updates
    FROM read_parquet('/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet')
    WHERE event_name = 'playerUpdate'
    GROUP BY game_id
    ORDER BY player_updates DESC LIMIT 5
""").fetchall()
print("playerUpdate frequency per game:")
for r in result:
    print(f"  {r[0]}: {r[1]} updates")
```

---

## Questions for Planning Agent

1. **Data Sparsity:** With only 225 playerUpdate events across 31K+ ws_events, how should we handle player state for ticks without updates?
   - Option A: Forward-fill (carry last known value)
   - Option B: Interpolate (estimate between updates)
   - Option C: Only generate training samples at playerUpdate ticks

2. **Execution Tracking:** The execution tracking fields (execution_tick, latency_ms) require matching ButtonEvents to server responses. Is this currently implemented, or do we need to add it?

3. **Derived Features:** Where should derived features (velocity, acceleration, PnL) be calculated?
   - Option A: At capture time (in LiveStateProvider)
   - Option B: At training time (in ObservationBuilder)
   - Option C: Both (capture raw, derive on export)

4. **Episode Definition:** What constitutes a complete episode for RL training?
   - Full game (start → rug)?
   - Single position (open → close)?
   - Fixed window (N ticks)?

5. **Action Labels:** Should training data include:
   - Only ACTION buttons (BUY, SELL, SIDEBET)?
   - All buttons including bet adjustments?
   - Implicit HOLD actions between button presses?

6. **Reward Design:** What reward signal should we use?
   - P&L at position close?
   - P&L at each tick?
   - Survival bonus (avoiding rug)?

---

## Expected Outputs

After validation session:

1. **Validation Report:** Document which Pipeline C features are working/broken
2. **Data Gap Analysis:** List missing or sparse data that needs addressing
3. **Refined Pipeline D Plan:** Updated implementation plan based on real data
4. **Test Fixtures:** Sample events for Pipeline D unit tests

---

## Commands Reference

```bash
# Run app
cd /home/nomad/Desktop/VECTRA-PLAYER && ./run.sh

# Run tests
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short

# Query Parquet data
.venv/bin/python -c "import duckdb; print(duckdb.query('SELECT ...').fetchall())"

# Check data inventory
.venv/bin/python -c "import duckdb; print(duckdb.query('SELECT doc_type, COUNT(*) FROM read_parquet(\"/home/nomad/rugs_data/events_parquet/**/*.parquet\") GROUP BY doc_type').fetchall())"
```

---

*This prompt was generated to facilitate Pipeline D planning validation.*
