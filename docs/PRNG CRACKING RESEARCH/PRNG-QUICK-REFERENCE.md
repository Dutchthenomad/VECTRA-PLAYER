# PRNG Attack Suite - Quick Reference Card

## Connection

```bash
URL: wss://backend.rugs.fun?frontend-version=1.0
Protocol: Socket.IO v4 (NOT raw WebSocket)
Auth: None required (for read-only PRNG analysis)
Rate: ~4 events/sec during active games
```

## Critical Event: gameStateUpdate

**Contains everything you need:**

```javascript
{
  "gameId": "20251228-242b2d81e73e4f27",        // Seed component
  "price": 1.4444769765026393,                  // Current tick price
  "tickCount": 16,                              // Tick counter
  "rugged": false,                              // true = game ended
  "provablyFair": {
    "serverSeedHash": "bce19033...",            // Pre-reveal SHA-256 hash
    "version": "v3"
  },
  "gameHistory": [                              // Rolling window of ~10 games
    {
      "id": "20251228-previous-game",
      "prices": [1.0, 1.05, 1.12, ...],         // Full price series
      "peakMultiplier": 45.23,
      "provablyFair": {
        "serverSeed": "6500cdbe92a642aa...",    // REVEALED SEED (after rug)
        "serverSeedHash": "961079f9f7ebb139..."
      }
    }
  ]
}
```

## Server Seed Timeline

```
PRESALE/ACTIVE:  serverSeedHash visible, serverSeed HIDDEN
    ↓
RUG EVENT:       current game rugged, seed still hidden
    ↓
1-2 TICKS LATER: serverSeed appears in gameHistory[]
```

## PRNG Verification

```javascript
// 1. Combine seed
const combinedSeed = serverSeed + '-' + gameId;
const prng = new Math.seedrandom(combinedSeed);

// 2. Verify hash
const computedHash = sha256(serverSeed);
assert(computedHash === serverSeedHash);

// 3. Replay game
let price = 1.0;
for (let tick = 0; tick < 5000; tick++) {
    if (prng() < 0.005) {  // 0.5% rug probability
        break;  // Game rugged
    }
    price = driftPrice(price, prng);
}

// 4. Compare observed vs simulated prices
```

## Game Constants (v3)

```javascript
RUG_PROB = 0.005           // 0.5% per tick
DRIFT_MIN = -0.02          // -2%
DRIFT_MAX = 0.03           // +3%
BIG_MOVE_CHANCE = 0.125    // 12.5%
GOD_CANDLE_CHANCE = 0.00001 // 0.001% (if price <= 100x)
GOD_CANDLE_MOVE = 10.0     // 10x multiplier
```

## Minimal Python Collector

```python
import socketio
import hashlib

sio = socketio.Client()

@sio.on('gameStateUpdate')
def on_update(data):
    # Check for revealed seeds
    for game in data.get('gameHistory', []):
        pf = game.get('provablyFair', {})
        if 'serverSeed' in pf:
            seed = pf['serverSeed']
            hash_check = hashlib.sha256(seed.encode()).hexdigest()
            print(f"SEED: {game['id']}")
            print(f"  {seed}")
            print(f"  Hash OK: {hash_check == pf['serverSeedHash']}")

sio.connect('https://backend.rugs.fun?frontend-version=1.0')
sio.wait()
```

## Socket.IO Frame Parsing

```python
# Raw: 42["gameStateUpdate", {...}]
if payload.startswith('42'):
    event_name, data = json.loads(payload[2:])
```

## Key Timing

| Metric | Value |
|--------|-------|
| Expected game duration | ~50 seconds (200 ticks) |
| Median duration | ~35 seconds (138 ticks) |
| Tick rate | ~4/sec (250ms) |
| Max ticks | 5000 (auto-rug) |
| Cooldown between games | 10-30 seconds |

## Attack Vectors to Test

1. **Seed entropy analysis** - Check for weak RNG in serverSeed generation
2. **Rug distribution** - Should match Geometric(p=0.005)
3. **Price replay accuracy** - ANY mismatch is suspicious
4. **God candle frequency** - Should be ~0.001% per tick
5. **Directional bias** - Drift should be symmetric

## Full Documentation

See: `/home/devops/Desktop/VECTRA-BOILERPLATE/docs/PRNG-ATTACK-SUITE-CONNECTION-GUIDE.md`

---

*For comprehensive answers, use: `@agent-rugs-expert`*
