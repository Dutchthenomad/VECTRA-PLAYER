# System 02: Explorer UI + Analytics Orchestration (Agnostic Revision)

Legacy source basis: `VECTRA-PLAYER`

## Legacy Extraction Summary

Explorer currently combines three concerns in one Flask surface:

- strategy exploration
- bankroll simulation config/execution
- Monte Carlo configuration/execution

Representative evidence:

```python
# src/recording_ui/app.py:541-564
@app.route("/api/explorer/data")
def api_explorer_data():
    data = explorer_data.get_explorer_data(entry_tick, num_bets, limit)
    return jsonify(data)
```

```python
# src/recording_ui/app.py:597-675
@app.route("/api/explorer/simulate", methods=["POST"])
def api_explorer_simulate():
    config = position_sizing.WalletConfig(...)
    games_df = explorer_data.load_games_df()
    result = position_sizing.run_simulation(games_df, config)
```

```python
# src/recording_ui/app.py:797-830
@app.route("/api/explorer/monte-carlo", methods=["POST"])
def api_explorer_monte_carlo():
    results = run_strategy_comparison(...)
    return jsonify(results)
```

## Agnostic Target Boundary

Explorer should become a pure UI module backed by a query API/BFF.

- Explorer UI:
  - filter and parameter controls
  - result rendering
  - save/export actions
- API/BFF:
  - fans out to dedicated analysis services
  - unifies response schemas for UI

## Target Contract (Recommended)

### Explorer BFF endpoints

- `GET /explorer/strategy?entry_tick=&num_bets=&limit=`
- `POST /explorer/bankroll/run`
- `POST /explorer/monte-carlo/run`
- `GET /explorer/jobs/{job_id}`

### UI-safe response envelope

```json
{
  "version": "v1",
  "status": "ok",
  "request_id": "uuid",
  "data": {}
}
```

## Cleanup Checklist

1. Remove direct service imports from monolithic app handlers.
2. Move Explorer page JS to call a BFF namespace only.
3. Convert long-running Monte Carlo to async job flow.
4. Define versioned schemas for each result block.
5. Separate strategy-save from simulation-run side effects.

## Migration Notes

- Keep existing tab model; it is already a good mental model.
- Avoid hard-coding dataset path assumptions in UI labels.
- Ensure all simulated outputs include run metadata for reproducibility.
