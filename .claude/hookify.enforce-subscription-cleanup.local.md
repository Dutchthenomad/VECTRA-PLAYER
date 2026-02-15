---
name: enforce-subscription-cleanup
enabled: true
event: file
pattern: FoundationState\.subscribe\(|\.on\(['"]game\.|\.on\(['"]player\.|\.on\(['"]connection
action: warn
---

# PATTERN CHECK - Ensure Subscription Cleanup

**You are creating event subscriptions.**

This is a **reminder** to ensure subscriptions are cleaned up on page unload.

## Why cleanup is required:

1. **Memory leaks** - Orphan handlers consume memory
2. **Zombie events** - Old handlers fire on stale data
3. **Performance** - Accumulating handlers slow down event dispatch

## Required pattern:

```javascript
// Track unsubscribe functions
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
```

## Checklist:

- [ ] Unsubscribe functions stored in array
- [ ] beforeunload listener registered
- [ ] All subscriptions cleaned up

## Alternative for client.on():

```javascript
const client = new FoundationWSClient();
const unsub1 = client.on('game.tick', handleTick);
const unsub2 = client.on('player.state', handlePlayerState);

window.addEventListener('beforeunload', () => {
    unsub1();
    unsub2();
    client.disconnect();
});
```

**See: `docs/specs/ARTIFACT-DEVELOPMENT-RULES.md` Rule 5**
