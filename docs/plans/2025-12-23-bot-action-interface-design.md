# BotActionInterface Design

**Date:** 2025-12-23
**Status:** Draft
**Issue:** TBD (create after approval)

---

## Overview

A layered architecture for bot action execution with latency tracking, designed to serve:
- **Live automated trading** (Puppeteer + real WebSocket)
- **Validation/demo mode** (Tkinter UI + real WebSocket)
- **RL training** (Simulated, instant execution)

**Core Goal:** Track execution latency from button press to server confirmation, providing the RL model with timing data to inform decisions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      BotActionInterface                         │
│         (Orchestrates execution → confirmation → tracking)      │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ ActionExecutor  │  │ Confirmation    │  │ StateTracker    │
│                 │  │ Monitor         │  │                 │
│ • TkinterExec   │  │                 │  │ • Positions     │
│ • PuppeteerExec │  │ • WebSocket     │  │ • Balance       │
│ • SimulatedExec │  │   subscription  │  │ • Sidebets      │
│                 │  │ • Latency calc  │  │ • PNL           │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   EventStore    │
                    │  (PlayerAction  │
                    │   events)       │
                    └─────────────────┘
```

**Three Layers:**
1. **ActionExecutor** - Presses buttons (UI animation OR Puppeteer XPaths)
2. **ConfirmationMonitor** - Watches WebSocket for server-side confirmation
3. **StateTracker** - Tracks trade outcomes, feeds RL training data

**Two Runtime Modes:**
- **Live**: PuppeteerExecutor + real WebSocket + real state
- **Replay**: TkinterExecutor (animated) + recorded events + simulated state

---

## Layer 1: ActionExecutor

The "button pressing" layer. Knows HOW to execute actions but not WHETHER they succeeded.

```python
class ActionExecutor(ABC):
    """Base interface for executing button actions"""

    @abstractmethod
    def execute(self, action: ActionType, params: ActionParams) -> ExecutionRecord:
        """
        Execute action, return timing record.
        Does NOT wait for confirmation.
        """
        pass

class ExecutionRecord:
    """What the executor returns immediately after pressing"""
    action_id: str           # Unique ID to correlate with confirmation
    action_type: ActionType  # BUY, SELL, SIDEBET, etc.
    client_ts: int           # When we pressed (ms epoch)
    params: ActionParams     # Amount, percentage, etc.
    executor_type: str       # "tkinter" | "puppeteer" | "simulated"
```

### Implementations

| Executor | Purpose | Behavior |
|----------|---------|----------|
| `TkinterExecutor` | Demo/validation | Animates button visually in VECTRA UI |
| `PuppeteerExecutor` | Live trading | Sends XPath click to browser via MCP |
| `SimulatedExecutor` | RL training | Instant, no UI, direct state update |

### Puppeteer Integration

```python
class PuppeteerExecutor(ActionExecutor):
    # XPath mapping (configured, not hardcoded)
    BUTTON_XPATHS = {
        ActionType.BUY: "//button[contains(@class, 'buy-btn')]",
        ActionType.SELL: "//button[contains(@class, 'sell-btn')]",
        # ... etc
    }
```

**Key Design Point:** Executors are "fire and forget" - they press the button and return immediately with a timestamp. Confirmation comes from the next layer.

---

## Layer 2: ConfirmationMonitor

Watches WebSocket events and correlates them with pending actions.

```python
class ConfirmationMonitor:
    """Watches WebSocket for action confirmations"""

    def __init__(self, event_bus: EventBus):
        self.pending_actions: dict[str, ExecutionRecord] = {}
        self.latency_stats = LatencyStats()

        # Subscribe to relevant WebSocket events
        event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update)
        event_bus.subscribe(Events.NEW_TRADE, self._on_new_trade)

    def register_pending(self, record: ExecutionRecord):
        """Register an action waiting for confirmation"""
        self.pending_actions[record.action_id] = record

    def _on_player_update(self, event):
        """Check if any pending action was confirmed"""
        # Compare state changes to pending actions
        # Calculate latency, emit PlayerAction event
```

### Confirmation Detection Strategy

| Action | Confirmation Signal |
|--------|---------------------|
| BUY | `playerUpdate` shows new/increased position |
| SELL | `playerUpdate` shows position closed/reduced |
| SIDEBET | `playerUpdate` shows active sidebet |
| SIDEBET_RESOLVE | `playerUpdate` after rug shows sidebet payout |

### Latency Tracking

```python
class ConfirmationResult:
    action_id: str
    confirmed: bool
    client_ts: int          # From ExecutionRecord
    confirmed_ts: int       # When we saw the change
    total_latency_ms: int   # confirmed_ts - client_ts
    state_change: dict      # What changed (position, balance, etc.)

class LatencyStats:
    samples: deque[int]     # Rolling window (last N latencies)

    @property
    def avg_latency_ms(self) -> float: ...

    @property
    def p95_latency_ms(self) -> float: ...
```

---

## Layer 3: StateTracker

Maintains authoritative trade state and emits events for RL training.

```python
class StateTracker:
    """Tracks trading state and emits PlayerAction events"""

    def __init__(self, event_store: EventStore, event_bus: EventBus):
        self.event_store = event_store

        # Current state
        self.position: PositionState | None = None
        self.balance: Decimal = Decimal("0")
        self.active_sidebet: SidebetState | None = None

        # Session aggregates
        self.session_stats = SessionStats()

        # Subscribe to confirmations
        event_bus.subscribe(Events.ACTION_CONFIRMED, self._on_action_confirmed)
        event_bus.subscribe(Events.PLAYER_UPDATE, self._on_player_update)
        event_bus.subscribe(Events.GAME_RUG, self._on_game_rug)
```

### State Objects

```python
@dataclass
class PositionState:
    entry_price: Decimal
    entry_tick: int
    quantity: Decimal
    entry_ts: int              # When we entered (client_ts)

@dataclass
class SidebetState:
    amount: Decimal
    placed_tick: int
    placed_ts: int             # When we placed (client_ts)
    target_price: Decimal      # Price when placed

@dataclass
class SessionStats:
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: Decimal = Decimal("0")
    sidebets_won: int = 0
    sidebets_lost: int = 0
    avg_hold_ticks: float = 0.0
```

### Event Emission

```python
def _on_action_confirmed(self, confirmation: ConfirmationResult):
    """Emit PlayerAction event when action is confirmed"""

    player_action = PlayerAction(
        action_id=confirmation.action_id,
        action_type=confirmation.action_type,
        timestamps=ActionTimestamps(
            client_ts=confirmation.client_ts,
            server_ts=None,  # TBD from empirical analysis
            confirmed_ts=confirmation.confirmed_ts,
        ),
        state_before=self._snapshot_state(),
        outcome=ActionOutcome(
            success=confirmation.confirmed,
            executed_price=confirmation.executed_price,
        ),
    )

    self.event_store.write(player_action)
```

---

## Orchestrator: BotActionInterface

Coordinates all three layers and provides a unified API.

```python
class BotActionInterface:
    """
    Orchestrates execution → confirmation → state tracking

    Single API for all execution modes:
    - Live trading (Puppeteer + real WebSocket)
    - Validation (Tkinter + real WebSocket)
    - Training (Simulated + recorded/mocked events)
    """

    def __init__(
        self,
        executor: ActionExecutor,
        confirmation_monitor: ConfirmationMonitor,
        state_tracker: StateTracker,
        timeout_ms: int = 2000,
    ):
        self.executor = executor
        self.monitor = confirmation_monitor
        self.tracker = state_tracker
        self.timeout_ms = timeout_ms

    async def execute_action(
        self,
        action: ActionType,
        params: ActionParams
    ) -> ActionResult:
        """
        Full action lifecycle:
        1. Execute (press button)
        2. Wait for confirmation
        3. Update state
        4. Return result with latency
        """
        # Step 1: Execute
        record = self.executor.execute(action, params)

        # Step 2: Register and wait for confirmation
        self.monitor.register_pending(record)
        confirmation = await self.monitor.wait_for_confirmation(
            record.action_id,
            timeout_ms=self.timeout_ms
        )

        # Step 3: Update state (triggers PlayerAction emission)
        self.tracker.update_from_confirmation(confirmation)

        # Step 4: Return enriched result
        return ActionResult(
            success=confirmation.confirmed,
            action_id=record.action_id,
            latency_ms=confirmation.total_latency_ms,
            state=self.tracker.get_snapshot(),
        )

    @property
    def avg_latency_ms(self) -> float:
        return self.monitor.latency_stats.avg_latency_ms
```

### Factory Pattern

```python
class BotActionInterfaceFactory:

    @staticmethod
    def create_live(event_bus, event_store) -> BotActionInterface:
        """Live trading mode - Puppeteer + real WebSocket"""
        return BotActionInterface(
            executor=PuppeteerExecutor(),
            confirmation_monitor=ConfirmationMonitor(event_bus),
            state_tracker=StateTracker(event_store, event_bus),
        )

    @staticmethod
    def create_validation(main_window, event_bus, event_store) -> BotActionInterface:
        """Validation mode - Tkinter animation + real WebSocket"""
        return BotActionInterface(
            executor=TkinterExecutor(main_window),
            confirmation_monitor=ConfirmationMonitor(event_bus),
            state_tracker=StateTracker(event_store, event_bus),
        )

    @staticmethod
    def create_training(game_state, event_store) -> BotActionInterface:
        """Training mode - Simulated, instant, no UI"""
        return BotActionInterface(
            executor=SimulatedExecutor(game_state),
            confirmation_monitor=MockConfirmationMonitor(),
            state_tracker=StateTracker(event_store, event_bus=None),
        )
```

---

## RL Integration

```python
class RLObservationProvider:
    """Extends observations with latency-aware features"""

    def __init__(self, bot_action_interface: BotActionInterface):
        self.interface = bot_action_interface

    def get_observation(self) -> dict:
        """Observation vector for RL model"""
        state = self.interface.tracker.get_snapshot()
        latency = self.interface.monitor.latency_stats

        return {
            # Game state (existing)
            "price": state.price,
            "tick": state.tick,
            "phase": state.phase,

            # Position state
            "has_position": state.position is not None,
            "position_pnl_pct": state.position.unrealized_pnl_pct if state.position else 0,

            # Latency-aware features (NEW)
            "avg_latency_ticks": latency.avg_latency_ms / 250,
            "latency_p95_ticks": latency.p95_latency_ms / 250,
            "can_exit_safely": self._can_exit_before_rug(state, latency),

            # Sidebet state
            "has_sidebet": state.active_sidebet is not None,
            "sidebet_ticks_remaining": state.sidebet_ticks_remaining,
        }

    def _can_exit_before_rug(self, state, latency) -> bool:
        """Estimate if we can exit before likely rug."""
        ticks_to_exit = latency.p95_latency_ms / 250
        return state.tick + ticks_to_exit < state.estimated_safe_window
```

---

## File Structure

```
src/bot/
├── action_interface/
│   ├── __init__.py
│   ├── interface.py          # BotActionInterface orchestrator
│   ├── factory.py            # BotActionInterfaceFactory
│   ├── types.py              # ActionType, ActionParams, ActionResult, etc.
│   │
│   ├── executors/
│   │   ├── __init__.py
│   │   ├── base.py           # ActionExecutor ABC
│   │   ├── tkinter.py        # TkinterExecutor
│   │   ├── puppeteer.py      # PuppeteerExecutor
│   │   └── simulated.py      # SimulatedExecutor
│   │
│   ├── confirmation/
│   │   ├── __init__.py
│   │   ├── monitor.py        # ConfirmationMonitor
│   │   ├── latency.py        # LatencyStats
│   │   └── mock.py           # MockConfirmationMonitor (training)
│   │
│   └── state/
│       ├── __init__.py
│       ├── tracker.py        # StateTracker
│       └── models.py         # PositionState, SidebetState, SessionStats
│
├── rl/
│   └── observation.py        # RLObservationProvider
```

---

## ⚠️ REQUIRED: Empirical Validation Checkpoint

**BEFORE implementing ConfirmationMonitor, we MUST validate assumptions with live data.**

### Test Script v1.0

Execute a predetermined action sequence to create ground truth:

```
Phase 1: Single Actions (baseline latency)
──────────────────────────────────────────
• Wait for ACTIVE phase
• BUY 0.01 SOL                    → log client_ts
• Wait 10 ticks (~2.5s)
• SELL 100%                       → log client_ts
• Wait 10 ticks
• SIDEBET 0.01 SOL                → log client_ts
• Wait for sidebet resolution

Phase 2: Rapid Sequence (stress test)
──────────────────────────────────────
• BUY 0.01 SOL
• BUY 0.01 SOL (DCA, 2 ticks later)
• BUY 0.01 SOL (DCA, 2 ticks later)
• SELL 100%

Phase 3: Edge Cases
───────────────────
• BUY during COOLDOWN (should fail)
• SELL with no position (should fail)
• SIDEBET when one already active (should fail)

Output: test_recording_YYYYMMDD_HHMMSS.jsonl
────────────────────────────────────────────
Each line: { action, client_ts, params, expected_result }
```

### Analysis Tasks

1. **RECORD**: Capture live WebSocket sessions during test script execution
   - Use Chrome DevTools MCP or CDP capture scripts
   - Record full event payloads with timestamps

2. **MAP**: Analyze event patterns
   - Which event confirms BUY? (playerUpdate? newTrade? both?)
   - What fields change? (position, balance, timestamps?)
   - What's the typical latency distribution?
   - Are there ack callbacks we're missing?

3. **DOCUMENT**: Create precise event-to-confirmation mapping
   - `docs/specs/CONFIRMATION_EVENT_MAPPING.md`
   - Include real payload examples
   - Document edge cases (failed trades, partial fills, etc.)

4. **VALIDATE**: Update design if needed
   - Adjust ConfirmationMonitor detection logic
   - Refine latency calculation approach

**Tools:** Chrome DevTools MCP, CDP capture scripts
**Time Estimate:** 1-2 hours

---

## Summary

| Component | Responsibility |
|-----------|----------------|
| `ActionExecutor` | Press buttons (Tkinter/Puppeteer/Simulated) |
| `ConfirmationMonitor` | Watch WebSocket, calculate latency |
| `StateTracker` | Track positions/balance/sidebets, emit PlayerAction |
| `BotActionInterface` | Orchestrate all layers, unified API |
| `BotActionInterfaceFactory` | Create appropriate mode (live/validation/training) |
| `RLObservationProvider` | Latency-aware observations for RL model |

---

*Generated: 2025-12-23*
