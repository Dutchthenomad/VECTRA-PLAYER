# Scalping Explorer (Prototype Dev Lab)

Offline HTML artifact for strategy exploration using prerecorded games.

## Purpose

- Load prerecorded game data (`.json` / `.jsonl`)
- Classify each game from configurable baseline ticks
- Gate deterministic scalp playbooks by regime
- Limit late-game entries with configurable no-new-entry cutoff tick
- Simulate fixed-hold exits (3/5/7 ticks)
- Tune a single simulated bot using one-tick drift-based TP/SL multiplier permutations
- Review SOL-denominated outcomes (net SOL and end-of-game SOL) in a separate results window
- Inspect game-level trades on chart + table
- Use beginner-friendly help overlays (Quick Start, Controls, Results, Glossary)

## Notes

- This prototype intentionally favors debug readability over polished UI.
- It runs client-side only.
- No live Foundation WebSocket dependency.

## Open

Serve artifacts via Foundation HTTP and open:

`http://localhost:9001/artifacts/scalping-explorer/`

Or serve `src/artifacts/` directly and open:

`http://127.0.0.1:47911/tools/scalping-explorer/index.html`

Or open directly from filesystem if browser allows local file reads.

## Recommended Dataset Files

Generated canonical exports live here:

`/home/devops/rugs_data/exports/scalping_explorer`

Start with:

`/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60_quick500.jsonl`

Then scale to:

`/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60.jsonl`
