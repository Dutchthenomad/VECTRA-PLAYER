# Simplify AUDIT FIX Comments with Test References

**Labels:** `refactor`, `documentation`, `medium-priority`
**Assignee:** Copilot Subagent

## Summary

Simplify verbose AUDIT FIX comments by referencing characterization tests, following the pattern used in `event_bus.py`.

## Background

The codebase has ~164 remaining AUDIT FIX/PRODUCTION FIX comments (after EventBus cleanup). These verbose comments can be simplified once tests exist that verify the fixed behavior.

## Reference Pattern

EventBus was cleaned up like this:

```python
# BEFORE (verbose)
# AUDIT FIX: Prevent deadlock when subscriber callback raises.
# This was added after production incident where a callback raised
# an exception while holding the lock, causing all subsequent
# publish() calls to deadlock. The fix is to release the lock
# before calling any callbacks.
# See incident report: 2024-11-15

# AFTER (simple)
"""
Thread-safe event bus with deadlock prevention.

See test_characterization/test_event_bus_behavior.py for edge case tests.
"""
```

## Files to Process

### Priority 1: Files with Characterization Tests

1. `src/core/game_state.py` - Has tests in `test_game_state_behavior.py`
   - Simplify AUDIT FIX comments to reference tests

### Priority 2: Files Needing Tests First

2. `src/ui/controllers/live_feed_controller.py` - 7 PRODUCTION FIX patches
   - **BLOCKED** until Issue #03 (characterization tests) is complete

3. `src/browser/executor.py` - Legacy fallback patches
   - Requires browser testing infrastructure

## Task for game_state.py

1. Read `src/core/game_state.py`
2. Find all AUDIT FIX comments
3. For each, verify a test exists in `test_game_state_behavior.py`
4. Simplify comment to reference the test

## Template

```python
# BEFORE
# AUDIT FIX: Bounded history to prevent unbounded memory growth.
# Previously used list.append() which caused OOM after long sessions.
# Changed to deque with maxlen for O(1) bounded memory.
self._history = deque(maxlen=MAX_HISTORY_SIZE)

# AFTER
# Bounded history - see test_game_state_behavior.py::TestAuditFixBoundedHistory
self._history = deque(maxlen=MAX_HISTORY_SIZE)
```

## Acceptance Criteria

- [ ] All AUDIT FIX in `game_state.py` simplified (if tests exist)
- [ ] Each simplified comment references specific test
- [ ] No behavior changes
- [ ] All tests pass: `cd src && python -m pytest tests/test_characterization/test_game_state_behavior.py -v`
- [ ] Module docstring updated to reference test file

## Verification

```bash
# Count remaining verbose AUDIT FIX comments
grep -c "AUDIT FIX" src/core/game_state.py
# Should be reduced from current count
```

## Notes

- Only simplify comments where tests already exist
- If no test exists for an AUDIT FIX, leave it verbose and note it
- Do not remove essential context - just make it concise
- The goal is to move documentation to tests, not delete it
