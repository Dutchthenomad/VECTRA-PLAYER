# Scalping V1 Simulator Runbook

Date: 2026-02-08

This runbook defines the reliable launch path for the V1 toggleable simulator.

## Canonical URL

When serving `src/artifacts` statically:

`/tools/scalping-bot-v1-simulator/index.html`

Example full URL:

`http://127.0.0.1:49673/tools/scalping-bot-v1-simulator/index.html`

## Launch

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE/src/artifacts
python3 -m http.server 49673 --bind 127.0.0.1
```

## Load and Run

1. Load dataset file(s):
- `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60_quick500.jsonl`
- `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60.jsonl`
2. Select profile preset (`V1 Momentum Core` recommended baseline).
3. Click `Run V1 Simulation`.
4. Review:
- Primary results window (permutation leaderboard)
- Secondary results window (per-game SOL outcomes)
- Game inspector trace

## Smoke Checklist

1. URL returns `HTTP 200`.
2. Files load and dataset count updates.
3. Run completes with populated primary and secondary tables.
4. Inspect selected game renders chart + trade table.
