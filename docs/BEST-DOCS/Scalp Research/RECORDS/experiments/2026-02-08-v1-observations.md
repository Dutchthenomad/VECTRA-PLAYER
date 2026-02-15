# Scalping V1 Simulator Observations

Date: 2026-02-08

This document captures the latest understanding from the V1 toggleable bot simulator run on a 500-game sample.

## Run Context

- Artifact: `src/artifacts/tools/scalping-bot-v1-simulator/index.html`
- Data shape: prerecorded game files with tick-by-tick `prices[]`
- Sample size: `500` games (secondary results window listing)
- Scope assumptions: no latency, no slippage, no fee model, no rug-hazard overlays
- Evidence source: session-observed per-game results table (ranked by net SOL)

## Key Observations from the 500-Game Table

1. The per-game outcome envelope was approximately:
- best net: `+0.0126 SOL` (end `1.0126`)
- worst net: `-0.0163 SOL` (end `0.9837`)

2. The crossover from positive to non-positive outcomes appeared near ranks `301..304`, implying about `~60%` of games were non-negative at displayed precision.

3. Tail asymmetry is visible:
- best single-game upside (`+1.26%`) is smaller than worst single-game downside (`-1.63%`) in normalized per-game terms.

4. Exit behavior in the displayed table was mostly `TP/TIME` with very few `SL` hits in higher-ranked rows, which implies stop-loss often remained inactive while time exits did most of the cleanup.

5. High-ranked outcomes were concentrated in `trend_up`, `trend_down`, and `expansion` classifications, with `uncertain` and `chop` present but less dominant.

6. Typical trade counts per game in the ranked section were mostly `2..4`, indicating this setup is capturing short burst opportunities rather than heavy trade frequency.

## Design Implications (Current Understanding)

1. Keep the momentum-led V1 profile family as the baseline exploration anchor.
2. Add first-class toggles for regime filtering (`ALL` vs `trend_up+expansion`) to reduce noise participation.
3. Add SL strictness modes because current behavior suggests time-exit is carrying most risk control.
4. Use regime-aware risk scaling (stake reduction in `uncertain`/`chop`) rather than one-size-fits-all stake.
5. Evaluate profile quality using both return and downside metrics, not top-net ranking alone.

## Status Checkpoint

- V1 simulator artifact is in place and runnable.
- Current profile family appears productive enough to continue exploration.
- Next phase should formalize toggle A/B tests and then run Monte Carlo robustness on shortlisted policies.
