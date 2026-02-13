# Rugs Sanitizer Subscriber Guide

**Version:** 1.0.0 | **Service Port:** 9017 | **Rosetta Stone:** v0.2.0

This document is the canonical reference for building downstream subscribers that consume the rugs-sanitizer WebSocket feed. Follow this guide exactly to ensure consistent, reliable integration.

---

## Quick Start

```javascript
// Minimal subscriber — connect, receive, process
const ws = new WebSocket('ws://localhost:9017/feed/all');

ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    // msg.channel = "game" | "stats" | "trades" | "history"
    // msg.data    = sanitized model payload
    // msg.phase   = "ACTIVE" | "RUGGED" | "PRESALE" | "COOLDOWN" | "UNKNOWN"
    // msg.game_id = current game ID (e.g. "20260207-88dd406ff6d74eb1")
    console.log(`[${msg.channel}] phase=${msg.phase}`, msg.data);
};
```

```python
# Python subscriber (asyncio)
import asyncio
import json
import websockets

async def subscribe():
    async with websockets.connect("ws://localhost:9017/feed/game") as ws:
        async for raw in ws:
            msg = json.loads(raw)
            print(f"[{msg['channel']}] price={msg['data']['price']}")

asyncio.run(subscribe())
```

---

## Architecture

```
rugs.fun (raw WebSocket)
    |
    v
rugs-feed (port 9016) -- raw event relay
    |
    v
rugs-sanitizer (port 9017) -- typed, phase-annotated, categorized
    |
    +---> /feed/game     GameTick events (~4/sec during active play)
    +---> /feed/stats    SessionStats events (~4/sec, mostly unchanged)
    +---> /feed/trades   Annotated Trade events (sporadic, ~0-2/sec)
    +---> /feed/history  GameHistoryRecord events (every 10th rug)
    +---> /feed/all      All channels combined
```

**Subscribers never connect to rugs.fun directly.** The sanitizer is the single source of truth for all downstream consumers.

---

## Connection Endpoints

| Endpoint | Use Case |
|----------|----------|
| `ws://localhost:9017/feed/game` | Price/tick stream, phase detection, daily records |
| `ws://localhost:9017/feed/stats` | Player count, multiplier averages |
| `ws://localhost:9017/feed/trades` | Individual player trades with annotations |
| `ws://localhost:9017/feed/history` | Complete game records (prices array, provably fair) |
| `ws://localhost:9017/feed/all` | All of the above (use for monitors/dashboards) |

**Choose the narrowest channel that covers your needs.** A trading bot only needs `/feed/game`. A trade analyzer needs `/feed/trades`. Only use `/feed/all` for full-spectrum monitors.

### HTTP Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check with upstream/pipeline/broadcaster stats |
| `/stats` | GET | Detailed pipeline statistics (poll every 5s max) |
| `/channels` | GET | List channels with current client counts |
| `/monitor` | GET | Built-in diagnostic UI |

---

## Wire Format: SanitizedEvent Envelope

Every WebSocket message is a JSON object with this structure:

```json
{
    "channel": "game",
    "event_type": "gameStateUpdate",
    "data": { ... },
    "timestamp": "2026-02-07T19:14:21.903000+00:00",
    "game_id": "20260207-88dd406ff6d74eb1",
    "phase": "ACTIVE"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `channel` | string | `"game"`, `"stats"`, `"trades"`, or `"history"` |
| `event_type` | string | Original rugs.fun event name |
| `data` | object | Channel-specific payload (see schemas below) |
| `timestamp` | string | ISO 8601 UTC timestamp |
| `game_id` | string | Current game ID (format: `YYYYMMDD-hex16`) |
| `phase` | string | Derived game phase (see Phase Detection) |

---

## Phase Detection

The sanitizer derives phase from raw fields using this priority:

| Priority | Condition | Phase |
|----------|-----------|-------|
| 1 | `active=true AND rugged=false` | `ACTIVE` |
| 2 | `rugged=true` | `RUGGED` |
| 3 | `cooldown_timer > 0 AND allow_pre_round_buys=true` | `PRESALE` |
| 4 | `cooldown_timer > 0` | `COOLDOWN` |
| 5 | `allow_pre_round_buys=true` | `PRESALE` |
| 6 | None matched | `UNKNOWN` |

**Game lifecycle:** `ACTIVE` -> `RUGGED` -> `COOLDOWN` -> `PRESALE` -> `ACTIVE` (next game)

**Key timing:** The cooldown is 15 seconds total (5s settlement buffer + 10s player-facing presale). There is no `timer=0` event on the wire -- use `active=true` as the game-start signal.

> **Rosetta Stone Reference:** Section 1.2 (Phase Detection), Section 1.3 (Timing)

---

## Channel Schemas

### /feed/game -- GameTick

Emitted ~4 times per second during active play, plus transition ticks during cooldown.

```json
{
    "game_id": "20260207-88dd406ff6d74eb1",
    "phase": "ACTIVE",
    "active": true,
    "price": 2.3456,
    "rugged": false,
    "tick_count": 195,
    "trade_count": 42,
    "cooldown_timer": 0,
    "cooldown_paused": false,
    "allow_pre_round_buys": false,
    "partial_prices": {
        "start_tick": 191,
        "end_tick": 195,
        "values": { "191": 2.30, "192": 2.31, "193": 2.34, "194": 2.33, "195": 2.35 }
    },
    "provably_fair": {
        "server_seed_hash": "80dc4d98...",
        "version": "v3",
        "server_seed": null
    },
    "rugpool": {
        "instarug_count": 3,
        "threshold": 10,
        "rugpool_amount": 0.15
    },
    "leaderboard": [ ... ],
    "game_version": "v3",
    "daily_records": null,
    "has_god_candle": false
}
```

| Field | Type | Always Present | Notes |
|-------|------|:--------------:|-------|
| `game_id` | string | Yes | Provably fair triplet member |
| `phase` | string | Yes | Derived (see Phase Detection) |
| `active` | bool | Yes | `true` = game in play |
| `price` | float | Yes | Current multiplier (starts at 1.0) |
| `rugged` | bool | Yes | `true` = game ended |
| `tick_count` | int | Yes | Monotonic tick counter |
| `trade_count` | int | No | Total trades this game |
| `cooldown_timer` | int | Yes | Seconds remaining (0 during active) |
| `partial_prices` | object/null | No | Current candlestick (5 ticks = 1.25s) |
| `provably_fair` | object/null | No | `server_seed` revealed only post-rug |
| `rugpool` | object/null | No | Consolation prize state |
| `leaderboard` | array | Yes | Top 10 by PnL (may be empty) |
| `daily_records` | object/null | Rare | Only on transition ticks (~0.5% of events) |
| `has_god_candle` | bool | Yes | Change-detected by backend (not stale re-reports) |

#### Transition-Only Fields: daily_records

`daily_records` appears only on 1-2 ticks per rug (the first cooldown ticks after the game ends). It is `null` on all active gameplay ticks. Subscribers that need this data **must cache it** -- it will not be re-sent until the next rug.

```json
{
    "highest_today": 12036.98,
    "highest_today_timestamp": 1770346597293,
    "highest_today_game_id": "20260207-bbe7588027a049fa",
    "highest_today_server_seed": "3b0be421...",
    "god_candle_2x": { "multiplier": null, "timestamp": null, "game_id": null, "server_seed": null, "massive_jump": null },
    "god_candle_10x": { "multiplier": null, "timestamp": null, "game_id": null, "server_seed": null, "massive_jump": null },
    "god_candle_50x": { "multiplier": 12036.98, "timestamp": 1770346597293, "game_id": "20260207-915a16cab2b34fe9", "server_seed": "...", "massive_jump": null }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `highest_today` | float/null | Highest peak multiplier of UTC day |
| `highest_today_game_id` | string/null | Game that set the daily record |
| `god_candle_Nx` | object | Tier record: `multiplier` non-null = god candle exists for this tier |

> **Rosetta Stone Reference:** Section 1.11 (Daily Records / God Candles)

#### Leaderboard Entry Schema

Each entry in the `leaderboard` array:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Player Privy DID |
| `username` | string | Display name |
| `level` | int | Player level (affects leverage access) |
| `pnl` | float | Total PnL (SOL) |
| `regular_pnl` | float | Long position PnL |
| `sidebet_pnl` | float | Sidebet PnL |
| `short_pnl` | float | Short position PnL |
| `pnl_percent` | float | PnL as percentage |
| `has_active_trades` | bool | Whether player has open positions |
| `position_qty` | float | Token units held |
| `avg_cost` | float | VWAP entry price (TENTATIVE) |
| `total_invested` | float | Cumulative SOL deployed (TENTATIVE) |
| `position` | int | Leaderboard rank (1 = top) |
| `side_bet` | object/null | Active sidebet (40-tick window, 5x payout) |
| `short_position` | object/null | Active short position |

> **Rosetta Stone Reference:** Section 1.9 (Leaderboard)

---

### /feed/stats -- SessionStats

Server-computed aggregate statistics. Updates ~4/sec but values change only at game boundaries (except `connected_players` which updates continuously).

```json
{
    "connected_players": 185,
    "average_multiplier": 126.91,
    "count_2x": 41,
    "count_10x": 11,
    "count_50x": 5,
    "count_100x": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `connected_players` | int | Current player count |
| `average_multiplier` | float/null | Rolling average of recent rug multipliers |
| `count_2x` | int/null | Games reaching 2x today |
| `count_10x` | int/null | Games reaching 10x today |
| `count_50x` | int/null | Games reaching 50x today |
| `count_100x` | int/null | Games reaching 100x today |

**Note:** Multiplier counts (`count_Nx`) reset to `null` during the cooldown between games. They are server-computed daily aggregates, not session-scoped.

> **Rosetta Stone Reference:** Section 1.5 (Server-Computed Stats)

---

### /feed/trades -- Annotated Trade

Individual player trades from `standard/newTrade` with sanitizer-added annotations.

```json
{
    "id": "trade-uuid",
    "game_id": "20260207-88dd406ff6d74eb1",
    "player_id": "did:privy:...",
    "username": "GOB",
    "level": 5,
    "price": 2.3456,
    "type": "buy",
    "tick_index": 195,
    "coin": "solana",
    "amount": 0.050,
    "qty": 0.021,
    "leverage": null,
    "bonus_portion": 0.050,
    "real_portion": 0.0,
    "is_forced_sell": false,
    "is_liquidation": false,
    "is_practice": true,
    "token_type": "practice"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique trade ID |
| `game_id` | string | Game this trade belongs to |
| `player_id` | string | Player Privy DID |
| `username` | string | Display name |
| `level` | int | Player level |
| `price` | float | Multiplier at trade time |
| `type` | string | `"buy"`, `"sell"`, `"short_open"`, `"short_close"` |
| `tick_index` | int | Tick when trade occurred |
| `coin` | string | Token identifier |
| `amount` | float | SOL amount |
| `qty` | float | Token quantity |
| `leverage` | int/null | Leverage multiplier (1-5, level 10+ only) |
| **Annotations** | | *Added by sanitizer (not from wire)* |
| `is_forced_sell` | bool | Sell during RUGGED phase (forced by platform) |
| `is_liquidation` | bool | Leveraged position hit liquidation threshold |
| `is_practice` | bool | Trade uses practice token |
| `token_type` | string | `"practice"`, `"real"`, or `"unknown"` |

**Critical note:** Forced sells at rug are indistinguishable from voluntary sells on the raw wire. The sanitizer infers `is_forced_sell` from the current phase -- if a sell occurs during `RUGGED` phase, it was forced.

> **Rosetta Stone Reference:** Event 2 (standard/newTrade)

---

### /feed/history -- GameHistoryRecord

Complete game records emitted during cooldown. The sanitizer collects these every 10th rug (configurable via `HISTORY_COLLECTION_INTERVAL`), plus on any rug where a god candle was detected.

```json
{
    "id": "20260207-88dd406ff6d74eb1",
    "timestamp": 1770388462000,
    "peak_multiplier": 3.85,
    "rugged": true,
    "game_version": "v3",
    "prices": [1.0, 1.02, 0.98, 1.05, ...],
    "global_trades": [],
    "global_sidebets": [ ... ],
    "provably_fair": {
        "server_seed": "abc123...",
        "server_seed_hash": "80dc4d98..."
    }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Game ID |
| `timestamp` | int | Unix ms when game ended |
| `peak_multiplier` | float | Highest multiplier reached |
| `rugged` | bool | Always `true` on public feed |
| `prices` | float[] | Complete tick-by-tick price array |
| `global_trades` | array | **Always empty on public feed** |
| `global_sidebets` | array | Sidebet records for the game |
| `provably_fair` | object | Both seed and hash revealed post-rug |

**The `prices` array is the most valuable field** -- it contains every tick's price for the entire game, enabling full replay and ML training.

> **Rosetta Stone Reference:** Section 1.10 (gameHistory)

---

## Subscriber Patterns

### Pattern 1: Phase-Aware State Machine

Most subscribers need to track game lifecycle:

```javascript
let currentPhase = 'UNKNOWN';
let currentGameId = null;

ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.channel !== 'game') return;

    const prevPhase = currentPhase;
    currentPhase = msg.phase;

    // New game detection
    if (msg.game_id !== currentGameId) {
        currentGameId = msg.game_id;
        onNewGame(msg.game_id);
    }

    // Phase transitions
    if (prevPhase !== currentPhase) {
        onPhaseChange(prevPhase, currentPhase, msg.data);
    }

    // Active gameplay
    if (currentPhase === 'ACTIVE') {
        onTick(msg.data);
    }
};
```

### Pattern 2: Sticky Rare Data

`daily_records` only appears on 1-2 transition ticks. Cache it:

```javascript
let cachedDailyRecords = null;

ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.channel !== 'game') return;

    // Update cache only when data is present
    if (msg.data.daily_records) {
        cachedDailyRecords = msg.data.daily_records;
    }

    // Use cachedDailyRecords throughout the session
};
```

### Pattern 3: Keepalive Ping

The sanitizer supports client-initiated pings for connection health monitoring:

```javascript
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'ping', ts: Date.now() }));
    }
}, 30000);

// Server responds with: { "type": "pong", "ts": <your_ts> }
```

### Pattern 4: Reconnection with Backoff

```javascript
let reconnectDelay = 1000;
const MAX_DELAY = 30000;

function connect() {
    const ws = new WebSocket('ws://localhost:9017/feed/game');

    ws.onopen = () => { reconnectDelay = 1000; };

    ws.onclose = () => {
        setTimeout(() => {
            reconnectDelay = Math.min(reconnectDelay * 1.5, MAX_DELAY);
            connect();
        }, reconnectDelay);
    };
}
```

---

## Common Gotchas

| Gotcha | Explanation |
|--------|-------------|
| `daily_records` is almost always `null` | Only appears on ~1-2 ticks per rug (~0.5% of events). Cache it. |
| `global_trades` is always empty | Public feed never includes other players' individual trades in history. |
| `has_god_candle` is change-detected | The raw wire re-reports stale god candle data all day. The sanitizer's `GodCandleDetector` only flags genuinely NEW god candles. |
| Multiplier counts reset during cooldown | `count_2x`, `count_10x`, etc. go `null` between games. |
| Presale positions are irrevocable | Once a player enters presale, they cannot exit until the game starts. |
| No `timer=0` event exists | Use `active=true` as the game-start signal. |
| Forced sells look like voluntary sells | The sanitizer infers `is_forced_sell` from phase. Don't re-derive it. |
| Leaderboard mixes practice + real | Filter by `selected_coin` if you need to distinguish practice from real players. |
| `partial_prices` = one candlestick | 5 ticks x 250ms = 1.25s, presented as a "1s candle". |
| Leverage requires level 10+ | 1-5x whole integers only. |

---

## Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `UPSTREAM_URL` | `ws://localhost:9016/feed` | rugs-feed WebSocket URL |
| `PORT` | `9017` | Service listen port (**sacred allocation**) |
| `HOST` | `0.0.0.0` | Bind address |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `HISTORY_COLLECTION_INTERVAL` | `10` | Collect gameHistory every N-th rug |

**Docker (docker-compose):**
```yaml
depends_on:
  rugs-feed:
    condition: service_healthy
environment:
  - UPSTREAM_URL=ws://vectra-rugs-feed:9016/feed
```

**Local development:**
```bash
cd services/rugs-sanitizer
.venv/bin/python -m src.main
```

---

## Health Monitoring

Before subscribing, verify the service is healthy:

```bash
curl http://localhost:9017/health | jq '.status, .upstream.state'
# "healthy"
# "connected"
```

Key health indicators:
- `status` = `"healthy"`
- `upstream.state` = `"connected"` (sanitizer connected to rugs-feed)
- `broadcaster.is_running` = `true`

---

## Reference Documents

| Document | Location | Description |
|----------|----------|-------------|
| **Rosetta Stone** | `docs/rosetta-stone/ROSETTA-STONE.md` | Canonical field definitions for all raw wire events |
| Rosetta Stone Samples | `docs/rosetta-stone/reference-data/key-samples.json` | Annotated real event samples |
| Full Game Recording | `docs/rosetta-stone/reference-data/game-20260206-*.json` | Complete 1,311-event game |
| Module Extension Spec | `docs/specs/MODULE-EXTENSION-SPEC.md` | Rules for adding new modules |
| Port Allocation | `docs/specs/PORT-ALLOCATION-SPEC.md` | Sacred port assignments |
| Sanitizer Models | `services/rugs-sanitizer/src/models.py` | Pydantic schema source of truth |

---

*Rugs Sanitizer v1.0.0 | Rosetta Stone v0.2.0 | February 2026*
