# VECTRA-PLAYER Session Scratchpad

Last Updated: 2025-12-23 (Schema v2.0.0 Complete)

---

## Quick Start for Fresh Sessions

```bash
# Read key context files
Read the following files:
1. /home/nomad/Desktop/VECTRA-PLAYER/CLAUDE.md
2. /home/nomad/Desktop/VECTRA-PLAYER/.claude/scratchpad.md
3. /home/nomad/Desktop/VECTRA-PLAYER/docs/plans/2025-12-23-expanded-event-schema-design.md

# Run tests (VECTRA-PLAYER has its own venv now)
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short

# Check GitHub issues
gh issue list --repo Dutchthenomad/VECTRA-PLAYER
```

---

## Current State

### Schema v2.0.0 COMPLETE

**Issue #136 CLOSED** - Architecture decisions made:
1. EventStore is canonical (all events → Parquet)
2. Legacy recorders → DELETE (~2989 lines)
3. Schema expanded with player_action, other_player, alerts, sidegames
4. Latency tracking: client_ts → server_ts → confirmed_ts

### Codex Working On

Tasks assigned to Codex agent:
- **Task A:** Create core event models (player_action.py, other_player.py, alert_trigger.py, ml_episode.py)
- **Task B:** Create sidegame placeholders (bbc_round.py, candleflip.py, short_position.py)
- **Task C:** Delete legacy recorders (#137)
- **Task D:** Update EventStore schema

### Next Session Priority

**BotActionInterface design** - Foundation for bot UI interaction:
- Base interface for all game actions
- `UIActionExecutor` - Clicks real buttons (live trading)
- `SimulatedActionExecutor` - Direct state updates (training)
- Integration with `player_action` schema

---

## GitHub Issue Status

| Issue | Title | Status |
|-------|-------|--------|
| #136 | Agent Coordination | ✅ CLOSED |
| #137 | Remove Legacy Recording Systems | 🔄 Codex working |
| #138 | Migrate Toast to Socket Events | ⏳ Blocked by #137 |
| #139 | Path Migration to RUGS_DATA_DIR | ⏳ Pending |
| #140 | Final Legacy Cleanup | ⏳ Pending |

---

## Schema v2.0.0 Summary

### New DocTypes
| DocType | Purpose |
|---------|---------|
| `player_action` | Our button presses with full context |
| `other_player` | Other players' trades for ML training |
| `alert_trigger` | Toast notification triggers |
| `ml_episode` | RL episode boundaries |
| `bbc_round` | Bull/Bear/Crab sidegame (placeholder) |
| `candleflip` | Candleflip sidegame (placeholder) |
| `short_position` | Short position tracking (placeholder) |

### New ActionTypes
- Main game: BUY, SELL, SIDEBET
- Shorts: SHORT_OPEN, SHORT_CLOSE
- Bet adjustment: BET_INCREMENT, BET_DECREMENT, BET_PERCENTAGE
- Sidegames: BBC_PREDICT, CANDLEFLIP_BET

### Alert Categories
- Trade: TRADE_SUCCESS, TRADE_FAILED
- Position: POSITION_PROFIT, POSITION_LOSS, SIDEBET_WON/LOST
- Game: GAME_START, GAME_RUG, MULTIPLIER_MILESTONE
- Volatility/Timing: VOLATILITY_SPIKE, SIDEBET_OPTIMAL_ZONE, HIGH_POTENTIAL_ENTRY/EXIT, RUG_WARNING
- Shorts: SHORT_ENTRY_SIGNAL, SHORT_EXIT_SIGNAL, SHORT_LIQUIDATION_WARNING
- Sidegames: BBC_ROUND_START, CANDLEFLIP_START
- Custom signals: CUSTOM_SIGNAL_1/2/3 (placeholders for data exploration)

---

## Key Documentation

| Document | Location |
|----------|----------|
| Schema v2.0.0 Design | `docs/plans/2025-12-23-expanded-event-schema-design.md` |
| Migration Guide | `docs/MIGRATION_GUIDE.md` |
| GUI Audit Report | `docs/GUI_AUDIT_REPORT.md` |

---

## Test Coverage

```bash
# Run all tests
cd /home/nomad/Desktop/VECTRA-PLAYER/src
../.venv/bin/python -m pytest tests/ -v --tb=short

# Current: 1071 passing, 1 failing (minor test fixture issue)
```

---

## Session History

- **2025-12-23**: Schema v2.0.0 complete, #136 closed, Codex tasks assigned
- **2025-12-22**: GUI audit issues created (#136-#140), PR #135 merged
- **2025-12-21**: Phase 12D complete, main_window.py refactored (68% reduction)
- **2025-12-17**: EventStore/Parquet writer development
- **2025-12-15**: VECTRA-PLAYER forked from REPLAYER
