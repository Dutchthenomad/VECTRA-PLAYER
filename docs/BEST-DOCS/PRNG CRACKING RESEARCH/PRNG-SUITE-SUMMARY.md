# PRNG Attack Suite - Documentation Summary

**Created**: February 4, 2026
**Target**: rugs.fun provably fair verification and PRNG analysis

---

## Documents Created

| Document | Purpose | Priority |
|----------|---------|:--------:|
| **PRNG-ATTACK-SUITE-CONNECTION-GUIDE.md** | Complete protocol reference (14 sections) | P0 |
| **PRNG-QUICK-REFERENCE.md** | One-page cheat sheet | P0 |
| **PRNG-DOCKER-SETUP.md** | Containerized deployment guide | P1 |
| This summary | Navigation guide | - |

---

## Quick Navigation

### I Need To: Connection Basics

**"What's the WebSocket URL?"**
- URL: `wss://backend.rugs.fun?frontend-version=1.0`
- Protocol: Socket.IO v4 (NOT raw WebSocket)
- See: Quick Reference, Section "Connection"

**"How do I parse Socket.IO frames?"**
- Strip `42` prefix, parse JSON array `[event_name, data]`
- See: Connection Guide, Section 1 "WebSocket Connection Details"

**"Do I need authentication?"**
- No, for read-only PRNG analysis
- Yes, only if you want to place trades
- See: Connection Guide, Section 7 "Authentication"

### I Need To: Get Server Seeds

**"Where are server seeds revealed?"**
- In `gameStateUpdate.gameHistory[].provablyFair.serverSeed`
- Appears 1-2 ticks AFTER rug event
- See: Connection Guide, Section 3 "Server Seed Revelation Timeline"

**"When exactly do seeds appear?"**
```
ACTIVE GAME → RUG EVENT → 1-2 TICKS → SEED IN gameHistory[]
```
- See: Connection Guide, Section 3, diagram

**"How do I verify the hash?"**
```python
import hashlib
computed = hashlib.sha256(serverSeed.encode()).hexdigest()
assert computed == serverSeedHash
```
- See: Connection Guide, Section 11 "Example Implementation"

### I Need To: Replay Games

**"What's the PRNG algorithm?"**
```javascript
const combinedSeed = serverSeed + '-' + gameId;
const prng = new Math.seedrandom(combinedSeed);
```
- See: Connection Guide, Section 4 "PRNG Algorithm (v3)"

**"What are the game constants?"**
- RUG_PROB = 0.005 (0.5% per tick)
- DRIFT_MIN = -0.02, DRIFT_MAX = 0.03
- GOD_CANDLE_CHANCE = 0.00001
- See: Quick Reference, Section "Game Constants"

**"Why don't my replays match?"**
1. Wrong Math.seedrandom version
2. Floating point precision differences
3. God candle event (check for 10x jump)
- See: Connection Guide, Section 10 "Troubleshooting"

### I Need To: Deploy Containers

**"How do I run this in Docker?"**
```bash
docker build -t rugs-prng-suite -f Dockerfile.prng .
docker-compose -f docker-compose.prng.yml up -d
```
- See: Docker Setup, Section "Quick Start"

**"What data should I persist?"**
- `/app/data/verified_seeds/` - Verified game JSONs
- `/app/data/analysis/` - Statistical outputs
- See: Docker Setup, Section "Directory Structure"

**"How do I monitor the collector?"**
```bash
docker logs -f rugs-prng-collector
ls -lh data/verified_seeds/
```
- See: Docker Setup, Section 2 "Monitor Collection"

### I Need To: Analyze Data

**"What should I test for?"**
1. Seed entropy analysis
2. Rug distribution (should be Geometric(p=0.005))
3. Price replay accuracy (100% match expected)
4. God candle frequency (0.001%)
5. Directional price bias
- See: Connection Guide, Section 14 "Statistical Attack Vectors"

**"What events contain full game data?"**
- `gameStateUpdate` - Contains everything
- Specifically `gameHistory[].prices[]` - Full price series
- See: Connection Guide, Section 2 "Core Events"

**"How many games are in gameHistory?"**
- Rolling window of ~10 completed games
- Updates every tick
- See: Connection Guide, Section 6 "Data Availability Windows"

---

## Critical Insights

### Timing & Lifecycle

| Phase | Duration | serverSeed Status |
|-------|----------|-------------------|
| PRESALE | ~10-30 sec | Hash visible, seed hidden |
| ACTIVE | ~50 sec (avg) | Hash visible, seed hidden |
| RUG EVENT | Instant | Hash visible, seed hidden |
| 1-2 TICKS LATER | ~250-500ms | Seed REVEALED in gameHistory |

**Expected game duration:** ~50 seconds (200 ticks @ 0.5% rug probability)

### Data Flow

```
gameStateUpdate (~4/sec)
    ├─ Current game: gameId, price, tick, serverSeedHash
    └─ gameHistory[]: Completed games with REVEALED seeds
         └─ prices[]: Full tick-by-tick price series
```

### Hash Verification Chain

```
1. Extract serverSeed from gameHistory[0].provablyFair.serverSeed
2. Compute SHA-256: hash = sha256(serverSeed)
3. Compare with serverSeedHash from provablyFair.serverSeedHash
4. If match: ✅ Seed is valid, proceed to replay
5. If mismatch: 🚨 CRITICAL ANOMALY - document immediately
```

---

## Code Examples

### Minimal Collector (10 lines)

```python
import socketio, hashlib

sio = socketio.Client()

@sio.on('gameStateUpdate')
def on_update(data):
    for game in data.get('gameHistory', []):
        if 'serverSeed' in game.get('provablyFair', {}):
            seed = game['provablyFair']['serverSeed']
            print(f"{game['id']}: {seed}")

sio.connect('https://backend.rugs.fun?frontend-version=1.0')
sio.wait()
```

### Game Replay (Pseudocode)

```python
def replay_game(server_seed, game_id):
    combined = f"{server_seed}-{game_id}"
    prng = Math.seedrandom(combined)  # Need JS library

    price = 1.0
    prices = [price]

    for tick in range(5000):
        if prng() < 0.005:  # Rug check
            break
        price = drift_price(price, prng)
        prices.append(price)

    return prices
```

---

## File Locations

All documentation in: `/home/devops/Desktop/VECTRA-BOILERPLATE/docs/`

### Reference Docs (Read These)

- `PRNG-ATTACK-SUITE-CONNECTION-GUIDE.md` - Main reference (14 sections)
- `PRNG-QUICK-REFERENCE.md` - Cheat sheet (1 page)
- `PRNG-DOCKER-SETUP.md` - Deployment guide

### Canonical Sources (Original Data)

- `docs/rag/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md` - Full event spec v3.0
- `docs/rag/knowledge/rugipedia/canon/PROVABLY_FAIR_VERIFICATION.md` - PRNG algorithm
- `docs/rag/knowledge/rugs-events/BROWSER_CONNECTION_PROTOCOL.md` - CDP connection (if auth needed)
- `docs/rag/knowledge/rugs-events/FIELD_DICTIONARY.md` - Field definitions

---

## Deployment Checklist

For containerized PRNG attack suite:

### Phase 1: Basic Connection (Day 1)
- [ ] Set up Docker environment
- [ ] Build minimal collector image
- [ ] Connect to WebSocket successfully
- [ ] Receive gameStateUpdate events
- [ ] Log raw events to verify connection

### Phase 2: Seed Collection (Day 2-3)
- [ ] Parse gameStateUpdate properly
- [ ] Extract serverSeedHash from active games
- [ ] Detect rug events (rugged: true)
- [ ] Wait for gameHistory[] to populate
- [ ] Extract revealed serverSeed
- [ ] Verify SHA-256 hash matches
- [ ] Save verified games to persistent volume

### Phase 3: Game Replay (Week 1)
- [ ] Implement Math.seedrandom in Python/container language
- [ ] Implement drift_price() function
- [ ] Replay games with revealed seeds
- [ ] Compare observed vs simulated prices
- [ ] Calculate replay accuracy (should be 100%)
- [ ] Log any mismatches as anomalies

### Phase 4: Statistical Analysis (Week 2)
- [ ] Collect 100+ verified games
- [ ] Analyze rug tick distribution
- [ ] Test for Geometric(p=0.005) fit
- [ ] Analyze price drift distribution
- [ ] Check big move frequency (~12.5%)
- [ ] Verify god candle frequency (~0.001%)
- [ ] Test for directional bias
- [ ] Analyze server seed entropy

### Phase 5: Attack Detection (Ongoing)
- [ ] Set up anomaly alerts
- [ ] Monitor for hash verification failures
- [ ] Monitor for replay mismatches
- [ ] Track statistical deviations
- [ ] Document any suspicious patterns

---

## Success Metrics

### Data Collection

- **Target**: 1000 verified games in 30 days
- **Rate**: ~33 games/day @ 50 sec/game = ~30 min active gameplay/day
- **Storage**: ~1 MB per 100 games (at 200 ticks avg)

### Verification Quality

- **Hash verification**: 100% success rate expected
- **Replay accuracy**: 100% price match expected (within float precision)
- **Data completeness**: 100% of games should have prices[] array

### Statistical Confidence

- **Minimum sample**: 100 games for basic distribution tests
- **Good sample**: 1000 games for rare event analysis (god candles)
- **Excellent sample**: 10,000+ games for high-confidence statistical tests

---

## Support & Questions

**Protocol Questions:**
- Use `@agent-rugs-expert` MCP server (has canonical knowledge)
- Reference: Connection Guide sections 1-6

**Docker Questions:**
- Reference: Docker Setup guide
- Check logs: `docker logs -f rugs-prng-collector`

**Statistical Analysis:**
- Reference: Connection Guide section 14 "Statistical Attack Vectors"
- Reference: PROVABLY_FAIR_VERIFICATION.md for algorithm details

**PRNG Implementation:**
- Reference: Connection Guide section 4 "PRNG Algorithm (v3)"
- Need exact Math.seedrandom library (JavaScript)

---

## Next Steps

1. **Read**: PRNG-QUICK-REFERENCE.md (5 minutes)
2. **Study**: PRNG-ATTACK-SUITE-CONNECTION-GUIDE.md sections 1-4 (30 minutes)
3. **Deploy**: Follow PRNG-DOCKER-SETUP.md (1 hour)
4. **Collect**: Let collector run for 24 hours
5. **Verify**: Check hash verification success rate
6. **Analyze**: Run statistical tests on collected data

---

**Created by**: rugs-expert agent
**Based on**: Canonical WebSocket Events Spec v3.0
**Target System**: rugs.fun provably fair gambling platform
**Purpose**: PRNG verification, statistical analysis, potential attack detection

---

*For comprehensive protocol knowledge, see the canonical spec at:*
`/home/devops/Desktop/VECTRA-BOILERPLATE/docs/rag/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md`
