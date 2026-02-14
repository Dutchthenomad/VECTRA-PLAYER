# Real-Time Prediction Engine

Bayesian price prediction system using equilibrium tracking, adaptive AR modeling, and Kalman filtering.

## Components

### EquilibriumTracker
Tracks the "true" mean price and detects market regimes:
- **NORMAL**: Standard oscillation around equilibrium
- **SUPPRESSED**: Price below equilibrium (after large payouts)
- **INFLATED**: Price above equilibrium
- **VOLATILE**: High volatility period

Uses EWMA (Exponential Weighted Moving Average) for fast adaptation.

### DynamicWeighter
Modulates prediction confidence based on current regime:
- High confidence during SUPPRESSED regime (most predictable)
- Low confidence during VOLATILE regime
- Automatic volatility penalty

### StochasticOscillationModel
Learns price oscillation patterns using adaptive AR(p) model:
- Online RLS (Recursive Least Squares) parameter updates
- Automatic order selection via BIC criterion
- O(p²) per update - very fast

### BayesianForecaster
Fuses all components using Kalman filtering:
- Mean-reversion component
- AR oscillation component
- Peak effect (high peaks suppress next price)
- Duration effect
- 95% credible intervals

## Predictions

### Final Price
- **Weighted combination** of mean-reversion, AR forecast, peak/duration effects
- **Typical accuracy**: MAE < $0.0050 during stable regimes

### Peak Multiplier
- **Crash bonus**: Higher peaks after price crashes
- **Payout penalty**: Lower peaks after high payouts
- **Duration suppression**: Long games reduce next peak

### Duration
- **Inverse of peak**: High peaks = short duration
- **Volatility adjustment**: Longer games during volatile regimes

## Usage

1. Connect to Foundation Service (ws://localhost:9000/feed)
2. Engine auto-trains on each completed game
3. Predictions update after each game ends
4. View accuracy metrics in sidebar

## Data Requirements

Needs at least 10-20 completed games to calibrate models effectively.
Accuracy improves with more data (100+ games recommended).

## Algorithm References

Based on algorithms from `HAIKU-CRITICAL-FINDINGS.md`:
- Lines 560-637: EquilibriumTracker
- Lines 650-705: DynamicWeighter
- Lines 711-810: StochasticOscillationModel
- Lines 821-899: BayesianForecaster

## Files

```
prediction-engine/
├── index.html              # Main UI
├── main.js                 # Application logic
├── README.md               # This file
└── components/
    ├── equilibrium-tracker.js   # Equilibrium + regime detection
    ├── dynamic-weighter.js      # Confidence modulation
    ├── stochastic-oscillator.js # Adaptive AR model
    └── bayesian-forecaster.js   # Kalman filter fusion
```
