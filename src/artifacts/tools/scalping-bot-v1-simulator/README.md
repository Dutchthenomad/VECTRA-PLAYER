# Scalping Bot V1 Simulator (Prototype Dev Lab)

Simple offline artifact for testing toggleable V1 bot profiles on prerecorded games.

## Workflow

1. Load `.json` or `.jsonl` recorded game files.
2. Pick a V1 bot profile preset (or custom).
3. Click `Run V1 Simulation`.
4. Read:
- Primary results window: best permutation + leaderboard.
- Secondary results window: per-game net/end SOL outcomes.
- Inspector window: one game chart + trade-level trace.

## Data Source Compatibility

Accepts the same recording formats as `scalping-explorer`:
- direct game arrays containing `prices[]`
- JSONL rows with nested payloads and game history
- complete game records with embedded `raw_json`

## Recommended Files

- `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60_quick500.jsonl`
- `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60.jsonl`
