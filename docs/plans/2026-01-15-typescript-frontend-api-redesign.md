# Implementation Plan: TypeScript Frontend + Dedicated REST API

## Goal
Replace Flask-based UI with a clean TypeScript frontend and dedicated FastAPI backend, starting with a minimal WebSocket-first architecture.

## GitHub Issue
None - create issue first after plan approval

## Problem Statement

The current Flask UI (`src/recording_ui/`) has critical issues:
1. **Mixed concerns** - Routes, templates, business logic intertwined in `app.py` (1000+ lines)
2. **Hardcoded paths** - File paths scattered throughout code
3. **No API contract** - Frontend and backend tightly coupled
4. **Untyped JavaScript** - Vanilla JS in `static/js/*.js` with no type safety
5. **Duplicate WebSocket handling** - CDP intercept vs direct Socket.IO vs Flask-SocketIO

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TypeScript Frontend                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  REST Client │  │  WS Client  │  │  React Components       │  │
│  │  (fetch/axios)│  │ (native WS) │  │  - Dashboard            │  │
│  └──────┬───────┘  └──────┬──────┘  │  - Backtest Viewer      │  │
│         │                 │         │  - Profile Manager       │  │
│         │                 │         └─────────────────────────┘  │
└─────────┼─────────────────┼─────────────────────────────────────┘
          │                 │
          │    HTTP :8000   │    WS :8000/ws
          ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  REST Routes    │  │  WebSocket Hub  │  │  Config         │  │
│  │  /api/v1/...    │  │  /ws/feed       │  │  (from env)     │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────┘  │
│           │                    │                                 │
│           ▼                    ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Service Layer                             ││
│  │  - ProfileService (existing)                                 ││
│  │  - BacktestService (existing)                                ││
│  │  - EventStoreService (existing)                              ││
│  │  - GameFeedService (NEW - wraps WebSocketFeed)               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Core Services (Reuse)                         │
│  src/services/event_bus.py      - Internal pub/sub              │
│  src/services/event_store/      - Parquet persistence           │
│  src/sources/websocket_feed.py  - rugs.fun Socket.IO client     │
│  src/models/                    - Data models                   │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
VECTRA-PLAYER/
├── api/                          # NEW: FastAPI backend
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry
│   ├── config.py                 # Pydantic Settings (env-based)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── profiles.py           # /api/v1/profiles
│   │   ├── recordings.py         # /api/v1/recordings
│   │   ├── backtest.py           # /api/v1/backtest
│   │   └── system.py             # /api/v1/status, /api/v1/health
│   ├── ws/
│   │   ├── __init__.py
│   │   └── feed.py               # WebSocket endpoint
│   └── services/
│       ├── __init__.py
│       └── game_feed.py          # Wraps WebSocketFeed for WS broadcast
│
├── frontend/                     # NEW: TypeScript React app
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── client.ts         # REST API client
│   │   │   └── types.ts          # API types (from OpenAPI)
│   │   ├── ws/
│   │   │   └── feed.ts           # WebSocket client
│   │   ├── stores/
│   │   │   └── gameStore.ts      # Zustand state management
│   │   ├── components/
│   │   │   ├── GameChart.tsx
│   │   │   ├── RecordingToggle.tsx
│   │   │   └── ...
│   │   └── pages/
│   │       ├── Dashboard.tsx
│   │       ├── Backtest.tsx
│   │       └── Profiles.tsx
│   └── public/
│
├── src/                          # KEEP: Core Python services
│   ├── services/                 # EventBus, EventStore, etc.
│   ├── sources/                  # WebSocketFeed
│   ├── models/                   # Data models
│   └── ...
│
└── src/recording_ui/             # DEPRECATED: Move to _archived/
```

## Phase 1: Minimal WebSocket Feed (Priority)

**Goal:** Get a working WebSocket endpoint that broadcasts rugs.fun game ticks to connected clients.

### Task 1.1: Create FastAPI Skeleton
**Files:**
- `api/__init__.py`
- `api/main.py`
- `api/config.py`

```python
# api/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Paths (from environment, with defaults)
    rugs_data_dir: Path = Path.home() / "rugs_data"
    chrome_profile: str = "rugs_bot"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # WebSocket
    ws_reconnect_interval: float = 5.0

    class Config:
        env_prefix = "VECTRA_"
        env_file = ".env"

settings = Settings()
```

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="VECTRA API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

### Task 1.2: WebSocket Feed Endpoint

```python
# api/ws/feed.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead.append(connection)
        for d in dead:
            self.active_connections.discard(d)

manager = ConnectionManager()

# In main.py:
@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive commands
            data = await websocket.receive_text()
            # Handle subscribe/unsubscribe commands
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### Task 1.3: Game Feed Service (Bridge)

```python
# api/services/game_feed.py
import asyncio
import threading
from sources.websocket_feed import WebSocketFeed
from api.ws.feed import manager

class GameFeedService:
    """Bridges rugs.fun WebSocket to our API WebSocket."""

    def __init__(self):
        self.feed = WebSocketFeed()
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return

        self._running = True

        @self.feed.on('signal')
        def on_signal(signal):
            # Broadcast to all connected clients
            asyncio.run(manager.broadcast({
                "type": "game_tick",
                "data": {
                    "gameId": signal.gameId,
                    "tickCount": signal.tickCount,
                    "price": float(signal.price),
                    "phase": signal.phase,
                    "active": signal.active,
                    "rugged": signal.rugged,
                    "timestamp": signal.timestamp,
                }
            }))

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self.feed.connect()
        self.feed.wait()

    def stop(self):
        self._running = False
        self.feed.disconnect()
```

### Task 1.4: TypeScript Frontend Skeleton

```bash
cd VECTRA-PLAYER
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install zustand @tanstack/react-query
```

```typescript
// frontend/src/ws/feed.ts
export interface GameTick {
  gameId: string;
  tickCount: number;
  price: number;
  phase: string;
  active: boolean;
  rugged: boolean;
  timestamp: number;
}

export interface WSMessage {
  type: 'game_tick' | 'connection_status';
  data: GameTick | { connected: boolean };
}

export class GameFeedClient {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor(private url: string = 'ws://localhost:8000/ws/feed') {}

  connect(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.emit('connection_status', { connected: true });
    };

    this.ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      this.emit(msg.type, msg.data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...');
      this.emit('connection_status', { connected: false });
      this.reconnectTimeout = window.setTimeout(() => this.connect(), 5000);
    };
  }

  on(event: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }

  private emit(event: string, data: any): void {
    this.listeners.get(event)?.forEach(cb => cb(data));
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    this.ws?.close();
  }
}
```

```typescript
// frontend/src/stores/gameStore.ts
import { create } from 'zustand';
import { GameTick, GameFeedClient } from '../ws/feed';

interface GameState {
  connected: boolean;
  currentTick: GameTick | null;
  priceHistory: { tick: number; price: number }[];

  // Actions
  setConnected: (connected: boolean) => void;
  onTick: (tick: GameTick) => void;
  clearHistory: () => void;
}

export const useGameStore = create<GameState>((set, get) => ({
  connected: false,
  currentTick: null,
  priceHistory: [],

  setConnected: (connected) => set({ connected }),

  onTick: (tick) => {
    const { priceHistory, currentTick } = get();

    // Reset history on new game
    const newHistory = currentTick?.gameId !== tick.gameId
      ? [{ tick: tick.tickCount, price: tick.price }]
      : [...priceHistory, { tick: tick.tickCount, price: tick.price }];

    set({
      currentTick: tick,
      priceHistory: newHistory.slice(-500), // Keep last 500 ticks
    });
  },

  clearHistory: () => set({ priceHistory: [] }),
}));
```

## Phase 2: REST API Endpoints

After Phase 1 is working, migrate REST endpoints:

| Flask Endpoint | FastAPI Endpoint | Notes |
|----------------|------------------|-------|
| `/api/status` | `GET /api/v1/status` | System status |
| `/api/recording/toggle` | `POST /api/v1/recording/toggle` | Recording control |
| `/api/profiles` | `GET /api/v1/profiles` | List profiles |
| `/api/profiles/<name>` | `GET /api/v1/profiles/{name}` | Get profile |
| `/api/profiles` (POST) | `POST /api/v1/profiles` | Create profile |
| `/api/backtest/strategies` | `GET /api/v1/strategies` | List strategies |
| `/api/browser/connect` | `POST /api/v1/browser/connect` | CDP connection |

## Phase 3: Frontend Pages

1. **Dashboard** - Connection status, recording toggle, live tick display
2. **Backtest Viewer** - Strategy/profile selector, chart, playback controls
3. **Profiles** - CRUD for trading profiles

## Phase 4: Deprecate Flask UI

1. Move `src/recording_ui/` to `src/_archived/recording_ui/`
2. Update `scripts/start.sh` to launch FastAPI + Vite
3. Update CLAUDE.md with new architecture

---

## Tasks (TDD Order)

### Task 1: FastAPI Health Endpoint
**Test First:**
```python
# api/tests/test_health.py
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_returns_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Verify:**
```bash
cd api && pytest tests/test_health.py -v
```

### Task 2: WebSocket Connection
**Test First:**
```python
# api/tests/test_ws.py
from fastapi.testclient import TestClient
from api.main import app

def test_websocket_connects():
    client = TestClient(app)
    with client.websocket_connect("/ws/feed") as websocket:
        # Connection should succeed
        pass
```

### Task 3: Game Feed Broadcast
**Test First:**
```python
# api/tests/test_game_feed.py
import pytest
from unittest.mock import Mock, patch
from api.services.game_feed import GameFeedService

def test_game_feed_broadcasts_ticks():
    with patch('api.services.game_feed.manager') as mock_manager:
        service = GameFeedService()
        # Simulate a tick
        # Assert manager.broadcast was called
```

### Task 4: Frontend WebSocket Client
**Test First:**
```typescript
// frontend/src/ws/feed.test.ts
import { describe, it, expect, vi } from 'vitest';
import { GameFeedClient } from './feed';

describe('GameFeedClient', () => {
  it('connects to WebSocket server', async () => {
    const client = new GameFeedClient('ws://localhost:8000/ws/feed');
    const onConnect = vi.fn();
    client.on('connection_status', onConnect);
    client.connect();
    // ... assertions
  });
});
```

---

## Risks
- [ ] **Breaking existing workflows** → Deprecation is phased, Flask UI remains until Phase 4
- [ ] **WebSocket reliability** → Reuse battle-tested WebSocketFeed with reconnection logic
- [ ] **Type sync between Python/TS** → Generate types from OpenAPI schema

## Definition of Done
- [ ] FastAPI server runs on port 8000
- [ ] WebSocket broadcasts live game ticks
- [ ] TypeScript frontend displays live chart
- [ ] Recording toggle works via REST API
- [ ] Flask UI moved to `_archived/`
- [ ] CLAUDE.md updated
- [ ] All tests pass

---

## Quick Start (After Implementation)

```bash
# Terminal 1: API Server
cd VECTRA-PLAYER
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend Dev Server
cd VECTRA-PLAYER/frontend
npm run dev

# Open: http://localhost:5173
```

## Configuration (Environment Variables)

```bash
# .env
VECTRA_RUGS_DATA_DIR=~/rugs_data
VECTRA_CHROME_PROFILE=rugs_bot
VECTRA_API_PORT=8000
```
