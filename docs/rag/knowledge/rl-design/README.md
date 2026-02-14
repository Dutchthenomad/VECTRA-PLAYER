# RL Design Documentation

Comprehensive RL environment specifications for rugs.fun bot training.

---

## Documents

| Document | Purpose | Status |
|----------|---------|--------|
| **sidebet-observation-space-design.md** | Complete RL env spec for sidebet timing | READY |
| **sidebet-feature-reference.md** | Quick reference tables & code examples | READY |
| **action-space-design.md** | General action space (trading + sidebets) | DRAFT |
| **implementation-plan.md** | Pipeline: recording → training | DRAFT |

---

## Sidebet Timing RL Environment

### Quick Stats

- **Observation Space**: `Box(28,)` - 28-dimensional continuous vector
- **Action Space**: `Discrete(2)` - HOLD vs PLACE_5X
- **Episode**: One complete game (PRESALE → RUGGED)
- **Avg Episode Length**: 267 ticks (median: 150)
- **Target Win Rate**: >20% (breakeven: 16.67% for 5x)

### Feature Breakdown

```
28 features total:
├── 6  Game State (Raw)        - Direct from gameStateUpdate
├── 7  Price Features          - Bayesian predictors (TOP 5)
├── 3  Position Context        - Player trading state
├── 4  Market Context          - Multi-player dynamics
├── 5  Session Context         - Meta-game statistics
└── 3  Sidebet State          - Current sidebet status
```

### Key Bayesian Features (from 568 games analysis)

1. **ticks_since_peak** [index 8] - Time since max price
2. **distance_from_peak** [index 7] - % below peak price
3. **volatility_10** [index 10] - 10-tick rolling volatility
4. **age** [index 6] - Game duration (tick count)
5. **momentum_5** [index 12] - 5-tick price momentum

### Training Config

```python
from stable_baselines3 import PPO

model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    gamma=0.99,
    ent_coef=0.01,
)

model.learn(total_timesteps=1_000_000)
```

---

## Data Sources

### Live Data (Primary)

```
~/rugs_data/events_parquet/
├── doc_type=ws_event/         # Real-time WebSocket events
├── doc_type=game_tick/        # Price stream
├── doc_type=player_action/    # Our actions with latency
└── doc_type=complete_game/    # Finished games with full history
```

### Historical Analysis

```
/home/devops/Desktop/JUPYTER-CENTRAL-FOLDER/
├── bayesian_sidebet_analysis.py  # Bayesian baseline (568 games)
└── sidebet_optimization.ipynb    # Jupyter exploration
```

### Protocol Specification

```
/home/devops/Desktop/claude-flow/knowledge/rugs-events/
└── WEBSOCKET_EVENTS_SPEC.md      # Canonical protocol v3.0
```

---

## Implementation Roadmap

### Phase 1: Environment Implementation ✅ DESIGNED

- [x] Design observation space (28 features)
- [x] Define action space (Discrete(2))
- [x] Specify reward function
- [x] Define episode structure
- [ ] Implement `SidebetObservationBuilder`
- [ ] Implement `SidebetTimingEnv(gym.Env)`
- [ ] Write unit tests

### Phase 2: Data Pipeline 🔄 IN PROGRESS

- [x] EventStore captures complete games
- [ ] Feature extraction from Parquet
- [ ] Replay buffer implementation
- [ ] Training data converter

### Phase 3: Training 📋 PENDING

- [ ] Baseline PPO model
- [ ] Hyperparameter tuning
- [ ] Evaluate vs Bayesian model
- [ ] Ablation studies

### Phase 4: Deployment 📋 PENDING

- [ ] Live environment integration
- [ ] Performance monitoring
- [ ] Online learning
- [ ] A/B testing

---

## Success Metrics

| Metric | Target | Current | Source |
|--------|--------|---------|--------|
| Win Rate | >20% | 17.4% | 568 games baseline |
| Expected Value | >0 SOL/bet | TBD | Live testing |
| Bayesian Alignment | >70% | TBD | Model comparison |
| Placement Timing | 200-500 ticks | TBD | Tick analysis |
| Max Drawdown | <20% | TBD | Risk management |

---

## Key Files

### Implementation Files (Future)

```
src/rl/
├── envs/
│   └── sidebet_timing_env.py       # Main Gymnasium environment
├── observation/
│   ├── sidebet_builder.py          # Observation builder
│   └── normalizers.py              # Running statistics
├── rewards/
│   └── sidebet_reward.py           # Reward function
└── buffers/
    └── replay_buffer.py            # Experience replay
```

### Training Scripts (Future)

```
scripts/
├── train_sidebet_rl.py             # Main training script
├── evaluate_sidebet_model.py       # Model evaluation
└── compare_with_bayesian.py        # Benchmark vs Bayesian
```

---

## Related Systems

### VECTRA-PLAYER Architecture

```
VECTRA-PLAYER (this repo)
├── EventStore (Parquet)           # Canonical data storage
├── LiveStateProvider              # Server-authoritative state
├── Browser Bridge (CDP)           # WebSocket interception
└── RL Environment (NEW)           # Training infrastructure
```

### External Dependencies

- **Gymnasium**: RL environment API
- **Stable-Baselines3**: PPO/DQN/SAC algorithms
- **DuckDB**: Query Parquet data
- **NumPy/Pandas**: Feature engineering

---

## Quick Start

### Read the Design

1. Start with: `sidebet-observation-space-design.md` (full specification)
2. Reference: `sidebet-feature-reference.md` (quick lookup)
3. Context: `action-space-design.md` (broader action space)

### Understand the Data

```python
import duckdb

# Query complete games
conn = duckdb.connect()
df = conn.execute("""
    SELECT *
    FROM read_parquet('~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet')
    LIMIT 10
""").df()
```

### Explore Bayesian Analysis

```bash
cd /home/devops/Desktop/JUPYTER-CENTRAL-FOLDER
python bayesian_sidebet_analysis.py
```

---

## Contributing

When adding new RL environments:

1. Create design doc in `docs/rag/knowledge/rl-design/`
2. Specify observation/action spaces with Gymnasium
3. Define reward function with clear rationale
4. Link to empirical data analysis
5. Provide code examples
6. Include success criteria

---

## References

- [Gymnasium Documentation](https://gymnasium.farama.org/)
- [Stable-Baselines3 Guide](https://stable-baselines3.readthedocs.io/)
- [rugs.fun WebSocket Protocol v3.0](../../../claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md)
- [Bayesian Survival Analysis Paper](https://en.wikipedia.org/wiki/Survival_analysis)

---

**Maintained by**: Claude Code
**Last Updated**: 2026-01-07
**Status**: Active Development
