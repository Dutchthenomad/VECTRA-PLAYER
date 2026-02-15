#!/usr/bin/env bash
# Validate that the current branch follows VEC-NNN-description pattern.
# Used as a pre-commit hook and in CI.
#
# Allowed patterns:
#   - VEC-NNN-description (e.g., VEC-001-pin-dependencies)
#   - main
#
# Exit codes:
#   0 = valid
#   1 = invalid

set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# Allow main branch (CI runs on main after merge)
if [ "$BRANCH" = "main" ]; then
    exit 0
fi

# Allow detached HEAD (CI checkout)
if [ "$BRANCH" = "HEAD" ]; then
    exit 0
fi

# Validate VEC-NNN-description pattern
if echo "$BRANCH" | grep -qE '^VEC-[0-9]+-[a-z0-9]([a-z0-9-]*[a-z0-9])?$'; then
    exit 0
fi

echo "BLOCK: Branch name does not follow VEC-NNN-description pattern."
echo "  Current branch: $BRANCH"
echo "  Required: VEC-NNN-description (e.g., VEC-001-pin-dependencies)"
echo ""
echo "To fix:"
echo "  1. Register a project in governance/projects/registry.json"
echo "  2. Create a charter in governance/charters/"
echo "  3. git checkout -b VEC-NNN-description"
exit 1
