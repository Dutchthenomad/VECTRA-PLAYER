---
name: enforce-subscriber-location
enabled: true
event: file
conditions:
  - field: file_path
    operator: not_regex_match
    pattern: ^src/subscribers/
  - field: new_text
    operator: regex_match
    pattern: class\s+\w+\(BaseSubscriber\)
action: block
---

# MODULE EXTENSION VIOLATION - BLOCKED

**You are creating a BaseSubscriber outside the allowed directory.**

Per `docs/specs/MODULE-EXTENSION-SPEC.md` (Section: Python Subscribers):

> **Location:** `src/subscribers/<name>/`

## Why This Is Required

1. **Discoverability** - All subscribers in one place
2. **Consistency** - Same pattern everywhere
3. **Isolation** - Subscribers are separate from Foundation core

## Allowed Location

```
src/subscribers/<your-subscriber-name>/
├── __init__.py
├── subscriber.py      # Your BaseSubscriber class goes HERE
├── config.py
├── manifest.json
└── tests/
    └── test_subscriber.py
```

## How to Fix

1. Create directory: `src/subscribers/<your-name>/`
2. Move your subscriber code there
3. Create the required manifest.json

**DO NOT create subscribers outside src/subscribers/.**
