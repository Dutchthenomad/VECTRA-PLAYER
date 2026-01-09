# Probabilistic Reasoning for Sidebet Optimization

## Core Problem Statement

**Given**: A rugs.fun game at tick `t` with observable price history `prices[0:t]`

**Find**: Optimal tick `t*` to maximize expected value of placing a 40-tick sidebet

**Constraint**: Sidebet wins if rug occurs in ticks `[t+1, t+40]`, loses otherwise

## 1. Bayesian Survival Analysis

### Mathematical Foundation

**Survival Function**:
```
S(t) = P(game survives past tick t)
```

**Hazard Rate**:
```
h(t) = P(rug at tick t | survived to t)
     = lim[Δt→0] P(t ≤ T < t+Δt | T ≥ t) / Δt
```

**Relationship**:
```
S(t) = exp(-∫[0,t] h(u) du)
```

### Empirical Estimation

From 568 games, we compute:

```python
# Count rugs at each tick
rug_counts[t] = sum(1 for game in games if game.rug_tick == t)

# Count games surviving to each tick
survival_counts[t] = sum(1 for game in games if game.tick_count >= t)

# Hazard rate
h(t) = rug_counts[t] / survival_counts[t]
```

**Smoothing**: Apply moving average to reduce noise from small sample sizes at high ticks.

### Prediction

**Base Probability** (unconditional):
```
P(rug in [t, t+40]) = S(t) - S(t+40)
                     = P(survived to t) - P(survived to t+40)
```

**Conditional Probability** (with features):
```
P(rug in [t, t+40] | features) = BaseProb × AdjustmentFactor(features)
```

### Bayesian Update

**Prior**: Historical distribution of rug timing (survival function)

**Likelihood**: Feature-conditional rug probability

**Posterior**:
```
P(rug | features, age) ∝ P(features | rug) × P(rug | age)
```

**Feature Adjustments** (empirical priors):
- `rapid_fall = True`: Multiply by 2.0 (strong rug signal)
- `volatility_10 > 0.1`: Multiply by 1.5 (instability)
- `ticks_since_peak > 20`: Multiply by 1.3 (mean reversion)
- `distance_from_peak > 0.3`: Multiply by 1.2 (far from peak)
- `rapid_rise = True`: Multiply by 0.7 (momentum)

**Justification**: These multipliers are conservative Bayesian priors. They should be refined through:
1. Logistic regression on training data
2. Cross-validation to prevent overfitting
3. Information gain analysis to validate importance

## 2. Conditional Probability Analysis

### Joint Probability Decomposition

**Goal**: Estimate P(rug in window | age, price, volatility, ...)

**Method**: Empirical conditional frequency

```python
# Filter training data by conditions
filtered = training_df[
    (age >= age_min) & (age < age_max) &
    (price >= price_min) & (price < price_max)
]

# Conditional probability
P(rug | conditions) = mean(filtered['rug_in_window'])
```

### Independence Assumptions

**Naïve approach**: Treat features as independent
```
P(rug | f1, f2, ..., fn) ≈ P(rug) × ∏ P(fi | rug) / P(fi)
```

**Reality**: Features are correlated (e.g., volatility and ticks_since_peak)

**Solution**: Use empirical joint distribution or feature interaction terms

### Heatmap Interpretation

The age × price heatmap shows:
```
P(rug in 40 ticks | age ∈ [a1, a2], price ∈ [p1, p2])
```

**Usage**:
1. Locate current game state in heatmap
2. Read off probability
3. Compare to breakeven threshold (20% for 5x)
4. If above threshold → positive EV region

## 3. Expected Value Optimization

### EV Formula

**General Form**:
```
EV = ∑ P(outcome) × Value(outcome)
```

**Sidebet Specific**:
```
EV = P(win) × Payout - P(lose) × Bet
   = P(win) × (Bet × Multiplier) - (1 - P(win)) × Bet
   = Bet × [P(win) × Multiplier - (1 - P(win))]
   = Bet × [P(win) × (Multiplier + 1) - 1]
```

**Example** (5x payout, 0.001 SOL bet, P(win) = 0.25):
```
EV = 0.001 × [0.25 × 6 - 1]
   = 0.001 × [1.5 - 1]
   = 0.001 × 0.5
   = 0.0005 SOL
```

### Breakeven Analysis

**Breakeven condition**: EV = 0
```
0 = P(win) × (M + 1) - 1
P(win) = 1 / (M + 1)
```

**Results**:
- 5x payout: P(win) > 16.67%
- 10x payout: P(win) > 9.09%
- 20x payout: P(win) > 4.76%

### Optimal Stopping Problem

**Question**: At which tick `t*` should we place the sidebet?

**Formulation**:
```
t* = argmax[t] EV(t)
   = argmax[t] [P(rug in [t, t+40]) × (M + 1) - 1]
```

**Algorithm**:
1. For each tick t ∈ [50, 500]:
   - Extract features at tick t
   - Predict P(rug in [t, t+40])
   - Compute EV
2. Select t* with maximum EV

**Constraints**:
- Must have enough price history (t > 50)
- Don't wait too long (diminishing returns after t > 500)

## 4. Feature Importance (Information Gain)

### Entropy and Information Theory

**Entropy** (uncertainty in target):
```
H(Y) = -∑ P(y) × log₂(P(y))
```

For binary target (rug or no rug):
```
H(Y) = -[p × log₂(p) + (1-p) × log₂(1-p)]
```

**Conditional Entropy** (uncertainty given feature):
```
H(Y | X) = ∑ P(x) × H(Y | X=x)
```

**Information Gain**:
```
IG(Y, X) = H(Y) - H(Y | X)
```

**Interpretation**: How much does knowing feature X reduce uncertainty about Y?

### Example Calculation

**Baseline entropy** (p_rug = 0.174):
```
H(Y) = -[0.174 × log₂(0.174) + 0.826 × log₂(0.826)]
     ≈ 0.664 bits
```

**Conditional entropy** (if we know game age):
```
H(Y | age) = ∑ P(age_bin) × H(Y | age_bin)
```

If knowing age reduces entropy to 0.50 bits:
```
IG(Y, age) = 0.664 - 0.50 = 0.164 bits
```

**Ranking**: Features with higher IG are more predictive

### Why Age is Top Feature

Intuition: Older games have higher rug probability (empirically observed)

**Conditional probabilities**:
- P(rug | age < 100) ≈ 14%
- P(rug | age ∈ [200, 300]) ≈ 20%
- P(rug | age > 400) ≈ 25%

**Information gain**: Age partitions data into high-entropy (early) and low-entropy (late) regions

## 5. Kelly Criterion

### Derivation

**Goal**: Maximize expected log wealth growth

**Objective**:
```
max E[log(1 + f × G)]
```

where:
- f = fraction of bankroll to bet
- G = net gain (multiplier for win, -1 for loss)

**Solution** (for binary outcome):
```
f* = (p × b - q) / b
```

where:
- p = P(win)
- q = 1 - p
- b = net payout odds (M - 1)

### Example (5x payout, P(win) = 0.25)

```
b = 5 - 1 = 4
p = 0.25
q = 0.75

f* = (0.25 × 4 - 0.75) / 4
   = (1.0 - 0.75) / 4
   = 0.25 / 4
   = 0.0625
```

**Interpretation**: Bet 6.25% of bankroll

### Practical Adjustments

**Problem**: Full Kelly is aggressive (high variance)

**Solutions**:
1. **Fractional Kelly**: Use f* / 2 or f* / 4
2. **Empirical estimates**: P(win) has uncertainty → reduce bet size
3. **Risk tolerance**: Adjust for personal variance preferences

**Recommended**: Use 1/4 Kelly for conservative sizing

## 6. Regime Detection (HMM-like)

### Hidden Markov Model Intuition

**States** (hidden):
- STABLE: Low rug risk
- UNSTABLE: Moderate rug risk
- CRITICAL: High rug risk

**Observations**: Price, volatility, momentum, etc.

**Transition probabilities**:
```
P(state_t+1 | state_t, observations)
```

### Simplified Classification

Instead of full HMM, use rule-based classification:

```python
if rapid_fall and volatility_10 > 0.15 and distance_from_peak > 0.3:
    regime = CRITICAL  # Very high rug risk
elif volatility_10 > 0.10 or rapid_fall or ticks_since_peak > 30:
    regime = UNSTABLE  # Moderate rug risk
else:
    regime = STABLE    # Low rug risk
```

### Usage

**Regime-conditional probabilities**:
- P(rug | STABLE) ≈ 10-15%
- P(rug | UNSTABLE) ≈ 20-25%
- P(rug | CRITICAL) ≈ 30-40%

**Decision rule**:
- Only place sidebets in UNSTABLE or CRITICAL regimes

## 7. Combining All Methods

### Multi-Model Ensemble

**Prediction pipeline**:
1. **Survival model**: Compute base P(rug | age)
2. **Feature adjustment**: Apply Bayesian multipliers
3. **Regime detection**: Check if in favorable regime
4. **Conditional probability**: Validate against historical conditionals
5. **Final decision**: Combine predictions (e.g., weighted average)

### Example Decision Flow

```python
# Step 1: Base probability
p_base = survival_model.predict(tick=250, window=40)

# Step 2: Feature adjustment
features = extract_features(prices, tick=250)
p_adjusted = p_base * feature_adjustment(features)

# Step 3: Regime check
regime = detect_regime(features)
if regime == "STABLE":
    p_adjusted *= 0.8  # Reduce confidence

# Step 4: Validate against conditionals
p_conditional = conditional_rug_probability(
    training_df,
    {'age': (240, 260), 'volatility_10': (features.volatility_10 - 0.02, features.volatility_10 + 0.02)}
)

# Step 5: Ensemble (weighted average)
p_final = 0.5 * p_adjusted + 0.5 * p_conditional

# Step 6: Decision
ev = expected_value(p_final, payout_multiplier=5)
if ev > 0 and p_final > breakeven_probability(5):
    action = PLACE_SIDEBET
    kelly_frac = kelly_criterion(p_final, 5) / 4  # Use 1/4 Kelly
    bet_size = bankroll * kelly_frac
else:
    action = HOLD
```

## 8. Model Validation

### Cross-Validation Strategy

**Problem**: We have limited data (568 games)

**Solution**: K-fold cross-validation

```python
from sklearn.model_selection import KFold

kf = KFold(n_splits=5, shuffle=True, random_state=42)

for train_idx, test_idx in kf.split(games_df):
    train_games = games_df.iloc[train_idx]
    test_games = games_df.iloc[test_idx]
    
    # Fit model on train
    model = BayesianSurvivalModel(train_games)
    
    # Evaluate on test
    for game in test_games:
        predicted_p = model.predict(...)
        actual_rug = ...
        # Compute calibration metrics
```

### Calibration Metrics

**Brier Score** (mean squared error of probabilities):
```
BS = mean((p_predicted - actual_outcome)²)
```

**Log Loss** (cross-entropy):
```
LL = -mean(actual × log(p) + (1-actual) × log(1-p))
```

**Calibration Plot**:
- Bin predictions by decile (0-10%, 10-20%, ..., 90-100%)
- For each bin, compute actual rug rate
- Plot predicted vs actual
- Perfect calibration → 45° line

### Backtesting

**Procedure**:
1. For each historical game:
   - Replay tick-by-tick
   - At each tick, predict P(rug in 40 ticks)
   - If P(rug) > threshold, simulate sidebet placement
   - Record outcome (win/loss)
2. Compute aggregate metrics:
   - Total bets placed
   - Win rate
   - Average EV
   - Sharpe ratio (return / volatility)

**Expected Results** (based on 19.9% late-game win rate):
- Bets placed: ~150-200 (out of 568 games)
- Win rate: ~20%
- Avg EV per bet: ~0.0 SOL (break-even)
- Improvement needed: Feature refinement, better timing

## 9. Limitations and Future Work

### Current Limitations

1. **Sample size**: 568 games may not capture rare events (instarugs, god candles)
2. **Feature engineering**: Hand-crafted features may miss complex patterns
3. **Independence assumptions**: Features are correlated, not independent
4. **Stationarity**: Game mechanics may change (updates, patches)

### Proposed Improvements

1. **More data**: Capture 1000+ games for better hazard rate estimation
2. **Machine learning**: Train gradient boosting or neural network for P(rug)
3. **Feature interactions**: Include polynomial features (age × volatility, etc.)
4. **Online learning**: Update model in real-time as new games complete
5. **Multi-objective optimization**: Balance EV, variance, and max drawdown

### Advanced Topics

**Gaussian Processes** for survival analysis:
```
h(t) ~ GP(μ(t), k(t, t'))
```

**Reinforcement Learning**:
- State: (age, price, features)
- Action: HOLD or PLACE_SIDEBET
- Reward: Actual payout - bet
- Policy: π(a | s) trained with PPO/DQN

**Causal Inference**:
- Does high volatility CAUSE rugs, or is it just correlated?
- Use do-calculus to identify causal effects
- Apply propensity score matching

---

**Last Updated**: January 7, 2026  
**Author**: rugs-expert (Claude Code Agent)  
**Status**: Research document - requires empirical validation
