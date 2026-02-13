---
name: enforce-html-artifact-imports
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/artifacts/tools/.*/.*\.html$
  - field: new_text
    operator: not_contains
    pattern: vectra-styles.css
action: block
---

# MODULE EXTENSION VIOLATION - BLOCKED

**Your HTML artifact does not import the required shared stylesheet.**

Per `docs/specs/MODULE-EXTENSION-SPEC.md` (Section: HTML Artifacts), ALL HTML artifacts MUST include:

```html
<link rel="stylesheet" href="../../shared/vectra-styles.css">
```

## Why This Is Required

1. **Consistency** - All artifacts use the same Catppuccin Mocha theme
2. **Maintainability** - Style changes propagate to all artifacts
3. **Token efficiency** - Don't recreate existing CSS

## How to Fix

Add this line inside your `<head>` tag:

```html
<link rel="stylesheet" href="../../shared/vectra-styles.css">
```

Then add any artifact-specific styles in a local `<style>` block AFTER the import.

**DO NOT create artifacts without shared styles.**
