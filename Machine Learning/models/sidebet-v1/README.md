# Sidebet RL Model v1.0 - "Sniper"

**Created:** January 10, 2026
**Status:** Design Complete - Pending Implementation
**Strategy:** Single late bet in optimal zone (tick 200+)

---

## Overview

This is the first RL model for rugs.fun sidebet timing. It uses a "Sniper" strategy:
- Wait for optimal zone (tick 200+)
- Place ONE bet per game
- Achieve 18-21% win rate (above 16.67% breakeven)

**Why Sniper First?**
- Simpler reward function (no martingale complexity)
- Validates training methodology
- Prevents reward hacking before adding complexity
- Establishes baseline for future iterations

---

## Folder Structure

```
sidebet-v1/
├── README.md                          # This file
├── design/
│   ├── SIDEBET_RL_DESIGN_SESSION_2026-01-10.md   # Session notes
│   ├── PRNG_EXPLORATION_SESSION_2026-01-10.md    # Tangential research
│   └── REWARD_FUNCTION_v1.md                     # Reward function + audit
├── training_data/
│   ├── README.md                      # Data documentation
│   ├── games_deduplicated.parquet     # 888 unique games
│   └── sidebets_deduplicated.parquet  # 35,023 sidebets
└── [PENDING: implementation/]
└── [PENDING: checkpoints/]
└── [PENDING: evaluation/]
```

---

## Key Statistics

### Training Data
| Metric | Value |
|--------|-------|
| Unique games | 888 |
| Total sidebets | 35,023 |
| Median duration | 144 ticks |
| Unplayable games | 18.5% (<40 ticks) |

### Strategic Zones
| Zone | Tick Range | Win Rate | EV |
|------|------------|----------|-----|
| Very Early | 0-49 | 17.6% | -0.15 |
| Dead Zone | 50-99 | 16.0% | -0.52 |
| Marginal Early | 100-149 | 17.4% | -0.31 |
| Marginal Late | 150-199 | 15.9% | -0.24 |
| **Optimal** | **200+** | **18.5%** | **+0.13** |

---

## Design Decisions

### Reward Function
- **Win rewards:** +1.5 to +4.0 (graduated by zone)
- **Loss penalties:** -0.50 to -1.00 (graduated by zone)
- **Skip penalties:** 0.0 to -1.75 (scaled by game length)
- **Near-miss bonus:** +0.08 to +0.15 (for close losses)

### Reward Hacking Audit
Audited for 8 potential exploit vectors:
- Skip exploitation: FIXED
- Passive strategy: FIXED
- Boundary gaming: Accepted for v1
- Information leakage: Verified safe

### Observation Space
Using 28-dimensional feature vector from existing design:
- 6 game state features
- 7 price features (Bayesian predictors)
- 3 position context
- 4 market context
- 5 session context
- 3 sidebet state

See: `docs/rag/knowledge/rl-design/sidebet-observation-space-design.md`

---

## Implementation Plan

### Phase 1: Environment
- [ ] Create `SidebetTimingEnv(gym.Env)`
- [ ] Implement observation builder
- [ ] Add action masking
- [ ] Unit tests

### Phase 2: Training
- [ ] PPO with Stable-Baselines3
- [ ] VecNormalize for observation scaling
- [ ] TensorBoard logging
- [ ] 1M timesteps initial training

### Phase 3: Evaluation
- [ ] Win rate > 20%
- [ ] Positive expected value
- [ ] Bayesian alignment > 70%
- [ ] Live validation (100 bets)

### Phase 4: Deployment
- [ ] Integration with BotActionInterface
- [ ] Player piano execution
- [ ] Real-time monitoring

---

## Tangential Research (NOT FOR v1)

The following patterns were discovered but intentionally excluded from v1:

1. **0.02 Ceiling:** No games end above 0.02 final price
2. **Two Game Types:** Ceiling (15%) vs Normal (85%)
3. **Cross-game Correlation:** Weak/no evidence of treasury balancing

See: `design/PRNG_EXPLORATION_SESSION_2026-01-10.md`

**Rationale:** Keep v1 simple. These patterns may be incorporated in v2+ after validating base methodology.

---

## Success Criteria

| Metric | Target | Status |
|--------|--------|--------|
| Win rate (validation) | >20% | PENDING |
| Positive EV | >0 SOL/bet | PENDING |
| Bayesian alignment | >70% | PENDING |
| Training convergence | <100k steps | PENDING |
| Live performance | Profit on 100 bets | PENDING |

---

## Related Documents

| Document | Location |
|----------|----------|
| Observation Space Design | `/docs/rag/knowledge/rl-design/sidebet-observation-space-design.md` |
| Action Space Design | `/docs/rag/knowledge/rl-design/action-space-design.md` |
| WebSocket Protocol | `/docs/specs/WEBSOCKET_EVENTS_SPEC.md` |
| BotActionInterface | `/src/bot/action_interface.py` |

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-01-10 | Initial design session |

---

*Collaboratively designed by Human + Claude*
