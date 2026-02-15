# VECTRA DevOps Standards

**Origin:** 9 foundational rules from a 20-year veteran developer, adapted for
AI-assisted development with Claude Code.

**Status:** Implemented in VEC-001 | **Date:** 2026-02-14

---

## The 9 Rules

### 1. Lock Project Isolation Using Project IDs

Every unit of work gets a unique project ID: `VEC-001`, `VEC-002`, etc.

- Branch names: `VEC-NNN-description`
- Commit messages: `VEC-NNN: description`
- PR titles: must include `VEC-NNN`

**Implementation:**
- `governance/projects/registry.json` — project registry
- `scripts/validate-branch-name.sh` — pre-commit hook
- `scripts/validate-commit-msg.sh` — commit-msg hook
- `.github/workflows/ci.yml` — CI gate validates on PR

---

### 2. Create a Master Project Folder as the Operating System

The `governance/` directory is the control plane for all development. It
enforces rules, tracks work, detects conflicts, and alerts on violations.

```
governance/
├── projects/registry.json    # Project ID registry
├── charters/VEC-NNN-*.md     # One charter per project
├── conflicts/                # Conflict incident logs
├── rules/severity-levels.md  # Severity definitions
└── templates/                # Charter + conflict templates
```

**Implementation:** `governance/` directory with all subdirectories and templates.

---

### 3. Write Project Charters Before Doing Anything

Before ANY work begins, write a charter at `governance/charters/VEC-NNN-<name>.md`
covering:

- **Objectives** — What we're building/fixing and why
- **Scope (In/Out)** — What we ARE and ARE NOT touching
- **Guardrails** — Constraints that must not be violated
- **Deliverables** — Concrete outputs (files, tests)
- **Definition of Success** — Measurable criteria for "done"

**Implementation:** `governance/templates/charter.md` — charter template.

---

### 4. Aggressively Enforce "No Project ID, No Work"

This is the single most important rule. Without a project ID, nothing happens.

| Layer | Enforcement |
|-------|------------|
| Claude Code session | `hookify.enforce-project-id.local.md` blocks edits on non-VEC branches |
| Git commits | `scripts/validate-commit-msg.sh` blocks commits without VEC-NNN: prefix |
| Git branches | `scripts/validate-branch-name.sh` blocks non-VEC branch names |
| GitHub PRs | CI `validate-branch` job blocks PRs from non-conforming branches |
| Merge to main | Branch protection requires all CI checks to pass |

**Implementation:** 4-layer enforcement stack (hookify, pre-commit, CI, branch protection).

---

### 5. Install Conflict Detection

A skill that detects conflicting actions before they happen:

| Conflict Type | Detection Method |
|---------------|-----------------|
| Port collision | Check PORT-ALLOCATION-SPEC against new service |
| File ownership | Two projects modifying same files |
| Layer violation | Service importing from wrong layer |
| Contract break | Envelope format changed without version bump |
| Dependency conflict | Two services pinning different versions |

**Implementation:** `.claude/skills/conflict-detection/SKILL.md`

---

### 6. Log All Detected Conflicts

Every conflict gets a dedicated log file at `governance/conflicts/`:

```
governance/conflicts/
├── 2026-02-14-VEC-001-port-collision.md
├── 2026-02-15-VEC-003-layer-violation.md
└── ...
```

Each entry records: severity, project ID, timestamp, description, resolution, status.

**Implementation:** `governance/templates/conflict.md` — conflict log template.

---

### 7. Pipe Errors to a Messenger Bot

BLOCK/REJECT/CRITICAL events are routed to the Open Claw agent bot on VPS
via Apprise API.

| Severity | Notification |
|----------|-------------|
| INFO | Conflict log only |
| WARN | Conflict log only |
| BLOCK | Conflict log + Apprise notification |
| REJECT | Conflict log + Apprise notification |
| CRITICAL | Conflict log + Apprise notification + session halt |

**VPS Apprise endpoint:** `http://72.62.160.2:8901/notify`

**Implementation:** Conflict detection skill calls Apprise on BLOCK+ severity.

---

### 8. Define Error Severity Levels Up Front

Defined once, used everywhere. No ad-hoc severity decisions.

| Level | Action | Example |
|-------|--------|---------|
| **INFO** | Log only, continue | New file created in services/ |
| **WARN** | Log + notify, continue | Test coverage dropped below 70% |
| **BLOCK** | Prevent action, require fix | Branch name missing project ID |
| **REJECT** | Prevent action, log conflict | Port already allocated |
| **CRITICAL** | Prevent + alert + halt | Force push to main attempted |

**Implementation:** `governance/rules/severity-levels.md`

---

### 9. Kill Everything That Is Fast but Wrong

Safety over speed. Always.

This principle is enforced through the entire governance stack:

- **17 hookify rules** block architecture drift in real-time
- **Pre-commit hooks** catch format and naming violations before they enter git
- **CI pipeline** catches broken code before it reaches main
- **Branch protection** prevents merges without passing CI
- **Contract tests** prevent breaking service communication
- **Service templates** prevent ad-hoc service creation

If it's fast but skips a rule, it gets blocked.

---

## Enforcement Stack Summary

| Layer | Mechanism | When It Fires | Severity |
|-------|-----------|--------------|----------|
| **Session** | 17 hookify rules | Every file edit/write in Claude Code | BLOCK |
| **Commit** | Pre-commit hooks (ruff, branch name, commit msg) | Every `git commit` | BLOCK |
| **PR** | GitHub Actions CI (7 gates) | Every push / PR | BLOCK |
| **Merge** | Branch protection (GitHub ruleset) | Before merge to main | BLOCK |
| **Contract** | `tests/verify_contracts.py` (81 tests) | CI pipeline | REJECT |
| **Frontend** | TypeScript + Vitest + Storybook + Vite build | CI pipeline | BLOCK |
| **Template** | `scripts/new-service.sh` | Service creation | BLOCK |
| **Alert** | Apprise messenger bot | BLOCK+ severity events | CRITICAL |

---

## Service Layer Architecture

Services are classified into layers. Dependencies flow **downward only**.

| Layer | Services | Role |
|-------|----------|------|
| **L0** | foundation | Chrome CDP bridge, WebSocket broadcast |
| **L1** | rugs-feed, rugs-sanitizer, recording | Ingest, dedup, validate |
| **L2** | optimization, feature-extractor, decision-engine | Intelligence |
| **L3** | execution, monitoring | Trade execution, health |
| **L4** | nexus-ui | React frontend |

---

## Cost Optimization Strategies

### Multi-Model Routing

Use tiered model hierarchy based on task complexity:

| Tier | Task Type | Model | Cost |
|------|-----------|-------|------|
| 1 | Heartbeats, system checks | Local LLM (ollama/qwen3:8b) | Free |
| 2 | Web research, data scraping | claude-3-haiku | Cheap |
| 3 | Email drafting, reasoning | claude-3.5-sonnet | Balanced |
| 4 | Complex coding, architecture | claude-opus-4-6 | Premium |

### Context Bloat Prevention

- Clear conversation histories regularly
- Use `/clear` with scratchpad skill to preserve key context
- Keep CLAUDE.md under 500 lines
- Disconnect unused MCP servers via `/mcp`
- Use `model: haiku` for simple subagents

### Token Efficiency

- Set effort parameter appropriately (`low`/`medium` for simple tasks)
- Use prompt caching for repeated system prompts
- Estimate token cost before large tasks
- Use batch API for bulk/non-urgent operations

---

## Feature Development Workflow

Every feature follows this 10-step workflow. No exceptions.

```
 0. Charter   -> Write project charter (objectives, scope, guardrails)
 1. Register  -> Get project ID (VEC-NNN) from registry.json
 2. Branch    -> git checkout -b VEC-NNN-description main
 3. Storybook -> Build UI components in isolation, visual review
 4. Tests     -> Write Vitest tests for logic (not UI chrome)
 5. Wire      -> Connect to real service data via WebSocket/HTTP
 6. PR        -> Push, open PR, CI runs 7 gates automatically
 7. Preview   -> Vercel deploys preview URL (future)
 8. Review    -> User reviews Storybook + preview URL visually
 9. Merge     -> Squash merge to main after all CI gates pass
```

### CI Gates (All Must Pass for Merge)

| Gate | Tool | Severity |
|------|------|----------|
| Branch Name | `validate-branch-name.sh` | BLOCK |
| Commit Messages | `validate-commit-msg.sh` | BLOCK |
| Python Lint | `ruff check` + `ruff format --check` | BLOCK |
| Service Tests | `pytest` per service (matrix) | BLOCK |
| Root Tests | `pytest` on src/tests/ | BLOCK |
| Contract Tests | `tests/verify_contracts.py` (81 tests) | REJECT |
| TypeScript Check | `tsc --noEmit` | BLOCK |
| Vitest | `vitest run` | BLOCK |
| Storybook Build | `storybook build` | WARN |
| Production Build | `vite build` | BLOCK |
| Docker Build | `docker compose build` | BLOCK |

---

## Frontend Stack (nexus-ui)

| Tool | Version | Purpose |
|------|---------|---------|
| Vite | 6 | Build tool + dev server (instant HMR) |
| React | 19 | UI framework |
| TypeScript | strict | Type safety |
| Tailwind CSS | 4 | Utility-first styling |
| shadcn/ui | latest | Copy-paste component library |
| Storybook | 8 | Visual component dev + review |
| Vitest | latest | Unit/integration tests |

### Frontend Commands

```bash
cd services/nexus-ui
npm run dev          # Start Vite dev server (port 3000)
npm run build        # Production build to dist/
npm run test         # Run Vitest
npm run typecheck    # TypeScript check
npm run storybook    # Storybook dev server (port 6006)
```

---

## Quick Start for New Projects

```bash
# 1. Register project
#    Edit governance/projects/registry.json, increment next_id

# 2. Write charter
cp governance/templates/charter.md governance/charters/VEC-NNN-name.md
#    Fill in objectives, scope, guardrails, deliverables, success criteria

# 3. Create branch
git checkout -b VEC-NNN-description main

# 4. Work (all commits must start with VEC-NNN:)
git commit -m "VEC-NNN: description of change"

# 5. Push and open PR
git push -u origin VEC-NNN-description
gh pr create --title "VEC-NNN: title"

# 6. CI runs 7 gates automatically, merge after all pass
```

## Quick Start for New Services

```bash
# Generate service skeleton with all required files
./scripts/new-service.sh <name> <layer> <upstream-port>

# Example: create an L2 service consuming from rugs-sanitizer
./scripts/new-service.sh signal-detector L2 9017
```

---

*These standards apply to all VECTRA projects. No exceptions.*
