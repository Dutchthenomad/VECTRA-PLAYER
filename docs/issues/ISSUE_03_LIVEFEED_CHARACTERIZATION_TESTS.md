# Create LiveFeedController Characterization Tests

**Labels:** `testing`, `characterization`, `medium-priority`
**Assignee:** Copilot Subagent

## Summary

Create characterization tests for `LiveFeedController` to document PRODUCTION FIX edge cases before refactoring.

## Context

`src/ui/controllers/live_feed_controller.py` has 7 "PRODUCTION FIX" patches indicating complex race conditions and edge cases. These need to be captured in tests before any refactoring.

## Reference Implementation

Follow the pattern established in:
- `src/tests/test_characterization/test_event_bus_behavior.py`
- `src/tests/test_characterization/test_game_state_behavior.py`

## File to Create

`src/tests/test_characterization/test_live_feed_behavior.py`

## Key Behaviors to Test

Search for `PRODUCTION FIX` comments in the controller and create tests for each:

1. **Connection state transitions**
   - Test: Disconnection during active game
   - Test: Reconnection after timeout

2. **Race conditions**
   - Test: Rapid connect/disconnect cycles
   - Test: Event received during shutdown

3. **State synchronization**
   - Test: State recovery after reconnect
   - Test: Partial state updates

## Template

```python
"""
LiveFeedController Characterization Tests - PRODUCTION FIX Edge Cases

Documents and tests the specific behaviors fixed by PRODUCTION FIX patches.
DO NOT modify expected values to make tests pass.
"""

import pytest
from unittest.mock import Mock, patch

from ui.controllers.live_feed_controller import LiveFeedController


class TestProductionFixConnectionHandling:
    """
    PRODUCTION FIX: Connection state edge cases.
    """

    def test_disconnect_during_active_game(self):
        """
        Document: Disconnection during game should preserve state.

        PRODUCTION FIX: [describe the fix]
        """
        # TODO: Implement based on actual PRODUCTION FIX comment
        pass


class TestProductionFixRaceConditions:
    """
    PRODUCTION FIX: Race condition prevention.
    """

    def test_rapid_connect_disconnect_no_crash(self):
        """
        Document: Rapid connection cycling should not cause errors.
        """
        pass
```

## Acceptance Criteria

- [ ] Test file created at correct location
- [ ] At least one test class per PRODUCTION FIX category
- [ ] Each test documents the specific fix with comments
- [ ] Tests capture CURRENT behavior (even if suboptimal)
- [ ] All tests pass: `cd src && python -m pytest tests/test_characterization/test_live_feed_behavior.py -v`

## Research Required

1. Read `src/ui/controllers/live_feed_controller.py`
2. Search for all `PRODUCTION FIX` comments
3. Understand each fix's purpose
4. Create minimal tests that exercise each edge case

## Notes

- DO NOT modify expected values to make tests pass
- These are "golden master" tests capturing existing behavior
- Tests may need mocking of WebSocket connections
- Focus on documenting behavior, not fixing issues
