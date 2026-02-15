# 09 Operations Runbook

Status: active
Last validated: 2026-02-08

## Objective

Provide one practical run path for explorer and V1 simulator artifacts.

## A) Scalping Explorer (Preferred Control Surface)

Use the project control script:

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE
./scripts/scalping_explorer_ctl.sh start
./scripts/scalping_explorer_ctl.sh smoke
./scripts/scalping_explorer_ctl.sh open
```

Stop:

```bash
./scripts/scalping_explorer_ctl.sh stop
```

Notes:

1. URL path is `/tools/scalping-explorer/index.html`.
2. Script tracks PID/port/log in `.run/`.
3. Default bind host is `127.0.0.1` with auto-incrementing port behavior.

## B) V1 Bot Simulator (Static Server Path)

Launch from artifacts root with a chosen port:

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE/src/artifacts
PORT=49673
python3 -m http.server "$PORT" --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:${PORT}/tools/scalping-bot-v1-simulator/index.html
```

## C) Dataset Load Paths

Recommended files:

1. `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60_quick500.jsonl`
2. `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60.jsonl`
3. `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min30.jsonl`

## D) Smoke Checklist

1. URL returns HTTP 200.
2. Dataset loads and game count updates.
3. Run completes and tables populate.
4. Inspector/trace renders selected game output.

## E) Common Failure Patterns

1. Wrong route family (`/artifacts/tools/...`) when server expects `/tools/...`.
2. Port already in use.
3. Serving from wrong directory (must be `src/artifacts` for static path).
4. Running ad-hoc without control script for explorer (PID drift and stale ports).

## Legacy Runbook Records

1. `../RECORDS/legacy-flat/SCALPING-EXPLORER-RUNBOOK.md`
2. `../RECORDS/legacy-flat/SCALPING-V1-SIMULATOR-RUNBOOK.md`
