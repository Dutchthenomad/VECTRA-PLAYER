# Rugs Feed Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a containerized, persistent, lightweight WebSocket connection to rugs.fun that captures all events for PRNG attack analysis.

**Architecture:** Direct Socket.IO connection to `https://backend.rugs.fun` (bypassing Foundation) captures raw events including `provablyFair.serverSeed` reveals. Events stored in SQLite with JSONL export for attack suite consumption. Service runs 24/7 in Docker container.

**Tech Stack:** Python 3.12, python-socketio, aiohttp, SQLite, FastAPI, Docker

---

## Prerequisites

Before starting, update port allocation:

**File:** `docs/specs/PORT-ALLOCATION-SPEC.md`

Add to Port Registry table:
```markdown
| **9016** | Rugs Feed Service | HTTP | Raw WebSocket capture API | `services/rugs-feed/` |
```

---

## Task 1: Create Service Directory Structure

**Files:**
- Create: `services/rugs-feed/manifest.json`
- Create: `services/rugs-feed/requirements.txt`
- Create: `services/rugs-feed/README.md`

**Step 1: Create manifest.json**

```json
{
  "name": "rugs-feed",
  "version": "1.0.0",
  "description": "Direct WebSocket capture service for rugs.fun events",
  "port": 9016,
  "health_endpoint": "/health",
  "start_command": "python -m src.main",
  "working_dir": "services/rugs-feed",
  "requires_foundation": false,
  "events_consumed": [],
  "events_emitted": ["raw.game_state", "raw.trade", "raw.sidebet", "raw.seed_reveal"],
  "dependencies": [],
  "author": "VECTRA Team",
  "created": "2026-02-04",
  "docker": {
    "image": "vectra-rugs-feed",
    "compose_file": "docker-compose.yml"
  },
  "storage": {
    "type": "sqlite",
    "path": "/data/rugs_feed.db"
  }
}
```

**Step 2: Create requirements.txt**

```
# WebSocket Client
python-socketio[asyncio_client]>=5.11.0
aiohttp>=3.9.0
websocket-client>=1.7.0

# API Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Data Storage
aiosqlite>=0.20.0

# Configuration
pyyaml>=6.0
python-dotenv>=1.0.0

# Utilities
pytz>=2024.1
```

**Step 3: Create README.md**

```markdown
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
```

**Step 4: Commit**

```bash
git add services/rugs-feed/manifest.json services/rugs-feed/requirements.txt services/rugs-feed/README.md
git commit -m "feat(rugs-feed): initialize service structure with manifest"
```

---

## Task 2: Create Socket.IO Client

**Files:**
- Create: `services/rugs-feed/src/__init__.py`
- Create: `services/rugs-feed/src/client.py`

**Step 1: Create empty __init__.py**

```python
"""Rugs Feed Service - Direct WebSocket capture."""
```

**Step 2: Write the failing test**

Create: `services/rugs-feed/tests/test_client.py`

```python
"""Tests for RugsFeedClient."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, "services/rugs-feed")

from src.client import RugsFeedClient, ConnectionState


class TestRugsFeedClient:
    """Test RugsFeedClient initialization and state."""

    def test_initial_state_is_disconnected(self):
        """Client should start in DISCONNECTED state."""
        client = RugsFeedClient()
        assert client.state == ConnectionState.DISCONNECTED

    def test_url_default(self):
        """Client should use correct default URL."""
        client = RugsFeedClient()
        assert "backend.rugs.fun" in client.url

    def test_url_custom(self):
        """Client should accept custom URL."""
        client = RugsFeedClient(url="wss://custom.example.com")
        assert client.url == "wss://custom.example.com"

    def test_event_handlers_registered(self):
        """Client should have handlers for key events."""
        client = RugsFeedClient()
        assert client._handlers is not None
        assert "gameStateUpdate" in client._handlers
        assert "standard/newTrade" in client._handlers
```

**Step 3: Run test to verify it fails**

Run: `cd services/rugs-feed && python -m pytest tests/test_client.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.client'"

**Step 4: Write minimal implementation**

Create: `services/rugs-feed/src/client.py`

```python
"""
RugsFeedClient - Direct Socket.IO connection to rugs.fun backend.

Captures raw events including:
- gameStateUpdate with provablyFair.serverSeed
- standard/newTrade for timing analysis
- Sidebet events
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import socketio

logger = logging.getLogger(__name__)

RUGS_BACKEND_URL = "https://backend.rugs.fun"


class ConnectionState(Enum):
    """WebSocket connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class CapturedEvent:
    """A captured WebSocket event."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    game_id: Optional[str] = None
    raw_message: Optional[str] = None


class RugsFeedClient:
    """
    Direct Socket.IO client for rugs.fun backend.

    Captures all game events for PRNG analysis, including:
    - Server seed reveals (provablyFair)
    - Game state updates with timestamps
    - Trade events for timing correlation
    """

    def __init__(
        self,
        url: str = RUGS_BACKEND_URL,
        on_event: Optional[Callable[[CapturedEvent], None]] = None,
    ):
        """
        Initialize client.

        Args:
            url: Backend URL (default: https://backend.rugs.fun)
            on_event: Callback for captured events
        """
        self._url = url
        self._on_event = on_event
        self._state = ConnectionState.DISCONNECTED
        self._sio: Optional[socketio.AsyncClient] = None
        self._handlers: Dict[str, Callable] = {}
        self._current_game_id: Optional[str] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

        # Register default handlers
        self._register_handlers()

    @property
    def url(self) -> str:
        """Get backend URL."""
        return self._url

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == ConnectionState.CONNECTED

    def _register_handlers(self) -> None:
        """Register Socket.IO event handlers."""
        self._handlers = {
            "gameStateUpdate": self._handle_game_state,
            "standard/newTrade": self._handle_trade,
            "currentSidebet": self._handle_sidebet,
            "currentSidebetResult": self._handle_sidebet_result,
            "usernameStatus": self._handle_identity,
            "playerUpdate": self._handle_player_update,
        }

    async def connect(self) -> None:
        """
        Connect to rugs.fun backend.

        Maintains connection with automatic reconnection.
        """
        self._state = ConnectionState.CONNECTING

        # Create Socket.IO client
        self._sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=self._max_reconnect_attempts,
            reconnection_delay=1,
            reconnection_delay_max=30,
            logger=False,
        )

        # Register connection handlers
        @self._sio.event
        async def connect():
            self._state = ConnectionState.CONNECTED
            self._reconnect_attempts = 0
            logger.info(f"Connected to {self._url}")

        @self._sio.event
        async def disconnect():
            self._state = ConnectionState.DISCONNECTED
            logger.warning("Disconnected from backend")

        @self._sio.event
        async def connect_error(data):
            self._reconnect_attempts += 1
            logger.error(f"Connection error (attempt {self._reconnect_attempts}): {data}")

        # Register event handlers
        for event_name, handler in self._handlers.items():
            self._sio.on(event_name, handler)

        # Connect with query params
        try:
            await self._sio.connect(
                self._url,
                transports=["websocket", "polling"],
                headers={"Origin": "https://rugs.fun"},
            )
        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            logger.error(f"Failed to connect: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from backend."""
        if self._sio:
            await self._sio.disconnect()
        self._state = ConnectionState.DISCONNECTED

    async def wait(self) -> None:
        """Wait for connection to close."""
        if self._sio:
            await self._sio.wait()

    def _emit_event(self, event: CapturedEvent) -> None:
        """Emit captured event to callback."""
        if self._on_event:
            try:
                self._on_event(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    async def _handle_game_state(self, *args) -> None:
        """Handle gameStateUpdate event."""
        # Socket.IO can pass trace object + data
        data = args[-1] if args else {}

        game_id = data.get("gameId")
        self._current_game_id = game_id

        # Extract seed reveal (only present after rug)
        provably_fair = data.get("provablyFair", {})
        server_seed = provably_fair.get("serverSeed")

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data=data,
            game_id=game_id,
        )

        # Log seed reveals (critical for PRNG analysis)
        if server_seed and data.get("rugged"):
            logger.info(f"SEED REVEAL: game={game_id} seed={server_seed[:16]}...")

        self._emit_event(event)

    async def _handle_trade(self, *args) -> None:
        """Handle standard/newTrade event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="standard/newTrade",
            data=data,
            game_id=data.get("gameId"),
        )
        self._emit_event(event)

    async def _handle_sidebet(self, *args) -> None:
        """Handle currentSidebet event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="currentSidebet",
            data=data,
            game_id=data.get("gameId"),
        )
        self._emit_event(event)

    async def _handle_sidebet_result(self, *args) -> None:
        """Handle currentSidebetResult event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="currentSidebetResult",
            data=data,
            game_id=data.get("gameId"),
        )
        self._emit_event(event)

    async def _handle_identity(self, *args) -> None:
        """Handle usernameStatus event (auth confirmation)."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="usernameStatus",
            data=data,
        )
        logger.info(f"Identity confirmed: {data.get('username', 'unknown')}")
        self._emit_event(event)

    async def _handle_player_update(self, *args) -> None:
        """Handle playerUpdate event."""
        data = args[-1] if args else {}

        event = CapturedEvent(
            event_type="playerUpdate",
            data=data,
        )
        self._emit_event(event)
```

**Step 5: Run test to verify it passes**

Run: `cd services/rugs-feed && python -m pytest tests/test_client.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add services/rugs-feed/src/__init__.py services/rugs-feed/src/client.py services/rugs-feed/tests/test_client.py
git commit -m "feat(rugs-feed): implement RugsFeedClient with Socket.IO connection"
```

---

## Task 3: Create SQLite Storage Layer

**Files:**
- Create: `services/rugs-feed/src/storage.py`
- Create: `services/rugs-feed/tests/test_storage.py`

**Step 1: Write the failing test**

```python
"""Tests for EventStorage."""
import pytest
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, "services/rugs-feed")

from src.storage import EventStorage
from src.client import CapturedEvent


class TestEventStorage:
    """Test EventStorage SQLite layer."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, temp_db):
        """Storage should create tables on init."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        # Should have games and events tables
        games = await storage.get_recent_games(limit=10)
        assert games == []

    @pytest.mark.asyncio
    async def test_store_game_state_event(self, temp_db):
        """Should store gameStateUpdate events."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-test123",
                "price": 1.5,
                "tickCount": 10,
                "rugged": False,
                "provablyFair": {"serverSeedHash": "abc123"},
            },
            game_id="20260204-test123",
        )

        await storage.store_event(event)
        games = await storage.get_recent_games(limit=10)
        assert len(games) == 1
        assert games[0]["game_id"] == "20260204-test123"

    @pytest.mark.asyncio
    async def test_store_seed_reveal(self, temp_db):
        """Should capture server seed reveals."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-test456",
                "rugged": True,
                "provablyFair": {
                    "serverSeed": "e9cdaf558aada61213b2ef434ec4e811",
                    "serverSeedHash": "8cc2bab9e7fa24d16fce964233a25ac2",
                },
            },
            game_id="20260204-test456",
        )

        await storage.store_event(event)
        seeds = await storage.get_seed_reveals(limit=10)
        assert len(seeds) == 1
        assert seeds[0]["server_seed"] == "e9cdaf558aada61213b2ef434ec4e811"

    @pytest.mark.asyncio
    async def test_export_for_prng(self, temp_db):
        """Should export data in PRNG attack format."""
        storage = EventStorage(temp_db)
        await storage.initialize()

        # Store a complete game with seed
        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-prng1",
                "rugged": True,
                "price": 2.5,
                "tickCount": 150,
                "provablyFair": {
                    "serverSeed": "abc123def456",
                },
            },
            game_id="20260204-prng1",
            timestamp=datetime(2026, 2, 4, 12, 0, 0),
        )
        await storage.store_event(event)

        export = await storage.export_for_prng()
        assert len(export) == 1
        assert export[0]["game_id"] == "20260204-prng1"
        assert export[0]["server_seed"] == "abc123def456"
        assert "timestamp_ms" in export[0]
```

**Step 2: Run test to verify it fails**

Run: `cd services/rugs-feed && python -m pytest tests/test_storage.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.storage'"

**Step 3: Write minimal implementation**

Create: `services/rugs-feed/src/storage.py`

```python
"""
EventStorage - SQLite storage for captured WebSocket events.

Stores:
- Raw events with timestamps
- Game summaries with seed reveals
- Export format for PRNG attack suite
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from .client import CapturedEvent

logger = logging.getLogger(__name__)


class EventStorage:
    """
    SQLite storage for WebSocket events.

    Tables:
    - games: Game summaries with final state and seed
    - events: Raw event log for replay/analysis
    """

    def __init__(self, db_path: str):
        """
        Initialize storage.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize database connection and create tables."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        # Create tables
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL,
                rugged INTEGER DEFAULT 0,
                final_price REAL,
                tick_count INTEGER,
                server_seed TEXT,
                server_seed_hash TEXT,
                peak_multiplier REAL,
                timestamp_ms INTEGER
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                game_id TEXT,
                timestamp TEXT NOT NULL,
                timestamp_ms INTEGER,
                data TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_game_id ON events(game_id);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_games_rugged ON games(rugged);
            CREATE INDEX IF NOT EXISTS idx_games_server_seed ON games(server_seed);
        """)
        await self._db.commit()
        logger.info(f"Database initialized: {self._db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def store_event(self, event: CapturedEvent) -> None:
        """
        Store a captured event.

        Args:
            event: CapturedEvent to store
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        timestamp_str = event.timestamp.isoformat()
        timestamp_ms = int(event.timestamp.timestamp() * 1000)
        data_json = json.dumps(event.data)

        # Store raw event
        await self._db.execute(
            """
            INSERT INTO events (event_type, game_id, timestamp, timestamp_ms, data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event.event_type, event.game_id, timestamp_str, timestamp_ms, data_json),
        )

        # Update game record for gameStateUpdate events
        if event.event_type == "gameStateUpdate" and event.game_id:
            await self._update_game_record(event)

        await self._db.commit()

    async def _update_game_record(self, event: CapturedEvent) -> None:
        """Update or create game record from gameStateUpdate."""
        data = event.data
        game_id = event.game_id
        timestamp_str = event.timestamp.isoformat()
        timestamp_ms = int(event.timestamp.timestamp() * 1000)

        rugged = 1 if data.get("rugged") else 0
        price = data.get("price")
        tick_count = data.get("tickCount")

        # Extract provably fair data
        pf = data.get("provablyFair", {})
        server_seed = pf.get("serverSeed")
        server_seed_hash = pf.get("serverSeedHash")

        # Check if game exists
        cursor = await self._db.execute(
            "SELECT game_id, peak_multiplier FROM games WHERE game_id = ?",
            (game_id,),
        )
        existing = await cursor.fetchone()

        if existing:
            # Update existing game
            peak = max(existing["peak_multiplier"] or 1.0, price or 1.0)

            await self._db.execute(
                """
                UPDATE games SET
                    last_updated_at = ?,
                    rugged = ?,
                    final_price = ?,
                    tick_count = ?,
                    server_seed = COALESCE(?, server_seed),
                    server_seed_hash = COALESCE(?, server_seed_hash),
                    peak_multiplier = ?,
                    timestamp_ms = ?
                WHERE game_id = ?
                """,
                (
                    timestamp_str,
                    rugged,
                    price,
                    tick_count,
                    server_seed,
                    server_seed_hash,
                    peak,
                    timestamp_ms,
                    game_id,
                ),
            )
        else:
            # Insert new game
            await self._db.execute(
                """
                INSERT INTO games (
                    game_id, first_seen_at, last_updated_at, rugged,
                    final_price, tick_count, server_seed, server_seed_hash,
                    peak_multiplier, timestamp_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    timestamp_str,
                    timestamp_str,
                    rugged,
                    price,
                    tick_count,
                    server_seed,
                    server_seed_hash,
                    price or 1.0,
                    timestamp_ms,
                ),
            )

    async def get_recent_games(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get most recent games.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of game dicts
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT * FROM games
            ORDER BY last_updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_seed_reveals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get games with revealed server seeds.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of games with server_seed present
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT * FROM games
            WHERE server_seed IS NOT NULL
            ORDER BY last_updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def export_for_prng(self) -> List[Dict[str, Any]]:
        """
        Export data in format suitable for PRNG attack suite.

        Returns:
            List of dicts with game_id, server_seed, timestamp_ms, etc.
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT
                game_id,
                timestamp_ms,
                server_seed,
                server_seed_hash,
                peak_multiplier,
                final_price,
                tick_count
            FROM games
            WHERE server_seed IS NOT NULL
            ORDER BY timestamp_ms ASC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_game_events(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for a specific game.

        Args:
            game_id: Game identifier

        Returns:
            List of event dicts
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT * FROM events
            WHERE game_id = ?
            ORDER BY timestamp ASC
            """,
            (game_id,),
        )
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            event_dict = dict(row)
            event_dict["data"] = json.loads(event_dict["data"])
            result.append(event_dict)

        return result

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if not self._db:
            return {}

        cursor = await self._db.execute("SELECT COUNT(*) as count FROM games")
        games_count = (await cursor.fetchone())["count"]

        cursor = await self._db.execute(
            "SELECT COUNT(*) as count FROM games WHERE server_seed IS NOT NULL"
        )
        seeds_count = (await cursor.fetchone())["count"]

        cursor = await self._db.execute("SELECT COUNT(*) as count FROM events")
        events_count = (await cursor.fetchone())["count"]

        return {
            "total_games": games_count,
            "seed_reveals": seeds_count,
            "total_events": events_count,
        }
```

**Step 4: Run test to verify it passes**

Run: `cd services/rugs-feed && python -m pytest tests/test_storage.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add services/rugs-feed/src/storage.py services/rugs-feed/tests/test_storage.py
git commit -m "feat(rugs-feed): implement SQLite storage with PRNG export"
```

---

## Task 4: Create FastAPI Application

**Files:**
- Create: `services/rugs-feed/src/api.py`
- Create: `services/rugs-feed/tests/test_api.py`

**Step 1: Write the failing test**

```python
"""Tests for FastAPI application."""
import pytest
from fastapi.testclient import TestClient
import tempfile

import sys
sys.path.insert(0, "services/rugs-feed")

from src.api import create_app


class TestAPI:
    """Test API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            app = create_app(db_path=f.name, auto_connect=False)
            yield TestClient(app)

    def test_health_endpoint(self, client):
        """Health endpoint should return service info."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rugs-feed"

    def test_games_endpoint(self, client):
        """Games endpoint should return empty list initially."""
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert isinstance(data["games"], list)

    def test_seeds_endpoint(self, client):
        """Seeds endpoint should return empty list initially."""
        response = client.get("/api/seeds")
        assert response.status_code == 200
        data = response.json()
        assert "seeds" in data
        assert isinstance(data["seeds"], list)

    def test_export_endpoint(self, client):
        """Export endpoint should return PRNG attack format."""
        response = client.get("/api/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"
```

**Step 2: Run test to verify it fails**

Run: `cd services/rugs-feed && python -m pytest tests/test_api.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.api'"

**Step 3: Write minimal implementation**

Create: `services/rugs-feed/src/api.py`

```python
"""
FastAPI application for Rugs Feed Service.

Endpoints:
- /health - Health check
- /api/games - Recent captured games
- /api/games/{game_id} - Single game with events
- /api/seeds - Seed reveals for PRNG analysis
- /api/export - JSONL export for attack suite
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse

from .storage import EventStorage

logger = logging.getLogger(__name__)

# Global storage reference
_storage: Optional[EventStorage] = None
_start_time: Optional[datetime] = None
_auto_connect: bool = True


def create_app(
    db_path: str = "/data/rugs_feed.db",
    auto_connect: bool = True,
) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        db_path: Path to SQLite database
        auto_connect: Whether to auto-connect to rugs.fun

    Returns:
        FastAPI application instance
    """
    global _storage, _start_time, _auto_connect

    _auto_connect = auto_connect
    _start_time = datetime.utcnow()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        global _storage

        # Startup
        _storage = EventStorage(db_path)
        await _storage.initialize()
        logger.info(f"Storage initialized: {db_path}")

        yield

        # Shutdown
        if _storage:
            await _storage.close()
            logger.info("Storage closed")

    app = FastAPI(
        title="Rugs Feed Service",
        description="Direct WebSocket capture for rugs.fun PRNG analysis",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        stats = await _storage.get_stats() if _storage else {}

        return {
            "status": "healthy",
            "service": "rugs-feed",
            "version": "1.0.0",
            "uptime_seconds": (datetime.utcnow() - _start_time).total_seconds() if _start_time else 0,
            "stats": stats,
        }

    @app.get("/api/games")
    async def get_games(limit: int = 100):
        """Get recent captured games."""
        if not _storage:
            raise HTTPException(500, "Storage not initialized")

        games = await _storage.get_recent_games(limit=limit)
        return {"games": games, "count": len(games)}

    @app.get("/api/games/{game_id}")
    async def get_game(game_id: str):
        """Get single game with all events."""
        if not _storage:
            raise HTTPException(500, "Storage not initialized")

        events = await _storage.get_game_events(game_id)
        if not events:
            raise HTTPException(404, f"Game {game_id} not found")

        return {"game_id": game_id, "events": events, "event_count": len(events)}

    @app.get("/api/seeds")
    async def get_seeds(limit: int = 100):
        """Get games with revealed server seeds."""
        if not _storage:
            raise HTTPException(500, "Storage not initialized")

        seeds = await _storage.get_seed_reveals(limit=limit)
        return {"seeds": seeds, "count": len(seeds)}

    @app.get("/api/export")
    async def export_prng():
        """Export data in JSONL format for PRNG attack suite."""
        if not _storage:
            raise HTTPException(500, "Storage not initialized")

        data = await _storage.export_for_prng()

        async def generate():
            for item in data:
                yield json.dumps(item) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=rugs_seeds.jsonl"},
        )

    @app.get("/api/stats")
    async def get_stats():
        """Get service statistics."""
        if not _storage:
            raise HTTPException(500, "Storage not initialized")

        return await _storage.get_stats()

    return app
```

**Step 4: Run test to verify it passes**

Run: `cd services/rugs-feed && python -m pytest tests/test_api.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add services/rugs-feed/src/api.py services/rugs-feed/tests/test_api.py
git commit -m "feat(rugs-feed): implement FastAPI endpoints for PRNG export"
```

---

## Task 5: Create Main Entry Point

**Files:**
- Create: `services/rugs-feed/src/main.py`
- Create: `services/rugs-feed/config/config.yaml`

**Step 1: Create config.yaml**

```yaml
# Rugs Feed Service Configuration

# Backend connection
rugs_backend_url: "https://backend.rugs.fun"

# Storage
storage_path: "/data/rugs_feed.db"

# API Server
port: 9016
host: "0.0.0.0"

# Reconnection settings
max_reconnect_attempts: 100
reconnect_delay_seconds: 5

# Logging
log_level: "INFO"
```

**Step 2: Create main.py**

```python
"""
Rugs Feed Service Main Entry Point

Starts:
- Direct Socket.IO connection to rugs.fun
- SQLite storage for event capture
- FastAPI server for querying captured data

Usage:
    python -m src.main
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
import yaml

from .api import create_app
from .client import RugsFeedClient, CapturedEvent
from .storage import EventStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from file and environment."""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    defaults = {
        "rugs_backend_url": "https://backend.rugs.fun",
        "storage_path": "/data/rugs_feed.db",
        "port": 9016,
        "host": "0.0.0.0",
        "max_reconnect_attempts": 100,
        "reconnect_delay_seconds": 5,
        "log_level": "INFO",
    }

    # Load from config file
    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = yaml.safe_load(f) or {}
            defaults.update(file_config)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    # Override with environment variables
    env_mappings = {
        "RUGS_BACKEND_URL": "rugs_backend_url",
        "STORAGE_PATH": "storage_path",
        "PORT": "port",
        "HOST": "host",
        "LOG_LEVEL": "log_level",
    }

    for env_key, config_key in env_mappings.items():
        value = os.environ.get(env_key)
        if value:
            if config_key == "port":
                defaults[config_key] = int(value)
            else:
                defaults[config_key] = value

    return defaults


# Global references for cleanup
_client: RugsFeedClient | None = None
_storage: EventStorage | None = None


async def run_service():
    """Run the Rugs Feed Service."""
    global _client, _storage

    config = load_config()
    start_time = datetime.utcnow()

    # Set log level
    logging.getLogger().setLevel(config["log_level"])

    logger.info("=" * 60)
    logger.info("Rugs Feed Service Starting")
    logger.info("=" * 60)
    logger.info(f"Backend URL: {config['rugs_backend_url']}")
    logger.info(f"Storage Path: {config['storage_path']}")
    logger.info(f"API Port: {config['port']}")

    # Initialize storage
    _storage = EventStorage(config["storage_path"])
    await _storage.initialize()

    # Event handler that stores to SQLite
    def on_event(event: CapturedEvent):
        asyncio.create_task(_storage.store_event(event))

    # Initialize client
    _client = RugsFeedClient(
        url=config["rugs_backend_url"],
        on_event=on_event,
    )

    # Create API app
    app = create_app(
        db_path=config["storage_path"],
        auto_connect=False,  # We manage connection separately
    )

    # Shutdown handler
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start API server
    uvicorn_config = uvicorn.Config(
        app,
        host=config["host"],
        port=config["port"],
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    async def run_api():
        await server.serve()

    async def run_websocket():
        """Maintain WebSocket connection with reconnection."""
        while not shutdown_event.is_set():
            try:
                logger.info("Connecting to rugs.fun backend...")
                await _client.connect()
                await _client.wait()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            if not shutdown_event.is_set():
                delay = config["reconnect_delay_seconds"]
                logger.info(f"Reconnecting in {delay}s...")
                await asyncio.sleep(delay)

    async def periodic_stats():
        """Log statistics periodically."""
        while not shutdown_event.is_set():
            try:
                stats = await _storage.get_stats()
                logger.info(
                    f"Stats: {stats['total_games']} games, "
                    f"{stats['seed_reveals']} seeds, "
                    f"{stats['total_events']} events"
                )
            except Exception as e:
                logger.error(f"Stats error: {e}")
            await asyncio.sleep(300)  # Every 5 minutes

    try:
        await asyncio.gather(
            run_api(),
            run_websocket(),
            periodic_stats(),
        )
    except asyncio.CancelledError:
        logger.info("Service tasks cancelled")
    finally:
        logger.info("Cleaning up...")
        if _client:
            await _client.disconnect()
        if _storage:
            await _storage.close()
        logger.info("Rugs Feed Service stopped")


if __name__ == "__main__":
    asyncio.run(run_service())
```

**Step 3: Commit**

```bash
git add services/rugs-feed/src/main.py services/rugs-feed/config/config.yaml
git commit -m "feat(rugs-feed): implement main entry point with persistent connection"
```

---

## Task 6: Create Docker Configuration

**Files:**
- Create: `services/rugs-feed/Dockerfile`
- Create: `services/rugs-feed/docker-compose.yml`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

LABEL maintainer="VECTRA Team"
LABEL description="Rugs Feed Service - Direct WebSocket capture for PRNG analysis"
LABEL version="1.0.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Create data directory
RUN mkdir -p /data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=9016
ENV HOST=0.0.0.0
ENV STORAGE_PATH=/data/rugs_feed.db
ENV RUGS_BACKEND_URL=https://backend.rugs.fun

# Expose API port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run service
CMD ["python", "-m", "src.main"]
```

**Step 2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  rugs-feed:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: vectra-rugs-feed
    restart: unless-stopped

    ports:
      - "${PORT:-9016}:${PORT:-9016}"

    volumes:
      # Configuration (read-only)
      - ./config:/app/config:ro

      # Data storage (persistent)
      - ${DATA_PATH:-rugs-feed-data}:/data

    environment:
      - RUGS_BACKEND_URL=${RUGS_BACKEND_URL:-https://backend.rugs.fun}
      - PORT=${PORT:-9016}
      - HOST=0.0.0.0
      - STORAGE_PATH=/data/rugs_feed.db
      - LOG_LEVEL=${LOG_LEVEL:-INFO}

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${PORT:-9016}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

    networks:
      - vectra-network

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

volumes:
  rugs-feed-data:
    name: vectra-rugs-feed-data

networks:
  vectra-network:
    name: vectra-network
    driver: bridge
```

**Step 3: Commit**

```bash
git add services/rugs-feed/Dockerfile services/rugs-feed/docker-compose.yml
git commit -m "feat(rugs-feed): add Docker configuration for persistent deployment"
```

---

## Task 7: Integration Test and Documentation

**Files:**
- Create: `services/rugs-feed/tests/test_integration.py`
- Update: `services/rugs-feed/README.md`

**Step 1: Create integration test**

```python
"""Integration tests for Rugs Feed Service."""
import pytest
import asyncio
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, "services/rugs-feed")

from src.client import RugsFeedClient, CapturedEvent, ConnectionState
from src.storage import EventStorage
from src.api import create_app
from fastapi.testclient import TestClient


class TestIntegration:
    """Test full service integration."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_event_flow(self, temp_db):
        """Test event capture through storage to API."""
        # Setup storage
        storage = EventStorage(temp_db)
        await storage.initialize()

        # Simulate captured event
        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={
                "gameId": "20260204-integration",
                "price": 3.5,
                "tickCount": 200,
                "rugged": True,
                "provablyFair": {
                    "serverSeed": "integration-test-seed-12345",
                    "serverSeedHash": "hash-abc123",
                },
            },
            game_id="20260204-integration",
        )

        # Store event
        await storage.store_event(event)

        # Verify via API
        app = create_app(db_path=temp_db, auto_connect=False)
        with TestClient(app) as client:
            # Check games endpoint
            response = client.get("/api/games")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["games"][0]["game_id"] == "20260204-integration"

            # Check seeds endpoint
            response = client.get("/api/seeds")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["seeds"][0]["server_seed"] == "integration-test-seed-12345"

            # Check export endpoint
            response = client.get("/api/export")
            assert response.status_code == 200
            assert "integration-test-seed" in response.text

        await storage.close()

    def test_client_initialization(self):
        """Test client can be initialized without connection."""
        client = RugsFeedClient()
        assert client.state == ConnectionState.DISCONNECTED
        assert "backend.rugs.fun" in client.url
        assert not client.is_connected
```

**Step 2: Run all tests**

Run: `cd services/rugs-feed && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 3: Update README.md with full documentation**

```markdown
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
```

**Step 4: Final commit**

```bash
git add services/rugs-feed/tests/test_integration.py services/rugs-feed/README.md
git commit -m "feat(rugs-feed): complete service with integration tests and docs"
```

---

## Summary

| Task | Files | Tests |
|------|-------|-------|
| 1. Directory Structure | manifest.json, requirements.txt, README.md | - |
| 2. Socket.IO Client | src/client.py | test_client.py (4 tests) |
| 3. SQLite Storage | src/storage.py | test_storage.py (4 tests) |
| 4. FastAPI Application | src/api.py | test_api.py (4 tests) |
| 5. Main Entry Point | src/main.py, config.yaml | - |
| 6. Docker Configuration | Dockerfile, docker-compose.yml | - |
| 7. Integration | test_integration.py, README.md | test_integration.py (2 tests) |

**Total: 7 tasks, ~14 tests, 8 commits**

---

**Plan complete and saved to `docs/plans/2026-02-04-rugs-feed-service.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session in worktree with executing-plans, batch execution with checkpoints

**Which approach?**
