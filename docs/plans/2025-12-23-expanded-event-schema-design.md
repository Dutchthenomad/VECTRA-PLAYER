# Expanded Event Schema Design

**Date:** December 23, 2025
**Status:** APPROVED
**Schema Version:** 2.0.0
**GitHub Issue:** #136

---

## Overview

This document defines the expanded event schema for VECTRA-PLAYER that captures:
1. **Player Actions** - Human/bot button presses with full context
2. **Server State** - Authoritative wallet, position, PnL updates
3. **Action-Outcome Correlation** - Link actions to server confirmations
4. **Latency Tracking** - Client → Server → Confirmation timing
5. **Other Player Tracking** - Exceptional player identification for ML training
6. **Toast Notification Triggers** - Real-time alerts for player advantages

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER ACTION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │   Button    │───▶│   Client    │───▶│   Server    │───▶│  playerUpdate│ │
│   │   Press     │    │  Timestamp  │    │  Timestamp  │    │  Confirmation│ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                  │                  │                  │          │
│         │     t_client     │    t_server      │   t_confirmed    │          │
│         ▼                  ▼                  ▼                  ▼          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      player_action (doc_type)                       │  │
│   │  - action_id, button, amount                                        │  │
│   │  - game_context: {game_id, tick, price, phase}                     │  │
│   │  - state_before: {cash, position_qty, avg_cost, pnl}               │  │
│   │  - timestamps: {client_ts, server_ts, confirmed_ts}                │  │
│   │  - latency: {send_latency_ms, confirm_latency_ms, total_latency_ms}│  │
│   │  - outcome: {success, executed_price, error}                       │  │
│   │  - state_after: {cash, position_qty, avg_cost, pnl}                │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Schema Version 2.0.0

### DocType Enum (Expanded)

```python
class DocType(str, Enum):
    """Document types for partitioning - v2.0.0"""

    # === EXISTING (v1.0.0) ===
    WS_EVENT = "ws_event"           # Raw WebSocket events
    GAME_TICK = "game_tick"         # Price/tick stream
    SERVER_STATE = "server_state"   # Server-authoritative snapshots
    SYSTEM_EVENT = "system_event"   # Connection/disconnect/errors

    # === ENHANCED (v2.0.0) ===
    PLAYER_ACTION = "player_action"       # Our actions (human/bot)
    OTHER_PLAYER_ACTION = "other_player"  # Other players' trades (from newTrade)

    # === PLACEHOLDER (v2.x.0) ===
    ALERT_TRIGGER = "alert_trigger"       # Toast notification triggers
    ML_EPISODE = "ml_episode"             # Episode boundaries for RL

    # === SIDEGAMES (v2.x.0 - TBD) ===
    BBC_ROUND = "bbc_round"               # Bull/Bear/Crab game rounds
    CANDLEFLIP_ROUND = "candleflip"       # Candleflip game rounds
    SHORT_POSITION = "short_position"     # Short position state snapshots
```

---

## Core Schemas

### 1. player_action (Enhanced)

Captures the complete action lifecycle: intent → execution → outcome.

```python
@dataclass
class PlayerAction:
    """
    Complete action record for ML training.

    RL Tuple Mapping:
    - state (s):  state_before + game_context
    - action (a): action_type + button + amount
    - next_state (s'): state_after
    - reward (r): Derived from state_before.cash → state_after.cash
    """

    # === IDENTITY ===
    action_id: str              # UUID for correlation
    session_id: str             # Recording session
    game_id: str                # Game context
    player_id: str              # Our player ID
    username: str | None        # Our display name

    # === ACTION INTENT ===
    action_type: ActionType     # BUY, SELL, SIDEBET, BET_ADJUST
    button: str                 # Raw button text: "BUY", "SELL 25%", "+0.01"
    amount: Decimal | None      # Trade amount (SOL)
    percentage: int | None      # Sell percentage (10, 25, 50, 100)

    # === GAME CONTEXT (at action time) ===
    game_context: GameContext   # Snapshot of game state

    # === PLAYER STATE BEFORE ===
    state_before: PlayerState   # Wallet/position before action

    # === TIMESTAMPS (for latency) ===
    timestamps: ActionTimestamps

    # === OUTCOME ===
    outcome: ActionOutcome | None  # Server response

    # === PLAYER STATE AFTER (from playerUpdate) ===
    state_after: PlayerState | None  # Wallet/position after confirmation

    # === DERIVED METRICS ===
    @property
    def reward(self) -> Decimal:
        """RL reward = PnL delta from action."""
        if self.state_after and self.state_before:
            return self.state_after.cumulative_pnl - self.state_before.cumulative_pnl
        return Decimal(0)

    @property
    def total_latency_ms(self) -> int | None:
        """Total round-trip time."""
        return self.timestamps.total_latency_ms


class ActionType(str, Enum):
    """Action types for classification."""

    # === MAIN GAME - LONG ===
    BUY = "BUY"
    SELL = "SELL"
    SIDEBET = "SIDEBET"

    # === MAIN GAME - SHORT (New Feature) ===
    SHORT_OPEN = "SHORT_OPEN"          # Enter short position
    SHORT_CLOSE = "SHORT_CLOSE"        # Exit short position

    # === BET ADJUSTMENT ===
    BET_INCREMENT = "BET_INCREMENT"    # +0.001, +0.01, +0.1, +1
    BET_DECREMENT = "BET_DECREMENT"    # -0.001, -0.01, -0.1, -1
    BET_PERCENTAGE = "BET_PERCENTAGE"  # 10%, 25%, 50%, MAX

    # === SIDEGAMES (New Games) ===
    BBC_PREDICT = "BBC_PREDICT"        # Bull/Bear/Crab prediction
    CANDLEFLIP_BET = "CANDLEFLIP_BET"  # Candleflip wager


@dataclass
class GameContext:
    """Game state snapshot at action time."""
    game_id: str
    tick: int
    price: Decimal
    phase: GamePhase          # ACTIVE, COOLDOWN, RUGGED
    is_pre_round: bool        # allowPreRoundBuys
    connected_players: int

    # Optional context
    volatility_1m: Decimal | None = None  # Price volatility (for ML)
    time_since_start: int | None = None   # Ticks since game start


class GamePhase(str, Enum):
    COOLDOWN = "cooldown"
    ACTIVE = "active"
    RUGGED = "rugged"


@dataclass
class PlayerState:
    """
    Player wallet/position state - from playerUpdate.
    Server-authoritative truth.
    """
    cash: Decimal               # Wallet balance (SOL)
    position_qty: Decimal       # Position size (units)
    avg_cost: Decimal           # Average entry price
    total_invested: Decimal     # Total SOL invested
    cumulative_pnl: Decimal     # Total PnL this game

    # Derived
    @property
    def has_position(self) -> bool:
        return self.position_qty > 0

    @property
    def position_value(self) -> Decimal:
        """Current position value at avg_cost."""
        return self.position_qty * self.avg_cost


@dataclass
class ActionTimestamps:
    """
    Precision timestamps for latency analysis.
    All timestamps in milliseconds (Unix epoch).
    """
    # Client-side
    client_ts: int              # When button was pressed (local clock)

    # Server-side (from response)
    server_ts: int | None       # Server's timestamp in response

    # Confirmation (when playerUpdate received)
    confirmed_ts: int | None    # When we received confirmation

    # Derived latencies
    @property
    def send_latency_ms(self) -> int | None:
        """Client → Server latency."""
        if self.server_ts:
            return self.server_ts - self.client_ts
        return None

    @property
    def confirm_latency_ms(self) -> int | None:
        """Server → Client (confirmation) latency."""
        if self.server_ts and self.confirmed_ts:
            return self.confirmed_ts - self.server_ts
        return None

    @property
    def total_latency_ms(self) -> int | None:
        """Total round-trip time."""
        if self.confirmed_ts:
            return self.confirmed_ts - self.client_ts
        return None


@dataclass
class ActionOutcome:
    """
    Server response to action.
    From buyOrder/sellOrder/sidebet response.
    """
    success: bool
    executed_price: Decimal | None = None
    executed_amount: Decimal | None = None
    fee: Decimal | None = None

    # Error details
    error: str | None = None
    error_reason: str | None = None

    # Server metadata
    server_request_id: int | None = None  # Socket.IO request ID
```

---

### 2. other_player (New)

Track other players' actions for ML training data and exceptional player identification.

```python
@dataclass
class OtherPlayerAction:
    """
    Other players' trades from newTrade broadcast.

    Use Cases:
    - Exceptional player identification (consistent winners)
    - Behavioral pattern analysis
    - Imitation learning targets
    - Entry/exit timing analysis
    """

    # === IDENTITY ===
    session_id: str
    game_id: str
    player_id: str              # Other player's ID
    username: str | None        # Other player's username

    # === ACTION ===
    action_type: Literal["BUY", "SELL", "SHORT_OPEN", "SHORT_CLOSE"]
    amount: Decimal             # Trade amount (SOL)
    price: Decimal              # Execution price

    # === GAME CONTEXT ===
    tick: int
    game_phase: GamePhase       # Where in game lifecycle

    # === TIMESTAMPS ===
    server_ts: int              # From newTrade timestamp
    ingested_ts: int            # When we received it

    # === PLAYER PROFILE (from leaderboard) ===
    player_level: int | None = None
    player_pnl: Decimal | None = None       # Their current game PnL
    player_position: Decimal | None = None  # Their position size
    leaderboard_rank: int | None = None     # Their rank

    # === SHORT POSITION (New Feature) ===
    short_position: Decimal | None = None   # Their short position size
    short_entry_price: Decimal | None = None

    # === DERIVED FLAGS ===
    @property
    def is_profitable_player(self) -> bool:
        """Player has positive PnL."""
        return self.player_pnl is not None and self.player_pnl > 0

    @property
    def is_early_entry(self) -> bool:
        """Entry in first 50 ticks."""
        return self.tick < 50 and self.action_type in ("BUY", "SHORT_OPEN")


@dataclass
class ExceptionalPlayer:
    """
    Identified exceptional players for training data.
    Built from aggregating other_player actions.
    """
    player_id: str
    username: str | None

    # Performance metrics
    total_games_observed: int
    total_trades_observed: int
    win_rate: Decimal           # % of profitable games
    avg_pnl_per_game: Decimal

    # Behavioral patterns
    avg_entry_tick: int         # When they typically buy
    avg_exit_tick: int          # When they typically sell
    preferred_entry_zone: str   # "early", "mid", "late"
    avg_hold_duration: int      # Ticks held on average

    # Classification
    is_consistent_winner: bool  # > 60% win rate
    is_imitation_target: bool   # Worth copying
    specialization: str | None  # "long", "short", "sidebet", "mixed"
```

---

### 3. alert_trigger (Placeholder)

Toast notification triggers for player advantages.

```python
class AlertType(str, Enum):
    """Alert categories for toast notifications."""

    # === TRADE EXECUTION ===
    TRADE_SUCCESS = "trade_success"
    TRADE_FAILED = "trade_failed"

    # === POSITION ALERTS ===
    POSITION_PROFIT = "position_profit"       # Position up X%
    POSITION_LOSS = "position_loss"           # Position down X%
    SIDEBET_WON = "sidebet_won"
    SIDEBET_LOST = "sidebet_lost"

    # === GAME EVENTS ===
    GAME_START = "game_start"
    GAME_RUG = "game_rug"
    MULTIPLIER_MILESTONE = "multiplier_milestone"  # 2x, 10x, 50x, 100x

    # === VOLATILITY & TIMING SIGNALS (Future) ===
    VOLATILITY_SPIKE = "volatility_spike"           # Unusual price movement
    VOLATILITY_CALM = "volatility_calm"             # Low volatility period
    SIDEBET_OPTIMAL_ZONE = "sidebet_optimal_zone"   # Statistical sweet spot for sidebet entry
    HIGH_POTENTIAL_ENTRY = "high_potential_entry"   # ML suggests favorable buy zone
    HIGH_POTENTIAL_EXIT = "high_potential_exit"     # ML suggests favorable sell zone
    RUG_WARNING = "rug_warning"                     # High rug probability (temporal model)
    SURVIVAL_MILESTONE = "survival_milestone"       # Game duration reaching key percentiles

    # === PLAYER PATTERN SIGNALS (Future - from data exploration) ===
    EXCEPTIONAL_PLAYER_ENTRY = "exceptional_entry"  # Consistent winner bought
    EXCEPTIONAL_PLAYER_EXIT = "exceptional_exit"    # Consistent winner sold
    # Placeholder for higher-order signals discovered through data analysis
    CUSTOM_SIGNAL_1 = "custom_signal_1"
    CUSTOM_SIGNAL_2 = "custom_signal_2"
    CUSTOM_SIGNAL_3 = "custom_signal_3"

    # === SHORT POSITION ALERTS (New Feature) ===
    SHORT_ENTRY_SIGNAL = "short_entry_signal"       # Favorable short entry
    SHORT_EXIT_SIGNAL = "short_exit_signal"         # Short take-profit/stop-loss
    SHORT_LIQUIDATION_WARNING = "short_liquidation" # Position at risk

    # === SIDEGAME ALERTS (New Games) ===
    BBC_ROUND_START = "bbc_round_start"             # Bull/Bear/Crab round starting
    BBC_OPTIMAL_PREDICTION = "bbc_optimal_pred"     # Statistical edge detected
    CANDLEFLIP_ROUND_START = "candleflip_start"     # Candleflip round starting
    CANDLEFLIP_STREAK_ALERT = "candleflip_streak"   # Streak pattern detected

    # === SYSTEM ===
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    LATENCY_WARNING = "latency_warning"       # High latency detected


@dataclass
class AlertTrigger:
    """
    Alert event for toast notification system.

    These are DERIVED events - generated by analyzing other events.
    """
    alert_id: str
    alert_type: AlertType
    severity: Literal["info", "success", "warning", "error"]

    # Timing
    triggered_at: datetime
    expires_at: datetime | None  # Auto-dismiss time

    # Context
    game_id: str | None
    player_id: str | None       # For player-specific alerts

    # Display
    title: str                  # Short title
    message: str                # Detailed message

    # Source data
    source_event: str | None    # Event that triggered this
    source_data: dict | None    # Raw data for debugging

    # User preference
    can_dismiss: bool = True
    sound_enabled: bool = False
    priority: int = 0           # Higher = more important
```

---

### 4. ml_episode (Placeholder)

Episode boundaries for RL training.

```python
@dataclass
class MLEpisode:
    """
    Episode record for RL training.

    One episode = one game from start to end (rug or exit).
    """
    episode_id: str
    session_id: str
    game_id: str
    player_id: str

    # Timing
    started_at: datetime
    ended_at: datetime
    duration_ticks: int
    duration_ms: int

    # Outcome
    outcome: Literal["rug", "exit_profit", "exit_loss", "timeout"]
    final_pnl: Decimal
    peak_pnl: Decimal
    max_drawdown: Decimal

    # Summary stats
    total_actions: int
    buy_count: int
    sell_count: int
    avg_position_size: Decimal

    # Entry/Exit timing
    first_buy_tick: int | None
    last_sell_tick: int | None
    avg_hold_time_ticks: int

    # For RL training
    total_reward: Decimal       # Sum of step rewards
    avg_reward_per_step: Decimal
```

---

### 5. Sidegames (Placeholders)

New game modes requiring their own event schemas.

```python
# =============================================================================
# BBC (Bull, Bear, Crab) - Prediction Game
# =============================================================================

class BBCPrediction(str, Enum):
    """BBC prediction options."""
    BULL = "BULL"   # Price will go up
    BEAR = "BEAR"   # Price will go down
    CRAB = "CRAB"   # Price will stay flat


@dataclass
class BBCRound:
    """
    BBC round state - prediction game on price direction.

    Placeholder - schema TBD based on actual WebSocket events.
    """
    round_id: str
    game_id: str                    # Parent game context
    session_id: str

    # Round timing
    start_tick: int
    end_tick: int
    duration_ticks: int

    # Our prediction
    our_prediction: BBCPrediction | None = None
    our_bet_amount: Decimal | None = None

    # Outcome
    actual_result: BBCPrediction | None = None
    won: bool | None = None
    payout: Decimal | None = None

    # Timestamps
    prediction_ts: int | None = None    # When we predicted
    result_ts: int | None = None        # When result announced

    # Context for ML
    price_at_start: Decimal | None = None
    price_at_end: Decimal | None = None
    volatility_during: Decimal | None = None


# =============================================================================
# Candleflip - Coin Toss Game
# =============================================================================

class CandleflipChoice(str, Enum):
    """Candleflip bet options."""
    GREEN = "GREEN"   # Bullish candle
    RED = "RED"       # Bearish candle


@dataclass
class CandleflipRound:
    """
    Candleflip round state - binary outcome game.

    Placeholder - schema TBD based on actual WebSocket events.
    """
    round_id: str
    game_id: str
    session_id: str

    # Our bet
    our_choice: CandleflipChoice | None = None
    our_bet_amount: Decimal | None = None

    # Outcome
    result: CandleflipChoice | None = None
    won: bool | None = None
    payout: Decimal | None = None

    # Streak tracking (for pattern detection)
    current_streak: int = 0         # Consecutive same results
    streak_direction: CandleflipChoice | None = None

    # Timestamps
    bet_ts: int | None = None
    result_ts: int | None = None


# =============================================================================
# Short Positions (Main Game Extension)
# =============================================================================

@dataclass
class ShortPositionState:
    """
    Short position tracking - extension to PlayerState.

    Shorts profit when price goes DOWN (opposite of longs).
    """
    has_short: bool = False
    short_qty: Decimal = Decimal(0)
    short_entry_price: Decimal = Decimal(0)
    short_pnl: Decimal = Decimal(0)

    # Liquidation tracking
    liquidation_price: Decimal | None = None
    margin_ratio: Decimal | None = None
    at_risk: bool = False

    @property
    def short_value(self) -> Decimal:
        """Current short position value."""
        return self.short_qty * self.short_entry_price
```

---

## Correlation IDs

To link actions to outcomes across events:

```python
# Action → Outcome linking
action_id = str(uuid4())  # Generated client-side at button press

# Flow:
# 1. player_action created with action_id
# 2. buyOrder/sellOrder sent to server
# 3. Server response received (43XXX format)
# 4. playerUpdate received with new state
# 5. Update player_action with outcome + state_after

# The action_id appears in:
# - player_action.action_id (created at step 1)
# - state_after linked by matching game_id + sequence proximity
```

---

## Parquet Partitioning

```
~/rugs_data/events_parquet/
├── doc_type=player_action/
│   └── session_id=<uuid>/
│       └── data.parquet
├── doc_type=other_player/
│   └── session_id=<uuid>/
│       └── data.parquet
├── doc_type=server_state/
│   └── session_id=<uuid>/
│       └── data.parquet
├── doc_type=game_tick/
│   └── session_id=<uuid>/
│       └── data.parquet
└── doc_type=alert_trigger/
    └── session_id=<uuid>/
        └── data.parquet
```

---

## DuckDB Query Examples

### Get action with full context

```sql
-- Action with before/after state
SELECT
    pa.action_id,
    pa.action_type,
    pa.amount,
    pa.timestamps_client_ts,
    pa.timestamps_server_ts,
    pa.timestamps_total_latency_ms,
    pa.state_before_cash,
    pa.state_after_cash,
    pa.state_after_cash - pa.state_before_cash AS pnl_delta,
    pa.game_context_tick,
    pa.game_context_price
FROM '~/rugs_data/events_parquet/doc_type=player_action/**/*.parquet' pa
WHERE pa.action_type IN ('BUY', 'SELL')
ORDER BY pa.timestamps_client_ts;
```

### Identify exceptional players

```sql
-- Find players with > 60% win rate
WITH player_games AS (
    SELECT
        player_id,
        username,
        game_id,
        SUM(CASE WHEN action_type = 'SELL' THEN amount * price ELSE -amount * price END) AS game_pnl
    FROM '~/rugs_data/events_parquet/doc_type=other_player/**/*.parquet'
    GROUP BY player_id, username, game_id
),
player_stats AS (
    SELECT
        player_id,
        MAX(username) AS username,
        COUNT(*) AS total_games,
        SUM(CASE WHEN game_pnl > 0 THEN 1 ELSE 0 END) AS winning_games,
        AVG(game_pnl) AS avg_pnl
    FROM player_games
    GROUP BY player_id
    HAVING COUNT(*) >= 10  -- Minimum sample size
)
SELECT *,
    winning_games::FLOAT / total_games AS win_rate
FROM player_stats
WHERE win_rate > 0.6
ORDER BY avg_pnl DESC;
```

### Latency analysis

```sql
-- Latency distribution by action type
SELECT
    action_type,
    COUNT(*) AS count,
    AVG(timestamps_total_latency_ms) AS avg_latency,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY timestamps_total_latency_ms) AS p50,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY timestamps_total_latency_ms) AS p95,
    MAX(timestamps_total_latency_ms) AS max_latency
FROM '~/rugs_data/events_parquet/doc_type=player_action/**/*.parquet'
WHERE timestamps_total_latency_ms IS NOT NULL
GROUP BY action_type;
```

---

## Migration Path

### Phase 1: Schema Implementation
1. Add new dataclasses to `models/events/`
2. Update EventEnvelope with new factory methods
3. Update EventStore writer for new doc_types

### Phase 2: Capture Integration
1. Hook into UI button handlers for player_action
2. Hook into newTrade events for other_player
3. Correlate playerUpdate with pending actions

### Phase 3: Alert System
1. Implement AlertTrigger generation
2. Connect to toast notification system
3. Add user preference storage

### Phase 4: ML Export
1. Implement episode boundary detection
2. Create export scripts for rugs-rl-bot
3. Build exceptional player identification pipeline

---

## Files to Create

### Core Models (v2.0.0)

| File | Purpose | Priority |
|------|---------|----------|
| `models/events/player_action.py` | PlayerAction, GameContext, PlayerState, ActionTimestamps | HIGH |
| `models/events/other_player.py` | OtherPlayerAction, ExceptionalPlayer | HIGH |
| `models/events/alert_trigger.py` | AlertTrigger, AlertType enum | MEDIUM |
| `models/events/ml_episode.py` | MLEpisode | MEDIUM |

### Sidegame Placeholders (v2.x.0 - TBD)

| File | Purpose | Priority |
|------|---------|----------|
| `models/events/bbc_round.py` | BBCRound, BBCPrediction | LOW (placeholder) |
| `models/events/candleflip.py` | CandleflipRound, CandleflipChoice | LOW (placeholder) |
| `models/events/short_position.py` | ShortPositionState | LOW (placeholder) |

### Services

| File | Purpose | Priority |
|------|---------|----------|
| `services/action_tracker.py` | Correlate actions to outcomes | HIGH |
| `services/alert_generator.py` | Generate alert triggers from events | MEDIUM |
| `services/player_analyzer.py` | Identify exceptional players | LOW |
| `bot/action_interface.py` | BotActionInterface base class | HIGH |

---

## Codex-Parallelizable Work

Based on this design, the following can be assigned to Codex:

### Batch 1: Core Models (Can run in parallel)

| Task | File(s) | Complexity | Notes |
|------|---------|------------|-------|
| Create `player_action.py` | `models/events/player_action.py` | Low | ~200 lines |
| Create `other_player.py` | `models/events/other_player.py` | Low | ~100 lines |
| Create `alert_trigger.py` | `models/events/alert_trigger.py` | Low | ~150 lines |
| Create `ml_episode.py` | `models/events/ml_episode.py` | Low | ~80 lines |
| Update `__init__.py` | `models/events/__init__.py` | Low | Add exports |

### Batch 2: Placeholder Models (Optional, can defer)

| Task | File(s) | Complexity | Notes |
|------|---------|------------|-------|
| Create `bbc_round.py` | `models/events/bbc_round.py` | Low | Placeholder |
| Create `candleflip.py` | `models/events/candleflip.py` | Low | Placeholder |
| Create `short_position.py` | `models/events/short_position.py` | Low | Placeholder |

### Batch 3: Legacy Cleanup (After models complete)

| Task | File(s) | Complexity | Notes |
|------|---------|------------|-------|
| Delete legacy recorders | See #137 | Medium | ~2989 lines removal |
| Path migration | See #139 | Medium | Config changes |
| Toast migration | See #138 | Medium | Needs alert model |

### Not Suitable for Codex

| Task | Reason |
|------|--------|
| `services/action_tracker.py` | Complex integration logic |
| `bot/action_interface.py` | Architectural decisions needed |
| EventStore integration | Requires coordination |

---

## Decision Summary

**Issue #136 Resolution:**

1. **EventStore is canonical** - All events flow through EventStore to Parquet
2. **Legacy recorders DELETE** - No migration, just removal (~2989 lines)
3. **Schema v2.0.0** - Expanded with player_action, other_player, alerts, sidegames
4. **Latency tracking** - client_ts → server_ts → confirmed_ts chain
5. **Future-proofed** - Placeholders for BBC, Candleflip, Shorts, custom signals

---

*Schema Version 2.0.0 - December 23, 2025*
