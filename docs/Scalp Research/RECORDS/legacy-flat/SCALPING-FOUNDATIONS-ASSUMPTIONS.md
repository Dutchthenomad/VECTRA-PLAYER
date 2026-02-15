# Scalping Foundations and Assumptions

Date: 2026-02-08

This document defines the modeling boundaries for the current research system.

## Scope

The system is an offline research explorer for discovering bot-friendly scalp patterns from prerecorded game data.

Core workflow:

1. Load recorded games with tick-by-tick `prices[]`
2. Classify early-game behavior into regime
3. Generate entry signals using playbook rules (single-playbook or regime-gated auto)
4. Simulate exits (TP/SL/time) with one active position at a time
5. Report outcomes in both return% and SOL terms (current bot path is SOL-first)

## Active System Surfaces (Current)

1. `src/artifacts/tools/scalping-explorer/index.html`
- Main exploration lab for classifier + playbook + drift-permutation sweeps.

2. `src/artifacts/tools/scalping-bot-v1-simulator/index.html`
- V1 policy prototyping surface with profile presets, toggle controls, and primary/secondary outcome windows.

## Explicit Assumptions

1. No latency modeling.
2. No slippage modeling.
3. No fee modeling.
4. No second/third-order hazard overlays (including rug hazard) in current optimization objective.
5. Long-only strategy path in current prototype.
6. One active position at a time in bot simulation.

These are deliberate simplifications for first-principles edge discovery.

## Core Definitions

- `Classification Ticks`: early ticks used to infer regime.
- `No-New-Entry After Tick`: hard stop for opening new trades.
- `Max Hold Ticks`: latest forced exit if TP/SL not hit.
- `One-Tick Drift Reference`: percentile anchor (P50/P75/P90) used to scale TP/SL thresholds.
- `TPx/SLx`: integer multipliers over drift reference to create exit thresholds.
- `Net SOL`: sum of per-trade SOL PnL.
- `End SOL`: `starting bankroll + net SOL`.
- `Per-Game End SOL`: per-game normalized outcome used in V1 secondary window to compare game-level contribution spread.

## Why Entry Quality Is Primary

Exit tuning can optimize around a weak edge, but cannot create edge where entries are noise.
Therefore the optimization order is:

1. Entry signal discovery and validation
2. Exit surface optimization on top of strong entries
3. Robustness and risk calibration

## Data and Sampling Foundations

Canonical source for current work:

- `/home/devops/rugs_data/events_parquet/doc_type=complete_game`
- Exported to `/home/devops/rugs_data/exports/scalping_explorer`

Current canonical analysis dataset:

- `scalping_unique_games_min60.jsonl` (1,772 games)

## Design Principle

Prefer broad plateaus over sharp local maxima.

A strategy is higher quality when it remains good under nearby parameter perturbations.

## Current Risk Readout Principle

Ranking by top net alone is insufficient.
Current policy evaluation should include:

1. `Net/End SOL` central tendency.
2. Downside anchors (`p10_game_net_sol`, worst-game net).
3. Participation quality (trade count and no-trade collapse avoidance).
