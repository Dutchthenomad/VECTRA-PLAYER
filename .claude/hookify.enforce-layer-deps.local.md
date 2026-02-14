# Hookify Rule: Enforce Layer Dependencies

## Purpose
Services are organized in layers. Dependencies may only flow downward.
This prevents circular dependencies and maintains clean architecture.

## Trigger
- PreToolUse:Edit — When editing service code that imports from or connects to other services
- PreToolUse:Write — When creating new service code

## Severity
BLOCK

## Rule

Layer hierarchy (higher number = higher layer):
- L0 (Source): foundation
- L1 (Pipeline Core): rugs-feed, rugs-sanitizer, recording
- L2 (Intelligence): optimization, feature-extractor, decision-engine
- L3 (Action): execution, monitoring
- L4 (Presentation): nexus-ui

**Allowed dependencies:** A service may only depend on services in a LOWER layer.
- L2 can consume L1 feeds
- L3 can consume L2 and L1 feeds
- L4 can consume all layers via HTTP/WS proxy

**Forbidden dependencies:**
- L1 cannot depend on L2, L3, or L4
- L2 cannot depend on L3 or L4
- Lateral dependencies within the same layer are WARN (allowed but discouraged)

## Detection

When editing a service's code:
1. Read the service's `manifest.json` to determine its layer
2. Check any upstream/import references to other services
3. Read the target service's `manifest.json` to determine its layer
4. If target layer >= source layer, severity is BLOCK

## Enforcement Message

```
BLOCK: Layer dependency violation detected.
Service '<name>' (L2) cannot depend on '<target>' (L3).
Dependencies must flow downward: L0 ← L1 ← L2 ← L3 ← L4
```
