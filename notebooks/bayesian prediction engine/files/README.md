# Bayesian Predictor MVP

Real-time game outcome predictions using mean-reversion analysis.

## Quick Start

```bash
# 1. Install dependencies
pip install websockets numpy

# 2. Start your Foundation WebSocket server (port 9000)
# (Assumes your existing ws://localhost:9000/feed is running)

# 3. Run the predictor
python -m bayesian_predictor.subscriber

# 4. Open UI in browser
# Open ui/index.html
```

## Architecture

```
rugs.fun WebSocket (ws://localhost:9000/feed)
        ↓
   subscriber.py (connects to WS, feeds events)
        ↓
   prediction_engine.py (orchestrates predictions)
        ↓
   ┌────┴────┐
   ↓         ↓
SimpleBayesianForecaster    HTTP API (:9001)
(mean reversion model)           ↓
                            ui/index.html
                         (displays predictions)
```

## How It Works

1. **Warmup Phase (first 5 games)**: Model observes outcomes to establish baseline
2. **Prediction Phase**: At game start (tick ≤5), model predicts:
   - Peak multiplier with confidence interval
   - Duration in ticks with confidence interval
   - Price direction (up/down/stable based on mean reversion)
3. **Scoring**: When game ends, prediction is scored against actuals

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /state` | Full engine state (game, prediction, stats, history) |
| `GET /prediction` | Current prediction only |
| `GET /stats` | Accuracy statistics |
| `GET /history` | Recent prediction history |

## Model Logic (from HAIKU findings)

The model uses these empirically observed patterns:

1. **Final Price Mean Reversion**: Prices oscillate around μ ≈ 0.0135
   - After crashes (final < 0.005) → expect recovery
   - After payouts (final > 0.019) → expect correction

2. **Peak Suppression After Payouts**: High finals → lower next peaks

3. **Duration Suppression After Big Peaks**:
   - After peak > 5x → ~45% shorter next game
   - After peak > 2x → ~20% shorter next game

## Expected Accuracy (from HAIKU)

| Metric | Target | Confidence |
|--------|--------|------------|
| Peak CI hit rate | >65% | Medium (64-72%) |
| Duration CI hit rate | >80% | High (81-88%) |
| Direction prediction | >65% | Medium |

## Files

```
bayesian_predictor/
├── __init__.py           # Package exports
├── game_state_manager.py # WebSocket event → game state
├── prediction_engine.py  # Forecaster + API server
├── subscriber.py         # WebSocket client, main entry
├── requirements.txt
├── README.md
└── ui/
    └── index.html        # Real-time visualization
```

## Integration with Foundation Framework

If using the Foundation subscriber pattern:

```python
from foundation.client import FoundationClient
from bayesian_predictor.subscriber import FoundationBayesianSubscriber

client = FoundationClient(url="ws://localhost:9000/feed")
subscriber = FoundationBayesianSubscriber(client, api_port=9001)
await client.connect()
```

## Next Steps

1. **Observe behavior**: Run for 20-50 games, watch CI hit rates
2. **If signal is real**: Integrate full forecaster from your uploaded files (Kalman fusion, ensemble)
3. **Add persistence**: Connect PredictionRecorder for SQLite storage
4. **ML enhancement**: Add concept drift detection, regime-aware weighting
