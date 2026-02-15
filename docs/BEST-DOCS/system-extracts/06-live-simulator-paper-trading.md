# System 06: Live Simulator / Paper Trading Engine (Agnostic Revision)

Legacy source basis: `VECTRA-PLAYER`

## Legacy Extraction Summary

Current live simulator consumes provider feed ticks, runs strategy checks per tick, and emits session updates over Socket.IO.

Representative evidence:

```python
# src/recording_ui/services/live_backtest_service.py:297-303
from sources.websocket_feed import WebSocketFeed
self.ws_feed = WebSocketFeed(log_level="INFO")
self.ws_feed.on("signal", self._on_game_tick)
```

```python
# src/recording_ui/services/live_backtest_service.py:384-392
if self.socketio:
    self.socketio.emit(
        "live_tick",
        {"tick": tick_data, "session": session.to_dict()},
        room=session_id,
    )
```

```python
# src/recording_ui/services/live_backtest_service.py:476-487
if self.real_execution_enabled and self.execution_bridge:
    self._execute_in_async_loop(
        self.execution_bridge.execute_sidebet(Decimal(str(bet_size)))
    )
```

## Agnostic Target Boundary

Split into three layers:

- feed adapter: provider-specific intake + normalization
- simulation engine: strategy + paper wallet logic
- delivery adapter: websocket/SSE/event-bus fanout

Real-money execution should be a separate service, not a mode toggle inside simulator.

## Target Contract (Recommended)

- `POST /live-sim/sessions`
- `GET /live-sim/sessions/{id}`
- `POST /live-sim/sessions/{id}/stop`
- `GET /live-sim/sessions/{id}/stream`

Session response should include:

- wallet
- active bets
- cumulative stats
- connection state
- source metadata

## Cleanup Checklist

1. Remove direct provider websocket dependency from core simulator.
2. Remove real execution path from simulator process.
3. Replace framework singleton state with external session store.
4. Introduce feed-sequence integrity checks and replay support.
5. Add explicit event schema for outbound `live_tick` messages.

## Migration Notes

- Keep paper-trading behavior deterministic where possible for replay/debug mode.
- Keep per-session room/channel model; it maps well to multi-user dashboards.
