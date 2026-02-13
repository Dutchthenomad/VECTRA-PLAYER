# Artifact Development Rules

**Version:** 1.0.0
**Date:** 2026-01-25
**Status:** Mandatory

---

## Overview

HTML artifacts are self-contained UI modules that connect to Foundation Service. These 10 rules ensure artifacts are isolated, maintainable, and don't interfere with each other or the host page.

**Violations of these rules may be blocked by hookify rules and CI/CD checks.**

---

## The 10 Rules

### Rule 1: No Global Pollution

Artifacts must not leak variables, functions, or classes into the global scope.

```javascript
// FORBIDDEN - pollutes global scope
window.myHelper = function() {};
var globalThing = 'bad';
function globalFunc() {}

// REQUIRED - ES modules (preferred)
export class MyArtifact { ... }

// ACCEPTABLE - IIFE for legacy support
(function() {
    'use strict';
    // All code here is scoped
    const localVar = 'safe';
    function localFunc() {}
})();
```

**Why:** Global pollution causes naming collisions between artifacts and makes debugging difficult.

---

### Rule 2: Namespace Your CSS

All CSS selectors must be prefixed with the artifact slug or use data attributes.

```css
/* FORBIDDEN - affects entire page */
.button { color: red; }
h1 { font-size: 40px; }
input { border: none; }

/* REQUIRED - prefix with artifact slug */
.recording-control-button { color: red; }
.recording-control h1 { font-size: 40px; }

/* ALSO ACCEPTABLE - data attribute scoping */
[data-artifact="recording-control"] .button { color: red; }
[data-artifact="recording-control"] h1 { font-size: 40px; }
```

**Why:** Un-namespaced CSS bleeds into other artifacts and the host page.

---

### Rule 3: Never Modify Shared Files

These files are read-only for artifacts:

| File | Purpose |
|------|---------|
| `/shared/foundation-ws-client.js` | WebSocket client |
| `/shared/foundation-state.js` | State manager |
| `/shared/vectra-styles.css` | Base styles |

If you need new functionality:
1. Create a feature request issue
2. Propose the change for review
3. Wait for the change to be merged

**Why:** Shared files affect all artifacts. Changes must be reviewed.

---

### Rule 4: Handle Your Own Errors

Artifacts must catch all errors internally and provide user feedback.

```javascript
// FORBIDDEN - crashes entire page
function handleTick(data) {
    const price = data.price.toFixed(2);  // Crashes if data.price is undefined
    throw new Error('Something broke');     // Unhandled exception
}

// REQUIRED - defensive coding
function handleTick(data) {
    try {
        if (!data || typeof data.price !== 'number') {
            console.warn('[MyArtifact] Invalid tick data:', data);
            return;
        }
        const price = data.price.toFixed(2);
        updateUI(price);
    } catch (err) {
        console.error('[MyArtifact] Error handling tick:', err);
        showUserFriendlyError('Failed to update price display');
    }
}
```

**Why:** Unhandled errors in one artifact should never break others.

---

### Rule 5: Clean Up On Unload

Artifacts must unsubscribe from all events when the page unloads.

```javascript
// Track all unsubscribe functions
const unsubscribers = [];

function init() {
    // Store unsubscribe functions
    unsubscribers.push(
        FoundationState.subscribe('game.tick', handleTick)
    );
    unsubscribers.push(
        FoundationState.subscribe('player.state', handlePlayerState)
    );
}

// REQUIRED - clean up on unload
window.addEventListener('beforeunload', () => {
    unsubscribers.forEach(fn => fn());
    console.log('[MyArtifact] Cleaned up subscriptions');
});

// Also handle visibility changes for mobile
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Optionally pause expensive operations
    }
});
```

**Why:** Memory leaks and zombie event handlers degrade performance.

---

### Rule 6: Use Provided Utilities

Use Foundation utilities instead of raw browser APIs.

```javascript
// FORBIDDEN - raw WebSocket
const ws = new WebSocket('ws://localhost:9000/feed');
ws.onmessage = (e) => { ... };

// FORBIDDEN - direct service port access
fetch('http://localhost:9010/api/status');

// REQUIRED - use provided utilities
import { FoundationWSClient } from '/shared/foundation-ws-client.js';
import { FoundationState } from '/shared/foundation-state.js';

// For event subscriptions (preferred)
FoundationState.subscribe('game.tick', handleTick);

// For client-level features
const client = new FoundationWSClient();
client.on('game.tick', handleTick);
client.connect();

// For service APIs - use Foundation proxy
fetch('/api/recording/status');  // Proxied through Foundation
```

**Why:** Utilities handle reconnection, buffering, and error recovery.

---

### Rule 7: Respect the API Contract

Only use events documented in `FOUNDATION-API-CONTRACT.md`.

```javascript
// FORBIDDEN - undocumented event
FoundationState.subscribe('internal.debug.tick', handler);

// FORBIDDEN - accessing raw rugs.fun event names
FoundationState.subscribe('gameStateUpdate', handler);  // Use 'game.tick'

// REQUIRED - documented Foundation events
FoundationState.subscribe('game.tick', handler);
FoundationState.subscribe('player.state', handler);
FoundationState.subscribe('connection.authenticated', handler);
```

**When unsure about event semantics:**
```javascript
// Query rugs-expert MCP for authoritative answers
mcp__rugs-expert__search_rugs_knowledge({ query: "player.state fields" })
```

**Why:** Undocumented events may change without notice.

---

### Rule 8: No External DOM Access

Artifacts may only manipulate DOM elements within their own container.

```javascript
// FORBIDDEN - modifying external elements
document.querySelector('#main-control-panel').style.display = 'none';
document.body.classList.add('my-artifact-active');
document.getElementById('other-artifact').remove();

// REQUIRED - only your own container
const container = document.querySelector('#recording-control-container');
container.classList.add('active');
container.querySelector('.status').textContent = 'Recording...';

// Use data attributes to scope queries
document.querySelector('[data-artifact="recording-control"] .button').click();
```

**Why:** Artifacts must be isolated. One artifact should never affect another.

---

### Rule 9: Version Your Artifact

Every artifact must have version metadata.

```javascript
// In your artifact's main file
const ARTIFACT_NAME = 'recording-control';
const ARTIFACT_VERSION = '1.0.0';

// Log on initialization
console.log(`[${ARTIFACT_NAME}] v${ARTIFACT_VERSION} initialized`);

// Include in manifest.json
{
    "name": "recording-control",
    "version": "1.0.0",
    "description": "Recording control panel",
    "dependencies": {
        "foundation-ws-client": "^1.0.0",
        "foundation-state": "^1.0.0"
    },
    "events_consumed": ["game.tick", "player.state"]
}
```

**Why:** Versioning enables debugging, compatibility checks, and rollbacks.

---

### Rule 10: Fail Gracefully

Artifacts must handle disconnection and errors without crashing.

```javascript
// Handle disconnection gracefully
FoundationState.subscribe('connection', (data) => {
    if (!data.connected) {
        showStatus('Disconnected - attempting to reconnect...');
        disableInteractiveElements();
    } else {
        showStatus('Connected');
        enableInteractiveElements();
    }
});

// Don't spam reconnection attempts (handled by client)
// Don't show error popups for transient issues

// Degrade gracefully when data is stale
function updateUI() {
    const lastUpdate = FoundationState.getState().connection.lastEventTime;
    const staleThreshold = 5000;  // 5 seconds

    if (Date.now() - lastUpdate > staleThreshold) {
        showStatus('Data may be stale');
        document.querySelector('.price').classList.add('stale');
    }
}
```

**Why:** Users should see helpful messages, not blank screens.

---

## Checklist for New Artifacts

Before submitting a new artifact:

- [ ] No global variables or functions
- [ ] CSS is namespaced with artifact slug
- [ ] Does not modify shared files
- [ ] All event handlers wrapped in try/catch
- [ ] beforeunload cleanup for subscriptions
- [ ] Uses FoundationWSClient/FoundationState, not raw WebSocket
- [ ] Only uses documented Foundation events
- [ ] Only modifies own DOM container
- [ ] Has manifest.json with version
- [ ] Handles disconnection gracefully

---

## Examples

### Good Artifact Structure

```
src/artifacts/tools/my-artifact/
├── manifest.json         # Required metadata
├── index.html            # Main entry point
├── style.css             # Namespaced styles
├── script.js             # Main logic (ES module)
└── README.md             # Usage documentation
```

### Minimal Artifact Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>My Artifact</title>
    <link rel="stylesheet" href="/shared/vectra-styles.css">
    <link rel="stylesheet" href="./style.css">
</head>
<body data-artifact="my-artifact">
    <div id="my-artifact-container">
        <div class="my-artifact-status">Connecting...</div>
        <div class="my-artifact-content"></div>
    </div>

    <script type="module">
        import { FoundationWSClient } from '/shared/foundation-ws-client.js';
        import { FoundationState } from '/shared/foundation-state.js';

        const ARTIFACT_NAME = 'my-artifact';
        const ARTIFACT_VERSION = '1.0.0';
        const unsubscribers = [];

        function init() {
            console.log(`[${ARTIFACT_NAME}] v${ARTIFACT_VERSION} initializing...`);

            // Create client and connect
            const client = new FoundationWSClient();

            // Subscribe to events via state manager
            unsubscribers.push(
                FoundationState.subscribe('game.tick', handleTick)
            );
            unsubscribers.push(
                FoundationState.subscribe('connection', handleConnection)
            );

            client.connect().catch(err => {
                console.error(`[${ARTIFACT_NAME}] Connection failed:`, err);
                showStatus('Connection failed');
            });
        }

        function handleTick(data) {
            try {
                const price = data.price?.toFixed(4) || 'N/A';
                document.querySelector('.my-artifact-content').textContent = `Price: ${price}`;
            } catch (err) {
                console.error(`[${ARTIFACT_NAME}] Error:`, err);
            }
        }

        function handleConnection(data) {
            const status = data.connected ? 'Connected' : 'Disconnected';
            showStatus(status);
        }

        function showStatus(message) {
            document.querySelector('.my-artifact-status').textContent = message;
        }

        // Cleanup on unload
        window.addEventListener('beforeunload', () => {
            unsubscribers.forEach(fn => fn());
            console.log(`[${ARTIFACT_NAME}] Cleaned up`);
        });

        // Initialize
        init();
    </script>
</body>
</html>
```

---

## Related Documentation

- [Foundation API Contract](./FOUNDATION-API-CONTRACT.md) - Event types and schemas
- [Module Extension Spec](./MODULE-EXTENSION-SPEC.md) - Module types and patterns
- [Port Allocation Spec](./PORT-ALLOCATION-SPEC.md) - Reserved ports

---

## Changelog

### v1.0.0 (2026-01-25)

- Initial release
- Defined 10 isolation rules
- Added artifact checklist
- Included minimal template
