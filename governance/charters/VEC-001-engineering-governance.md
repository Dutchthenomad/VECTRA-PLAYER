# VEC-001: Engineering Governance & DevOps Foundation

## Objectives

Establish automated engineering discipline for VECTRA. The project has working services
and tests but zero governance guardrails — no CI/CD, no branch protection, no dependency
pinning, no commit conventions. This charter covers the complete governance foundation.

Primary failure mode: **architecture drift** — services silently deviating from
established patterns, ports, contracts, and conventions.

## Scope

### In Scope

- `governance/` — project registry, charters, conflict logs, templates
- `.github/workflows/ci.yml` — CI pipeline (validate-branch, lint, test, contracts, docker)
- `.pre-commit-config.yaml` — branch name, commit message, ruff hooks
- `scripts/validate-branch-name.sh` — branch name validation
- `scripts/validate-commit-msg.sh` — commit message validation
- `.claude/hookify.enforce-project-id.local.md` — project ID enforcement
- `.claude/skills/conflict-detection/` — conflict detection skill
- `services/*/requirements.txt` — pin all dependencies
- `services/*/.dockerignore` — add to all services with Dockerfiles
- GitHub branch protection rules for `main`

### Out of Scope

- Service business logic changes
- Frontend rebuild (Phase 3, separate charter)
- Service template generator (Phase 2, separate charter)
- VPS deployment (Phase 1.8, separate charter)
- Test suite audit (Phase 1.6, separate charter)

## Guardrails

- No direct pushes to main after branch protection is enabled
- No force pushes to main ever
- All new branches must follow VEC-NNN-description pattern
- All commits must start with VEC-NNN:
- No unpinned dependencies (>= is forbidden in requirements.txt)
- Port allocation spec remains canonical

## Deliverables

1. `governance/` directory with registry, templates, severity definitions
2. Hookify rule blocking edits without project ID branch
3. Pre-commit hooks for branch name and commit message validation
4. Conflict detection skill
5. Pinned dependencies for all services
6. .dockerignore for all services with Dockerfiles
7. GitHub Actions CI pipeline with 5 job types
8. Branch protection on main

## Definition of Success

- `governance/projects/registry.json` exists with VEC-001 registered
- Branch name validation rejects `feature/foo` but accepts `VEC-002-foo`
- Commit message validation rejects `fix stuff` but accepts `VEC-001: fix stuff`
- `ruff check` passes clean across all Python services
- `pytest` passes for all services with pinned deps
- GitHub Actions CI runs on PR with all jobs passing
- Direct push to `main` is blocked
