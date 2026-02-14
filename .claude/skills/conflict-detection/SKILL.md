---
name: conflict-detection
description: Detect and log conflicts before they happen — port collisions, layer violations, file ownership overlaps, and contract breaks.
---

# Conflict Detection

Run this check before creating services, modifying ports, changing upstream/downstream
connections, or editing shared infrastructure files.

## Checks to Perform

### 1. Port Collision Detection

Read `docs/specs/PORT-ALLOCATION-SPEC.md` to get the current port registry.
If a new service is being created or a port is being changed:

1. Check if the requested port is already allocated
2. Check if the port falls within the correct range for the service layer
3. If collision detected: severity **REJECT**, log to `governance/conflicts/`

Port ranges:
- 9000-9009: Foundation Core (SACRED)
- 9010-9019: Subscriber Services
- 9020-9029: Analysis Services
- 9030-9039: External Integrations
- 9222: Chrome CDP (fixed)

### 2. File Ownership Detection

Read `governance/projects/registry.json` to get project scopes.
If a file is being modified:

1. Check if the file falls within another active project's scope
2. If overlap detected: severity **WARN**, note in conflict log

### 3. Layer Dependency Violation

Services are layered:
- **L0** (Source): foundation
- **L1** (Pipeline Core): rugs-feed, rugs-sanitizer
- **L2** (Intelligence): feature-extractor, decision-engine, v2-explorer
- **L3** (Action): execution, monitoring
- **L4** (Presentation): nexus-ui, pipeline-ui

Rule: Layers may only depend **downward**. L2 can consume L1, but NOT L3.

If a service imports from or connects to a higher layer:
- Severity: **BLOCK**
- Log to `governance/conflicts/`

### 4. Contract Break Detection

If `services/*/manifest.json` is being modified:
1. Check that `events_consumed` still matches upstream `events_produced`
2. Check that port references are consistent with PORT-ALLOCATION-SPEC
3. If break detected: severity **REJECT**

## Conflict Log Format

Write conflict logs to `governance/conflicts/YYYY-MM-DD-VEC-NNN-<type>.md`:

```markdown
# Conflict: <type>

- **Severity:** BLOCK|REJECT|CRITICAL
- **Project:** VEC-NNN
- **Detected:** ISO-8601 timestamp
- **Description:** What was detected
- **Resolution:** How it was resolved (fill in after resolution)
- **Status:** Open|Resolved
```

## Apprise Notification

For BLOCK+ severity, notify via VPS Apprise:

```bash
curl -X POST http://72.62.160.2:8901/notify \
  -H "Content-Type: application/json" \
  -d '{"title": "VECTRA Conflict: <type>", "body": "<description>", "type": "warning"}'
```

## When to Run This Skill

- Before `scripts/new-service.sh` creates a service
- Before modifying `docs/specs/PORT-ALLOCATION-SPEC.md`
- Before modifying any `manifest.json`
- Before creating cross-service imports or WebSocket connections
- On CI: as part of contract verification job
