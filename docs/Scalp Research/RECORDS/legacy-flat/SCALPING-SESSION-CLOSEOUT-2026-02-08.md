# Scalping Research Session Closeout (2026-02-08)

Last updated: 2026-02-08

## Purpose

This is the consolidated checkpoint for this session. It captures:

1. What is validated by data (fact).
2. What is still exploratory (hypothesis).
3. What we should run next in V2 research.

## Scope and Boundaries

1. This work is offline research on pre-recorded games.
2. No live feed integration is in scope yet.
3. No code or config changes were made to `/home/devops/rugs-data-pipeline`.
4. Simulator assumptions still exclude latency/slippage/fees unless explicitly added in a run.

## Data and Artifacts Used

1. Canonical dataset: `scalping_unique_games_min60.jsonl` (`1,772` games).
2. Larger-pass dataset: `scalping_unique_games_min30.jsonl` (`2,056` games).
3. Main artifact family:
- `src/artifacts/tools/scalping-bot-v1-simulator/index.html`
- `src/artifacts/tools/scalping-optimization-planner/index.html`
4. Core analysis docs:
- `SCALPING-LONG-SHORT-EDGE-STUDY-2026-02-08.md`
- `SCALPING-TRIGGER-VARIANTS-VALIDATION-2026-02-08.md`
- `SCALPING-TA-TOOLKIT-BRAINSTORM.md`
- `SCALPING-CLASSIFICATION-AND-REGIME-PRIMER.md`

## Empirically Validated Findings (Current Facts)

1. Long-side concentrated rebound contexts are the strongest current edge family.
2. A narrow expansion-pullback pocket showed materially better behavior than broad naive filters:
- `n=42`, `+5% hit in 5 ticks: 54.8%`, `<= -5% in 5 ticks: 16.7%`.
3. Short-side setups are not yet stable as a primary strategy:
- strict short niche can look positive in some slices, but split stability remains weak.
4. One-trade-per-game realism validation supports a higher-order long policy:
- `HOS_V1_SCORE_ROUTED` on `min60`: `n=1,054`, win `68.8%`, mean/median `+2.66% / +3.16%`.
- `HOS_V1_SCORE_ROUTED` on `min30`: `n=1,080`, win `68.9%`, mean/median `+2.63% / +3.19%`.
5. Coverage-quality balance currently favors `HOS_V1_SCORE_ROUTED` over narrower long variants.

## Tentative but Not Yet Final

1. Bayesian posterior regime engine as the primary decision layer.
2. Converted TA panel (price-only) as state estimators:
- EMA/SMA pressure, RSI/MACD momentum, Bollinger/ATR-style volatility, Donchian breakout context.
3. GameHistory priors (`2x/10x/50x/100x`) as hierarchical Bayesian context.
4. Short playbooks as secondary toggles until robust cross-split stability is proven.

## Decision Log (What We Agreed)

1. Prioritize entry-quality modeling first, then optimize exits.
2. Keep research grounded in source mechanics and deterministic PRNG constraints.
3. Treat large outliers and rare tails carefully; avoid overfitting.
4. Keep a strict split between:
- facts (validated outcomes),
- hypotheses (promising but unproven ideas).
5. Keep docs updated as first-class artifacts before each major design jump.

## Current Recommended Research Policy (Working Default)

1. Primary: `HOS_V1_SCORE_ROUTED` (long only).
2. Baselines: `L1_EXPANSION_IMMEDIATE`, `L3_HYBRID_SPLIT`.
3. Experimental only: `S1_BLOWOFF_STRICT_SHORT` with low weight.
4. Always track:
- median return,
- downside tail behavior,
- split stability by date/hash partitions.

## Known Gaps Before Production Claims

1. Fee/rake-adjusted PnL accounting not fully integrated into every evaluation path.
2. Full walk-forward validation (strict rolling train/holdout) still pending.
3. Confidence intervals/bootstrap uncertainty reporting should be standard in result tables.
4. Threshold sensitivity maps should be expanded for robustness drift detection.

## V2 Research Execution Order

1. Freeze a compact feature set for posterior regime scoring.
2. Run walk-forward validation on the frozen trigger family.
3. Add uncertainty reporting and fee-aware PnL side-by-side with current raw outcomes.
4. Promote only stable policies into the next simulator profile tier.
5. Keep short-side tracks sandboxed until they pass the same stability bar.

## Stop-Here Checkpoint

If this session is resumed later, start from:

1. `SCALPING-SESSION-CLOSEOUT-2026-02-08.md` (this file).
2. `SCALPING-TRIGGER-VARIANTS-VALIDATION-2026-02-08.md`.
3. `SCALPING-TA-TOOLKIT-BRAINSTORM.md`.
4. `SCALPING-LONG-SHORT-EDGE-STUDY-2026-02-08.md`.
