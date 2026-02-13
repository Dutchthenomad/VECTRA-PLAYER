# PRNG Attack Suite - Complete Connection Guide
**rugs.fun WebSocket Protocol for Containerized PRNG Analysis**
**Version**: 3.0 | **Date**: February 4, 2026

---

## Executive Summary

This guide provides everything needed to build a containerized, persistent WebSocket connection to rugs.fun for running PRNG attack suites and statistical analysis.

**Critical Success Factors:**
1. Use **Chrome DevTools Protocol (CDP)** for authenticated connections
2. Target WebSocket URL: `wss://backend.rugs.fun?frontend-version=1.0`
3. Protocol: **Socket.IO v4** (Engine.IO transport layer)
4. Server seeds revealed ONLY after rug event via `provablyFair` object

---

## 1. WebSocket Connection Details

### Primary Connection Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| **WebSocket URL** | `wss://backend.rugs.fun?frontend-version=1.0` | Socket.IO endpoint |
| **Protocol** | Socket.IO v4 (Engine.IO) | NOT raw WebSocket |
| **Broadcast Rate** | ~4 messages/sec (~250ms) | During active games |
| **Transport** | WebSocket with polling fallback | Engine.IO handles this |
| **Auth Method** | Phantom Wallet (Solana) via browser | CDP required for auth events |

### Socket.IO Message Prefixes

| Prefix | Type | Direction | Description |
|--------|------|-----------|-------------|
| `0` | OPEN | Server→Client | Connection handshake |
| `2` | PING | Bidirectional | Heartbeat keepalive |
| `3` | PONG | Bidirectional | Heartbeat response |
| `4` | MESSAGE | Bidirectional | Generic message |
| `42` | EVENT | Server→Client | JSON event broadcast |
| `42XXXX` | REQUEST | Client→Server | Request with ID XXXX |
| `43XXXX` | ACK | Server→Client | Response to request XXXX |

### Example Frame Structure

```javascript
// Standard broadcast (most common)
42["gameStateUpdate", {"gameId": "20251228-xxx", "price": 1.5, ...}]

// Client request (trade action)
42424["buyOrder", {"amount": 0.001}]

// Server ACK response
43424[{"success": true, "timestamp": 1765069123456}]
```

### Parsing Logic

```python
def parse_socketio_frame(payload: str) -> tuple:
    """Parse Socket.IO frame into (event_name, data)."""
    if not payload.startswith('42'):
        return None, None  # Not an event frame

    # Strip "42" prefix
    json_str = payload[2:]

    # Parse JSON array: [event_name, data]
    try:
        parsed = json.loads(json_str)
        if len(parsed) >= 2:
            return parsed[0], parsed[1]  # event_name, data
    except json.JSONDecodeError:
        return None, None

    return None, None
```

---

## 2. Game Events for PRNG Analysis

### Core Events (Priority 0 - Critical)

#### gameStateUpdate (PRIMARY TICK EVENT)

**Frequency**: ~4/sec during active games
**Auth Required**: No
**Contains**: Complete game state including price history

```json
{
  "gameId": "20251228-242b2d81e73e4f27",
  "gameVersion": "v3",
  "active": true,
  "rugged": false,
  "price": 1.4444769765026393,
  "tickCount": 16,
  "cooldownTimer": 0,
  "allowPreRoundBuys": false,
  "partialPrices": {
    "startTick": 10,
    "endTick": 16,
    "values": {
      "10": 1.0,
      "11": 1.05,
      "12": 1.12,
      "13": 1.08,
      "14": 1.15,
      "15": 1.22,
      "16": 1.4444769765026393
    }
  },
  "provablyFair": {
    "serverSeedHash": "bce190330836fffda61bdecbed6d8a83bfb7bb3a6b2bd278002a36df773c809a",
    "version": "v3"
  },
  "gameHistory": [
    {
      "id": "20251228-previous-game-id",
      "timestamp": 1765068982439,
      "prices": [1.0, 0.99, 1.01, 1.05, ... ],
      "rugged": true,
      "peakMultiplier": 45.23,
      "provablyFair": {
        "serverSeed": "6500cdbe92a642aac84b178756ceea75665fd5f82ced512ecadb30fefed15755",
        "serverSeedHash": "961079f9f7ebb139fe1c89d74bb16d0b606776c508b1b75c428ff39b077d7a8a",
        "version": "v3"
      }
    }
  ]
}
```

**Key Fields for PRNG Analysis:**

| Field | Type | Critical For |
|-------|------|--------------|
| `gameId` | string | Seed component (format: `YYYYMMDD-uuid`) |
| `price` | float | Current tick price |
| `tickCount` | int | Tick counter (~4 ticks/sec) |
| `partialPrices.values` | object | Rolling window of recent prices |
| `provablyFair.serverSeedHash` | string | Pre-reveal hash (SHA-256) |
| `gameHistory[].prices[]` | array | Complete price series for completed games |
| `gameHistory[].provablyFair.serverSeed` | string | REVEALED server seed (post-rug) |

---

## 3. Server Seed Revelation Timeline

**CRITICAL**: Server seeds are revealed ONLY after the game rugs.

### Lifecycle Phases

```
┌──────────────┐
│   COOLDOWN   │  cooldownTimer > 0
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   PRESALE    │  allowPreRoundBuys = true, active = false
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    ACTIVE    │  active = true, rugged = false
│              │  serverSeedHash visible (NOT seed)
└──────┬───────┘
       │
       ▼  (RUG EVENT)
┌──────────────┐
│    RUGGED    │  rugged = true
│              │  serverSeed REVEALED in gameHistory[]
└──────────────┘
```

### Server Seed Availability

| Phase | serverSeedHash | serverSeed | Where |
|-------|----------------|------------|-------|
| PRESALE | ✅ Visible | ❌ Hidden | `gameStateUpdate.provablyFair.serverSeedHash` |
| ACTIVE | ✅ Visible | ❌ Hidden | `gameStateUpdate.provablyFair.serverSeedHash` |
| RUGGED | ✅ Visible | ❌ Hidden (current) | Current game's seed NOT revealed yet |
| RUGGED | ✅ Visible | ✅ REVEALED | `gameHistory[0].provablyFair.serverSeed` |

**Key Insight**: On rug event, the CURRENT game's seed is NOT revealed. You must wait for it to appear in `gameHistory[]` array (typically 1-2 ticks after rug).

---

## 4. PRNG Algorithm (v3)

### Seed Combination

```javascript
const combinedSeed = serverSeed + '-' + gameId;
const prng = new Math.seedrandom(combinedSeed);
```

**Example:**
- `serverSeed`: `"6500cdbe92a642aac84b178756ceea75665fd5f82ced512ecadb30fefed15755"`
- `gameId`: `"20251218-831db215e62e461e"`
- `combinedSeed`: `"6500cdbe92a642aac84b178756ceea75665fd5f82ced512ecadb30fefed15755-20251218-831db215e62e461e"`

### Game Constants (v3)

```javascript
const RUG_PROB = 0.005;              // 0.5% per tick
const DRIFT_MIN = -0.02;             // -2% min drift
const DRIFT_MAX = 0.03;              // +3% max drift
const BIG_MOVE_CHANCE = 0.125;       // 12.5% chance
const BIG_MOVE_MIN = 0.15;           // 15% min big move
const BIG_MOVE_MAX = 0.25;           // 25% max big move
const GOD_CANDLE_CHANCE = 0.00001;   // 0.001% chance
const GOD_CANDLE_MOVE = 10.0;        // 10x multiplier
const STARTING_PRICE = 1.0;
```

### Price Generation Algorithm

```javascript
function driftPrice(price, randFn, version = 'v3') {
    // God Candle (v3 only) - rare 10x jump if price <= 100x
    if (version === 'v3' && randFn() < GOD_CANDLE_CHANCE && price <= 100 * STARTING_PRICE) {
        return price * GOD_CANDLE_MOVE;
    }

    let change = 0;

    // Big move (12.5% chance)
    if (randFn() < BIG_MOVE_CHANCE) {
        const moveSize = BIG_MOVE_MIN + randFn() * (BIG_MOVE_MAX - BIG_MOVE_MIN);
        change = randFn() > 0.5 ? moveSize : -moveSize;
    } else {
        // Normal drift
        const drift = DRIFT_MIN + randFn() * (DRIFT_MAX - DRIFT_MIN);
        const volatility = 0.005 * Math.min(10, Math.sqrt(price));  // v3 caps volatility
        change = drift + (volatility * (2 * randFn() - 1));
    }

    let newPrice = price * (1 + change);
    return Math.max(0, newPrice);  // Floor at 0
}

function simulateGame(serverSeed, gameId, version = 'v3') {
    const combinedSeed = serverSeed + '-' + gameId;
    const prng = new Math.seedrandom(combinedSeed);

    let price = STARTING_PRICE;
    let peakMultiplier = STARTING_PRICE;
    let prices = [price];

    for (let tick = 0; tick < 5000; tick++) {
        // Check for rug (0.5% per tick)
        if (prng() < RUG_PROB) {
            return { rugged: true, peakMultiplier, prices, rugTick: tick };
        }

        // Calculate next price
        price = driftPrice(price, prng.bind(prng), version);
        prices.push(price);

        if (price > peakMultiplier) {
            peakMultiplier = price;
        }
    }

    // Auto-rug at tick 5000
    return { rugged: true, peakMultiplier, prices, rugTick: 5000 };
}
```

---

## 5. Game Timing & Lifecycle

### Phase Detection Logic

```python
def detect_phase(event: dict) -> str:
    """Determine current game phase from gameStateUpdate."""
    if event.get('cooldownTimer', 0) > 0:
        return 'COOLDOWN'
    elif event.get('rugged', False) and not event.get('active', False):
        return 'COOLDOWN'  # Brief moment after rug
    elif event.get('allowPreRoundBuys', False) and not event.get('active', False):
        return 'PRESALE'
    elif event.get('active', False) and not event.get('rugged', False):
        return 'ACTIVE'
    elif event.get('rugged', False):
        return 'RUGGED'
    else:
        return 'UNKNOWN'
```

### Typical Game Duration

| Metric | Typical Range | Notes |
|--------|---------------|-------|
| Rug probability | 0.5% per tick | Independent trials |
| Tick rate | ~4/sec | 250ms intervals |
| Expected duration | ~50 seconds | Geometric distribution E[X] = 1/p = 200 ticks |
| Median duration | ~35 seconds | ln(0.5)/ln(0.995) ≈ 138 ticks |
| Max duration | 20.8 minutes | Hard limit: 5000 ticks |
| Cooldown | 10-30 seconds | Between games |

### Game Start/End Detection

```python
# Game start
if current['active'] == True and previous['active'] == False:
    print(f"GAME_START: gameId={current['gameId']}")
    print(f"  serverSeedHash: {current['provablyFair']['serverSeedHash']}")

# Rug event
if current['rugged'] == True and previous['rugged'] == False:
    print(f"RUG_EVENT: gameId={current['gameId']}, tick={current['tickCount']}")
    # Wait for serverSeed in gameHistory[]

# Server seed revealed (1-2 ticks after rug)
if 'gameHistory' in current and len(current['gameHistory']) > 0:
    latest_game = current['gameHistory'][0]
    if 'serverSeed' in latest_game.get('provablyFair', {}):
        print(f"SERVER_SEED_REVEALED:")
        print(f"  gameId: {latest_game['id']}")
        print(f"  serverSeed: {latest_game['provablyFair']['serverSeed']}")
        print(f"  prices: {len(latest_game['prices'])} ticks")
```

---

## 6. Rate Limiting & Connection Requirements

### Connection Stability

| Metric | Value | Notes |
|--------|-------|-------|
| Max idle timeout | Unknown | Send ping every 30 sec to be safe |
| Reconnect backoff | Standard Socket.IO | Exponential backoff on disconnect |
| Max concurrent connections | Unknown | Multiple connections from same IP work |
| IP bans | None observed | No rate limiting detected |

### Heartbeat Protocol

```javascript
// Client → Server (every ~30 seconds)
42XX["ping", {"lastPing": 169.2}]

// Server → Client
// (No explicit pong, just continued broadcasts)
```

### Data Availability Windows

| Data Type | When Available | Where |
|-----------|----------------|-------|
| Current game state | Always | `gameStateUpdate` root |
| Current price | Always | `gameStateUpdate.price` |
| Price history (rolling) | Always | `gameStateUpdate.partialPrices` |
| Server seed hash | PRESALE/ACTIVE/RUGGED | `gameStateUpdate.provablyFair.serverSeedHash` |
| Server seed REVEALED | After rug (1-2 ticks) | `gameStateUpdate.gameHistory[0].provablyFair.serverSeed` |
| Completed game prices | After rug | `gameStateUpdate.gameHistory[0].prices[]` |
| Last ~10 games | Always | `gameStateUpdate.gameHistory[]` (rolling window) |

---

## 7. Authentication (Optional)

### Authenticated vs Unauthenticated Connections

**Unauthenticated** (Direct WebSocket):
- ✅ Receives `gameStateUpdate` (all game data)
- ✅ Receives `standard/newTrade` (trade broadcasts)
- ❌ Does NOT receive `playerUpdate` (balance/position)
- ❌ Does NOT receive `usernameStatus` (identity)
- ❌ Cannot place trades

**Authenticated** (Via CDP + Phantom Wallet):
- ✅ All unauthenticated events
- ✅ `playerUpdate` - Server balance verification
- ✅ `usernameStatus` - Player identity
- ✅ Can place trades via `buyOrder`/`sellOrder`

**Recommendation for PRNG Suite**: Use **unauthenticated connection** unless you need to:
1. Verify server balance calculations
2. Place automated trades
3. Track personal PnL

### Simple Unauthenticated Connection (Python)

```python
import socketio

sio = socketio.Client()

@sio.on('gameStateUpdate')
def on_game_state(data):
    print(f"Tick {data['tickCount']}: Price = {data['price']:.4f}")

    # Check for revealed seeds
    if 'gameHistory' in data and len(data['gameHistory']) > 0:
        latest = data['gameHistory'][0]
        if 'serverSeed' in latest.get('provablyFair', {}):
            print(f"SEED REVEALED: {latest['provablyFair']['serverSeed']}")

@sio.event
def connect():
    print("Connected to rugs.fun")

@sio.event
def disconnect():
    print("Disconnected from rugs.fun")

# Connect
sio.connect('https://backend.rugs.fun?frontend-version=1.0')
sio.wait()
```

---

## 8. PRNG Attack Suite Data Flow

### Recommended Architecture

```
┌──────────────────────────────────────────────────┐
│              WebSocket Client                    │
│  (Socket.IO to wss://backend.rugs.fun)          │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│           Event Stream Parser                    │
│  - Filter gameStateUpdate events                 │
│  - Extract gameId, prices, serverSeedHash        │
│  - Detect rug events                             │
│  - Extract revealed serverSeed from gameHistory  │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│          Game State Tracker                      │
│  - Current game: gameId, tick, price             │
│  - Historical games: seed + full price series    │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│         PRNG Verification Engine                 │
│  - Verify serverSeed hash matches                │
│  - Replay game with seed + gameId                │
│  - Compare observed vs predicted prices          │
│  - Detect deviations (if any)                    │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│      Statistical Analysis Pipeline               │
│  - Rug distribution analysis                     │
│  - Price drift correlations                      │
│  - God candle frequency                          │
│  - Seed entropy analysis                         │
└──────────────────────────────────────────────────┘
```

### Container Persistence Strategy

**Store in persistent volume:**
1. **Raw events**: `gameStateUpdate` JSON per game
2. **Verified seeds**: `{gameId, serverSeed, serverSeedHash, verified: bool}`
3. **Price series**: `{gameId, prices[], tickCount, peakMultiplier}`
4. **Analysis results**: Statistical outputs, anomaly flags

**Example Docker Compose:**

```yaml
version: '3.8'

services:
  prng-collector:
    image: prng-attack-suite:latest
    container_name: rugs-prng-collector
    restart: unless-stopped
    volumes:
      - ./data/raw_events:/app/data/raw_events
      - ./data/verified_seeds:/app/data/verified_seeds
      - ./data/analysis:/app/data/analysis
    environment:
      - RUGS_WS_URL=https://backend.rugs.fun?frontend-version=1.0
      - LOG_LEVEL=INFO
      - VERIFY_SEEDS=true
    networks:
      - prng-net

networks:
  prng-net:
    driver: bridge
```

---

## 9. Complete Event Reference

### All Available Events

| Event | Auth | Frequency | Purpose |
|-------|:----:|-----------|---------|
| `gameStateUpdate` | No | ~4/sec | Core game state (CRITICAL) |
| `standard/newTrade` | No | Sporadic | Trade broadcasts (all players) |
| `goldenHourUpdate` | No | Sporadic | Special tournament events |
| `usernameStatus` | **Yes** | Once on connect | Player identity confirmation |
| `playerUpdate` | **Yes** | After trades | Balance/position sync |
| `gameStatePlayerUpdate` | **Yes** | After trades | Your leaderboard entry |
| `buyOrder` / `sellOrder` | **Yes** | On action | Trade requests |
| `requestSidebet` | **Yes** | On action | Sidebet placement |
| `currentSidebet` | **Yes** | After sidebet | Sidebet confirmation |
| `currentSidebetResult` | **Yes** | On rug | Sidebet payout |
| `success` | **Yes** | After request | ACK response |
| `ping` | No | ~30 sec | Heartbeat |

**For PRNG Analysis**: Focus on `gameStateUpdate` - contains everything needed.

---

## 10. Troubleshooting

### No Events Received

**Problem**: Socket.IO connects but no events arrive

**Solutions**:
1. Verify frontend-version query param: `?frontend-version=1.0`
2. Check Socket.IO client version (need v4 compatible)
3. Enable debug logging: `socketio.Client(logger=True, engineio_logger=True)`
4. Test with web browser DevTools (Network → WS filter)

### Server Seed Never Revealed

**Problem**: `gameHistory[].provablyFair.serverSeed` is missing

**Root Cause**: Need to wait 1-2 ticks after rug event

**Solution**:
```python
def wait_for_seed(game_id: str, timeout: int = 60):
    """Wait for server seed to appear in gameHistory."""
    start = time.time()
    while time.time() - start < timeout:
        # Check latest gameStateUpdate
        if game_id in gameHistory and 'serverSeed' in gameHistory[game_id]:
            return gameHistory[game_id]['serverSeed']
        time.sleep(0.3)  # Wait ~1 tick
    raise TimeoutError(f"Server seed not revealed for {game_id}")
```

### Price Mismatch After Replay

**Problem**: Simulated prices don't match observed prices

**Potential Causes**:
1. Using wrong `Math.seedrandom` library (need exact same version)
2. Floating point precision differences (JavaScript vs Python)
3. Server using different PRNG parameters (unlikely)
4. God candle triggered (check for 10x jump)

**Debugging**:
```python
def verify_game_replay(observed_prices, server_seed, game_id):
    """Compare observed vs simulated prices."""
    simulated = simulate_game(server_seed, game_id)

    for tick, (obs, sim) in enumerate(zip(observed_prices, simulated['prices'])):
        diff = abs(obs - sim)
        if diff > 1e-10:  # Floating point tolerance
            print(f"MISMATCH at tick {tick}: observed={obs}, simulated={sim}, diff={diff}")
            return False

    print("✅ Game replay VERIFIED")
    return True
```

---

## 11. Example Implementation (Python)

```python
import socketio
import json
import hashlib
from datetime import datetime

class RugsPRNGCollector:
    def __init__(self):
        self.sio = socketio.Client()
        self.current_game = {}
        self.completed_games = []

        # Register event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('gameStateUpdate', self.on_game_state_update)

    def on_connect(self):
        print(f"[{datetime.now()}] Connected to rugs.fun")

    def on_disconnect(self):
        print(f"[{datetime.now()}] Disconnected from rugs.fun")

    def on_game_state_update(self, data):
        game_id = data.get('gameId')

        # Track current game
        if not self.current_game or self.current_game.get('gameId') != game_id:
            print(f"\n[NEW GAME] {game_id}")
            print(f"  serverSeedHash: {data['provablyFair']['serverSeedHash']}")
            self.current_game = {
                'gameId': game_id,
                'serverSeedHash': data['provablyFair']['serverSeedHash'],
                'prices': [],
                'ticks': []
            }

        # Record price
        tick = data.get('tickCount', 0)
        price = data.get('price', 1.0)
        self.current_game['prices'].append(price)
        self.current_game['ticks'].append(tick)

        # Check for rug
        if data.get('rugged') and not self.current_game.get('rugged'):
            print(f"[RUG EVENT] {game_id} at tick {tick}, price={price:.4f}")
            self.current_game['rugged'] = True
            self.current_game['rugTick'] = tick

        # Check for revealed seed in gameHistory
        if 'gameHistory' in data and len(data['gameHistory']) > 0:
            for hist_game in data['gameHistory']:
                hist_id = hist_game.get('id')
                pf = hist_game.get('provablyFair', {})

                if 'serverSeed' in pf:
                    # Found revealed seed
                    server_seed = pf['serverSeed']
                    server_seed_hash = pf['serverSeedHash']

                    # Verify hash
                    computed_hash = hashlib.sha256(server_seed.encode()).hexdigest()
                    hash_match = computed_hash == server_seed_hash

                    print(f"[SEED REVEALED] {hist_id}")
                    print(f"  serverSeed: {server_seed}")
                    print(f"  Hash verified: {hash_match}")

                    if not hash_match:
                        print(f"  ⚠️  HASH MISMATCH! Computed: {computed_hash}")

                    # Store completed game
                    self.completed_games.append({
                        'gameId': hist_id,
                        'serverSeed': server_seed,
                        'serverSeedHash': server_seed_hash,
                        'prices': hist_game.get('prices', []),
                        'peakMultiplier': hist_game.get('peakMultiplier'),
                        'rugTick': len(hist_game.get('prices', [])),
                        'verified': hash_match
                    })

                    # Save to disk
                    self.save_game(self.completed_games[-1])

    def save_game(self, game_data):
        """Persist game data to disk."""
        filename = f"data/verified_seeds/{game_data['gameId']}.json"
        with open(filename, 'w') as f:
            json.dump(game_data, f, indent=2)
        print(f"  💾 Saved to {filename}")

    def run(self):
        """Start collector."""
        print("Starting PRNG collector...")
        self.sio.connect('https://backend.rugs.fun?frontend-version=1.0')
        self.sio.wait()

if __name__ == '__main__':
    collector = RugsPRNGCollector()
    collector.run()
```

---

## 12. Related Documentation

| Document | Location |
|----------|----------|
| **Full WebSocket Spec** | `/home/devops/Desktop/VECTRA-BOILERPLATE/docs/rag/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md` |
| **CDP Connection Guide** | `/home/devops/Desktop/VECTRA-BOILERPLATE/docs/rag/knowledge/rugs-events/BROWSER_CONNECTION_PROTOCOL.md` |
| **Provably Fair Verification** | `/home/devops/Desktop/VECTRA-BOILERPLATE/docs/rag/knowledge/rugipedia/canon/PROVABLY_FAIR_VERIFICATION.md` |
| **Field Dictionary** | `/home/devops/Desktop/VECTRA-BOILERPLATE/docs/rag/knowledge/rugs-events/FIELD_DICTIONARY.md` |

---

## 13. Quick Start Checklist

For PRNG attack suite deployment:

- [ ] Use Socket.IO v4 client (not raw WebSocket)
- [ ] Connect to `wss://backend.rugs.fun?frontend-version=1.0`
- [ ] Listen for `gameStateUpdate` events (~4/sec)
- [ ] Extract `gameId`, `price`, `tickCount`, `provablyFair.serverSeedHash`
- [ ] Detect rug via `rugged: true` transition
- [ ] Wait 1-2 ticks for `gameHistory[0].provablyFair.serverSeed` to appear
- [ ] Verify SHA-256 hash: `sha256(serverSeed) == serverSeedHash`
- [ ] Replay game using `Math.seedrandom(serverSeed + '-' + gameId)`
- [ ] Compare observed vs simulated prices
- [ ] Store verified games in persistent volume
- [ ] Run statistical analysis on accumulated data

---

## 14. Statistical Attack Vectors

### What to Look For

1. **Seed Predictability**
   - Analyze server seed entropy
   - Check for patterns in seed generation
   - Test for time-based correlations

2. **Rug Distribution Anomalies**
   - Expected: Geometric(p=0.005)
   - Check for deviations from expected distribution
   - Test for clustering or periodicity

3. **Price Drift Bias**
   - Expected: Uniform drift in [-0.02, 0.03]
   - Check for directional bias
   - Test big move frequency (should be 12.5%)

4. **God Candle Frequency**
   - Expected: 0.001% per tick
   - Check actual frequency
   - Verify price <= 100x condition

5. **Replay Verification**
   - CRITICAL: Every game should replay exactly
   - Any mismatch = potential attack vector
   - Document all anomalies

---

**END OF GUIDE**

For questions about this protocol, consult the `@agent-rugs-expert` MCP server which has deep canonical knowledge of rugs.fun events.

*Last updated: February 4, 2026*
