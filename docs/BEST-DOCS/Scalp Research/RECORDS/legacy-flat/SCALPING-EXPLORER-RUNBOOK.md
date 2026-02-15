# Scalping Explorer Runbook (Never-Again Baseline)

This runbook defines a single reliable way to launch and verify the offline artifact.

## Canonical URL

Use this path format for direct static serving:

`/tools/scalping-explorer/index.html`

For Foundation HTTP mode, use:

`/artifacts/scalping-explorer/`

Do not use `/artifacts/tools/scalping-explorer/index.html` with Foundation mode.

## Single Control Surface

Use the control script:

```bash
./scripts/scalping_explorer_ctl.sh start
./scripts/scalping_explorer_ctl.sh smoke
./scripts/scalping_explorer_ctl.sh open
```

Stop when finished:

```bash
./scripts/scalping_explorer_ctl.sh stop
```

## Zero-Ambiguity Checklist

1. `status` shows `running` and a URL.
2. `smoke` returns `HTTP/1.0 200 OK` and `Smoke test passed.`
3. Browser URL matches the exact reported URL.
4. If using Foundation mode, ensure Foundation is started from project `.venv`.

## Failure Modes to Avoid

1. Wrong route family:
`/artifacts/tools/...` is not a valid Foundation route.

2. Wrong Python interpreter:
Foundation requires dependencies from this repo's virtual environment.

3. Untracked ad-hoc server commands:
Always use `scripts/scalping_explorer_ctl.sh` so PID/port/log state is explicit.

4. Module/runtime confusion from other artifacts:
Scalping explorer is offline-first and does not require live Foundation WebSocket.

## Companion Artifact

For the dedicated V1 toggleable bot surface, use:

- `SCALPING-V1-SIMULATOR-RUNBOOK.md`
