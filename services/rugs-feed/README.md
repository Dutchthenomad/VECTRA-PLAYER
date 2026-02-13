# Rugs Feed Service

**Master WebSocket broadcaster** for rugs.fun data. Maintains persistent connection to the backend and broadcasts raw events to downstream subscribers.

## Purpose

This service acts as the **single source of truth** for rugs.fun WebSocket data:

1. **Persistent Connection** - Maintains 24/7 Socket.IO connection to `backend.rugs.fun`
2. **WebSocket Broadcaster** - Broadcasts all raw events to downstream services via `/feed`
3. **gameHistory Capture** - Stores complete game records with serverSeeds on rug events
4. **PRNG Data Export** - Provides serverSeeds and timestamps for PRNG attack suite

**Critical for PRNG Attack Suite:** Captures the server seeds revealed after each game, along with timestamps for time-based seed correlation attacks.

## Architecture

```
backend.rugs.fun (Socket.IO)
         │
         ▼
┌─────────────────────────────────────┐
│       rugs-feed (Port 9016)         │  ← Containerized, 24/7
│  ┌─────────────────────────────┐    │
│  │    RugsFeedClient           │    │  Direct Socket.IO
│  │    (persistent connection)  │    │
│  └──────────────┬──────────────┘    │
│                 │                    │
│      ┌──────────┴──────────┐        │
│      ▼                     ▼        │
│  ┌────────────┐    ┌─────────────┐  │
│  │ Broadcaster│    │EventStorage │  │
│  │  (/feed)   │    │  (SQLite)   │  │
│  └─────┬──────┘    └──────┬──────┘  │
│        │                  │         │
│        ▼                  ▼         │
│  ┌─────────────────────────────┐    │
│  │        FastAPI              │    │
│  │  /feed, /api/*, /health     │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
         │
    ws://rugs-feed:9016/feed
         │
    ┌────┴────┬────────────┬──────────┐
    ▼         ▼            ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  PRNG  │ │   ML   │ │Recording│ │ Other  │
│ Attack │ │ Train  │ │ Service │ │Subscriber│
│ Suite  │ │ Data   │ │         │ │        │
└────────┘ └────────┘ └────────┘ └────────┘
```

## Quick Start

### Docker (Recommended)

```bash
cd services/rugs-feed
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
curl http://localhost:9016/health
```

### Local Development

```bash
cd services/rugs-feed
pip install -r requirements.txt
STORAGE_PATH=./data/rugs_feed.db python -m src.main
```

## WebSocket Feed

Connect to `ws://localhost:9016/feed` to receive all raw events from rugs.fun.

### Event Format

```json
{
  "type": "raw_event",
  "event_type": "gameStateUpdate",
  "data": { /* raw rugs.fun event data */ },
  "timestamp": "2026-02-05T01:57:08.087887",
  "game_id": "20260205-abc123"
}
```

### Python Subscriber Example

```python
import asyncio
import json
import websockets

async def subscribe_to_feed():
    uri = "ws://localhost:9016/feed"

    async with websockets.connect(uri) as ws:
        print("Connected to rugs-feed")

        while True:
            msg = await ws.recv()
            event = json.loads(msg)

            event_type = event["event_type"]
            data = event["data"]

            if event_type == "gameStateUpdate":
                price = data.get("price", 0)
                tick = data.get("tickCount", 0)
                rugged = data.get("rugged", False)

                if rugged:
                    print(f"RUGGED at tick {tick}, price {price}")
                else:
                    print(f"Tick {tick}: {price:.4f}x")

asyncio.run(subscribe_to_feed())
```

### Keepalive

Send ping messages to keep the connection alive:

```python
await ws.send(json.dumps({"action": "ping", "ts": time.time()}))
# Receives: {"type": "pong", "ts": <your_ts>}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with stats |
| `/feed` | WebSocket | Live event stream for subscribers |
| `/api/games` | GET | Recent captured games |
| `/api/games/{game_id}` | GET | Single game with all events |
| `/api/seeds` | GET | Games with revealed server seeds |
| `/api/history` | GET | Complete game records from gameHistory |
| `/api/export` | GET | JSONL export for PRNG attack suite |
| `/api/stats` | GET | Service + broadcaster statistics |

### Example: Get Complete Game History

```bash
# Get recent game history with full data
curl "http://localhost:9016/api/history?limit=10"

# Get only games with server seeds
curl "http://localhost:9016/api/history?with_seed_only=true"
```

### Example: Export for PRNG Analysis

```bash
# Get recent seed reveals
curl http://localhost:9016/api/seeds?limit=100

# Export JSONL for SEED-KRACKER
curl http://localhost:9016/api/export > seeds.jsonl
```

### Example: Feed to Attack Suite

```python
import requests

# Get complete game history
response = requests.get("http://localhost:9016/api/history")
records = response.json()["records"]

for record in records:
    game_id = record["game_id"]
    server_seed = record["server_seed"]
    timestamp_ms = record["timestamp_ms"]
    peak_multiplier = record["peak_multiplier"]

    # Feed to adaptive cracker
    cracker.add_sample(game_id, server_seed, timestamp_ms)
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RUGS_BACKEND_URL` | `https://backend.rugs.fun` | Backend WebSocket URL |
| `PORT` | `9016` | API server port |
| `STORAGE_PATH` | `/data/rugs_feed.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `MAX_RECONNECT_ATTEMPTS` | `100` | Max reconnection attempts |
| `RECONNECT_DELAY` | `5` | Seconds between reconnects |

## Data Schema

### Complete Game Record (from gameHistory)

```json
{
  "game_id": "20260205-abc123",
  "timestamp_ms": 1770256532595,
  "peak_multiplier": 1.2267,
  "rugged": true,
  "server_seed": "5d999966749be4cb6f808bebc0e1b8cc36d11137ca089fbbb98fc11f33fe5238",
  "server_seed_hash": "e63b30871757510da46f7cd1d86c8efbec294a2f452318e0537e4a4b1cb8ab9c",
  "global_trades": [],
  "global_sidebets": [
    {
      "playerId": "did:privy:xxx",
      "username": "Player1",
      "betAmount": 0.036,
      "payout": 0.18,
      "profit": 0.144,
      "xPayout": 5,
      "type": "payout"
    }
  ],
  "game_version": "v3",
  "captured_at": "2026-02-05T01:57:08.087887"
}
```

### JSONL Export Format

Compatible with SEED-KRACKER and AdaptiveCracker:

```jsonl
{"game_id":"20260204-abc","timestamp_ms":1738627200000,"server_seed":"e9cdaf...","peak_multiplier":2.5}
{"game_id":"20260204-def","timestamp_ms":1738627300000,"server_seed":"f1b2c3...","peak_multiplier":1.8}
```

## Port

- **9016** - Allocated per PORT-ALLOCATION-SPEC.md

## Testing

```bash
# Run all tests (22 tests)
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Service Manifest

See `manifest.json` for service registration details including:
- Port allocation: 9016
- Health endpoint: `/health`
- WebSocket feed: `/feed`
- Events captured: `gameStateUpdate`, `standard/newTrade`, `currentSidebet`, `playerUpdate`

## Downstream Subscribers

Services that consume the `/feed`:

| Service | Purpose |
|---------|---------|
| PRNG Attack Suite | Seed correlation analysis |
| ML Training | Game data for model training |
| Recording Service | Game recording and replay |

To create a subscriber, see `examples/sample_subscriber.py`.
