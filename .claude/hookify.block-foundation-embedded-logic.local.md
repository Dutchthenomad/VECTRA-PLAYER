---
name: block-foundation-embedded-logic
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/foundation/(?!http_server\.py|launcher\.py|config\.py|service_manager\.py|__init__\.py).*\.py$
  - field: new_text
    operator: regex_match
    pattern: recording|recorder|parquet|duckdb|save.*event|persist|write.*file|ml_|rl_|training
action: block
---

# ARCHITECTURAL VIOLATION - BLOCKED

**You are attempting to embed recording/persistence logic in Foundation Service.**

This pattern is **FORBIDDEN** in VECTRA-BOILERPLATE. It violates:
- **Isolation Principle**: Foundation crashes should NOT crash recording
- **Single Responsibility**: Foundation BROADCASTS, it does not PERSIST
- **Rule 4 & 5**: Subscribers are SEPARATE modules in src/subscribers/

## Foundation Service responsibilities (ONLY these):

1. Receive events from CDP interception
2. Normalize to Foundation event types
3. Broadcast via WebSocket to subscribers
4. Serve HTTP health/status endpoints

## Excluded files (core infrastructure):

These files are excluded from this rule as they handle routing/orchestration:
- `http_server.py` - HTTP routing and static file serving
- `launcher.py` - Startup orchestration and browser tab management
- `config.py` - Configuration management
- `service_manager.py` - Service lifecycle management

## Recording/ML/RL logic belongs in:

```
src/subscribers/recording/     # Recording service
src/subscribers/ml_training/   # ML data collection
src/subscribers/rl_episode/    # RL episode tracking
```

Each subscriber:
- Inherits from BaseSubscriber
- Runs in its OWN Docker container
- Can be toggled ON/OFF independently
- Crashes without affecting Foundation

**NEVER add persistence, recording, or ML logic to Foundation Service.**
