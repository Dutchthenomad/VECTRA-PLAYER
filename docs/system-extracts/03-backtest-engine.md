# System 03: Backtest Engine (Agnostic Revision)

Legacy source basis: `VECTRA-PLAYER`

## Legacy Extraction Summary

Backtest is a sessioned playback simulator with tick-level control and strategy persistence.

Representative evidence:

```python
# src/recording_ui/app.py:364-387
@app.route("/api/backtest/start", methods=["POST"])
def api_start_backtest():
    strategy = ...
    session_id = service.start_playback(strategy)
    state = service.get_state(session_id)
```

```python
# src/recording_ui/services/backtest_service.py:358-395
def tick(self, session_id: str) -> dict | None:
    ...
    if game.current_tick >= strategy.get("entry_tick", 200) and game.phase == "active":
        self._check_bet_placement(state, strategy)
    game.current_tick += 1
```

```python
# src/recording_ui/services/backtest_service.py:29-30
ML_DIR = Path("/home/devops/Desktop/VECTRA-PLAYER/Machine Learning")
DEFAULT_STRATEGIES_DIR = ML_DIR / "strategies"
```

## Agnostic Target Boundary

Backtest service should be framework-agnostic and stateless at API tier.

- Domain engine:
  - tick simulation
  - outcome settlement
  - risk accounting
- Session manager:
  - external state store (Redis/Postgres)
- API adapter:
  - HTTP/gRPC wrapper only

## Target Contract (Recommended)

- `POST /backtest/sessions`
- `GET /backtest/sessions/{id}`
- `POST /backtest/sessions/{id}/tick`
- `POST /backtest/sessions/{id}/control`
- `DELETE /backtest/sessions/{id}`

Control payload:

```json
{ "action": "pause|resume|next|speed|stop", "value": 2.0 }
```

## Cleanup Checklist

1. Remove absolute strategy/data paths.
2. Move session state out of in-memory singleton.
3. Isolate deterministic split logic from transport layer.
4. Add idempotent command handling for control actions.
5. Add explicit dataset/version identifiers in every session state response.

## Migration Notes

- Keep deterministic validation split behavior; this supports reproducible testing.
- Keep per-tick stepping API; it is useful for UI debugging and bot explainability.
