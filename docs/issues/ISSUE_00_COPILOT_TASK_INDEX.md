# Copilot Subagent Task Index

**Created:** December 19, 2025
**Purpose:** Index of delegatable refactoring tasks for GitHub Copilot subagents

## Task Summary

| Issue | Title | Risk | Priority | Dependencies |
|-------|-------|------|----------|--------------|
| #01 | [Print to Logging](./ISSUE_01_PRINT_TO_LOGGING.md) | Low | Medium | None |
| #02 | [Wildcard Import Fix](./ISSUE_02_WILDCARD_IMPORT_FIX.md) | Low | Low | None |
| #03 | [LiveFeed Characterization Tests](./ISSUE_03_LIVEFEED_CHARACTERIZATION_TESTS.md) | Low | High | None |
| #04 | [Phase Marker Categorization](./ISSUE_04_PHASE_MARKER_CATEGORIZATION.md) | None | Medium | None |
| #05 | [AUDIT FIX Simplification](./ISSUE_05_AUDIT_FIX_SIMPLIFICATION.md) | Low | Medium | #03 for live_feed |

## Execution Order

### Can Run in Parallel (No Dependencies)

1. **ISSUE_01** - Print to Logging
2. **ISSUE_02** - Wildcard Import Fix
3. **ISSUE_03** - LiveFeed Characterization Tests
4. **ISSUE_04** - Phase Marker Categorization

### Sequential (Has Dependencies)

5. **ISSUE_05** - AUDIT FIX Simplification (wait for #03 to complete)

## Trust Levels

### High Trust (Copilot Safe)
- Simple find/replace patterns
- Linting fixes
- Import organization
- Documentation-only tasks

**Issues:** #01, #02, #04

### Medium Trust (Review Required)
- Test creation (may need manual verification)
- Code comment cleanup (context-dependent)

**Issues:** #03, #05

## Verification Commands

After each task, run:

```bash
# Full test suite
cd /home/user/VECTRA-PLAYER/src && python -m pytest tests/ -v --tb=short

# Ruff lint check
ruff check src/

# Specific file verification (adjust per issue)
grep -r "print(" src/ml/backtest.py  # Issue #01
grep "from tkinter import \*" src/  # Issue #02
```

## Creating GitHub Issues

Since `gh` CLI is not available, create issues manually at:
https://github.com/Dutchthenomad/VECTRA-PLAYER/issues/new

Copy the content from each `ISSUE_XX_*.md` file.

## Notes

- All issues are designed to be safe for autonomous completion
- Each issue includes acceptance criteria and verification steps
- Issues reference the existing test patterns in the repo
- No issue modifies core business logic
