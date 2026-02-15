# System 05: Monte Carlo Comparison Engine (Agnostic Revision)

Legacy source basis: `VECTRA-PLAYER`

## Legacy Extraction Summary

Current Monte Carlo module runs multiple strategy configs and ranks them by performance/risk metrics.

Representative evidence:

```python
# src/recording_ui/services/monte_carlo_service.py:24-46
def create_strategy_configs(...):
    return {
        "fixed_baseline": SimulationConfig(...),
        "quarter_kelly": SimulationConfig(...),
        ...
    }
```

```python
# src/recording_ui/services/monte_carlo_service.py:256-265
best_by_metric = {
    "highest_mean": ...,
    "highest_median": ...,
    "highest_profit_prob": ...,
    "best_sortino": ...,
}
```

```python
# src/recording_ui/services/monte_carlo.py:551-565
var_95 = np.percentile(returns, 5)
var_99 = np.percentile(returns, 1)
cvar_95 = returns[returns <= var_95].mean() if np.any(returns <= var_95) else var_95
sortino = expected_return / downside_std if downside_std > 0 else 0
```

## Agnostic Target Boundary

Convert to async compute service with externalized workload control.

- API layer:
  - submit/poll/cancel jobs
- worker layer:
  - simulation execution
- result store:
  - structured metrics and sampled curves

## Target Contract (Recommended)

- `POST /mc/jobs`
- `GET /mc/jobs/{job_id}`
- `DELETE /mc/jobs/{job_id}`
- `GET /mc/jobs/{job_id}/result`

Job request example:

```json
{
  "strategies": ["fixed_baseline", "quarter_kelly", "theta_bayesian_conservative"],
  "iterations": 10000,
  "num_games": 500,
  "initial_bankroll": 0.1,
  "win_rate": 0.185,
  "seed": 42
}
```

## Cleanup Checklist

1. Remove absolute file path dependencies for volatility data.
2. Isolate strategy profile catalog from execution engine.
3. Add deterministic seeding support per job.
4. Add resource limits and timeout policy per job class.
5. Version metric schema (VaR/CVaR definitions must be stable).

## Migration Notes

- Keep current metric set; it is decision-useful and already broad.
- Promote comparison output to a common schema reusable by Explorer UI and reporting pipelines.
