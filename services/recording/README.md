# Recording Service

**Version:** 1.0.0 | **Port:** 9010 | **Status:** Production Ready

Captures game data via gameHistory extraction on RUG events. Stores complete games to Parquet files with automatic deduplication.

---

## Overview

The Recording Service subscribes to Foundation Service events and captures complete game data when games end (RUG events). Instead of buffering individual ticks (which risks data loss), it extracts the `gameHistory` array that the server maintains - providing:

- **Zero data loss**: Server maintains authoritative game history
- **Automatic backfill**: 10 most recent games available on each RUG
- **Built-in deduplication**: gameId-based tracking prevents duplicates
- **Compact storage**: Complete games only, no redundant tick data

---

## Quick Start

### Local Development (Recommended)

```bash
# Use the startup script (handles env vars, checks prerequisites)
./start.sh           # Foreground mode
./start.sh --daemon  # Background mode

# View logs (daemon mode)
tail -f /tmp/recording-service.log
```

### Manual Start

```bash
# Set environment variables
export STORAGE_PATH=~/rugs_recordings/raw_captures
export DEDUP_PATH=$(pwd)/config/seen_games.json
export FOUNDATION_WS_URL=ws://localhost:9000/feed

# Run service (CORRECT method)
python -m src.main

# ⚠️ DO NOT use uvicorn directly - it uses a placeholder subscriber:
# uvicorn src.main:app  <-- WRONG, won't connect to Foundation
```

### Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/recording/status` | Current recording status |
| POST | `/recording/start` | Start recording |
| POST | `/recording/stop` | Stop recording |
| GET | `/recording/stats` | Detailed statistics |
| GET | `/recording/recent?limit=10` | Recent captured games |

### Example Responses

**Health Check:**
```json
{
  "status": "healthy",
  "service": "recording-service",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "foundation_connected": true,
  "memory_mb": 98.5
}
```

**Recording Stats:**
```json
{
  "session": 12,
  "today": 47,
  "total": 3042,
  "deduped": 847,
  "storage": {
    "storage_path": "/home/user/rugs_recordings/raw_captures",
    "total_size_mb": 2.4,
    "file_count": 15,
    "parquet_available": true
  }
}
```

**Recent Games:**
```json
[
  {
    "game_id": "20260120-505db5427d6e4931",
    "ticks": 11811,
    "final_price": 5.68,
    "captured_at": "2026-01-20T04:05:02.191031+00:00"
  }
]
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FOUNDATION_WS_URL` | `ws://localhost:9000/feed` | Foundation WebSocket URL |
| `PORT` | `9010` | API server port |
| `HOST` | `0.0.0.0` | API server host |
| `STORAGE_PATH` | `~/rugs_recordings/raw_captures` | Game storage directory |
| `DEDUP_PATH` | `./config/seen_games.json` | Dedup state file |
| `AUTO_START_RECORDING` | `true` | Start recording on service startup |

### Config File

`config/config.yaml` provides defaults; environment variables override.

---

## Storage Format

Games are stored in Parquet files partitioned by date:

```
~/rugs_recordings/raw_captures/
├── games_2026-01-19.parquet
├── games_2026-01-20.parquet
└── ...
```

### gameHistory Field Mapping

| Server Field | Description |
|--------------|-------------|
| `id` | Game ID (format: `YYYYMMDD-<16char_hex>`) |
| `timestamp` | Unix timestamp (ms) when game ended |
| `prices` | Array of tick-by-tick prices (length = ticks) |
| `peakMultiplier` | Highest price reached |
| `rugged` | Always `true` for completed games |
| `provablyFair` | Cryptographic verification data |
| `globalSidebets` | Sidebet events during game |

---

## Architecture

```
Foundation Service (9000) ──WebSocket──▶ RecordingSubscriber
                                              │
                                              ▼
                                        DeduplicationTracker
                                              │
                                              ▼
                                         GameStorage
                                              │
                                              ▼
                                      Parquet Files (~/)
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `RecordingSubscriber` | `src/subscriber.py` | Event handling, gameHistory extraction |
| `DeduplicationTracker` | `src/dedup.py` | gameId tracking, LRU cache |
| `GameStorage` | `src/storage.py` | Parquet write, buffering |
| `API` | `src/api.py` | FastAPI endpoints |
| `Main` | `src/main.py` | Service entry point |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_subscriber.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Troubleshooting

### `foundation_connected: false`

**Cause:** Service started with `uvicorn src.main:app` instead of `python -m src.main`

**Fix:** Use `./start.sh` or `python -m src.main`

### Storage permission denied

**Cause:** Config uses Docker path `/data/raw_captures`

**Fix:** Set `STORAGE_PATH=~/rugs_recordings/raw_captures`

### "Game in history missing gameId"

**Cause:** Old code looking for `gameId` instead of `id`

**Fix:** Update to v1.0.0+ which uses `game.get("id")`

### No games being captured

1. Verify Foundation connection: `curl localhost:9010/health`
2. Check recording is enabled: `curl localhost:9010/recording/status`
3. Wait for a RUG event (games only captured on RUG)

---

## Module Compliance

This service follows **VECTRA-BOILERPLATE MODULE-EXTENSION-SPEC v1.0.0**:

- ✅ Located in `services/<name>/`
- ✅ Has `manifest.json` with required fields
- ✅ Has `Dockerfile` and `docker-compose.yml`
- ✅ Exposes `/health` endpoint
- ✅ Uses `BaseSubscriber` pattern (via `FoundationClient`)
- ✅ Unit tests in `tests/`

---

## License

Part of VECTRA-BOILERPLATE project.
