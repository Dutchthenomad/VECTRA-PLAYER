# Categorize and Document Phase Markers

**Labels:** `documentation`, `tech-debt`, `copilot-safe`
**Assignee:** Copilot Subagent

## Summary

Inventory all phase markers in the codebase and categorize them for cleanup.

## Background

There are ~340 phase markers (e.g., `# Phase 10.6:`, `# Phase 8.1`) across the codebase indicating incomplete refactoring waves. These need to be categorized before cleanup.

## Task

Create a markdown report at `docs/PHASE_MARKER_INVENTORY.md` with:

### 1. Full Inventory

```bash
# Run this to find all phase markers
grep -rn "Phase [0-9]" src/ --include="*.py" | sort
```

### 2. Categorization

For each phase marker, categorize as:

| Category | Action | Example |
|----------|--------|---------|
| `COMPLETE` | Remove comment | "Phase 10.6: Auto-start recording DISABLED" (if feature works) |
| `INCOMPLETE` | Create GitHub issue | "Phase 8.1: TODO implement sell percentage" |
| `DOCUMENTATION` | Convert to docstring | "Phase 3.2: Explains why this approach was chosen" |
| `OBSOLETE` | Remove with code review | References to deprecated features |

### 3. Report Format

```markdown
# Phase Marker Inventory

**Generated:** [date]
**Total Markers:** [count]

## Summary by Category

| Category | Count | Files Affected |
|----------|-------|----------------|
| COMPLETE | X | [list] |
| INCOMPLETE | X | [list] |
| DOCUMENTATION | X | [list] |
| OBSOLETE | X | [list] |

## Detailed Inventory

### COMPLETE

| File:Line | Phase | Comment | Recommended Action |
|-----------|-------|---------|-------------------|
| ... | ... | ... | Remove comment |

### INCOMPLETE

| File:Line | Phase | Comment | Recommended Action |
|-----------|-------|---------|-------------------|
| ... | ... | ... | Create issue for [description] |

[etc.]
```

## Acceptance Criteria

- [ ] Report created at `docs/PHASE_MARKER_INVENTORY.md`
- [ ] All phase markers inventoried (use grep to verify none missed)
- [ ] Each marker categorized with reasoning
- [ ] No code changes - documentation only
- [ ] Report is valid markdown

## Verification

```bash
# Count phase markers
grep -rn "Phase [0-9]" src/ --include="*.py" | wc -l
# Should match total in report
```

## Notes

- This is research/documentation only - no code changes
- Focus on accurate categorization
- If unsure about a marker, categorize as `INCOMPLETE`
- Pay attention to files with many markers (main_window.py, live_feed_controller.py)
