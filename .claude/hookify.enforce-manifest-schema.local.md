# Hookify Rule: Enforce Manifest Schema

## Purpose
Every service must have a manifest.json with a consistent schema. This ensures
contract verification and service discovery work correctly.

## Trigger
- PreToolUse:Write — When creating files under `services/*/`
- PreToolUse:Edit — When editing `services/*/manifest.json`

## Severity
BLOCK

## Rule

When creating or modifying a `manifest.json` under `services/`:

1. Must be valid JSON
2. Must contain ALL required fields:
   - `name` (string)
   - `version` (string, semver)
   - `layer` (string: L0, L1, L2, L3, or L4)
   - `port` (integer)
   - `health` (string, health endpoint path)
   - `events_consumed` (array of strings)
   - `events_produced` (array of strings)
3. Optional fields: `upstream`, `feeds`, `stats`, `description`

When creating a NEW service directory under `services/`:
- A `manifest.json` MUST be included
- Use `scripts/new-service.sh` to generate the skeleton

## Enforcement Message

```
BLOCK: manifest.json missing required field: <field>
Required fields: name, version, layer, port, health, events_consumed, events_produced

Use scripts/new-service.sh to generate a valid service skeleton.
```
