---
name: enforce-artifact-error-handling
enabled: true
event: file
pattern: \.on\(['"]game\.tick['"]|\.subscribe\(['"]game\.tick['"]
action: warn
---

# PATTERN CHECK - Ensure Error Handling

**You are subscribing to game.tick events.**

This is a **reminder** to ensure your event handlers include error handling.

## Why error handling is required:

1. **Event data may be malformed** - Network issues, race conditions
2. **Errors in one artifact shouldn't crash others** - Isolation
3. **Users need friendly feedback** - Not blank screens

## Required pattern:

```javascript
// GOOD - wrapped in try/catch
FoundationState.subscribe('game.tick', (data) => {
    try {
        if (!data || typeof data.price !== 'number') {
            console.warn('[MyArtifact] Invalid tick data');
            return;
        }
        const price = data.price.toFixed(4);
        updateUI(price);
    } catch (err) {
        console.error('[MyArtifact] Error handling tick:', err);
        // Optionally show user-friendly error
    }
});

// BAD - unprotected handler
FoundationState.subscribe('game.tick', (data) => {
    const price = data.price.toFixed(4);  // Crashes if undefined
    updateUI(price);
});
```

## Checklist:

- [ ] Handler wrapped in try/catch
- [ ] Validates data before use
- [ ] Logs errors with artifact name prefix
- [ ] Fails gracefully (doesn't crash UI)

**See: `docs/specs/ARTIFACT-DEVELOPMENT-RULES.md` Rule 4**
