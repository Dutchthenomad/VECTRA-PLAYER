# Rugs Feed Service

Direct WebSocket capture service for rugs.fun events.

## Purpose

Captures raw Socket.IO events from rugs.fun backend for PRNG analysis:
- `gameStateUpdate` with `provablyFair.serverSeed` reveals
- `standard/newTrade` for timing correlation
- All sidebet events

## Usage

```bash
# Docker (recommended)
docker-compose up -d

# Local development
python -m src.main
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/games` | GET | Recent captured games |
| `/api/games/{game_id}` | GET | Single game with events |
| `/api/seeds` | GET | Seed reveals for PRNG analysis |
| `/api/export` | GET | JSONL export for attack suite |

## Port

- **9016** - API and health endpoint
