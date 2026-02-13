# VECTRA-PLAYER Process Flowcharts

**Version:** 1.0.0
**Date:** December 29, 2025
**Purpose:** ASCII flowchart documentation of all major codebase processes

This document provides comprehensive ASCII flowcharts mapping the entire codebase's processes and architecture.

---

## Table of Contents

1. [Application Lifecycle](#1-application-lifecycle)
2. [Event-Driven Architecture](#2-event-driven-architecture)
3. [Data Flow Pipeline](#3-data-flow-pipeline)
4. [Live vs Replay Mode](#4-live-vs-replay-mode)
5. [Browser Automation (CDP)](#5-browser-automation-cdp)
6. [Trading & Action Flow](#6-trading--action-flow)
7. [State Management](#7-state-management)
8. [Vector Indexing & RAG](#8-vector-indexing--rag)
9. [Testing & CI/CD](#9-testing--cicd)

---

## 1. Application Lifecycle

### 1.1 Main Application Startup Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    main.py: main()                          │
│                         ▼                                    │
│         Parse CLI args (--live flag)                        │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Application.__init__(live_mode=args.live)           │
├─────────────────────────────────────────────────────────────┤
│  1. Setup logging (setup_logging())                         │
│  2. Initialize config (config.validate())                   │
│  3. Create GameState(initial_balance, event_bus)            │
│  4. Start EventBus (event_bus.start())                      │
│  5. Start AsyncLoopManager (async_manager.start())          │
│  6. Setup event handlers (_setup_event_handlers())          │
│  7. Create Tk root window                                   │
│  8. Configure root window (_configure_root())               │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application.run()                          │
├─────────────────────────────────────────────────────────────┤
│  1. Create BrowserBridge (get_browser_bridge())             │
│  2. Create LiveStateProvider(event_bus)                     │
│  3. Create & Start EventStoreService(event_bus)             │
│  4. Create MinimalWindow(root, state, event_bus, ...)       │
│  5. Auto-load games (if not live_mode)                      │
│  6. Publish UI_READY event                                  │
│  7. Start Tk mainloop (root.mainloop())                     │
└────────────────────────┬────────────────────────────────────┘
                         ▼
         ┌───────────────────────────────────┐
         │   Application Running             │
         │   (Tkinter event loop active)     │
         └───────────────┬───────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            User Closes Window / Ctrl+C                      │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Application.shutdown()                        │
├─────────────────────────────────────────────────────────────┤
│  1. Set shutdown timeout (10s alarm)                        │
│  2. Save config to file                                     │
│  3. Calculate & log final metrics                           │
│  4. Stop EventStore (flushes buffers)                       │
│  5. Stop LiveStateProvider                                  │
│  6. Stop BrowserBridge                                      │
│  7. Stop EventBus                                           │
│  8. Cleanup MainWindow (unsubscribe events)                 │
│  9. Stop AsyncLoopManager                                   │
│  10. Quit & Destroy Tk root                                 │
│  11. Exit cleanly (sys.exit(0))                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Initialization Order

```
         Startup Order (Critical Dependencies)
         =====================================

    1. Logging
       └─→ All components need logger

    2. Config
       └─→ Validated early, used by all

    3. GameState
       └─→ Core state container

    4. EventBus
       └─→ Communication backbone
          │
          ├─→ 5. EventStoreService
          │      └─→ Subscribes to events
          │
          ├─→ 6. LiveStateProvider
          │      └─→ Subscribes to WS events
          │
          ├─→ 7. BrowserBridge
          │      └─→ Publishes WS events
          │
          └─→ 8. MinimalWindow (UI)
                 └─→ Subscribes & publishes

    9. AsyncLoopManager
       └─→ Handles async operations from Tk thread

    10. Tkinter mainloop()
        └─→ Blocks until app closes
```

---

## 2. Event-Driven Architecture

### 2.1 EventBus Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      EventBus Core                          │
│                  (Thread-Safe Pub/Sub)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Subscribers (dict):                                        │
│    Events.WS_RAW_EVENT → [callback1, callback2, ...]       │
│    Events.GAME_TICK    → [callback3, ...]                  │
│    Events.TRADE_BUY    → [callback4, ...]                  │
│                                                             │
│  Queue (5000 max):                                          │
│    ┌──────────────────────────────────────┐                │
│    │ (event, data) │ (event, data) │ ... │                │
│    └──────────────────────────────────────┘                │
│                                                             │
│  Processing Thread (daemon):                                │
│    while processing:                                        │
│      item = queue.get(timeout=0.1)                          │
│      _dispatch(event, data)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Publisher Flow:
───────────────
  Component A
     │
     │  event_bus.publish(Events.WS_RAW_EVENT, data)
     ▼
  ┌──────────┐
  │  Queue   │  ← Non-blocking put (drops if full)
  └────┬─────┘
       │
       │  Background thread processes
       ▼
  ┌──────────────┐
  │  _dispatch() │  ← Lock-free callback execution
  └──────┬───────┘
         │
         ├─→ callback1({"name": "ws.raw_event", "data": {...}})
         ├─→ callback2({"name": "ws.raw_event", "data": {...}})
         └─→ callback3({"name": "ws.raw_event", "data": {...}})

Subscriber Flow:
────────────────
  Component B
     │
     │  event_bus.subscribe(Events.WS_RAW_EVENT, self._on_ws_event)
     ▼
  ┌─────────────────┐
  │ _subscribers    │  ← Weak references by default
  │ [event] → list  │     (auto-cleanup when component dies)
  └─────────────────┘
```

### 2.2 Event Categories

```
Event Categories (Events Enum):
═══════════════════════════════

┌──────────────┐
│  UI Events   │  UI_READY, UI_UPDATE, UI_ERROR
└──────┬───────┘
       │
       ▼
┌────────────────┐
│  Game Events   │  GAME_START, GAME_END, GAME_TICK, GAME_RUG
└──────┬─────────┘
       │
       ▼
┌─────────────────┐
│ Trading Events  │  TRADE_BUY, TRADE_SELL, TRADE_CONFIRMED
└──────┬──────────┘
       │
       ▼
┌──────────────┐
│  Bot Events  │  BOT_ENABLED, BOT_DECISION, BOT_ACTION
└──────┬───────┘
       │
       ▼
┌────────────────┐
│  File Events   │  FILE_LOADED, FILE_SAVED, FILE_ERROR
└──────┬─────────┘
       │
       ▼
┌─────────────────┐
│ Replay Events   │  REPLAY_START, REPLAY_PAUSE, REPLAY_STOP
└──────┬──────────┘
       │
       ▼
┌──────────────────┐
│ WebSocket Events │  WS_RAW_EVENT, PLAYER_UPDATE, WS_CONNECTED
└──────────────────┘
```

---

## 3. Data Flow Pipeline

### 3.1 Complete WebSocket → Parquet Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Data Source Layer                         │
│            (rugs.fun WebSocket or Replay File)               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           │  Raw WebSocket Frames
                           ▼
┌──────────────────────────────────────────────────────────────┐
│           CDP WebSocket Interceptor (Browser)                │
│  OR  Fallback WebSocket Feed (socketio_parser.py)           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │  Parsed JSON events
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    BrowserBridge                             │
│  Normalizes & publishes:                                     │
│    event_bus.publish(Events.WS_RAW_EVENT, event_data)        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │  EventBus message
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                      EventBus                                │
│  Queue: (Events.WS_RAW_EVENT, data)                          │
└────────────┬─────────────────────┬────────────────────────────┘
             │                     │
             │                     │  Dispatches to subscribers
             ▼                     ▼
┌────────────────────┐   ┌──────────────────────────┐
│ EventStoreService  │   │  LiveStateProvider       │
│  (Parquet Writer)  │   │  (Server Auth State)     │
└─────────┬──────────┘   └────────┬─────────────────┘
          │                       │
          │                       │  Updates GameState
          │                       ▼
          │              ┌──────────────────┐
          │              │    GameState     │
          │              │ (Live snapshot)  │
          │              └──────────────────┘
          │
          │  Buffers events (100 events or 5s)
          ▼
┌──────────────────────────────────────────────────────────────┐
│               ParquetWriter (writer.py)                      │
│  Buffer: [event1, event2, ..., event100]                     │
│  Flush trigger: buffer_size (100) OR time (5s)              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │  Atomic write (partitioned)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│           ~/rugs_data/events_parquet/                        │
│  ├── doc_type=ws_event/                                      │
│  │   └── session_id=xxx/part-001.parquet                    │
│  ├── doc_type=game_tick/                                     │
│  │   └── session_id=xxx/part-001.parquet                    │
│  ├── doc_type=player_action/                                 │
│  │   └── session_id=xxx/part-001.parquet                    │
│  └── doc_type=server_state/                                  │
│      └── session_id=xxx/part-001.parquet                    │
│                                                              │
│  ** CANONICAL TRUTH - All queries start here **             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │  Optional: Derived indexes
                         ▼
┌──────────────────────────────────────────────────────────────┐
│          ChromaDB Vector Index (Rebuildable)                 │
│  ~/Desktop/claude-flow/rag-pipeline/storage/chroma/         │
│  Collections: rugs_events                                    │
│  Purpose: RAG queries for AI agents & Protocol Explorer     │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 EventStore Single Writer Pattern

```
┌─────────────────────────────────────────────────────────────┐
│           EventStoreService (service.py)                    │
│                   ** SINGLE WRITER **                       │
│                                                             │
│  Subscriptions (weak=False for persistence):                │
│    • Events.WS_RAW_EVENT    → _on_ws_raw_event()            │
│    • Events.GAME_TICK       → _on_game_tick()               │
│    • Events.PLAYER_UPDATE   → _on_player_update()           │
│    • Events.TRADE_BUY       → _on_trade_buy()               │
│    • Events.TRADE_SELL      → _on_trade_sell()              │
│    • Events.TRADE_SIDEBET   → _on_trade_sidebet()           │
│    • Events.TRADE_CONFIRMED → _on_trade_confirmed()         │
│                                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Each handler creates EventEnvelope
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          EventEnvelope (schema.py)                          │
│  Common fields:                                             │
│    • ts: timestamp (UTC)                                    │
│    • source: CDP | PUBLIC_WS | UI | BOT                     │
│    • doc_type: ws_event | game_tick | player_action | ...  │
│    • session_id: UUID for this recording session            │
│    • seq: monotonic sequence number                         │
│    • direction: inbound | outbound                          │
│    • raw_json: full event payload (for debugging)           │
│                                                             │
│  Type-specific fields:                                      │
│    • game_tick: tick, price (Decimal)                       │
│    • player_action: action_type, game_id, player_id         │
│    • server_state: cash, position_qty (Decimals)            │
│                                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  writer.write(envelope)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            ParquetWriter (writer.py)                        │
│                                                             │
│  1. Add to buffer: _buffer[doc_type].append(envelope)       │
│  2. Check flush conditions:                                 │
│     • Buffer size >= buffer_size (100 events)               │
│     • Time since last flush >= flush_interval (5s)          │
│  3. If flush triggered:                                     │
│     a. Convert to DataFrame (pandas)                        │
│     b. Determine partition path (doc_type, session_id)      │
│     c. Atomic write to Parquet file                         │
│     d. Clear buffer                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Why Single Writer?
──────────────────
  • No file conflicts
  • Guaranteed ordering within session
  • Atomic flushes
  • Thread-safe (EventBus serializes calls)
  • Partition by doc_type prevents contention
```

---

## 4. Live vs Replay Mode

### 4.1 Mode Selection

```
                        main.py
                           │
                           │  Parse --live flag
                           ▼
                   ┌───────────────┐
                   │  args.live?   │
                   └───┬───────┬───┘
                       │       │
                   No  │       │  Yes
                       │       │
                       ▼       ▼
            ┌──────────────┐  ┌──────────────┐
            │ REPLAY MODE  │  │  LIVE MODE   │
            └──────┬───────┘  └──────┬───────┘
                   │                 │
                   ▼                 ▼
```

### 4.2 Replay Mode Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      REPLAY MODE                            │
└─────────────────────────────────────────────────────────────┘

Data Source: ~/rugs_data/events_parquet/**/*.parquet
         │
         │  DuckDB query
         ▼
┌─────────────────────────────────────────────────────────────┐
│               ReplayEngine (replay_engine.py)               │
│  • Load events from Parquet                                 │
│  • Sort by timestamp                                        │
│  • Create event stream                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Playback control
                         ▼
┌─────────────────────────────────────────────────────────────┐
│       ReplayPlaybackController                              │
│  Controls:                                                  │
│    • Play/Pause/Stop                                        │
│    • Speed (0.5x, 1x, 2x, 5x)                               │
│    • Seek to tick                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Publishes at controlled rate
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      EventBus                               │
│  • GAME_TICK                                                │
│  • PLAYER_UPDATE                                            │
│  • TRADE_EXECUTED                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Updates UI
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   MinimalWindow (UI)                        │
│  • Chart updates                                            │
│  • Balance display                                          │
│  • Position display                                         │
└─────────────────────────────────────────────────────────────┘

Features:
─────────
  • No WebSocket needed
  • Historical analysis
  • Bot backtesting
  • Speed control
  • Seek capability
```

### 4.3 Live Mode Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       LIVE MODE                             │
└─────────────────────────────────────────────────────────────┘

Data Source: rugs.fun WebSocket (real-time)
         │
         │  wss://rugs.fun/socket.io/...
         ▼
┌─────────────────────────────────────────────────────────────┐
│         CDP WebSocket Interceptor (CDP Protocol)            │
│  OR  Fallback WebSocket Feed (direct connection)            │
│  • Capture raw frames from browser DevTools                 │
│  • Parse Socket.IO protocol                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Normalized events
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    BrowserBridge                            │
│  • event_bus.publish(Events.WS_RAW_EVENT, ...)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ├────────────────────┬────────────────┐
                         │                    │                │
                         ▼                    ▼                ▼
              ┌────────────────┐  ┌───────────────┐  ┌────────────────┐
              │  EventStore    │  │ LiveState     │  │ MinimalWindow  │
              │  (Parquet)     │  │ Provider      │  │ (UI Updates)   │
              │                │  │ (Reconcile)   │  │                │
              └────────────────┘  └───────────────┘  └────────────────┘

Live Features:
──────────────
  • Real-time data capture
  • Server-authoritative state (LiveStateProvider)
  • Automatic Parquet persistence
  • Live trading execution
  • Bot automation
  • Latency tracking (client_ts → server_ts → confirmed_ts)

State Authority:
────────────────
  • Server playerUpdate = CANONICAL TRUTH
  • Local state = optimistic updates only
  • Reconciliation on every playerUpdate
  • No local balance calculations
```

---

## 5. Browser Automation (CDP)

### 5.1 CDP Stack

```
┌─────────────────────────────────────────────────────────────┐
│                  Browser Automation Stack                   │
└─────────────────────────────────────────────────────────────┘

Layer 1: Chrome Browser
───────────────────────
  ┌──────────────────────────────────────────────┐
  │  Chrome/Chromium (--remote-debugging-port)   │
  │  • DevTools Protocol enabled                 │
  │  • WebSocket server on port 9222             │
  └────────────────────┬─────────────────────────┘
                       │
                       │  CDP over WebSocket
                       ▼
Layer 2: CDP Client
───────────────────
  ┌──────────────────────────────────────────────┐
  │  CDPWebSocketInterceptor                     │
  │  • Connect to ws://localhost:9222/...        │
  │  • Send: Network.enable, Fetch.enable        │
  │  • Listen: Network.webSocketFrameReceived    │
  └────────────────────┬─────────────────────────┘
                       │
                       │  WebSocket frame events
                       ▼
Layer 3: Parser
───────────────
  ┌──────────────────────────────────────────────┐
  │      SocketIOParser                          │
  │  • Parse Socket.IO protocol                  │
  │  • Extract event type + payload              │
  │  • Handle binary frames                      │
  └────────────────────┬─────────────────────────┘
                       │
                       │  Structured events
                       ▼
Layer 4: Bridge
───────────────
  ┌──────────────────────────────────────────────┐
  │       BrowserBridge                          │
  │  • Normalize event format                    │
  │  • Add metadata (source=cdp)                 │
  │  • Publish to EventBus                       │
  └────────────────────┬─────────────────────────┘
                       │
                       │  EventBus events
                       ▼
  ┌──────────────────────────────────────────────┐
  │              EventBus → EventStore            │
  └──────────────────────────────────────────────┘

Advantages:
───────────
  • No CORS issues
  • No proxy needed
  • Captures all frames
  • Low latency
  • Browser-level reliability
```

### 5.2 Fallback WebSocket Feed

```
If CDP unavailable:
───────────────────
  ┌──────────────────────────────────────────────┐
  │  Direct WebSocket Connection                 │
  │  (websocket_feed.py)                         │
  │                                              │
  │  • Connect to wss://rugs.fun/...             │
  │  • Parse Socket.IO protocol                  │
  │  • Publish to EventBus                       │
  └────────────────────┬─────────────────────────┘
                       │
                       │  Same event format
                       ▼
  ┌──────────────────────────────────────────────┐
  │            EventBus → EventStore              │
  └──────────────────────────────────────────────┘

Fallback Triggers:
──────────────────
  • CDP connection fails
  • Browser not available
  • --no-cdp flag
  • Testing/development

Source Tagging:
───────────────
  • CDP events: source="cdp"
  • Fallback events: source="public_ws"
  • Stored in Parquet for provenance
```

---

## 6. Trading & Action Flow

### 6.1 User Trade Flow (Buy/Sell)

```
┌─────────────────────────────────────────────────────────────┐
│                    MinimalWindow (UI)                       │
│  User clicks BUY button                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  self._on_buy_clicked()
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               TradeManager                                  │
│  1. Validate trade (balance, game state)                    │
│  2. Create trade request                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  trade_data = {
                         │    action: "buy",
                         │    amount: Decimal("0.01"),
                         │    client_ts: time.time()
                         │  }
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      EventBus                               │
│  event_bus.publish(Events.TRADE_BUY, trade_data)            │
└────────┬────────────────────────────────────────────────────┘
         │
         ├───────────────────────┬────────────────────────────┐
         │                       │                            │
         ▼                       ▼                            ▼
┌────────────────┐    ┌────────────────────┐    ┌────────────────────┐
│  EventStore    │    │  GameState         │    │  BrowserBridge     │
│  (Log action)  │    │  (Optimistic       │    │  (Execute trade)   │
│                │    │   update)          │    │                    │
│  doc_type=     │    │                    │    │  Send WebSocket:   │
│  player_action │    │  Reduce balance    │    │  "placeOrder"      │
└────────────────┘    └────────────────────┘    └────────┬───────────┘
                                                          │
                                                          │  WebSocket
                                                          ▼
                                            ┌──────────────────────────┐
                                            │  rugs.fun Server         │
                                            │  • Validate order        │
                                            │  • Execute trade         │
                                            │  • Broadcast result      │
                                            └────────────┬─────────────┘
                                                         │
                                                         │  "playerUpdate"
                                                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   BrowserBridge                             │
│  Receives playerUpdate from server                          │
│  event_bus.publish(Events.PLAYER_UPDATE, server_state)      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              LiveStateProvider                              │
│  • Compare server vs local state                            │
│  • Reconcile differences                                    │
│  • Update GameState with server truth                       │
│  • Calculate latency                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  event_bus.publish(Events.TRADE_CONFIRMED, ...)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   MinimalWindow                             │
│  • Update UI with confirmed state                           │
│  • Show latency metrics                                     │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Latency Tracking

```
Latency Tracking Chain:
═══════════════════════

  1. Client Action
     ─────────────
       client_ts = time.time()  # 1234567890.123
       │
       ▼
       Trade request created

  2. Server Receipt
     ──────────────
       server_ts = server_time  # 1234567890.245
       send_latency = server_ts - client_ts  # 122ms
       │
       ▼
       Server processes

  3. Confirmation
     ────────────
       confirmed_ts = time.time()  # 1234567890.456
       confirm_latency = confirmed_ts - server_ts  # 211ms
       total_latency = confirmed_ts - client_ts    # 333ms
       │
       ▼
       UI updated

Storage:
────────
  All timestamps in player_action doc_type:
    • client_ts: button click time
    • server_ts: server process time
    • confirmed_ts: confirmation time
    • send_latency: client → server
    • confirm_latency: server → confirmation
    • total_latency: full round-trip
```

---

## 7. State Management

### 7.1 GameState Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    GameState                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Core State (_state):                                       │
│    • balance: Decimal                                       │
│    • position: {qty, entry_price, ...}                      │
│    • sidebet: {type, amount, ...}                           │
│    • current_tick: int                                      │
│    • current_price: Decimal                                 │
│    • game_id: str                                           │
│    • game_active: bool                                      │
│    • rugged: bool                                           │
│    • phase: str                                             │
│                                                             │
│  Statistics (_stats):                                       │
│    • total_trades: int                                      │
│    • winning_trades: int                                    │
│    • total_pnl: Decimal                                     │
│    • max_drawdown: Decimal                                  │
│                                                             │
│  History (bounded deques):                                  │
│    • _history: deque[StateSnapshot] (max 1000)             │
│    • _transaction_log: deque[dict] (max 1000)              │
│    • _closed_positions: deque[dict] (max 500)              │
│                                                             │
│  Observers (dict):                                          │
│    • StateEvents.BALANCE_CHANGED → [callbacks]             │
│    • StateEvents.POSITION_OPENED → [callbacks]             │
│                                                             │
│  Thread Safety: threading.RLock()                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Live State Reconciliation

```
┌─────────────────────────────────────────────────────────────┐
│           LiveStateProvider                                 │
│  Purpose: Reconcile local optimistic state with server      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │  Subscribes to PLAYER_UPDATE
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  On playerUpdate event:                                     │
│  1. Extract server state:                                   │
│     • server_balance = data["cash"]                         │
│     • server_position = data["positionQty"]                 │
│  2. Get local state:                                        │
│     • local_balance = game_state.balance                    │
│     • local_position = game_state.position                  │
│  3. Compare:                                                │
│     • balance_diff = abs(server_balance - local_balance)    │
│     • position_diff = abs(server_position - local_qty)      │
│  4. If diff > threshold:                                    │
│     • Log reconciliation                                    │
│     • game_state.reconcile_with_server(server_state)        │
│     • Publish STATE_RECONCILED                              │
└─────────────────────────────────────────────────────────────┘

Reconciliation Rules:
═════════════════════
  Server State = ALWAYS TRUTH
  ────────────────────────────
  • Server balance overrides local
  • Server position overrides local
  • Server timestamps authoritative
  • Local = optimistic UI only

When to Reconcile:
──────────────────
  • Every playerUpdate event
  • After trade confirmation
  • On game start/end
  • After rug event
```

---

## 8. Vector Indexing & RAG

### 8.1 ChromaDB Integration

```
┌─────────────────────────────────────────────────────────────┐
│      Parquet Files (Canonical Truth)                       │
│      ~/rugs_data/events_parquet/**/*.parquet                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Query events
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          VectorIndexer                                      │
│  1. Read from Parquet (DuckDB)                              │
│  2. Chunk events                                            │
│  3. Generate embeddings (sentence-transformers)             │
│  4. Upsert to ChromaDB                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Embeddings + metadata
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  ChromaDB (~/Desktop/claude-flow/rag-pipeline/storage/)     │
│  Collection: rugs_events                                    │
│  Documents:                                                 │
│    • id: event_id                                           │
│    • embedding: [0.1, 0.2, ...] (384-dim)                   │
│    • metadata: {doc_type, game_id, tick, ...}              │
│    • document: JSON string                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  Query interface
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Query Paths                                 │
│                                                             │
│  A. RAG Agent (claude-flow rugs-expert):                    │
│     • Natural language query                                │
│     • Vector similarity search                              │
│     • Return relevant events                                │
│                                                             │
│  B. Protocol Explorer UI:                                   │
│     • Search by event type                                  │
│     • Filter by game_id, tick                               │
│     • Semantic search                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Vector Index Rebuild

```
Vector Index Rebuild Process:
═════════════════════════════

  Why Rebuild?
  ────────────
    • ChromaDB is DERIVED from Parquet
    • Parquet = canonical truth
    • Index can be rebuilt anytime
    • Safe to delete and regenerate

  How to Rebuild?
  ───────────────
    1. Delete old ChromaDB collection
    2. Create fresh collection
    3. Query all events from Parquet
    4. Chunk and embed in batches
    5. Upsert to ChromaDB

  CLI Command:
  ────────────
    vectra-player index build --full
```

---

## 9. Testing & CI/CD

### 9.1 Test Structure

```
src/tests/
├── conftest.py              # Shared fixtures
├── test_core/               # Core components
│   ├── test_event_bus.py
│   ├── test_game_state.py
│   └── test_trade_manager.py
├── test_services/           # Services
│   ├── test_event_store.py
│   ├── test_vector_indexer.py
│   └── test_live_state_provider.py
├── test_models/             # Data models
├── test_bot/                # Bot logic
├── test_ui/                 # UI components
└── test_integration/        # End-to-end tests
```

### 9.2 CI/CD Pipeline

```
Developer pushes code
         │
         ▼
  ┌────────────────┐
  │  CI Workflow   │  ← Tests (Python 3.11, 3.12)
  └────────┬───────┘
           │
  ┌────────────────┐
  │ Quality Check  │  ← Ruff linting + formatting
  └────────┬───────┘
           │
  ┌────────────────┐
  │ Security Scan  │  ← CodeQL + Bandit
  └────────┬───────┘
           │
  ┌────────────────┐
  │ PR Review      │  ← Automated review
  └────────┬───────┘
           │
           ▼
    All checks pass ✓
         │
         ▼
    Merge to main
```

### 9.3 Pre-commit Hooks

```
Pre-commit Flow:
════════════════

  Developer: git commit -m "..."
         │
         ▼
  ┌─────────────────────────────────────┐
  │  Pre-commit hooks                   │
  ├─────────────────────────────────────┤
  │  1. Ruff linting (auto-fix)         │
  │  2. Ruff formatting                  │
  │  3. End-of-file fixer                │
  │  4. Trailing whitespace removal      │
  │  5. YAML validation                  │
  │  6. TOML validation                  │
  │  7. Merge conflict detection         │
  │  8. Large file check (1MB max)       │
  └────────────┬────────────────────────┘
               │
               │  All pass?
               ▼
         ┌─────────────┐
         │  Yes → Commit│
         └─────────────┘
```

---

## Summary

This document provides comprehensive ASCII flowcharts for all major VECTRA-PLAYER processes:

1. **Application Lifecycle** - Startup, initialization, shutdown sequence
2. **Event-Driven Architecture** - EventBus pub/sub pattern and event categories
3. **Data Flow Pipeline** - WebSocket → EventBus → EventStore → Parquet flow
4. **Live vs Replay Mode** - Different data sources and operational modes
5. **Browser Automation** - CDP integration for WebSocket capture
6. **Trading & Action Flow** - User actions, bot trading, latency tracking
7. **State Management** - GameState structure and reconciliation
8. **Vector Indexing & RAG** - ChromaDB integration for AI agents
9. **Testing & CI/CD** - Test structure, workflows, and quality gates

**Key Architectural Principles:**

- **Event-driven architecture**: EventBus is the communication backbone
- **Single writer pattern**: EventStore is the only writer to Parquet
- **Server-authoritative state**: LiveStateProvider reconciles with server
- **Parquet as canonical truth**: Vector indexes are derived and rebuildable
- **Thread-safe operations**: RLocks and weak references prevent issues
- **Bounded memory**: Deques with maxlen prevent unbounded growth

**Related Documentation:**

- `README.md` - Project overview and quick start
- `CLAUDE.md` - Development context and architecture
- `CI_CD_GUIDE.md` - Detailed CI/CD documentation
- `WORKFLOW_ARCHITECTURE.md` - Workflow and automation details
- `ONBOARDING.md` - Developer onboarding guide

**For Developers:**

Use these flowcharts to:
- Understand system architecture
- Trace data flow through components
- Debug issues by following process paths
- Design new features that fit the architecture
- Onboard new team members

---

*Last Updated: December 29, 2025*
*Version: 1.0.0*
