# ML/RL System Overview & Research Prompt

**Date:** 2025-12-28
**Purpose:** Comprehensive context for research agent to optimize our ML/RL systems
**Repositories:** VECTRA-PLAYER, rugs-rl-bot, claude-flow

---

## PART 1: COMPLETE SYSTEM OVERVIEW

### 1.1 Project Vision

We're building an **AI-powered trading bot** for Rugs.fun, a crypto game where players bet on price multipliers before a "rug pull" ends the game. The system uses:

1. **Imitation Learning from Human Demos** - Learn optimal entry/exit timing from expert play
2. **Reinforcement Learning (PPO)** - Train policies via simulated replay
3. **Ensemble Prediction** - Sidebet model + RL policy coordination

**Core Challenges:**
- 100% of games eventually "rug" (crash) - timing is EVERYTHING
- Optimal entry zone: 25-50x multiplier (75% success rate)
- Median game lifespan: 138 ticks (50% rug by then)
- Must detect exit timing signals from noisy price data

---

### 1.2 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VECTRA-PLAYER (Data Layer)                           │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ CDP/WS Feed │───►│ EventStore  │───►│ Parquet     │───►│ DuckDB      │ │
│  │ (Live Data) │    │ (Writer)    │    │ (Canonical) │    │ (Queries)   │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│  │ ButtonEvent │───►│ ActionSeq   │───►│ Training    │                    │
│  │ Capture     │    │ Grouping    │    │ Labels      │                    │
│  └─────────────┘    └─────────────┘    └─────────────┘                    │
│                                                                             │
│  Event Types: ws_event, game_tick, player_action, button_event,            │
│               server_state, system_event, ml_episode                       │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RUGS-RL-BOT (ML Layer)                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    GYMNASIUM ENVIRONMENT                            │  │
│  │                                                                     │  │
│  │  Observation Space (89 features):                                   │  │
│  │  ├─ current (10): price, tick, bankroll, positions, volatility     │  │
│  │  ├─ history (20): last 5 games × 4 features                        │  │
│  │  ├─ positions (30): up to 10 positions × 3 features                │  │
│  │  ├─ meta_context (24): scalping signals, game progression          │  │
│  │  ├─ sweet_spot (3): 25-50x zone detection                          │  │
│  │  ├─ duration_pred (4): sidebet timing                              │  │
│  │  └─ rug_prediction (5): sidebet model outputs                      │  │
│  │                                                                     │  │
│  │  Action Space (MultiDiscrete [8, 9, 11]):                          │  │
│  │  ├─ action_type: WAIT, BUY_MAIN, SELL_MAIN, BUY_SIDE, BUY_BOTH,   │  │
│  │  │               EMERGENCY_EXIT, PARTIAL_SELL, SKIP                │  │
│  │  ├─ bet_size_idx: 9 discrete sizes (0.001 to 0.5 SOL)             │  │
│  │  └─ sell_percent_idx: 11 values (0% to 100% in 10% steps)         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    REWARD CALCULATOR                                │  │
│  │                                                                     │  │
│  │  Components (17 total, 2-5 enabled per config):                    │  │
│  │  ├─ financial: P&L from trades (THE ONLY THING THAT MATTERS)       │  │
│  │  ├─ bankruptcy: -10.0 penalty if bankroll < threshold              │  │
│  │  ├─ rug_avoidance: reward exits before rug (BUGGY - fixed)         │  │
│  │  ├─ zone_entry: reward 25-50x entries                              │  │
│  │  ├─ temporal_penalty: penalize holding too long                    │  │
│  │  ├─ survival_bonus: passive hold reward                            │  │
│  │  └─ ... (volatility exit, sweet spot, sidebet timing, etc.)        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                   SIDEBET PREDICTOR                                 │  │
│  │                                                                     │  │
│  │  Model: Gradient Boosting Classifier (v3)                          │  │
│  │  Performance: 38.1% win rate (vs 16.7% random), 754% ROI           │  │
│  │  Input: 14-dimensional feature vector (z-score, volatility, etc.)  │  │
│  │  Output: 5 features per tick                                       │  │
│  │  ├─ probability (0-1): rug probability                             │  │
│  │  ├─ confidence (0-1): prediction reliability                       │  │
│  │  ├─ ticks_to_rug_norm (0-1): normalized timing estimate            │  │
│  │  ├─ is_critical (0/1): emergency flag (prob >= 0.50)               │  │
│  │  └─ should_exit (0/1): exit recommendation (prob >= 0.40)          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Training: Stable Baselines 3 (PPO)                                        │
│  Algorithm Parameters:                                                      │
│  ├─ Vectorized env: DummyVecEnv + VecMonitor                              │
│  ├─ Learning rate: ~3e-4                                                   │
│  ├─ Batch size: 64 steps                                                   │
│  ├─ Entropy coefficient: 0.01                                              │
│  └─ Reward clipping: 1000.0                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       VALIDATION & DEPLOYMENT                               │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Visual      │    │ Action Dist │    │ Profitability│   │ Live        │ │
│  │ Replay      │    │ Analysis    │    │ Metrics      │   │ Trading     │ │
│  │ (REPLAYER)  │    │ (detect     │    │ (actual ROI) │   │ (Playwright)│ │
│  │             │    │  hacking)   │    │              │   │             │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.3 Data Pipeline

**Data Collection (VECTRA-PLAYER):**
```
WebSocket Events → EventBus → EventStore → Parquet (~/rugs_data/events_parquet/)
     │
     ├─ CDP interception: Full game state, player updates
     ├─ Public WebSocket: Market data, other players' trades
     └─ UI Events: ButtonEvent capture for imitation learning
```

**Current Dataset:**
- 929 recorded game sessions (JSONL format in `/home/nomad/rugs_recordings/`)
- 31,744 WebSocket events in Parquet
- 204 ButtonEvents (human actions with full game context)
- 59 distinct games captured

**Training Data Generation (Pipeline D - Ready to Start):**
```
Parquet Store
    ↓
Episode Segmenter (groups by game_id)
    ↓
Observation Builder (36-feature vectors)
    ↓
Training Generator → (obs, action, reward, next_obs, done) tuples
```

**36-Feature Observation Space (Validated):**
- Server State (9): tick, price, game_phase, cooldown, active, rugged, connected_players, game_id_hash
- Player State (5): balance, position_qty, avg_entry_price, cumulative_pnl, total_invested
- Rugpool (3): rugpool_amount, rugpool_threshold, instarug_count
- Session Stats (6): average_multiplier, count_2x, count_10x, count_50x, count_100x, highest_today
- Derived (6): price_velocity, price_acceleration, unrealized_pnl, position_pnl_pct, rugpool_ratio, balance_at_risk_pct
- Player Action (3): time_in_position, ticks_since_last_action, bet_amount
- Execution (5): execution_tick, execution_price, trade_id_hash, client_timestamp, latency_ms

---

### 1.4 Critical Lessons Learned (REWARD HACKING)

**The Problem:**
Training metrics appeared successful (reward 4,890) but model was completely broken:
- 0% ROI, 0 positions opened
- 81.4% SELL spam, 0% BUY
- Agent exploited reward bugs instead of trading

**Root Causes:**
1. **Rug Avoidance Bug:** Rewarded SELL without checking if positions existed
2. **Passive Rewards:** Agent farmed zone entry + survival bonuses without trading
3. **Complexity Enabled Exploitation:** 17-component reward function had exploit paths

**The Fix:**
```yaml
# configs/reward_config_minimal.yaml
global:
  reward_clip: 1000.0
  enabled_components:
    - financial
    - bankruptcy

financial:
  weight: 1.0  # Pure, unscaled P&L

bankruptcy:
  penalty: -10.0
  threshold: 0.001
```

**Key Lesson:** Complexity is the enemy. Start with 2 components. If the model can't learn to trade profitably with THIS config, there's a fundamental environment bug to fix first.

**Validation Requirements:**
1. Action distribution analysis (% BUY vs SELL vs WAIT)
2. Profitability metrics (actual ROI, not reward score)
3. Position tracking (did agent actually open positions?)
4. Visual inspection (watch bot play in real-time via REPLAYER)

---

### 1.5 Empirical Analysis Results

**From 929 Recorded Games:**

| Metric | Value | Implication |
|--------|-------|-------------|
| Rug Rate | 100% | All games eventually rug - exit timing is EVERYTHING |
| Sweet Spot | 25-50x | 75% success rate, 186-427% median returns |
| Median Game Life | 138 ticks | 50% of games rug by this point |
| Safe Window | < 69 ticks | Low rug probability |
| Danger Zone | > 138 ticks | 50%+ already rugged |

**Temporal Rug Probability Model:**
```python
TEMPORAL_RUG_PROB = {
    50: 0.234,   # 23.4% cumulative
    100: 0.386,  # 38.6%
    138: 0.500,  # 50% (median)
    200: 0.644,  # 64.4%
    300: 0.793   # 79.3%
}

OPTIMAL_HOLD_TIMES = {
    1: 65,   # 61% success
    25: 60,  # 75% success (SWEET SPOT)
    50: 48,  # 75% success (SWEET SPOT)
    100: 71  # 36% success
}
```

---

### 1.6 Current Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| RL Framework | Stable Baselines 3 | Latest | PPO training |
| Environment | Gymnasium | 0.29+ | Custom trading env |
| ML Models | scikit-learn | Latest | Gradient Boosting (sidebet) |
| Data Storage | DuckDB + Parquet | Latest | Canonical event store |
| Vector DB | ChromaDB | Latest | RAG for claude-flow agents |
| UI Framework | Tkinter + ttkbootstrap | Latest | Desktop app |
| Browser Control | Playwright | Latest | UI automation |
| WebSocket | Socket.IO / CDP | Latest | Live data capture |
| Python | 3.12 | Current | Runtime |

---

### 1.7 Project Roadmap

**Completed:**
- Phase 1: Environment & Data Collection (929 games)
- Phase 2: Sidebet Model (38.1% win rate, 754% ROI)
- Phase 3: Rewards Design + Empirical Analysis
- Pipeline A-C: Server State + ButtonEvent + Action Validation

**In Progress:**
- Phase 0 Revision: Fix reward hacking, minimal baseline training
- Pipeline D: Training data generation from Parquet

**Planned:**
- Phase 0.5: REPLAYER visual validation integration
- Phase 1: Hyperparameter tuning, extended training (500k-1M timesteps)
- Phase 2: Live trading deployment with Playwright automation
- Phase 3: Dual-model coordination (sidebet + RL policy)

---

## PART 2: RESEARCH PROMPT FOR OPTIMIZATION AGENT

### Research Objective

We need comprehensive research on ML/RL methods, tools, libraries, MCP servers, and approaches to optimize our trading bot system. We've built the foundation but need to ensure we're using state-of-the-art techniques and avoiding common pitfalls.

### Specific Research Areas

#### 2.1 Gymnasium Environment Design

**Current State:** Custom `RugsTradingEnv` with MultiDiscrete action space and Dict observation space.

**Research Questions:**
1. What are best practices for financial/trading Gymnasium environments?
2. How should we handle variable-length episodes (games have different durations)?
3. What observation space designs work best for time-series financial data?
4. Should we use frame stacking, LSTMs, or attention mechanisms for temporal context?
5. How do we properly normalize observations for stable training?
6. What's the optimal action space design for trading (discrete vs continuous vs hybrid)?

**Deliverables Needed:**
- Recommended observation space architectures
- Action space design patterns
- Episode management strategies
- Reference implementations or papers

#### 2.2 Reward Shaping & Reward Hacking Prevention

**Current State:** Discovered severe reward hacking where agent exploited bugs instead of trading. Now using minimal 2-component config.

**Research Questions:**
1. What are proven reward shaping techniques for financial RL?
2. How do we detect and prevent reward hacking systematically?
3. What's the trade-off between dense vs sparse rewards for trading?
4. Should we use potential-based reward shaping (PBRS)?
5. How do inverse RL (IRL) approaches compare for learning from demos?
6. What regularization techniques prevent exploitation (entropy bonuses, etc.)?

**Deliverables Needed:**
- Reward hacking detection methods
- Proven reward function designs for trading
- IRL/imitation learning approaches comparison
- Reward debugging tools and visualization

#### 2.3 Stable Baselines 3 & PPO Optimization

**Current State:** Using PPO with default hyperparameters, DummyVecEnv, VecMonitor.

**Research Questions:**
1. What are optimal PPO hyperparameters for financial trading?
2. Should we use SAC, TD3, or other algorithms instead of PPO?
3. How many parallel environments should we use (SubprocVecEnv)?
4. What callback strategies work best for training monitoring?
5. How do we implement proper early stopping and checkpointing?
6. What's the recommended training duration (timesteps) for trading bots?

**Deliverables Needed:**
- Hyperparameter tuning strategies
- Algorithm selection guidance (PPO vs SAC vs TD3 vs others)
- Training infrastructure best practices
- Evaluation and checkpointing patterns

#### 2.4 Imitation Learning from Human Demonstrations

**Current State:** 204 ButtonEvents captured with full game context. Haven't implemented imitation learning yet.

**Research Questions:**
1. Should we use Behavioral Cloning (BC), GAIL, DAgger, or other IL approaches?
2. How do we combine IL with RL (pretraining vs concurrent training)?
3. What's the minimum amount of demonstration data needed?
4. How do we handle suboptimal demonstrations?
5. What architectures work best for IL in trading (transformers, LSTMs)?

**Deliverables Needed:**
- IL algorithm comparison for trading
- Data requirements and collection strategies
- Integration patterns with SB3
- Reference implementations

#### 2.5 Feature Engineering for Financial RL

**Current State:** 36 validated features (price, volume, positions, derived metrics).

**Research Questions:**
1. What technical indicators improve RL trading performance?
2. How do we handle feature selection for high-dimensional observations?
3. Should we use attention mechanisms or feature embeddings?
4. What time-series preprocessing works best (normalization, differencing)?
5. How do we incorporate market microstructure features?

**Deliverables Needed:**
- Feature engineering best practices
- Dimensionality reduction approaches
- Attention/embedding architectures
- Real-world feature sets from successful trading bots

#### 2.6 Model Validation & Deployment

**Current State:** Manual evaluation scripts, no systematic validation pipeline.

**Research Questions:**
1. How do we properly backtest RL trading models?
2. What metrics beyond reward are critical (Sharpe ratio, max drawdown)?
3. How do we detect overfitting to training data?
4. What's the recommended validation/test split for financial RL?
5. How do we safely deploy RL models (paper trading, position limits)?

**Deliverables Needed:**
- Backtesting frameworks for RL
- Evaluation metrics suite
- Overfitting detection methods
- Deployment safety patterns

#### 2.7 Tools, Libraries, and MCP Servers

**Current State:** Using SB3, Gymnasium, scikit-learn, DuckDB, ChromaDB.

**Research Questions:**
1. What MCP servers exist for ML/RL development assistance?
2. Are there specialized RL debugging/visualization tools we should use?
3. What alternatives to SB3 should we consider (Ray RLlib, CleanRL, etc.)?
4. Are there pre-trained models or transfer learning approaches?
5. What MLOps tools work well for RL experiment tracking?

**Deliverables Needed:**
- MCP server recommendations (RL, ML, data science)
- Tool ecosystem overview
- Library comparisons
- MLOps/experiment tracking solutions

#### 2.8 Advanced Techniques to Consider

**Research Questions:**
1. How can we use transformers/attention for trading (Decision Transformer, etc.)?
2. Would offline RL (CQL, IQL) work better given our recorded data?
3. Should we implement multi-agent RL (other players' actions)?
4. How do we handle non-stationarity in market environments?
5. What uncertainty quantification methods work for trading RL?

**Deliverables Needed:**
- Advanced architecture recommendations
- Offline RL implementation guidance
- Uncertainty quantification methods
- Research paper recommendations

### Deliverable Format

For each research area, please provide:

1. **Summary:** 2-3 paragraph overview of the state-of-the-art
2. **Recommendations:** Prioritized list of what we should implement
3. **Tools/Libraries:** Specific packages, repos, or MCP servers to use
4. **Implementation Guidance:** How to integrate with our existing architecture
5. **References:** Papers, blog posts, GitHub repos for deeper reading

### Priority Order

1. **CRITICAL:** Reward shaping & hacking prevention (our #1 problem)
2. **HIGH:** Imitation learning integration (we have demo data)
3. **HIGH:** Stable Baselines 3 optimization
4. **MEDIUM:** Feature engineering improvements
5. **MEDIUM:** Validation & backtesting framework
6. **LOW:** Advanced techniques (transformers, offline RL)

### Context Files to Reference

If the research agent has access to these files, they provide additional context:

- `/home/nomad/Desktop/rugs-rl-bot/CLAUDE.md` - RL bot context
- `/home/nomad/Desktop/VECTRA-PLAYER/CLAUDE.md` - Data system context
- `/home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/training/reward_calculator.py` - Reward implementation
- `/home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/environment/trading_env.py` - Gymnasium env
- `/home/nomad/Desktop/VECTRA-PLAYER/docs/plans/GLOBAL-DEVELOPMENT-PLAN.md` - Development roadmap

---

## PART 3: SPECIFIC OPTIMIZATION QUESTIONS

### 3.1 Our Immediate Problems

1. **Reward Hacking:** Even with simplified rewards, how do we ensure the model doesn't find new exploits?

2. **Sparse Data:** 204 human demonstrations - is this enough for IL? How do we augment?

3. **Temporal Credit Assignment:** In trading, cause and effect are delayed (enter at tick 100, profit/loss at tick 200). How do we handle this?

4. **Distribution Shift:** Training on recorded data, deploying on live market. How do we handle?

5. **Risk Management:** The model should learn when NOT to trade. How do we reward inaction appropriately?

### 3.2 Architecture Questions

1. Should we use a recurrent architecture (LSTM) instead of feeding historical features?

2. Is Decision Transformer or other transformer-based RL suitable for our use case?

3. Should we separate the "when to act" model from the "what action to take" model?

4. How do we properly ensemble the sidebet predictor with the RL policy?

### 3.3 Training Questions

1. What learning rate schedule works best for financial RL?

2. How do we implement curriculum learning (start with easy games, progress to hard)?

3. Should we use prioritized experience replay?

4. How many training environments should we run in parallel?

---

## APPENDIX: Key File Locations

```
VECTRA-PLAYER (Data Layer):
├── src/services/event_store/       # Parquet writer, DuckDB queries
├── src/models/events/              # Event schemas (ButtonEvent, etc.)
├── src/core/game_state.py          # Centralized state management
├── src/browser/bridge.py           # CDP WebSocket interception
├── docs/plans/                     # Development plans
└── ~/rugs_data/events_parquet/     # Canonical data store

RUGS-RL-BOT (ML Layer):
├── archive/rugs_bot/environment/   # Gymnasium environments
├── archive/rugs_bot/training/      # Reward calculator, position manager
├── archive/rugs_bot/analysis/      # Volatility tracker, pattern detector
├── archive/rugs_bot/sidebet/       # Sidebet predictor
├── configs/                        # Reward configs (YAML)
├── models/                         # Trained models (.pkl, .zip)
└── scripts/                        # Training, evaluation scripts

CLAUDE-FLOW (Dev Layer):
├── rag-pipeline/storage/chroma/    # ChromaDB vector store
├── knowledge/rugs-events/          # WebSocket protocol documentation
└── plugins/superpowers/            # Claude Code skills
```

---

*Document generated: 2025-12-28*
*For: Research agent optimization task*
