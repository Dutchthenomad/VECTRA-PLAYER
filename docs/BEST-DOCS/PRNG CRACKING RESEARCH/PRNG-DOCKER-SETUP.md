# Containerized PRNG Attack Suite - Docker Setup

## Quick Start

```bash
# 1. Build image
docker build -t rugs-prng-suite -f Dockerfile.prng .

# 2. Run collector
docker-compose -f docker-compose.prng.yml up -d

# 3. Monitor logs
docker logs -f rugs-prng-collector

# 4. Check collected data
ls -lh data/verified_seeds/
```

## Dockerfile.prng

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    python-socketio[client]==5.10.0 \
    websocket-client \
    numpy \
    pandas \
    scipy

# Copy application code
COPY prng_collector/ /app/

# Create data directories
RUN mkdir -p /app/data/raw_events \
             /app/data/verified_seeds \
             /app/data/analysis

# Run collector
CMD ["python", "-u", "collector.py"]
```

## docker-compose.prng.yml

```yaml
version: '3.8'

services:
  prng-collector:
    image: rugs-prng-suite:latest
    container_name: rugs-prng-collector
    restart: unless-stopped

    volumes:
      # Persistent data storage
      - ./data/raw_events:/app/data/raw_events
      - ./data/verified_seeds:/app/data/verified_seeds
      - ./data/analysis:/app/data/analysis

      # Optional: mount config
      - ./config/prng.env:/app/.env

    environment:
      # Connection
      - RUGS_WS_URL=https://backend.rugs.fun?frontend-version=1.0
      - SOCKET_IO_VERSION=v4

      # Logging
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - LOG_FILE=/app/data/collector.log

      # Features
      - VERIFY_HASHES=true
      - REPLAY_GAMES=true
      - SAVE_RAW_EVENTS=false

      # Analysis
      - AUTO_ANALYZE=true
      - ANALYSIS_INTERVAL=3600  # Run every hour

    networks:
      - prng-net

    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  prng-analyzer:
    image: rugs-prng-suite:latest
    container_name: rugs-prng-analyzer
    restart: unless-stopped

    volumes:
      - ./data/verified_seeds:/app/data/verified_seeds:ro
      - ./data/analysis:/app/data/analysis

    environment:
      - LOG_LEVEL=INFO
      - ANALYSIS_MODE=batch

    command: ["python", "-u", "analyzer.py"]

    networks:
      - prng-net

    depends_on:
      - prng-collector

networks:
  prng-net:
    driver: bridge
```

## Directory Structure

```
prng-attack-suite/
├── Dockerfile.prng
├── docker-compose.prng.yml
├── config/
│   └── prng.env                    # Optional config overrides
├── prng_collector/
│   ├── collector.py                # Main WebSocket collector
│   ├── analyzer.py                 # Statistical analysis
│   ├── healthcheck.py              # Docker health check
│   ├── prng_verifier.py            # Game replay engine
│   └── requirements.txt
└── data/                           # Persistent volume mount
    ├── raw_events/                 # Optional: raw gameStateUpdate JSONs
    ├── verified_seeds/             # Verified games: {gameId}.json
    │   ├── 20251228-xxx.json
    │   └── 20251228-yyy.json
    └── analysis/                   # Statistical outputs
        ├── rug_distribution.json
        ├── seed_entropy.json
        └── anomalies.json
```

## prng_collector/collector.py (Minimal Example)

```python
#!/usr/bin/env python3
"""
Minimal PRNG data collector for rugs.fun.
Captures gameStateUpdate events and extracts revealed server seeds.
"""

import os
import json
import hashlib
import socketio
from datetime import datetime
from pathlib import Path

# Config from environment
WS_URL = os.getenv('RUGS_WS_URL', 'https://backend.rugs.fun?frontend-version=1.0')
DATA_DIR = Path('/app/data/verified_seeds')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Socket.IO client
sio = socketio.Client(logger=(LOG_LEVEL == 'DEBUG'))


@sio.on('connect')
def on_connect():
    print(f"[{datetime.now()}] ✅ Connected to {WS_URL}")


@sio.on('disconnect')
def on_disconnect():
    print(f"[{datetime.now()}] ❌ Disconnected from rugs.fun")


@sio.on('gameStateUpdate')
def on_game_state_update(data):
    """Process gameStateUpdate events and extract revealed seeds."""

    # Check for revealed seeds in gameHistory
    game_history = data.get('gameHistory', [])

    for game in game_history:
        game_id = game.get('id')
        provably_fair = game.get('provablyFair', {})

        # Check if we have a revealed server seed
        if 'serverSeed' not in provably_fair:
            continue

        # Extract data
        server_seed = provably_fair['serverSeed']
        server_seed_hash = provably_fair['serverSeedHash']
        prices = game.get('prices', [])
        peak = game.get('peakMultiplier')

        # Skip if already saved
        output_file = DATA_DIR / f"{game_id}.json"
        if output_file.exists():
            continue

        # Verify hash
        computed_hash = hashlib.sha256(server_seed.encode()).hexdigest()
        hash_verified = (computed_hash == server_seed_hash)

        if not hash_verified:
            print(f"[{datetime.now()}] ⚠️  HASH MISMATCH for {game_id}!")
            print(f"  Expected: {server_seed_hash}")
            print(f"  Computed: {computed_hash}")

        # Save verified game
        game_data = {
            'gameId': game_id,
            'serverSeed': server_seed,
            'serverSeedHash': server_seed_hash,
            'prices': prices,
            'peakMultiplier': peak,
            'rugTick': len(prices),
            'hashVerified': hash_verified,
            'capturedAt': datetime.now().isoformat(),
            'version': provably_fair.get('version', 'v3')
        }

        # Write to disk
        with output_file.open('w') as f:
            json.dump(game_data, f, indent=2)

        status = "✅" if hash_verified else "❌"
        print(f"[{datetime.now()}] {status} Saved {game_id}")
        print(f"  Rug at tick {len(prices)}, peak {peak:.2f}x")
        print(f"  File: {output_file}")


def main():
    """Main entry point."""
    print(f"Starting PRNG collector...")
    print(f"  WS URL: {WS_URL}")
    print(f"  Data dir: {DATA_DIR}")
    print(f"  Log level: {LOG_LEVEL}")

    try:
        sio.connect(WS_URL)
        sio.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sio.disconnect()
    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == '__main__':
    main()
```

## prng_collector/healthcheck.py

```python
#!/usr/bin/env python3
"""Docker healthcheck script."""

import sys
import socketio

try:
    # Quick connection test
    sio = socketio.Client()
    sio.connect('https://backend.rugs.fun?frontend-version=1.0', wait_timeout=5)
    sio.disconnect()
    print("OK")
    sys.exit(0)
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
```

## prng_collector/requirements.txt

```
python-socketio[client]==5.10.0
websocket-client==1.7.0
numpy==1.26.3
pandas==2.1.4
scipy==1.11.4
```

## Usage

### 1. Build and Start

```bash
# Build image
docker build -t rugs-prng-suite -f Dockerfile.prng .

# Start services
docker-compose -f docker-compose.prng.yml up -d

# Check status
docker-compose -f docker-compose.prng.yml ps
```

### 2. Monitor Collection

```bash
# Follow logs
docker logs -f rugs-prng-collector

# Check collected games
ls -lh data/verified_seeds/
wc -l data/verified_seeds/*.json

# View specific game
cat data/verified_seeds/20251228-xxx.json | jq .
```

### 3. Run Analysis

```bash
# Manual analysis run
docker exec rugs-prng-analyzer python analyzer.py

# View analysis results
cat data/analysis/rug_distribution.json | jq .
```

### 4. Stop and Cleanup

```bash
# Stop containers
docker-compose -f docker-compose.prng.yml down

# Cleanup (keeps data directory)
docker-compose -f docker-compose.prng.yml down --volumes

# Remove everything including data
rm -rf data/
```

## Data Volume Management

### Backup

```bash
# Backup verified seeds
tar -czf verified_seeds_backup_$(date +%Y%m%d).tar.gz data/verified_seeds/

# Copy to remote server
scp verified_seeds_backup_*.tar.gz user@backup-server:/backups/
```

### Restore

```bash
# Extract backup
tar -xzf verified_seeds_backup_20251228.tar.gz

# Restart collector
docker-compose -f docker-compose.prng.yml restart prng-collector
```

## Monitoring & Alerts

### Prometheus Metrics (Optional)

Add to `collector.py`:

```python
from prometheus_client import start_http_server, Counter, Gauge

# Metrics
games_collected = Counter('rugs_games_collected_total', 'Total games collected')
hash_failures = Counter('rugs_hash_failures_total', 'Hash verification failures')
current_tick = Gauge('rugs_current_tick', 'Current game tick')

# Expose metrics on :8000
start_http_server(8000)
```

Add to `docker-compose.prng.yml`:

```yaml
services:
  prng-collector:
    ports:
      - "8000:8000"  # Prometheus metrics
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs rugs-prng-collector

# Verify network connectivity
docker exec rugs-prng-collector ping -c 3 backend.rugs.fun

# Check Socket.IO connection manually
docker exec -it rugs-prng-collector python
>>> import socketio
>>> sio = socketio.Client()
>>> sio.connect('https://backend.rugs.fun?frontend-version=1.0')
```

### No Seeds Being Collected

**Possible causes:**
1. Need to wait for game to rug (avg 50 seconds)
2. Server seed appears 1-2 ticks after rug event
3. gameHistory might be empty initially (wait for first game)

**Debug:**
```bash
# Enable debug logging
docker-compose -f docker-compose.prng.yml up -d \
  -e LOG_LEVEL=DEBUG
```

### Hash Verification Failures

**If hashes don't match:**
1. Check encoding (UTF-8)
2. Verify SHA-256 implementation
3. Check for extra whitespace in serverSeed

```python
# Test hash manually
import hashlib
seed = "6500cdbe92a642aac84b178756ceea75665fd5f82ced512ecadb30fefed15755"
hash_hex = hashlib.sha256(seed.encode('utf-8')).hexdigest()
print(hash_hex)
```

## Advanced Configuration

### Rate Limiting

Add connection throttling:

```python
import time

# Reconnect with backoff
retry_delay = 1
while True:
    try:
        sio.connect(WS_URL)
        sio.wait()
    except Exception as e:
        print(f"Connection failed: {e}")
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s
```

### Multi-Container Deployment

Run multiple collectors for redundancy:

```yaml
services:
  prng-collector-1:
    image: rugs-prng-suite:latest
    volumes:
      - ./data/verified_seeds:/app/data/verified_seeds

  prng-collector-2:
    image: rugs-prng-suite:latest
    volumes:
      - ./data/verified_seeds:/app/data/verified_seeds
```

Note: Use file locking to prevent duplicate writes.

---

**Next Steps:**
1. Implement `analyzer.py` for statistical analysis
2. Add `prng_verifier.py` for game replay
3. Set up automated anomaly detection
4. Configure alerting for hash failures

See: `PRNG-ATTACK-SUITE-CONNECTION-GUIDE.md` for full protocol details.
