---
name: enforce-foundation-state-usage
enabled: true
event: file
pattern: this\.state\.tick\s*=|this\.state\.price\s*=|let\s+tick\s*=\s*data\.|let\s+price\s*=\s*data\.|this\.tick\s*=|this\.price\s*=
action: warn
---

# PATTERN WARNING - Consider Using FoundationState

**You are caching event data in local state variables.**

This is a **soft warning** - the pattern may be valid, but consider using `FoundationState` instead.

## Why FoundationState is preferred:

1. **Single source of truth** - All artifacts see the same state
2. **Automatic updates** - State is updated by Foundation client
3. **Memory efficiency** - No duplicate state copies
4. **Debugging** - One place to inspect state

## Alternative patterns:

**Instead of local caching:**
```javascript
// WARNING - local state caching
this.state.tick = data.tickCount;
this.state.price = data.price;
let tick = data.tickCount;

// PREFERRED - use FoundationState getters
const tick = FoundationState.getTick();
const price = FoundationState.getPrice();
const phase = FoundationState.getPhase();
```

**For reactive updates:**
```javascript
// PREFERRED - subscribe and react
FoundationState.subscribe('game.tick', (data, eventType, fullState) => {
    // data.tickCount, data.price available here
    // fullState has complete snapshot if needed
    updateUI(data.price, data.tickCount);
});
```

## When local state IS acceptable:

- Derived/computed values (moving averages, deltas)
- UI-specific state (selected tab, collapsed sections)
- Buffering for charts (historical data)

**See: `docs/specs/ARTIFACT-DEVELOPMENT-RULES.md` Rule 6**
