# ML/RL Optimization Guide for Rugs.fun Crypto Trading Bot

Your 736% training return collapsing to failure in deployment is a textbook case of **reward hacking combined with observation normalization mismatch**. This comprehensive guide addresses each priority area with state-of-the-art techniques, tools, and implementation patterns specifically designed for your SB3 PPO + Gymnasium stack with 929 recorded games and 204 human demonstrations.

---

## 1. Reward shaping and hacking prevention (CRITICAL)

The core insight: your model found shortcuts in training that don't generalize. **Potential-Based Reward Shaping (PBRS)** is the gold-standard solution—it provides dense learning signals without altering optimal policies. The mathematical guarantee from Ng et al. (1999) ensures that if shaping rewards follow `F(s,a,s') = γΦ(s') - Φ(s)` where Φ is a potential function, policy invariance is preserved.

For your Rugs.fun game with the **25-50x optimal entry zone**, design a potential function encoding domain knowledge: potential increases as multiplier approaches 25-50x, peaks around 37.5x, and decays afterward. Critical rule: **terminal state potentials must be zero** to maintain policy invariance. Recent research on Bootstrapped Reward Shaping (BSRS, 2025) shows that using the agent's own value function as the potential works well for complex environments.

**Reward hacking detection** has achieved 78.4% precision in automated detection. Monitor for three warning signals: action repetition rate exceeding 90%, reward component imbalance where one source dominates 80%+ of total reward, and proxy-true divergence where training reward improves while validation metrics decline. Your 736% training return failing in deployment is a classic detection signal—implement component decomposition tracking each reward source separately.

### Prioritized implementation

1. **Implement PBRS wrapper** encoding the 25-50x zone with γ*Φ(s') - Φ(s) shaping
2. **Decompose rewards** into separate tracked components (PnL, timing quality, survival bonus)
3. **Add caps** to prevent exploitation: clip each component to ±2.0
4. **Monitor action distributions** via callbacks detecting repetition patterns
5. **Use hindsight attribution** for the tick 100→200 credit assignment: increase `gae_lambda` toward 0.98-0.99

### Tools and libraries

| Tool | Purpose |
|------|---------|
| **imitation** library | AIRL, GAIL for learning reward functions from demos |
| **TensorBoard/W&B** | Reward component visualization |
| Built-in SB3 GAE | Set `gae_lambda=0.95-0.99` for temporal credit assignment |

---

## 2. Sim-to-real gap resolution (HIGH)

Three major factors cause trained agents to fail in real markets according to FinRL-Meta research: **low signal-to-noise ratio** in financial data, **survivorship bias** in training data, and **backtesting overfitting**. For your specific 736% training failure, the most likely culprits are VecNormalize statistics not saved/loaded correctly, action interpretation differences, and timing discrepancies.

**VecNormalize is the #1 suspect**. The model learned on normalized observations and is receiving differently-scaled inputs in deployment. You MUST save normalization statistics with `env.save("vec_normalize.pkl")` after training, load with `VecNormalize.load()`, and crucially set `env.training = False` and `env.norm_reward = False` at inference time. This single fix resolves the majority of sim-to-real failures.

**Domain randomization** bridges the gap by training with randomized latency (30-100ms delays), transaction costs (±10-20% variance), and slippage. Research on market making with RL shows that ignoring latency leads to unintended order cancellations. Create a wrapper that randomizes these parameters each episode reset.

### Debugging checklist

1. **Verify VecNormalize**: Print `obs_rms.mean` and `obs_rms.var` from saved stats vs deployment
2. **Compare observation shapes**: `observation_space.shape` must match exactly, including dtype (float32 vs float64)
3. **Replay validation**: Feed identical observations to both training and deployment environments, compare outputs
4. **Use `deterministic=True`** for inference: `model.predict(obs, deterministic=True)`
5. **Add domain randomization** to training for robustness

### Implementation pattern

```python
# CRITICAL: Correct save/load pattern
# Training
model.save("ppo_trading")
env.save("vec_normalize.pkl")  # Must save!

# Deployment
env = VecNormalize.load("vec_normalize.pkl", env)
env.training = False  # Freeze stats
env.norm_reward = False  # Not needed at inference
model = PPO.load("ppo_trading", env=env)
action, _ = model.predict(obs, deterministic=True)
```

---

## 3. Imitation learning from 204 demonstrations (HIGH)

**204 samples is borderline sufficient** for Behavioral Cloning pretraining, especially if they capture the optimal 25-50x entry zone behaviors. Research shows BC can work with as few as 10-50 demonstrations on simpler tasks. The recommended approach is **BC pretraining → PPO fine-tuning**, which consistently outperforms RL from scratch according to PIRLNav (CVPR 2023) findings that "RL from scratch fails to get off-the-ground" while BC pretraining provides crucial initialization.

For handling **suboptimal demonstrations** (since human traders aren't perfect), use confidence-weighted imitation. Assign higher weights to demos that entered the 25-50x zone and survived rug pulls. The Discriminator-Weighted BC (DWBC) approach from ICML 2022 trains a discriminator to distinguish good vs. bad demonstrations, using outputs as BC weights.

**Data augmentation** can expand your 204 samples to 500-1000+: add Gaussian noise to observations (σ=0.005-0.01), time-shift sequences by ±2 ticks, and scale multiplier growth rates by random factors (0.9-1.1). The `imitation` library from HumanCompatibleAI integrates directly with SB3 for BC, GAIL, DAgger, and AIRL.

### Recommended pipeline

1. **Filter demonstrations**: Keep only trades entering 25-50x zone
2. **Assign confidence scores**: 1.0 for optimal zone + survival, 0.7 for survival only, 0.3 for rug pulls (learning what NOT to do)
3. **Augment 3-5x** with noise injection and time warping
4. **BC pretrain** with L2 regularization (l2_weight=0.001-0.01) to prevent overfitting
5. **PPO fine-tune** with low learning rate (1e-5 to 3e-5) to preserve pretrained knowledge

### Tools

| Library | Purpose |
|---------|---------|
| **imitation** | BC, GAIL, AIRL integration with SB3 |
| **d3rlpy** | Alternative with scikit-learn-style API |

---

## 4. Stable Baselines 3 and PPO optimization (HIGH)

**PPO is the correct choice** for your trading bot—it supports both discrete and continuous action spaces, parallelizes excellently, and provides the most stable training. Research from financial RL benchmarks shows PPO provides consistent results while SAC shows higher variance despite occasional peak returns. TD3 underperforms in trading contexts due to its deterministic policy. For discrete trading actions (bet/hold/cash_out), **PPO is the only viable choice** among these three.

**Key insight for cloud training**: PPO with MLP policies runs primarily on CPU. SB3 documentation explicitly states "PPO is meant to be run primarily on the CPU, especially when you are not using a CNN." This means you can use high-core-count CPU instances (c6i.8xlarge at ~$1.36/hr) rather than expensive GPU instances. GPU becomes valuable only for RecurrentPPO/LSTM or larger networks.

For **parallel environment scaling**, use SubprocVecEnv with 8-16 environments—the sweet spot for most cloud instances. SubprocVecEnv provides true parallelism with near-linear scaling when env.step() takes >1ms (typical for trading simulations). Always wrap with VecNormalize for stable PPO training.

### Optimal hyperparameters for trading

| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| `learning_rate` | linear_schedule(3e-4) → 1e-5 | Decay over training |
| `n_steps` | 2048 | Match typical episode length |
| `batch_size` | 256 | Ensure n_steps*n_envs divisible |
| `n_epochs` | 10 | Reduce to 4 for faster iteration |
| `gamma` | 0.99 | Try 0.995 for longer horizons |
| `gae_lambda` | 0.95-0.99 | Higher for credit assignment |
| `clip_range` | 0.2 | Can use schedule |
| `ent_coef` | 0.01 | For exploration |
| `target_kl` | 0.015 | Early stopping on large KL |

### Cloud compute recommendations

| Provider | Instance | Price | Best For |
|----------|----------|-------|----------|
| **Thunder Compute** | A100 | $0.66-0.78/hr | Cheapest reliable |
| **Lambda Labs** | 1x A100 | $1.29/hr | RecurrentPPO/LSTM |
| **AWS EC2** | c6i.8xlarge (32 vCPU) | ~$1.36/hr | Parallel CPU training |

Training time estimate for 929 games (~1M steps): 2-4 hours with 16 parallel envs on 16-core CPU.

---

## 5. Gymnasium environment design (MEDIUM)

For your rug pull game with variable-length episodes, **use `terminated=True` for rug pull events** (natural episode end defined by the MDP where value of terminal state is zero) and **`truncated=True` only for artificial limits** (max episode length during training). This distinction is critical—when truncated, you must bootstrap from the last state's value estimate rather than setting next_value to zero.

**Observation space design** recommendation: start with **frame stacking** (8 historical timesteps via VecFrameStack) rather than LSTM. Research shows frame stacking remains competitive with LSTM for many tasks while being faster and simpler. Only switch to RecurrentPPO (sb3-contrib) if frame stacking underperforms and your environment has truly hidden state.

For **action space**, discrete is usually best for betting games: `Discrete(3)` for [hold, bet, cash_out] or MultiDiscrete for compound decisions (action type + bet size bucket). Use **MaskablePPO** from sb3-contrib for action masking when certain actions are invalid (can't cash out if not in game, can't bet with no balance).

### Key technical indicators for rug pull detection

- **Momentum**: RSI (14-period), Stochastic Oscillator
- **Trend**: MACD, EMA crossovers (5/20)
- **Volatility**: ATR, Bollinger Band width (critical for rug detection)
- **Derived**: `multiplier_velocity = multiplier.diff()`, `multiplier_acceleration = velocity.diff()`

### Normalization strategy

Use VecNormalize for all features with `clip_obs=10.0`. For manual preprocessing, use log returns (naturally bounded, stationary) for price features and normalize indicators to [-1, 1] based on known bounds (RSI/100, etc.).

---

## 6. Model validation and backtesting (MEDIUM)

Your 736% training return followed by deployment failure is a textbook case of **backtest overfitting**. Traditional train/test splits are insufficient. The state-of-the-art approach is **Combinatorial Purged Cross-Validation (CPCV)** from Marcos López de Prado, which creates multiple train/test combinations respecting chronology with demonstrably lower Probability of Backtest Overfitting (PBO).

**Walk-forward validation** with rolling windows is essential: divide your 929 games into overlapping train/validation segments, train on window_size games, validate on test_size games, then roll forward. Calculate Probability of Backtest Overfitting—target <10%.

### Metrics beyond reward

| Metric | Minimum | Good | Excellent |
|--------|---------|------|-----------|
| **Sharpe Ratio** | >1.0 | 1.5-2.0 | >2.0 |
| **Sortino Ratio** | >1.0 | 1.5-2.5 | >2.5 |
| **Max Drawdown** | <25% | <15% | <10% |
| **Profit Factor** | >1.2 | >1.5 | >2.0 |
| **Win Rate** | >45% | >50% | >55% |
| **PBO** | <25% | <15% | <10% |

### Safe deployment pattern

1. **Paper trading phase** (30+ days) with position limits (10-20% max per trade)
2. **Gradual rollout** with drawdown halts (pause at 15% drawdown)
3. **Multiple test periods** validating on different market regimes
4. **Continuous monitoring** with regime detection triggering retraining

---

## 7. Tools, libraries, and MCP servers (MEDIUM)

### Core RL stack

| Tool | Best For |
|------|----------|
| **Stable Baselines 3** | Your current stack—stable, well-documented |
| **sb3-contrib** | RecurrentPPO, MaskablePPO |
| **imitation** | BC, GAIL, AIRL for your demos |
| **d3rlpy** | Offline RL (CQL, IQL) for recorded data |
| **FinRL** | Full trading pipeline reference |
| **CleanRL** | Debugging, understanding implementations |

### Experiment tracking

| Tool | Purpose |
|------|---------|
| **Weights & Biases** | Best-in-class experiment tracking, RL dashboards |
| **TensorBoard** | Built into SB3, free, real-time |
| **MLflow** | Open source, model registry |
| **Optuna** | Hyperparameter optimization (integrates with SB3) |

### Backtesting and metrics

| Tool | Purpose |
|------|---------|
| **QuantStats** | Sharpe, Sortino, drawdown analysis |
| **Pyfolio** | Portfolio analytics tear sheets |
| **VectorBT** | Vectorized backtesting |

### Hugging Face resources

The Hugging Face ecosystem includes pre-trained Decision Transformer models (edbeeching/decision-transformer-gym-*) that can serve as initialization references, and the transformers library includes `DecisionTransformerModel` for implementation. MCP servers for ML development are available through Hugging Face Spaces including OpenAPI2MCP for creating custom MCP servers.

---

## 8. Advanced techniques (MEDIUM)

### Offline RL for your 929 recorded games

**d3rlpy with CQL or IQL** is the recommended approach for your offline data. CQL (Conservative Q-Learning) prevents overestimation on out-of-distribution actions while learning from existing data. IQL (Implicit Q-Learning) avoids querying OOD actions entirely, making it more stable.

The pattern: pretrain with offline RL on your 929 games, then transfer weights to PPO for online fine-tuning. This combines the sample efficiency of offline learning with the exploration benefits of online RL.

### Decision Transformers

Decision Transformers reframe RL as sequence modeling, conditioning on desired returns to generate actions. Recent research (Nov 2024) shows Decision Transformers initialized with pre-trained GPT-2 weights perform competitively against CQL/IQL for trading. Key advantage: they can extrapolate to achieve higher returns than seen in training by conditioning on ambitious target returns.

### Non-stationarity handling

Markets exhibit regime changes requiring adaptation. Implement **regime detection** by monitoring reward distribution shifts—when z-score of rolling mean exceeds 2.0 standard deviations from baseline, trigger retraining. For faster adaptation, consider **MAML (Model-Agnostic Meta-Learning)** which learns an initialization that can be fine-tuned with few samples from new regimes.

### Uncertainty quantification for "when NOT to trade"

Train an **ensemble of 3-5 critics** with different initializations. High disagreement (epistemic uncertainty) = abstain from trading. This directly addresses your question about teaching the model when NOT to trade. Combine with your sidebet predictor for hierarchical gating:

```python
if epistemic_uncertainty > threshold or sidebet_confidence < min_confidence:
    return "HOLD"  # Don't trade
else:
    action, _ = policy.predict(state)
    return action
```

---

## Addressing your 8 specific problems

### 1. Preventing new exploits with simplified rewards

Even with 2-component rewards, implement **reward capping** (clip each component to ±2.0), **component ratio monitoring** (alert when one component >80% of total), and **action distribution tracking** (detect >90% repetition). Use PBRS to add shaping without changing optimal policy. The key is monitoring multiple metrics during training, not just total reward.

### 2. Is 204 demos enough for IL?

**Yes, with augmentation**. Filter to high-quality demos (25-50x zone entries), assign confidence weights, augment 3-5x through noise injection and time warping, and use BC pretraining with L2 regularization. Research shows successful imitation with fewer demonstrations using careful filtering and augmentation. Quality matters more than quantity.

### 3. Temporal credit assignment (tick 100 → tick 200)

Increase `gae_lambda` to 0.95-0.99 (more Monte Carlo-like), use longer `n_steps` (2048-4096), and implement **hindsight attribution** at episode end—when the rug pull occurs or cash-out succeeds, retroactively attribute credit to entry decisions with exponential decay. The built-in GAE in PPO handles this well with proper lambda values.

### 4. Distribution shift between recorded and live data

Implement **domain randomization** during training (randomize latency, slippage, transaction costs). Use **rolling training windows** that include recent data. Add **regime detection** that monitors prediction confidence and reward distributions, triggering retraining when shifts are detected.

### 5. Teaching when NOT to trade

Use **ensemble uncertainty**: high critic disagreement = abstain. Combine with your **sidebet predictor confidence**. Model "waiting" as a temporally extended **option** that persists until trigger conditions are met. Add explicit **opportunity cost penalty** for missing optimal zone entries to prevent excessive abstention.

### 6. LSTM vs historical features

**Start with frame stacking (8 steps via VecFrameStack)**—simpler, faster, competitive performance. Only switch to RecurrentPPO if frame stacking underperforms and you have evidence of hidden state not captured in observations. LSTM adds complexity and slower training; justify its use with empirical comparison.

### 7. Separating "when to act" from "what action"

**Yes, use hierarchical architecture**. The Hierarchical Reinforced Trader (HRT) framework demonstrates this: a High-Level Controller (your sidebet predictor + uncertainty gating) handles strategic decisions (trade/don't trade), while a Low-Level Controller (PPO) optimizes specific actions when trading is enabled. This manages complexity through problem decomposition.

### 8. Ensembling sidebet predictor with RL policy

Create a **gating hierarchy**: sidebet predictor outputs confidence score, RL ensemble outputs uncertainty estimate. Trade only when both thresholds are met:

```python
sidebet_confidence = sidebet_model.predict_proba(features)
rl_uncertainty = np.std([critic(state) for critic in ensemble])

if sidebet_confidence > 0.7 and rl_uncertainty < 0.3:
    action, _ = rl_policy.predict(state)
    return action, calculate_position_size(sidebet_confidence)
else:
    return "HOLD", 0
```

You can also use the sidebet predictor output as an additional observation feature for the RL policy, letting the policy learn when to trust it.

---

## Implementation roadmap

### Week 1-2: Fix deployment (CRITICAL)
- Verify VecNormalize save/load
- Implement replay validation comparing training vs deployment
- Add domain randomization to training

### Week 3-4: Improve training pipeline
- Implement PBRS with 25-50x zone potential function
- Add reward component monitoring and hacking detection
- Set up BC pretraining with filtered, augmented demos

### Week 5-6: Add robustness
- Implement CPCV validation with PBO calculation
- Add trading metrics callbacks (Sharpe, drawdown, profit factor)
- Create ensemble uncertainty for trading gating

### Week 7-8: Production hardening
- Paper trading phase with position limits
- Regime detection and retraining triggers
- Weights & Biases experiment tracking integration

### Future exploration
- Offline RL pretraining with d3rlpy (CQL/IQL)
- Decision Transformer experimentation if data quality varies
- MAML for faster regime adaptation

---

## Key papers and resources

### Reward shaping
- Ng et al. (1999) "Policy Invariance Under Reward Transformations" - PBRS foundation
- Bootstrapped Reward Shaping (2025) - arxiv.org/abs/2501.00989
- Reward Hacking Detection (2025) - 78% precision framework

### Imitation learning
- imitation library: github.com/HumanCompatibleAI/imitation
- PIRLNav (CVPR 2023) - BC pretraining + RL fine-tuning
- DWBC (ICML 2022) - Handling suboptimal demos

### Offline RL
- d3rlpy: github.com/takuseno/d3rlpy
- Decision Transformer: arxiv.org/abs/2106.01345
- CQL: Conservative Q-Learning for Offline RL

### Financial RL
- FinRL: github.com/AI4Finance-Foundation/FinRL
- FLAG-Trader (Feb 2025): LLM+RL fusion for trading
- Deep RL for Quantitative Trading (Dec 2023): QTNet architecture

### Validation
- López de Prado "Advances in Financial Machine Learning" - CPCV, PBO
- QuantStats: github.com/ranaroussi/quantstats

The combination of PBRS reward shaping, proper VecNormalize handling, BC pretraining from filtered demos, CPCV validation, and hierarchical gating with uncertainty should transform your 736% training phantom into a deployable trading system.