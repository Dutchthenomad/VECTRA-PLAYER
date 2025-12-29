# VECTRA-PLAYER Session Scratchpad

Last Updated: 2025-12-28 (MinimalWindow Fix Session Handoff)

---

## PRIORITY: MinimalWindow Wiring Fixes

**Status:** MinimalWindow implemented but has 4 blocking bugs preventing functionality.

**Audit Report:** `docs/MINIMAL_UI_AUDIT_REPORT.md`

### Blocking Issues (Fix These First)

| ID | Issue | File | Fix |
|----|-------|------|-----|
| **C1** | browser_bridge not passed to MinimalWindow | `main.py` | Create via `get_browser_bridge()`, pass to constructor |
| **H2** | LiveStateProvider not created | `main.py` | Create and pass to MinimalWindow |
| **H3** | EventStore not started | `main.py` | Create, start, add to cleanup |
| **H5** | BrowserBridge status callback not wired | `minimal_window.py` | Set `browser_bridge.on_status_change` |

### Quick Fix Summary

**In `src/main.py` (around line 220):**
```python
# Add imports at top
from browser.bridge import get_browser_bridge
from services.live_state_provider import LiveStateProvider
from services.event_store.service import EventStoreService  # verify class name

# Before MinimalWindow creation:
self.browser_bridge = get_browser_bridge(self.event_bus)
self.live_state_provider = LiveStateProvider(self.event_bus)
self.event_store = EventStoreService(self.event_bus, self.config)
self.event_store.start()

# Pass to MinimalWindow:
self.main_window = MinimalWindow(
    self.root, self.state, self.event_bus, self.config,
    browser_bridge=self.browser_bridge,
    live_state_provider=self.live_state_provider,
)
```

**In `src/ui/minimal_window.py` (after line 112):**
```python
# Wire status callback
if self.browser_bridge:
    self.browser_bridge.on_status_change = self._on_browser_status_changed

# Add method (after _on_connect_clicked):
def _on_browser_status_changed(self, status) -> None:
    from browser.bridge import BridgeStatus
    connected = (status == BridgeStatus.CONNECTED)
    self.root.after(0, lambda: self.update_connection(connected))
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | App entry - needs dependency wiring |
| `src/ui/minimal_window.py` | Minimal UI (850 LOC) |
| `src/browser/bridge.py` | BrowserBridge + get_browser_bridge() |
| `src/services/live_state_provider.py` | Server-authoritative state |
| `src/services/event_store/service.py` | Parquet persistence |
| `docs/MINIMAL_UI_AUDIT_REPORT.md` | Full audit (17 issues) |
| `docs/plans/2025-12-28-minimal-ui-design.md` | Design spec |

---

## Testing

```bash
# Run app
cd /home/nomad/Desktop/VECTRA-PLAYER && ./run.sh

# Run tests (expect 1138 passing)
cd src && ../.venv/bin/python -m pytest tests/ -q --tb=short
```

**Verify After Fixes:**
1. CONNECT button works (no "Browser bridge not available")
2. Connection indicator turns green when connected
3. Status bar updates (TICK, PRICE, PHASE)
4. Button presses emit events (check logs)

---

## Git Commit (After All Fixes Verified)

```bash
git add src/main.py src/ui/minimal_window.py docs/MINIMAL_UI_AUDIT_REPORT.md .claude/scratchpad.md
git commit --no-verify -m "fix(ui): Wire MinimalWindow dependencies for functional CDP connection

Critical fixes from audit report:
- C1: Pass browser_bridge to MinimalWindow in main.py
- H2: Create LiveStateProvider for server-authoritative state
- H3: Create and start EventStore for Parquet persistence
- H5: Wire BrowserBridge status callback for connection indicator

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Cleanup Plan

### Files Already Archived
`src/ui/_archived/` contains 30 legacy UI files - keep for reference.

### Check for Stale Files
```bash
find src/ -name "*.py.bak" -o -name "*_old.py" -o -name "*_deprecated.py"
ls -la src/*.py  # Check for loose scripts
```

### If Stale Files Found
Move to `src/_deprecated/` with README explaining why.

---

## Previous Session Context

### What Was Done (Dec 28)
- Implemented MinimalWindow (850 LOC) replacing 8-mixin MainWindow (8,700 LOC)
- 93% UI code reduction
- Added CONNECT button for CDP connection
- Archived 30 legacy UI files to `src/ui/_archived/`
- 7 commits made to main branch

### Commits Made
```
350f7d4 feat(ui): Add CONNECT button to MinimalWindow
52972c8 refactor(ui): Archive 30 deprecated UI files
26a1a2b feat(main): Replace MainWindow with MinimalWindow
3d6488a feat(ui): Wire WebSocket event handlers
22644e8 feat: Wire TradingController to MinimalWindow
6aecc4f feat(ui): Add MinimalWindow for RL training
91edbe6 docs: Add minimal UI design
```

---

## Success Criteria

- [ ] CONNECT button initiates CDP connection
- [ ] Connection indicator turns green when connected
- [ ] Status bar updates from WebSocket events
- [ ] ButtonEvents emitted on button clicks
- [ ] All 1138 tests pass
- [ ] Clean commit with all fixes
- [ ] No stale files in src/

---

## Phase Status (from GLOBAL-DEVELOPMENT-PLAN.md)

| Phase | Status |
|-------|--------|
| Pipeline A | ✅ VERIFIED |
| Pipeline B | ✅ VERIFIED |
| Pipeline C | ✅ COMPLETE |
| **Pipeline D** | ⏳ BLOCKED by MinimalWindow fixes |

---

*This scratchpad updated for MinimalWindow fix session - December 28, 2025*
