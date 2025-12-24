# Models Code Audit Report (`src/models/`)

Date: 2025-12-22
Scope: All source files under `src/models/` (including `src/models/events/`).
Method: Manual static review + `python3 -m compileall -q src/models` (syntax check).

## Executive Summary

`src/models/` is split into two distinct model layers:

- **Runtime dataclasses** used by the app (`GameTick`, `Position`, `SideBet`, recording/demo models).
- **Pydantic schemas** for WebSocket events (`models/events/*`), used by schema validation and ingestion.

Most structures are clear and internally consistent (notably the event schemas). The most important issues to address are:

- A **hard bug** in a Pydantic validator (`isinstance(v, int | float)`) that will raise `TypeError` at runtime during schema validation.
- **Latency calculations** in trade response schemas appear sign-inverted (and in general need clearer semantics).
- Several “paper cuts” around precision handling, timestamp timezone conventions, and minor API typing inconsistencies.

No syntax errors were found.

## Inventory (Files Reviewed)

Top-level:
- `src/models/__init__.py`
- `src/models/demo_action.py`
- `src/models/enums.py`
- `src/models/game_tick.py`
- `src/models/position.py`
- `src/models/recording_config.py`
- `src/models/recording_models.py`
- `src/models/side_bet.py`

Event schemas:
- `src/models/events/__init__.py`
- `src/models/events/game_state_update.py`
- `src/models/events/player_update.py`
- `src/models/events/player_leaderboard_position.py`
- `src/models/events/system_events.py`
- `src/models/events/trade_events.py`
- `src/models/events/username_status.py`
- `src/models/events/CONTEXT.md` (documentation)

Non-runtime artifacts present in-tree:
- `src/models/__pycache__/...`
- `src/models/events/__pycache__/...`

## High Priority Findings (Fix Soon)

### 1) `game_state_update.py`: `isinstance(v, int | float)` is a runtime `TypeError`

**Why this matters**
- `isinstance(x, int | float)` is not a valid `isinstance` check; it will raise `TypeError`.
- This will break ingestion/validation for any payload that includes `AvailableShitcoin.max_bet` / `max_win` values.

**Where**
- `src/models/events/game_state_update.py:202` (`AvailableShitcoin.coerce_decimal`)

**Recommended remediation**
- Replace with `isinstance(v, (int, float))` and consider handling `Decimal`/`str` explicitly if needed.

### 2) `trade_events.py`: latency calculations likely inverted (and possibly conceptually wrong)

**Why this matters**
- `SidebetResponse.calculate_latency()` and `TradeOrderResponse.calculate_latency()` return `client_timestamp - self.timestamp`.
- If `client_timestamp` is “request sent time” and `self.timestamp` is “server response time”, you’ll get a negative value.
- Even if both are “client clock” timestamps, the naming suggests server timestamps, and the sign should be clarified so downstream metrics are meaningful.

**Where**
- `src/models/events/trade_events.py:136` (`SidebetResponse.calculate_latency`)
- `src/models/events/trade_events.py:220` (`TradeOrderResponse.calculate_latency`)

**Recommended remediation**
- Decide and document what `client_timestamp` means (request sent time vs response received time).
- Make the function return a **positive** duration by convention (e.g., `self.timestamp - client_timestamp` if both are comparable).

## Medium Priority Findings (Fix When Practical)

### 3) `trade_events.py`: `NewTrade.is_whale_trade` is a `@property` that accepts a parameter

**Why this matters**
- A property cannot be parameterized by callers; the `threshold` argument is effectively locked to its default.
- This can mislead call sites that expect to tune the threshold.

**Where**
- `src/models/events/trade_events.py` (`NewTrade.is_whale_trade`)

**Recommended remediation**
- Either remove the parameter and keep it as a property, or remove `@property` and make it a normal method.

### 4) Timestamp timezone consistency (naive vs UTC-aware)

**Why this matters**
- Several models use `datetime.utcnow()` or `datetime.fromtimestamp(...)` without timezone info, producing naive datetimes/strings.
- Other parts of the codebase (e.g., CDP interception) use timezone-aware UTC timestamps.
- Mixed conventions complicate ordering/correlation across sources.

**Where**
- `src/models/events/system_events.py` (`Field(default_factory=datetime.utcnow)`)
- `src/models/recording_config.py` (uses `datetime.now()` / `fromisoformat`)
- `src/models/recording_models.py` (uses `datetime.utcnow` defaults, `.isoformat()` serialization)

**Recommended remediation**
- Prefer timezone-aware UTC datetimes (`datetime.now(timezone.utc)`) for new ingestion timestamps, or standardize on one convention and document it.

### 5) `GameTick`: boolean coercion and precision/rounding behaviors

**Why this matters**
- `GameTick.from_dict()` uses `bool(data.get("active", False))` / `bool(data.get("rugged", False))`.
  - If these ever arrive as strings (e.g., `"false"`), Python treats non-empty strings as `True`.
- `__post_init__` rounds to 8 decimal places via `round(float(...), 8)` for non-Decimal prices, which may:
  - lose precision unexpectedly,
  - or introduce float conversion noise.

**Where**
- `src/models/game_tick.py` (`from_dict`, `__post_init__`)

**Recommended remediation**
- Use explicit boolean parsing (accept `bool`, `0/1`, `"true"/"false"`).
- Use `Decimal(str(value))` directly for floats/strings and perform quantization via `Decimal.quantize` when rounding is required.

### 6) `recording_models.GameStateRecord.fill_gaps()` silently ignores ticks beyond current array length

**Why this matters**
- If partial price backfills contain ticks you never appended (common if you missed a burst), `fill_gaps()` will skip them.
- This can produce incomplete recordings while still reporting “filled gaps”.

**Where**
- `src/models/recording_models.py` (`GameStateRecord.fill_gaps`)

**Recommended remediation**
- Extend `self.prices` to the max tick seen in `partial_prices` before filling (similar to `add_price` behavior).

### 7) Enum coverage mismatch for phases

**Why this matters**
- Several parts of the system refer to `"RUG_EVENT_2"`, but `Phase` only defines `RUG_EVENT` and `RUG_EVENT_1`.
- This is not necessarily breaking, but it increases drift between “phase strings in the wild” and the canonical enum.

**Where**
- `src/models/enums.py` (`Phase`)
- Cross-reference: live feed / state machine uses `"RUG_EVENT_2"`

**Recommended remediation**
- Either add the missing phase(s) or clearly document which phase strings are expected to exist.

## Low Priority Findings / Opportunities

### 8) Public API surface in `models/__init__.py`

**Notes**
- `src/models/__init__.py` re-exports many identifiers; this effectively becomes a stable API layer for the rest of the app/tests.
- Keep changes here deliberate to avoid churn across imports.

### 9) Duplication between demonstration and validation snapshots

**Notes**
- `src/models/demo_action.py:StateSnapshot` and `src/models/recording_models.py:LocalStateSnapshot` overlap conceptually but differ in field names and shape.
- This may be intentional (demo vs validation), but it’s easy for data producers/consumers to mix them up.

## Suggested Validation Checklist (After Fixes)

- Run tests: `cd src && python3 -m pytest tests/ -v`
- Specifically verify:
  - schema validation coverage still passes (Pydantic validators run on real payloads),
  - trade latency metrics are positive and consistent,
  - `GameTick.from_dict()` behaves correctly with non-bool inputs and preserves desired precision.
