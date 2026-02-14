# Hookify Rule: Enforce Pinned Dependencies

## Purpose
All Python dependencies must use exact version pins (`==`). Range specifiers
(`>=`, `~=`, `^`) are forbidden in service requirements.txt files.

## Trigger
- PreToolUse:Edit — When editing `services/*/requirements.txt`
- PreToolUse:Write — When creating `services/*/requirements.txt`

## Severity
BLOCK

## Rule

When editing or creating a `requirements.txt` file under `services/`:

1. Check that every non-comment, non-empty line uses `==` (exact pin)
2. Lines with `>=`, `~=`, `>`, `<`, `!=` are BLOCKED
3. Comments (lines starting with `#`) are allowed
4. Empty lines are allowed

## Enforcement Message

```
BLOCK: Unpinned dependency detected in requirements.txt.
All dependencies must use exact version pins (==).

Found: package>=1.0.0
Required: package==1.0.0

To find the installed version: pip show <package> | grep Version
```
