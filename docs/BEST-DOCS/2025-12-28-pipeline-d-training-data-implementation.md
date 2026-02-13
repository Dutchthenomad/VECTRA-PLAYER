# Implementation Plan: Pipeline D - Training Data Pipeline

**Date:** 2025-12-28
**Status:** PLANNING
**Prerequisites:** Pipeline C COMPLETE ✅ (36 validated features, 1149 tests)

---

## Goal

Generate RL training data from captured gameplay sessions using the validated 36-feature observation space schema.

## GitHub Issue

None - create issue first (GitHub API timeout, will create manually)

## Architecture Impact

| Component | Change Type | Description |
|-----------|-------------|-------------|
| `ml/observation_builder.py` | **CREATE** | Build 36-feature vectors from ws_events |
| `ml/episode_segmenter.py` | **CREATE** | Detect game boundaries (game_id changes) |
| `ml/training_generator.py` | **CREATE** | Generate training batches from Parquet |
| `ml/schemas.py` | **CREATE** | Pydantic models for observation space |
| `tests/test_ml/` | **CREATE** | New test directory for ML components |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PARQUET STORE                               │
│  ~/rugs_data/events_parquet/                                        │
│  ├── doc_type=ws_event/     (31,744 events)                         │
│  │   ├── gameStateUpdate    (tick, price, rugpool, stats)           │
│  │   ├── playerUpdate       (balance, position_qty, avgCost)        │
│  │   └── standard/newTrade  (market activity)                       │
│  └── doc_type=button_event/ (204 actions for labels)                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EPISODE SEGMENTER                                │
│  - Groups events by game_id                                          │
│  - Detects episode boundaries                                        │
│  - Filters incomplete episodes                                       │
│  - Output: List[Episode] with event sequences                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OBSERVATION BUILDER                                │
│  Per-tick processing:                                                │
│  - Server State (9): tick, price, phase, rugpool...                  │
│  - Player State (5): balance, position_qty, avgCost...               │
│  - Session Stats (6): averageMultiplier, count2x...                  │
│  - Derived (6): velocity, acceleration, unrealized_pnl...            │
│  - Player Action (3): time_in_position, ticks_since_action...        │
│  - Execution (5): execution_tick, latency_ms... (optional)           │
│  Output: np.ndarray(36,) per tick                                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  TRAINING GENERATOR                                  │
│  - Aligns observations with ButtonEvent actions                      │
│  - Creates (observation, action, reward, next_obs) tuples            │
│  - Handles terminal states (rug events)                              │
│  - Output: Training batches (numpy/torch)                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `src/ml/schemas.py` | Create | Observation dataclass + feature names |
| `src/ml/observation_builder.py` | Create | 36-feature vector construction |
| `src/ml/episode_segmenter.py` | Create | Game boundary detection |
| `src/ml/training_generator.py` | Create | Training batch generation |
| `src/tests/test_ml/__init__.py` | Create | Test package |
| `src/tests/test_ml/test_schemas.py` | Create | Schema tests |
| `src/tests/test_ml/test_observation_builder.py` | Create | Builder tests |
| `src/tests/test_ml/test_episode_segmenter.py` | Create | Segmenter tests |
| `src/tests/test_ml/test_training_generator.py` | Create | Generator tests |

---

## Tasks (TDD Order)

### Task 1: Create Observation Schema (schemas.py)

**Test First:**
```python
# tests/test_ml/test_schemas.py
import numpy as np
from ml.schemas import Observation, FEATURE_NAMES, FEATURE_COUNT

class TestObservationSchema:
    def test_feature_count_matches_spec(self):
        """36 features as defined in observation-space-design.md"""
        assert FEATURE_COUNT == 36
        assert len(FEATURE_NAMES) == 36

    def test_observation_to_numpy(self):
        """Observation converts to numpy array of correct shape"""
        obs = Observation(
            tick=100, price=2.5, game_phase=2, cooldown_timer_ms=0,
            allow_pre_round_buys=False, active=True, rugged=False,
            connected_players=200, game_id="test-game",
            balance=1.0, position_qty=0.1, avg_entry_price=2.0,
            cumulative_pnl=0.05, total_invested=0.2,
            rugpool_amount=5.0, rugpool_threshold=10.0, instarug_count=3,
            average_multiplier=3.5, count_2x=40, count_10x=5,
            count_50x=1, count_100x=0, highest_today=150.0,
            price_velocity=0.1, price_acceleration=0.01,
            unrealized_pnl=0.05, position_pnl_pct=0.25,
            rugpool_ratio=0.5, balance_at_risk_pct=0.09,
            time_in_position=50, ticks_since_last_action=10,
            bet_amount=0.01,
        )
        arr = obs.to_numpy()
        assert arr.shape == (36,)
        assert arr.dtype == np.float32

    def test_feature_names_order(self):
        """Feature names match observation dataclass field order"""
        assert FEATURE_NAMES[0] == "tick"
        assert FEATURE_NAMES[8] == "game_id"  # Will be encoded
        assert FEATURE_NAMES[35] == "latency_ms"
```

**Implementation:**
```python
# src/ml/schemas.py
from dataclasses import dataclass
from typing import Optional
import numpy as np

FEATURE_COUNT = 36

FEATURE_NAMES = [
    # Game State (9)
    "tick", "price", "game_phase", "cooldown_timer_ms",
    "allow_pre_round_buys", "active", "rugged", "connected_players", "game_id_hash",
    # Player State (5)
    "balance", "position_qty", "avg_entry_price", "cumulative_pnl", "total_invested",
    # Rugpool (3)
    "rugpool_amount", "rugpool_threshold", "instarug_count",
    # Session Stats (6)
    "average_multiplier", "count_2x", "count_10x", "count_50x", "count_100x", "highest_today",
    # Derived (6)
    "price_velocity", "price_acceleration", "unrealized_pnl",
    "position_pnl_pct", "rugpool_ratio", "balance_at_risk_pct",
    # Player Action (3)
    "time_in_position", "ticks_since_last_action", "bet_amount",
    # Execution Tracking (5)
    "execution_tick", "execution_price", "trade_id_hash",
    "client_timestamp", "latency_ms",
]

@dataclass
class Observation:
    """36-feature observation for RL training (Pipeline C validated)"""
    # ... fields as defined in observation-space-design.md

    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array for RL training"""
        # Implementation
```

**Verify:**
```bash
cd src && ../.venv/bin/python -m pytest tests/test_ml/test_schemas.py -v
```

---

### Task 2: Create Episode Segmenter (episode_segmenter.py)

**Test First:**
```python
# tests/test_ml/test_episode_segmenter.py
from ml.episode_segmenter import EpisodeSegmenter, Episode

class TestEpisodeSegmenter:
    def test_segments_by_game_id(self):
        """Events are grouped by game_id"""
        segmenter = EpisodeSegmenter()
        events = [
            {"game_id": "game-1", "tick": 1, "event_name": "gameStateUpdate"},
            {"game_id": "game-1", "tick": 2, "event_name": "gameStateUpdate"},
            {"game_id": "game-2", "tick": 1, "event_name": "gameStateUpdate"},
        ]
        episodes = segmenter.segment(events)
        assert len(episodes) == 2
        assert episodes[0].game_id == "game-1"
        assert len(episodes[0].events) == 2

    def test_detects_terminal_state(self):
        """Rug events mark episode as terminal"""
        segmenter = EpisodeSegmenter()
        events = [
            {"game_id": "game-1", "tick": 1, "rugged": False},
            {"game_id": "game-1", "tick": 2, "rugged": True},
        ]
        episodes = segmenter.segment(events)
        assert episodes[0].is_terminal
        assert episodes[0].terminal_tick == 2

    def test_filters_short_episodes(self):
        """Episodes with < min_ticks are filtered"""
        segmenter = EpisodeSegmenter(min_ticks=50)
        events = [{"game_id": "game-1", "tick": i} for i in range(10)]
        episodes = segmenter.segment(events)
        assert len(episodes) == 0

    def test_from_parquet(self):
        """Can load episodes from Parquet files"""
        segmenter = EpisodeSegmenter()
        episodes = segmenter.from_parquet(
            "/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet",
            limit=1000
        )
        assert len(episodes) > 0
```

**Verify:**
```bash
cd src && ../.venv/bin/python -m pytest tests/test_ml/test_episode_segmenter.py -v
```

---

### Task 3: Create Observation Builder (observation_builder.py)

**Test First:**
```python
# tests/test_ml/test_observation_builder.py
import numpy as np
from ml.observation_builder import ObservationBuilder
from ml.schemas import FEATURE_COUNT

class TestObservationBuilder:
    def test_builds_from_game_state_update(self):
        """Extracts server state features from gameStateUpdate"""
        builder = ObservationBuilder()
        event = {
            "event_name": "gameStateUpdate",
            "data": {
                "tickCount": 100, "price": 2.5, "active": True,
                "rugged": False, "connectedPlayers": 200,
                "cooldownTimer": 0, "allowPreRoundBuys": False,
                "rugpool": {"rugpoolAmount": 5.0, "threshold": 10.0, "instarugCount": 3},
                "averageMultiplier": 3.5, "count2x": 40, "count10x": 5,
                "count50x": 1, "count100x": 0, "highestToday": 150.0,
                "gameId": "test-game",
            }
        }
        builder.update(event)
        obs = builder.build()
        assert obs.tick == 100
        assert obs.price == 2.5
        assert obs.rugpool_ratio == 0.5

    def test_computes_derived_features(self):
        """Velocity, acceleration, unrealized_pnl calculated correctly"""
        builder = ObservationBuilder()
        # Feed 3 ticks to compute velocity and acceleration
        for i, price in enumerate([1.0, 1.5, 2.5]):
            builder.update({"data": {"tickCount": i, "price": price}})
        obs = builder.build()
        assert obs.price_velocity > 0  # Price increasing
        assert obs.price_acceleration > 0  # Acceleration increasing

    def test_updates_from_player_update(self):
        """Player state features from playerUpdate"""
        builder = ObservationBuilder()
        builder.update({
            "event_name": "playerUpdate",
            "data": {
                "cash": 1.5, "positionQty": 0.1, "avgCost": 2.0,
                "cumulativePnL": 0.05, "totalInvested": 0.2,
            }
        })
        obs = builder.build()
        assert obs.balance == 1.5
        assert obs.position_qty == 0.1

    def test_to_numpy_shape(self):
        """Output numpy array has correct shape"""
        builder = ObservationBuilder()
        builder.update({"data": {"tickCount": 1, "price": 1.0}})
        arr = builder.to_numpy()
        assert arr.shape == (FEATURE_COUNT,)
        assert arr.dtype == np.float32
```

**Verify:**
```bash
cd src && ../.venv/bin/python -m pytest tests/test_ml/test_observation_builder.py -v
```

---

### Task 4: Create Training Generator (training_generator.py)

**Test First:**
```python
# tests/test_ml/test_training_generator.py
import numpy as np
from ml.training_generator import TrainingDataGenerator
from ml.schemas import FEATURE_COUNT

class TestTrainingDataGenerator:
    def test_generates_observation_action_pairs(self):
        """Creates (obs, action, reward, next_obs, done) tuples"""
        generator = TrainingDataGenerator()
        # Load from Parquet
        dataset = generator.from_parquet(
            ws_events_path="/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet",
            button_events_path="/home/nomad/rugs_data/events_parquet/doc_type=button_event/**/*.parquet",
            limit=1000
        )
        assert len(dataset) > 0
        obs, action, reward, next_obs, done = dataset[0]
        assert obs.shape == (FEATURE_COUNT,)
        assert next_obs.shape == (FEATURE_COUNT,)

    def test_aligns_actions_with_observations(self):
        """ButtonEvents matched to correct game tick"""
        generator = TrainingDataGenerator()
        # Mock data test
        ws_events = [
            {"game_id": "g1", "tick": 100, "price": 2.0},
            {"game_id": "g1", "tick": 101, "price": 2.1},
        ]
        button_events = [
            {"game_id": "g1", "tick": 100, "button_id": "BUY"},
        ]
        samples = generator.align_events(ws_events, button_events)
        assert len(samples) == 1
        assert samples[0]["action"] == "BUY"
        assert samples[0]["tick"] == 100

    def test_handles_terminal_states(self):
        """Rug events create terminal samples with done=True"""
        generator = TrainingDataGenerator()
        ws_events = [
            {"game_id": "g1", "tick": 100, "rugged": False},
            {"game_id": "g1", "tick": 101, "rugged": True},
        ]
        samples = generator.process_episode(ws_events)
        assert samples[-1]["done"] == True

    def test_batch_generation(self):
        """Can generate batches for training"""
        generator = TrainingDataGenerator()
        dataset = generator.from_parquet(
            "/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet",
            "/home/nomad/rugs_data/events_parquet/doc_type=button_event/**/*.parquet",
        )
        batch = generator.get_batch(dataset, batch_size=32)
        assert batch["observations"].shape == (32, FEATURE_COUNT)
        assert batch["actions"].shape == (32,)
        assert batch["rewards"].shape == (32,)
        assert batch["next_observations"].shape == (32, FEATURE_COUNT)
        assert batch["dones"].shape == (32,)
```

**Verify:**
```bash
cd src && ../.venv/bin/python -m pytest tests/test_ml/test_training_generator.py -v
```

---

### Task 5: Integration Test with Real Data

**Test First:**
```python
# tests/test_ml/test_training_integration.py
import numpy as np
from ml.training_generator import TrainingDataGenerator
from ml.schemas import FEATURE_COUNT, FEATURE_NAMES

class TestTrainingIntegration:
    def test_full_pipeline_with_real_data(self):
        """End-to-end test with actual Parquet data"""
        generator = TrainingDataGenerator()

        # Load real data
        dataset = generator.from_parquet(
            ws_events_path="/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet",
            button_events_path="/home/nomad/rugs_data/events_parquet/doc_type=button_event/**/*.parquet",
        )

        print(f"\nDataset size: {len(dataset)} samples")

        # Verify structure
        assert len(dataset) > 0, "No training samples generated"

        obs, action, reward, next_obs, done = dataset[0]

        # Check feature dimensions
        assert obs.shape == (FEATURE_COUNT,), f"Expected {FEATURE_COUNT} features, got {obs.shape}"

        # Check no NaN values
        assert not np.isnan(obs).any(), "NaN values in observation"
        assert not np.isnan(next_obs).any(), "NaN values in next_observation"

        # Report statistics
        print(f"Observation min: {obs.min():.4f}, max: {obs.max():.4f}")
        print(f"Action: {action}")
        print(f"Reward: {reward:.4f}")
        print(f"Done: {done}")

    def test_batch_shapes_correct(self):
        """Batches have correct tensor shapes for RL training"""
        generator = TrainingDataGenerator()
        dataset = generator.from_parquet(
            "/home/nomad/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet",
            "/home/nomad/rugs_data/events_parquet/doc_type=button_event/**/*.parquet",
        )

        batch_size = min(32, len(dataset))
        batch = generator.get_batch(dataset, batch_size=batch_size)

        assert batch["observations"].shape == (batch_size, FEATURE_COUNT)
        assert batch["actions"].shape == (batch_size,)
        assert batch["rewards"].shape == (batch_size,)
        assert batch["next_observations"].shape == (batch_size, FEATURE_COUNT)
        assert batch["dones"].shape == (batch_size,)
```

**Verify:**
```bash
cd src && ../.venv/bin/python -m pytest tests/test_ml/test_training_integration.py -v
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Sparse playerUpdate events (225 vs 31K ws_events) | Interpolate player state between updates |
| Missing features in some events | Default values + validation |
| Memory pressure with large datasets | Streaming/batched processing |
| Action alignment edge cases | Tolerance window (±1 tick) |

## Definition of Done

- [ ] All tests pass (target: +30 new tests)
- [ ] Can generate 36-feature observations from Parquet
- [ ] Episode boundaries correctly detected
- [ ] Training batches properly aligned with actions
- [ ] No NaN values in output tensors
- [ ] Integration test passes with real data
- [ ] Documentation updated

## Estimated Effort

| Task | Complexity | Tests |
|------|------------|-------|
| Task 1: Schemas | Low | ~5 |
| Task 2: Episode Segmenter | Medium | ~8 |
| Task 3: Observation Builder | High | ~10 |
| Task 4: Training Generator | High | ~8 |
| Task 5: Integration | Low | ~3 |
| **Total** | | **~34 tests** |

---

## References

- `scripts/FLOW-CHARTS/observation-space-design.md` - Feature specification
- `src/ml/feature_extractor.py` - Existing sidebet feature extraction (reference)
- `src/ml/data_processor.py` - Existing JSONL processing (reference)
- `src/services/event_store/schema.py` - Parquet schema definition
