# Foundation API Contract

**Version:** 1.0.0
**Date:** 2026-01-25
**Status:** Active

---

## Overview

This document defines the API contract between the Foundation Service and HTML artifacts. All artifacts MUST use these event types and schemas. This contract is enforced by hookify rules and CI/CD validation.

**When in doubt about event semantics, query the rugs-expert MCP server.**

---

## Connection

### WebSocket Endpoint

```
ws://localhost:9000/feed
```

### Recommended Client

```javascript
import { FoundationWSClient } from '/shared/foundation-ws-client.js';

const client = new FoundationWSClient();
client.on('game.tick', (data) => console.log(data));
client.connect();
```

---

## Event Types

| Foundation Event | rugs.fun Source | Purpose | Frequency |
|------------------|-----------------|---------|-----------|
| `game.tick` | gameStateUpdate | Price/tick stream | ~4/sec |
| `player.state` | playerUpdate | Balance/position | On change (AUTH) |
| `player.trade` | standard/newTrade | Trade broadcasts | Per trade |
| `player.leaderboard` | playerLeaderboardPosition | Leaderboard rank | On change |
| `connection.authenticated` | usernameStatus | Auth confirmation | Once |
| `sidebet.placed` | currentSidebet | Sidebet placement | Per sidebet |
| `sidebet.result` | currentSidebetResult | Sidebet outcome | Per result |
| `connection` | internal | WS connect/disconnect | On state change |

---

## Event Envelope

All events follow this envelope structure:

```json
{
  "type": "game.tick",
  "ts": 1737830112000,
  "gameId": "20260125-7aa96600beb...",
  "seq": 141,
  "data": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Event type (see table above) |
| `ts` | number | Unix timestamp in milliseconds |
| `gameId` | string\|null | Current game ID (null for connection events) |
| `seq` | number | Sequence number (monotonically increasing) |
| `data` | object | Event-specific payload |

---

## Event Schemas

### game.tick

Primary event for game state. Emitted ~4 times per second.

```json
{
  "type": "game.tick",
  "ts": 1737830112000,
  "gameId": "20260125-7aa96600beb...",
  "seq": 141,
  "data": {
    "active": true,
    "rugged": false,
    "price": 6.05,
    "tickCount": 141,
    "phase": "ACTIVE",
    "cooldownTimer": 0,
    "allowPreRoundBuys": false,
    "tradeCount": 42,
    "leaderboard": [...],
    "gameHistory": [...]
  }
}
```

#### data Fields

| Field | Type | Description |
|-------|------|-------------|
| `active` | boolean | Game is currently active |
| `rugged` | boolean | Game has been rugged |
| `price` | number | Current token price |
| `tickCount` | number | Current tick number |
| `phase` | string | Game phase (see below) |
| `cooldownTimer` | number | Seconds until next game (0 if not in cooldown) |
| `allowPreRoundBuys` | boolean | Pre-round buying allowed |
| `tradeCount` | number | Total trades this game |
| `leaderboard` | array\|null | Top players list |
| `gameHistory` | array\|null | Recent game history |

#### Phase Values

| Phase | Condition |
|-------|-----------|
| `COOLDOWN` | `cooldownTimer > 0` |
| `PRESALE` | `allowPreRoundBuys=true && active=false` |
| `ACTIVE` | `active=true && rugged=false` |
| `RUGGED` | `rugged=true` |
| `UNKNOWN` | None of the above |

---

### player.state

Player balance and position. Emitted on change (requires authentication).

```json
{
  "type": "player.state",
  "ts": 1737830112000,
  "gameId": "20260125-7aa96600beb...",
  "seq": 200,
  "data": {
    "cash": 0.09503525,
    "positionQty": 0.003384584,
    "avgCost": 1.181828845,
    "totalInvested": 0.004,
    "cumulativePnL": 0.000888953
  }
}
```

#### data Fields

| Field | Type | Description |
|-------|------|-------------|
| `cash` | number | Available SOL balance |
| `positionQty` | number | Token quantity held |
| `avgCost` | number | Average cost basis per token |
| `totalInvested` | number | Total SOL invested |
| `cumulativePnL` | number | Cumulative profit/loss in SOL |

---

### connection.authenticated

Authentication confirmation. Emitted once after successful connection.

```json
{
  "type": "connection.authenticated",
  "ts": 1737830100000,
  "gameId": null,
  "seq": 5,
  "data": {
    "username": "Dutch",
    "player_id": "did:privy:cmaibr7rt0094jp0mc2mbpfu4",
    "hasUsername": true
  }
}
```

#### data Fields

| Field | Type | Description |
|-------|------|-------------|
| `username` | string | Player display name |
| `player_id` | string | Unique player identifier (DID format) |
| `hasUsername` | boolean | Whether username is set |

---

### player.trade

Trade broadcast from any player. Emitted per trade.

```json
{
  "type": "player.trade",
  "ts": 1737830115000,
  "gameId": "20260125-7aa96600beb...",
  "seq": 250,
  "data": {
    "username": "TraderJoe",
    "type": "buy",
    "qty": 0.01,
    "price": 6.10,
    "playerId": "did:privy:abc123..."
  }
}
```

#### data Fields

| Field | Type | Description |
|-------|------|-------------|
| `username` | string | Trader's display name |
| `type` | string | Trade type: `"buy"` or `"sell"` |
| `qty` | number | Trade quantity in SOL |
| `price` | number | Execution price |
| `playerId` | string | Trader's player ID |

---

### player.leaderboard

Leaderboard position update. Emitted when rank changes.

```json
{
  "type": "player.leaderboard",
  "ts": 1737830120000,
  "gameId": "20260125-7aa96600beb...",
  "seq": 300,
  "data": {
    "position": 5,
    "pnlPercent": 44.5
  }
}
```

---

### sidebet.placed

Sidebet placement confirmation.

```json
{
  "type": "sidebet.placed",
  "ts": 1737830130000,
  "gameId": "20260125-7aa96600beb...",
  "seq": 350,
  "data": {
    "betType": "over",
    "amount": 0.01,
    "target": 10.0
  }
}
```

---

### sidebet.result

Sidebet outcome.

```json
{
  "type": "sidebet.result",
  "ts": 1737830200000,
  "gameId": "20260125-7aa96600beb...",
  "seq": 400,
  "data": {
    "won": true,
    "payout": 0.019,
    "betType": "over"
  }
}
```

---

### connection

Internal connection state. Emitted by FoundationWSClient.

```json
{
  "type": "connection",
  "data": {
    "connected": true
  }
}
```

On disconnect:
```json
{
  "type": "connection",
  "data": {
    "connected": false,
    "code": 1006
  }
}
```

---

## Contract Rules

### Rule 1: Document First

No new event types may be added to Foundation without updating this contract document first.

### Rule 2: Backward Compatible

- **New fields** = Optional (artifacts must handle their absence)
- **Removed fields** = 2-week deprecation notice
- **Type changes** = Major version bump

### Rule 3: Version Bumps

| Change Type | Version Impact |
|-------------|----------------|
| New optional field | Patch (1.0.x) |
| New event type | Minor (1.x.0) |
| Breaking change | Major (x.0.0) |

### Rule 4: Query rugs-expert

When in doubt about event semantics, timing, or edge cases:

```javascript
// Use rugs-expert MCP for authoritative answers
mcp__rugs-expert__search_rugs_knowledge({ query: "gameStateUpdate fields" })
mcp__rugs-expert__get_game_event_schema({ event_name: "gameStateUpdate" })
```

---

## Changelog

### v1.0.0 (2026-01-25)

- Initial release
- Documented 8 event types
- Aligned with `src/foundation/normalizer.py`
