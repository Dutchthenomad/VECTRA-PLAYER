# Fix Wildcard Import in ui_mockup_modern.py

**Labels:** `refactor`, `good-first-issue`, `copilot-safe`
**Assignee:** Copilot Subagent

## Summary

Replace wildcard import `from tkinter import *` with explicit imports.

## File to Update

`src/ui/ui_mockup_modern.py`

## Current Issue

```python
# BAD - wildcard import pollutes namespace
from tkinter import *
```

## Fix

```python
# GOOD - explicit imports
import tkinter as tk
from tkinter import ttk
```

Then update all references from bare names to prefixed names:

```python
# BEFORE
root = Tk()
frame = Frame(root)
label = Label(frame, text="Hello")

# AFTER
root = tk.Tk()
frame = tk.Frame(root)
label = tk.Label(frame, text="Hello")
```

## Acceptance Criteria

- [ ] No wildcard imports in the file
- [ ] All tkinter references use `tk.` prefix
- [ ] All ttk references use `ttk.` prefix
- [ ] File still runs without import errors
- [ ] UI displays correctly (manual verification if possible)

## Verification

```bash
# Should find no wildcard imports
grep "from tkinter import \*" src/ui/ui_mockup_modern.py
# Expected: no output
```

## Notes

- This is a UI mockup file, so thorough testing may not be available
- Focus on import correctness
- Common tkinter classes: `Tk`, `Frame`, `Label`, `Button`, `Entry`, `Canvas`, `Scrollbar`, `Text`
