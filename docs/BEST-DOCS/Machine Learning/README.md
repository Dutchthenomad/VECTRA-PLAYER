# VECTRA-PLAYER Machine Learning

**Created:** January 10, 2026
**Purpose:** RL models for rugs.fun trading and sidebet optimization

---

## Models

| Model | Strategy | Status | Location |
|-------|----------|--------|----------|
| sidebet-v1 | Sniper (single late bet) | Design Complete | `models/sidebet-v1/` |

---

## Folder Structure

```
Machine Learning/
├── README.md          # This file
└── models/
    └── sidebet-v1/    # First RL model (sidebet timing)
        ├── design/    # Session notes, reward function, research
        └── training_data/  # Parquet files for training
```

---

## Development Philosophy

1. **Train sidebets first** - Simpler problem, validates methodology
2. **Sniper before Martingale** - Single bet before sequential betting
3. **Audit for reward hacking** - Every reward function gets security review
4. **Document everything** - Each iteration preserved for future reference
5. **Exclude PRNG patterns from v1** - Keep first model simple

---

## Quick Start

```python
import pandas as pd

# Load training data
games = pd.read_parquet('models/sidebet-v1/training_data/games_deduplicated.parquet')
sidebets = pd.read_parquet('models/sidebet-v1/training_data/sidebets_deduplicated.parquet')

# Filter to playable games
playable = games[~games['is_unplayable']]
print(f"Playable games: {len(playable)} / {len(games)}")

# Check optimal zone win rate
optimal = sidebets[sidebets['bet_in_optimal_zone']]
print(f"Optimal zone win rate: {optimal['bet_won'].mean():.1%}")
```

---

## Related Documentation

| Topic | Location |
|-------|----------|
| Observation Space Design | `/docs/rag/knowledge/rl-design/sidebet-observation-space-design.md` |
| Action Space Design | `/docs/rag/knowledge/rl-design/action-space-design.md` |
| Protocol Specification | `/docs/specs/WEBSOCKET_EVENTS_SPEC.md` |

---

*Last updated: January 10, 2026*
