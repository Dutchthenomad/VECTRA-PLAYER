---
name: enforce-subscriber-baseclass
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/subscribers/.*/.*\.py$
  - field: new_text
    operator: regex_match
    pattern: def\s+on_game_tick|def\s+on_player_state
  - field: new_text
    operator: not_contains
    pattern: BaseSubscriber
action: block
---

# MODULE EXTENSION VIOLATION - BLOCKED

**Your subscriber does not inherit from BaseSubscriber.**

Per `docs/specs/MODULE-EXTENSION-SPEC.md` (Section: Python Subscribers):

> Every Python subscriber MUST inherit from `BaseSubscriber`. No exceptions.

## Why This Is Required

1. **Contract enforcement** - BaseSubscriber defines the event interface
2. **Automatic registration** - Handlers registered on construction
3. **Consistency** - All subscribers work the same way

## How to Fix

```python
# WRONG
class MySubscriber:
    def on_game_tick(self, event):
        pass

# CORRECT
from foundation.subscriber import BaseSubscriber
from foundation.events import GameTickEvent

class MySubscriber(BaseSubscriber):
    def on_game_tick(self, event: GameTickEvent) -> None:
        pass
```

## Required Methods

When inheriting from BaseSubscriber, you MUST implement:

- `on_game_tick(self, event: GameTickEvent) -> None`
- `on_player_state(self, event: PlayerStateEvent) -> None`
- `on_connection_change(self, connected: bool) -> None`

**DO NOT create subscribers without inheriting BaseSubscriber.**
