# Rugs Feed Service

Direct WebSocket capture service for rugs.fun PRNG analysis.

## Purpose

Captures raw Socket.IO events from rugs.fun backend including:
- `gameStateUpdate` with `provablyFair.serverSeed` reveals
- `standard/newTrade` for timing correlation
- Sidebet events for complete game history

**Critical for PRNG Attack Suite:** This service captures the server seeds revealed after each game, along with timestamps for time-based seed correlation attacks.

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
python -m src.main
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with stats |
| `/api/games` | GET | Recent captured games |
| `/api/games/{game_id}` | GET | Single game with all events |
| `/api/seeds` | GET | Games with revealed server seeds |
| `/api/export` | GET | JSONL export for PRNG attack suite |
| `/api/stats` | GET | Service statistics |

### Example: Get Seeds for PRNG Analysis

```bash
# Get recent seed reveals
curl http://localhost:9016/api/seeds?limit=100

# Export for SEED-KRACKER
curl http://localhost:9016/api/export > seeds.jsonl
```

### Example: Feed to Attack Suite

```python
import requests

# Get seeds
response = requests.get("http://localhost:9016/api/seeds")
seeds = response.json()["seeds"]

for seed in seeds:
    game_id = seed["game_id"]
    server_seed = seed["server_seed"]
    timestamp_ms = seed["timestamp_ms"]

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

### Captured Game

```json
{
  "game_id": "20260204-abc123",
  "timestamp_ms": 1738627200000,
  "server_seed": "e9cdaf558aada61213b2ef434ec4e811c3af7ccde29a2f66b50df0f07b2a0b6d",
  "server_seed_hash": "8cc2bab9e7fa24d16fce964233a25ac2d2372923b80435c36c6441053bdae2e0",
  "peak_multiplier": 2.5,
  "final_price": 0.015,
  "tick_count": 150,
  "rugged": true
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

## Architecture

```
rugs.fun backend (Socket.IO)
         │
         ▼
  ┌─────────────────┐
  │ RugsFeedClient  │  Direct WebSocket connection
  └────────┬────────┘
           │ CapturedEvent
           ▼
  ┌─────────────────┐
  │  EventStorage   │  SQLite persistence
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │   FastAPI       │  Query & Export API
  └─────────────────┘
           │
           ▼
  SEED-KRACKER / AdaptiveCracker
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Service Manifest

See `manifest.json` for service registration details including:
- Port allocation: 9016
- Health endpoint: `/health`
- Events emitted: `raw.game_state`, `raw.trade`, `raw.sidebet`, `raw.seed_reveal`
