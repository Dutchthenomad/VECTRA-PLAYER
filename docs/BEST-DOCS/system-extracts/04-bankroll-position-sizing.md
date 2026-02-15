# System 04: Bankroll + Position Sizing Service (Agnostic Revision)

Legacy source basis: `VECTRA-PLAYER`

## Legacy Extraction Summary

Current implementation supports fixed, dynamic, drawdown-adjusted, and Kelly-based sizing in one simulation service.

Representative evidence:

```python
# src/recording_ui/services/position_sizing.py:50-83
@dataclass
class WalletConfig:
    initial_balance: float = 0.1
    bet_sizes: list[float] = field(default_factory=lambda: [0.001, 0.001, 0.001, 0.001])
    use_dynamic_sizing: bool = False
    use_kelly_sizing: bool = False
    kelly_fraction: float = 0.25
```

```python
# src/recording_ui/services/position_sizing.py:279-292
def kelly_criterion(win_rate: float, payout_ratio: float = SIDEBET_PAYOUT) -> float:
    kelly = win_rate - (1 - win_rate) / payout_ratio
    return max(0.0, kelly)
```

```python
# src/recording_ui/services/position_sizing.py:422-456
if config.take_profit_target is not None:
    ...
if current_drawdown >= config.max_drawdown_pct:
    ...
```

## Agnostic Target Boundary

Make this a pure compute service with no UI assumptions and no local-data assumptions.

- Input:
  - normalized game outcome/tick dataset reference
  - simulation config
- Output:
  - metrics bundle
  - equity/drawdown series
  - run metadata

## Target Contract (Recommended)

- `POST /bankroll/simulations`
- `GET /bankroll/simulations/{run_id}`
- `GET /bankroll/kelly?win_rate=&payout=`

Run request example:

```json
{
  "dataset_id": "games-v2026-02-12",
  "config": {
    "initial_balance": 0.1,
    "entry_tick": 200,
    "bet_sizes": [0.001, 0.001, 0.001, 0.001],
    "use_kelly_sizing": true,
    "kelly_fraction": 0.25
  }
}
```

## Cleanup Checklist

1. Remove direct dataframe loading from local repo paths.
2. Accept dataset references or inline canonicalized data payloads.
3. Add deterministic seed option for reproducibility.
4. Emit complete run provenance (`config_hash`, dataset id, engine version).
5. Keep business math in a pure module with test vectors.

## Migration Notes

- This module is a good candidate for headless batch execution and CI regression checks.
- Preserve current risk controls; promote them into explicit policy fields.
