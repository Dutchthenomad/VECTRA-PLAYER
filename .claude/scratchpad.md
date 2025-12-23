# VECTRA-PLAYER Session Scratchpad

Last Updated: 2025-12-23 22:30 (Codex Work In Progress)

---

## Active Issue
GitHub Issue #137: Remove Legacy Recording Systems
Branch: `fix/gui-audit-safety-fixes`

## Current SDLC Phase
**Implementation** - Codex completed Tasks A-D, needs review and commit

---

## Quick Start for Fresh Sessions

```bash
# Read key context files
Read the following files:
1. /home/nomad/Desktop/VECTRA-PLAYER/CLAUDE.md
2. /home/nomad/Desktop/VECTRA-PLAYER/.claude/scratchpad.md
3. /home/nomad/Desktop/VECTRA-PLAYER/docs/plans/2025-12-23-expanded-event-schema-design.md

# Run tests
cd /home/nomad/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short

# Check working directory (Codex made changes)
git status
```

---

## Codex Work Status (REVIEW NEEDED)

Codex appears to have completed significant work on #137. Review the following:

### New Model Files Created (untracked)
```
src/models/events/player_action.py      # Task A
src/models/events/other_player.py       # Task A
src/models/events/alert_trigger.py      # Task A
src/models/events/ml_episode.py         # Task A
src/models/events/bbc_round.py          # Task B
src/models/events/candleflip.py         # Task B
src/models/events/short_position.py     # Task B
```

### Legacy Files Deleted (Task C)
```
src/core/demo_recorder.py               # DELETED
src/core/recorder_sink.py               # DELETED
src/debug/raw_capture_recorder.py       # DELETED
src/services/recorders.py               # DELETED
src/services/unified_recorder.py        # DELETED
src/ui/controllers/recording_controller.py  # DELETED
src/ui/toast_notification.py            # DELETED
```

### Tests Deleted (Task C)
```
src/tests/test_core/test_demo_recorder.py
src/tests/test_core/test_recorder_sink.py
src/tests/test_core/test_thread_safety_stress.py
src/tests/test_debug/test_raw_capture_recorder.py
src/tests/test_fixes/test_issue_18_recording_state.py
src/tests/test_services/test_recorders.py
src/tests/test_services/test_unified_recorder.py
src/tests/test_characterization/test_recording_system.py
```

### Modified Files (need review)
```
src/models/events/__init__.py           # Task D - exports new models
src/services/__init__.py                # Updated exports
src/ui/main_window.py                   # Recording references removed
src/ui/builders/menu_bar_builder.py     # Recording menu removed
src/ui/builders/status_bar_builder.py   # Updated
src/ui/controllers/__init__.py          # Updated exports
src/ui/controllers/replay_controller.py # Recording refs removed
src/ui/handlers/event_handlers.py       # Updated
src/ui/window/shutdown.py               # Updated
src/tests/test_services/test_event_store/test_writer.py  # Updated
src/tests/test_ui/test_builders/test_menu_bar_builder.py # Updated
```

---

## Next Steps

1. [ ] Run tests to verify Codex changes work: `../.venv/bin/python -m pytest tests/ -v --tb=short`
2. [ ] Review new model files match Schema v2.0.0 design
3. [ ] If tests pass, stage and commit Codex work
4. [ ] Design BotActionInterface (next priority)

---

## Key Decisions Made (Session 2025-12-23)

1. **EventStore is canonical** - All events flow to Parquet via EventStore
2. **Legacy recorders → DELETE** - ~2989 lines removed (Codex did this)
3. **Schema v2.0.0** - Added player_action, other_player, alerts, sidegames
4. **Latency tracking** - client_ts → server_ts → confirmed_ts chain
5. **No whale detection** - User corrected: "player position size doesn't affect liquidity"
6. **Volatility signals instead** - VOLATILITY_SPIKE, SIDEBET_OPTIMAL_ZONE, etc.

---

## GitHub Issue Status

| Issue | Title | Status |
|-------|-------|--------|
| #136 | Agent Coordination | ✅ CLOSED |
| #137 | Remove Legacy Recording Systems | 🔄 Codex DONE, needs commit |
| #138 | Migrate Toast to Socket Events | ⏳ Pending |
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

### Latency Tracking Fields
```python
client_ts: int          # When we clicked (ms epoch)
server_ts: int | None   # Server timestamp from response
confirmed_ts: int | None # When we got confirmation
send_latency_ms: int | None    # server_ts - client_ts
confirm_latency_ms: int | None # confirmed_ts - server_ts
total_latency_ms: int | None   # confirmed_ts - client_ts
```

---

## After Codex Review: BotActionInterface Design

Foundation for bot UI interaction (next priority after #137 merged):

```python
class BotActionInterface(ABC):
    """Base interface for all game actions"""
    @abstractmethod
    def execute_action(self, action: ActionType, context: ActionContext) -> ActionResult

class UIActionExecutor(BotActionInterface):
    """Clicks real buttons via browser automation (live trading)"""

class SimulatedActionExecutor(BotActionInterface):
    """Direct state updates (RL training, replay mode)"""
```

---

## Key Documentation

| Document | Location |
|----------|----------|
| Schema v2.0.0 Design | `docs/plans/2025-12-23-expanded-event-schema-design.md` |
| Migration Guide | `docs/MIGRATION_GUIDE.md` |
| GUI Audit Report | `docs/GUI_AUDIT_REPORT.md` |

---

## Session History

- **2025-12-23 (evening)**: Codex completed Tasks A-D, awaiting review/commit
- **2025-12-23 (afternoon)**: Schema v2.0.0 complete, #136 closed, Codex tasks assigned
- **2025-12-22**: GUI audit issues created (#136-#140), PR #135 merged
- **2025-12-21**: Phase 12D complete, main_window.py refactored (68% reduction)
- **2025-12-17**: EventStore/Parquet writer development
- **2025-12-15**: VECTRA-PLAYER forked from REPLAYER
