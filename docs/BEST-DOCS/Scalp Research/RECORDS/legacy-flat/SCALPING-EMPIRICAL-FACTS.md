# Scalping Empirical Facts ("Imperial Facts" Checkpoint)

Date: 2026-02-08

This document captures what is currently established from recorded-game data.
Numbers below are from canonical dataset exports and reproducible checkpoint files.

## Data Provenance

- Canonical dataset: `/home/devops/rugs_data/exports/scalping_explorer/scalping_unique_games_min60.jsonl`
- Unique games: `1,772`
- Source selection details: `SCALPING-DATASET-COLLECTION-REPORT.md`
- Raw metric checkpoint: `checkpoints/scalping_empirical_checkpoint_2026-02-08.json`

## Fact Set A: Return Envelope by Horizon (raw path windows)

Returns are in percent.

| Horizon (ticks) | Count | Mean | Median | P10 | P90 |
|---|---:|---:|---:|---:|---:|
| 1 | 452,504 | 0.0569 | 0.4939 | -1.9597 | 2.9211 |
| 2 | 450,732 | 0.5018 | 0.9560 | -16.0532 | 16.2924 |
| 3 | 448,960 | 0.9493 | 1.3994 | -18.2846 | 19.7883 |
| 4 | 447,188 | 1.3989 | 1.8035 | -19.3616 | 21.8892 |
| 5 | 445,416 | 1.8502 | 2.1902 | -20.0888 | 23.7247 |
| 7 | 441,872 | 2.7609 | 2.8157 | -21.3465 | 27.1902 |
| 10 | 436,556 | 4.1502 | 3.5014 | -24.2919 | 33.3538 |

## Fact Set B: 5-Tick Excursions (MAE / MFE)

- MAE p10: `-21.7930%`
- MAE p25: `-9.7748%`
- MAE p50: `-1.0696%`
- MFE p50: `3.7411%`
- MFE p75: `10.7467%`
- MFE p90: `24.8136%`

Interpretation: within 5 ticks, downside excursions can be materially large even when median favorable excursion is positive.

## Fact Set C: 5-Tick Touch Probabilities

### TP touch probability within 5 ticks

- TP 2%: `67.0607%`
- TP 4%: `47.8999%`
- TP 6%: `34.9758%`
- TP 8%: `28.1629%`
- TP 10%: `25.4331%`
- TP 12%: `24.6051%`
- TP 15%: `23.8956%`

### SL touch probability within 5 ticks

- SL 2%: `38.5538%`
- SL 4%: `28.4301%`
- SL 6%: `25.9820%`
- SL 8%: `25.3231%`
- SL 10%: `24.9609%`
- SL 12%: `24.5386%`
- SL 15%: `22.8131%`

## Fact Set D: First-Touch Behavior (5 ticks)

| Pair (SL/TP) | TP First | SL First | Neither |
|---|---:|---:|---:|
| -4 / +6 | 34.4229% | 26.1740% | 39.4032% |
| -6 / +8 | 27.9029% | 24.6821% | 47.4150% |
| -8 / +10 | 25.2429% | 24.5099% | 50.2472% |
| -10 / +12 | 24.4448% | 24.4302% | 51.1250% |
| -12 / +15 | 23.7755% | 24.1956% | 52.0289% |

## Fact Set E: Time-Exit-Backstopped TP/SL Grid (5 ticks)

Raw checkpoint: `checkpoints/scalping_tp_sl_timeexit_checkpoint_2026-02-08.json`

Mean return by pair:

- `-2 / +4`: `1.4047%`
- `-3 / +5`: `1.5993%`
- `-4 / +6`: `1.6908%`
- `-5 / +7`: `1.7351%`
- `-6 / +8`: `1.7555%`
- `-8 / +10`: `1.7694%`
- `-10 / +12`: `1.7709%`
- `-12 / +15`: `1.9939%`

## Fact Set F: Confirmed Tooling Facts (as implemented)

In the current artifact, bot optimization is now:

- SOL-denominated (`stake SOL`, `starting bankroll SOL`, `net SOL`, `end SOL`)
- Drift-derived TP/SL (one-tick drift reference `P50/P75/P90`)
- Multiplier permutation based (`TPx`/`SLx` ranges)
- Best permutation selected and shown with end-of-game SOL breakdown

Reference implementation:

- `src/artifacts/tools/scalping-explorer/index.html`
- `src/artifacts/tools/scalping-explorer/main.js`

## Fact Set G: V1 Simulator Operational Snapshot (500-game run)

Date observed: `2026-02-08`

Run surface:

- `src/artifacts/tools/scalping-bot-v1-simulator/index.html`

Observed in the session's ranked per-game outcome table (`500` rows):

- best per-game net: `+0.0126 SOL` (end `1.0126`)
- worst per-game net: `-0.0163 SOL` (end `0.9837`)
- positive to non-positive crossover near ranks `301..304` (`~60%` non-negative at displayed precision)
- high-ranked outcomes concentrated in `trend_up`, `trend_down`, `expansion`
- exit mixes in higher ranks were mostly TP/TIME-dominant with very low SL incidence

Interpretation:

- Current V1 signal is productive enough to continue exploration.
- Downside tail magnitude still exceeds best single-game upside, so strict downside-aware ranking remains mandatory.

Reference note:

- Detailed write-up: `SCALPING-V1-SIMULATOR-OBSERVATIONS-2026-02-08.md`
- This snapshot is operational evidence from artifact output (not a canonical JSON checkpoint yet).

## What Is Definitive vs Not

Definitive:

- The measured envelopes/touch rates above on the canonical `min60` dataset.
- The current simulator mechanics and output fields.

Not yet definitive:

- Whether a found edge survives out-of-distribution regime shifts.
- Whether top results are robust to small parameter perturbations.
- Whether entry signals currently used are globally optimal.
