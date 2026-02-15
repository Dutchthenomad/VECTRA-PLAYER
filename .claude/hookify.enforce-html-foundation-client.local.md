---
name: enforce-html-foundation-client
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/artifacts/tools/.*/.*\.(html|js)$
  - field: new_text
    operator: regex_match
    pattern: new\s+WebSocket\s*\(
action: block
---

# MODULE EXTENSION VIOLATION - BLOCKED

**You are attempting to create a raw WebSocket connection in an HTML artifact.**

Per `docs/specs/MODULE-EXTENSION-SPEC.md` (Section: HTML Artifacts - FORBIDDEN Patterns):

> `new WebSocket()` - Use `FoundationWSClient` instead

## Why This Is Forbidden

1. **FoundationWSClient** handles reconnection, auth, event normalization
2. **Raw WebSocket** duplicates logic and WILL drift from Foundation
3. **Consistency** - All artifacts use the same connection pattern

## How to Fix

Replace:
```javascript
// WRONG
const ws = new WebSocket('ws://localhost:9000/feed');
```

With:
```javascript
// CORRECT
import { FoundationWSClient } from '../../shared/foundation-ws-client.js';
const client = new FoundationWSClient('ws://localhost:9000/feed');

client.on('game.tick', (event) => {
    // Handle event
});

client.connect();
```

**DO NOT use raw WebSocket in HTML artifacts.**
