# Hookify Rule: Enforce Project ID

## Purpose
Every code change must be associated with a project ID (VEC-NNN).
Branches must follow the pattern `VEC-NNN-description`.

## Trigger
- PreToolUse:Edit — Block file edits on non-conforming branches
- PreToolUse:Write — Block new file creation on non-conforming branches

## Severity
BLOCK

## Rule

Before editing or creating any file, check the current git branch name.

**ALLOWED branch patterns:**
- `VEC-[0-9]+-*` (e.g., VEC-001-pin-dependencies, VEC-042-add-monitoring)
- `main` (read-only operations only — no edits on main)

**BLOCKED branch patterns:**
- `feature/*` — Must use VEC-NNN prefix instead
- `fix/*` — Must use VEC-NNN prefix instead
- `hotfix/*` — Must use VEC-NNN prefix instead
- Any branch not matching `VEC-[0-9]+-*`

**EXEMPT paths** (may be edited on any branch for bootstrap):
- `.claude/` — hookify rules and settings
- `governance/` — governance infrastructure
- `CLAUDE.md` — project instructions

## Enforcement Message

When blocking, output:
```
BLOCK: Branch name does not follow VEC-NNN-description pattern.
Current branch: <branch_name>
Required pattern: VEC-NNN-description (e.g., VEC-001-pin-dependencies)

To fix:
1. Register a project: edit governance/projects/registry.json
2. Create a charter: governance/charters/VEC-NNN-<name>.md
3. Create branch: git checkout -b VEC-NNN-description
```
