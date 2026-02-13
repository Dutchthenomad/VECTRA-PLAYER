---
name: enforce-manifest-required
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/(artifacts/tools|subscribers)/[^/]+/index\.html$|src/(artifacts/tools|subscribers)/[^/]+/subscriber\.py$
action: warn
---

# MODULE MANIFEST REMINDER

**Every module requires a manifest.json file.**

Per `docs/specs/MODULE-EXTENSION-SPEC.md`, all modules must have:

```
<module-directory>/
├── index.html OR subscriber.py
└── manifest.json              # <-- REQUIRED
```

## Required Manifest Fields

```json
{
  "name": "module-name",
  "version": "1.0.0",
  "description": "What this module does",
  "author": "Your name",
  "created": "YYYY-MM-DD",
  "requires": {
    "foundation": "^1.0.0"
  },
  "events_consumed": ["game.tick", "player.state"]
}
```

## Before Committing

Ensure `manifest.json` exists in your module directory with all required fields.

**This is a reminder, not a block. But CI/CD WILL fail without a valid manifest.**
