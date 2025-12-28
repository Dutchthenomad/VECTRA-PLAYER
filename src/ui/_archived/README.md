# Archived UI Components

**Date:** 2025-12-28
**Reason:** Minimal UI refactoring for RL training data collection

These UI files were archived as part of Task 5 of the Minimal UI Design plan.
The complex MainWindow with 8 mixins has been replaced with a single-file
MinimalWindow (~838 LOC) focused on RL training data collection.

## What was archived

| Category | Files | LOC (approx) |
|----------|-------|--------------|
| MainWindow | main_window.py | 721 |
| Widgets | chart.py, toast_notification.py | 775 |
| Builders | 6 builders | 1,100 |
| Handlers | 5 handler mixins | 1,100 |
| Dialogs | 4 dialog files | 1,600 |
| Other | timing_overlay, audio_cue_player, etc. | 1,000+ |
| **Total** | **30 files** | **~6,300** |

## Why archived (not deleted)

- Preserves git history for reference
- Can restore specific components if needed
- Documents what was removed and when
- Tests for these components also archived in `tests/_archived/`

## Active UI files

After archiving, these remain in `src/ui/`:
- `minimal_window.py` - Single-file minimal UI (838 LOC)
- `controllers/trading_controller.py` - ButtonEvent emission
- `controllers/browser_bridge_controller.py` - CDP connection (optional)
- Various `__init__.py` files (minimal, just document the archiving)

## Restoring archived components

If you need to restore any component:

```bash
# Example: restore MainWindow
mv src/ui/_archived/main_window.py src/ui/

# Update __init__.py as needed
# Restore corresponding test files from tests/_archived/
```

## Related plan document

See `/docs/plans/2025-12-28-minimal-ui-design.md` for full design rationale.
