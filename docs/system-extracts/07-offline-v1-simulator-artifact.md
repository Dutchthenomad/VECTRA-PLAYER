# System 07: Offline V1 Simulator Artifact (Agnostic Revision)

Legacy source basis: `VECTRA-BOILERPLATE`

## Legacy Extraction Summary

Current artifact is an offline analysis workspace using local file uploads and in-browser simulation controls.

Representative evidence:

```json
// src/artifacts/tools/scalping-bot-v1-simulator/manifest.json:1-12
{
  "name": "scalping-bot-v1-simulator",
  "events_consumed": [],
  "events_emitted": []
}
```

```html
<!-- src/artifacts/tools/scalping-bot-v1-simulator/index.html:224-227 -->
<p class="desc">
  V1 bot design sandbox. Load prerecorded games, toggle between system presets, run drift-anchored TP/SL permutations,
  and inspect outcome windows in SOL before any live implementation decisions.
</p>
```

```javascript
// src/artifacts/tools/scalping-bot-v1-simulator/main.js:24-43
const PROFILE_PRESETS = {
  V1_MOMENTUM_CORE: {
    label: "V1 Momentum Core",
    values: { classificationTicks: 20, entryCutoffTick: 55, ... }
  }
}
```

## Agnostic Target Boundary

Retain this as a pure analysis UI shell with optional backend compute adapter.

- Offline mode:
  - fully local browser run
- Connected mode:
  - calls `simulator-service` for large or reproducible runs

## Target Contract (Recommended)

- `POST /simulator/runs`
- `GET /simulator/runs/{id}`
- `POST /simulator/runs/{id}/inspect`

Mode switch recommendation:

- `mode=local` -> browser compute
- `mode=remote` -> backend compute

## Cleanup Checklist

1. Extract simulation math into reusable shared library.
2. Keep UI presets declarative and versioned.
3. Add import validation schema for `.json`/`.jsonl` datasets.
4. Add export format for reproducible run configs.
5. Keep artifact independent from provider-specific runtime state.

## Migration Notes

- This module is useful as an R&D workbench and should remain fast to iterate.
- For team review and auditability, prefer remote run mode with persisted outputs.
