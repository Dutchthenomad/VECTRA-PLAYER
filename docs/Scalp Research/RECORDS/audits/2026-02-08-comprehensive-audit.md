# Scalping System Comprehensive Audit

Date: 2026-02-08
Scope: VECTRA-BOILERPLATE scalping artifacts + `knowledge-export` (rugipedia, rl-design, external-docs)

## Inputs Reviewed

1. Artifact code
- `src/artifacts/tools/scalping-explorer/main.js`
- `src/artifacts/tools/scalping-bot-v1-simulator/main.js`
- `src/artifacts/tools/scalping-optimization-planner/main.js`

2. Research docs and checkpoints
- `docs/SCALP TRADING RESEARCH/*.md`
- `docs/SCALP TRADING RESEARCH/checkpoints/*.json`

3. Knowledge-export corpus
- `rugipedia/canon/*`
- `rugipedia/archive/Q_files_2025-12-27/review data/*` (selected)
- `rl-design/*`
- `external-docs/*` (selected index docs)

## Executive Summary

Current system quality is strong for fast offline hypothesis exploration, but it is not yet statistically sound for strategy promotion. The two largest blockers are:

1. Evaluation leakage/selection bias in permutation selection.
2. Non-path bankroll accounting that masks risk-of-ruin and drawdown structure.

If uncorrected, these can make weak strategies look robust. V2 should first harden evaluation and risk accounting before adding model complexity.

## Findings (Ordered by Severity)

### Critical 1: Canonical knowledge contamination (facts mixed with unmarked hypothesis)

Impact:
- Your "single source of truth" can feed contradictory claims into downstream RAG and design decisions.

Evidence:
- `rugipedia/CONTEXT.md:56` defines canonical promotion laws requiring live evidence and explicit theoretical marking.
- `rugipedia/canon/PROVABLY_FAIR_VERIFICATION.md:157` adds an unmarked claim that meta-layer manipulation is already proven.

Why this matters:
- This breaks evidence-tier hygiene and can bias optimization goals toward unverified narratives.

Recommendation:
1. Split `PROVABLY_FAIR_VERIFICATION.md` into:
- canonical factual section (verifiable algorithm/mechanics only),
- separate hypothesis appendix marked `theoretical`.
2. Add a hard validation tag field (`canonical|verified|reviewed|theoretical`) to every claim block.

---

### Critical 2: In-sample permutation selection bias (optimistic performance inflation)

Impact:
- Reported "best permutation" is chosen on the same data it is evaluated on, so performance is upward-biased.

Evidence:
- Drift stats are computed from the full filtered set: `src/artifacts/tools/scalping-bot-v1-simulator/main.js:933`.
- All permutations are evaluated on the same set: `src/artifacts/tools/scalping-bot-v1-simulator/main.js:955`.
- The top permutation is then selected by in-sample `netSol`: `src/artifacts/tools/scalping-bot-v1-simulator/main.js:996`, `src/artifacts/tools/scalping-bot-v1-simulator/main.js:1002`.

Observed symptom:
- Full-grid envelope has no negative-net configs, only positive or zero/no-trade (`positive=1740`, `zero=360`, `negative=0`), consistent with aggressive in-sample selection behavior.

Recommendation:
1. Add split-aware evaluation:
- Train split: choose permutation.
- Validation split: rank candidates.
- Test split: final report only.
2. Add walk-forward mode by date windows to reduce temporal leakage.

---

### High 3: Bankroll path is not enforced (risk understated)

Impact:
- SOL outcomes do not represent executable bankroll dynamics.

Evidence:
- PnL is computed as `retPct * stake` with fixed stake: `src/artifacts/tools/scalping-bot-v1-simulator/main.js:843`.
- End bankroll is post-hoc sum: `src/artifacts/tools/scalping-bot-v1-simulator/main.js:969`, `src/artifacts/tools/scalping-bot-v1-simulator/main.js:1019`.
- No affordability guard (trade still "executes" even if bankroll < stake), no liquidation/ruin logic.

Recommendation:
1. Simulate bankroll sequentially through each game path.
2. Enforce `stake <= available_cash`.
3. Track `max_drawdown`, ruin probability, and halted paths as first-class outputs.

---

### High 4: Exit surface currently acts mostly as time-exit, not TP/SL control

Impact:
- "TP/SL optimization" is often a mislabel; strategy edge is mostly from entry + time exit.

Evidence:
- Best checkpoint config uses wide thresholds (`TP +31.12%`, `SL -37.95%`) with `84.54%` time exits in Stage B top result:
  - `docs/SCALP TRADING RESEARCH/checkpoints/scalping_opt_sweep_2026-02-08.json` (`best_config.selected_tp_pct`, `best_config.selected_sl_pct`, `best_config.time_exit_pct`).
- Stage-B top-50 median time exits are similarly dominant (~87%).
- Threshold generation has lower bound but no upper cap relative to hold horizon: `src/artifacts/tools/scalping-bot-v1-simulator/main.js:773`.

Recommendation:
1. Re-anchor TP/SL to horizon-conditional excursions (e.g., conditional MFE/MAE for the chosen hold horizon and regime), not only global one-tick drift percentiles.
2. Add a "TP/SL activation rate" metric and minimum activation gate for promoted strategies.

---

### High 5: Quick dataset construction is time-biased, not stratified

Impact:
- Fast iteration set can overrepresent latest market regime and distort candidate ranking.

Evidence:
- Data is ordered by latest date: `scripts/build_scalping_dataset.py:73`.
- Quick set is first N rows from that order: `scripts/build_scalping_dataset.py:113`.

Recommendation:
1. Build quick set via stratified sampling over date buckets + regime + game length.
2. Keep a reproducible random seed and write sampled IDs to manifest.

---

### Medium 6: Planner artifact is static and can drift from reality

Impact:
- Planning numbers may become stale if checkpoints update.

Evidence:
- Baseline metrics are hardcoded constants: `src/artifacts/tools/scalping-optimization-planner/main.js:10`.

Recommendation:
1. Load baseline stats from checkpoint JSON at runtime (or import generated snapshot).
2. Show checkpoint timestamp/hash in UI.

---

### Medium 7: Reproducibility gap for checkpoint generation

Impact:
- Existing checkpoint outputs are present, but generation pipeline is not codified in repo for full replay.

Evidence:
- Visualization script consumes checkpoint files (`scripts/generate_scalping_outcome_visuals.py`) but no script in repo regenerates the optimization checkpoint suite end-to-end.

Recommendation:
1. Add a deterministic runner script that:
- builds datasets,
- runs Stage A/B/full-grid,
- writes checkpoint JSON + metadata,
- logs git SHA + config hash.

---

### Low 8: Canonical index path mismatch

Impact:
- Minor confusion for automation that follows file paths literally.

Evidence:
- `rugipedia/CONTEXT.md:26` references `PROVABLY_FAIR.md`, while actual file is `PROVABLY_FAIR_VERIFICATION.md`.

Recommendation:
1. Fix path in `CONTEXT.md`.

## Logic Quality Check Against Goals

Goal stated: optimize bot-friendly scalp strategies from prerecorded games, with simplified assumptions (no latency/slippage/fee/hazard overlays for now).

Assessment:
1. Aligned:
- Offline deterministic prototyping flow is aligned with your intended simplification.
- Regime-first + playbook routing + configurable classifier window is a good scaffold.
2. Misaligned:
- Current selection/evaluation pipeline is too optimistic for promoting "optimal" ranges.
- Current risk accounting does not support min/max loss analysis at path level.

## High-Quality Additions Worth Pulling from knowledge-export (V2 candidates)

1. Event-phase correctness layer
- Use phase model (`COOLDOWN/PRESALE/ACTIVE/RUGGED`) from canonical spec:
  - `rugipedia/canon/WEBSOCKET_EVENTS_SPEC.md:103`.
- Ensure simulation entries are evaluated only in equivalent active context.

2. Execution-truth instrumentation
- Use `playerUpdate` and `standard/newTrade` schema to support execution-aware replay fields:
  - `rugipedia/canon/WEBSOCKET_EVENTS_SPEC.md:603`.
- Reuse validated execution fields in RL design (`execution_tick`, `execution_price`, `latency_ms`):
  - `rl-design/observation-space-design.md`.

3. Game-history and partial-price ingestion improvements
- Integrate `gameHistory[]` and `partialPrices` handling to reduce missing-tick bias:
  - `rugipedia/canon/WEBSOCKET_EVENTS_SPEC.md:345`
  - `rugipedia/canon/WEBSOCKET_EVENTS_SPEC.md:414`.

4. Path-risk analytics stack
- Add risk metrics from curated risk-management sources:
  - drawdown distribution,
  - risk-of-ruin,
  - percentile terminal bankroll,
  - regime-stress scenarios.

5. Evidence-tier discipline for theory-driven research
- Keep archive hypotheses (e.g., meta-layer claims) in a separate theoretical lane until pre-registered tests pass.

## V2 Plan (Recommended)

### V2.0 - Correctness and Evaluation Hygiene (must do first)

Deliverables:
1. Train/validation/test split + walk-forward mode.
2. Out-of-sample permutation selection and reporting.
3. Sequential bankroll simulator with affordability checks and ruin handling.
4. New scoreboard:
- median end SOL,
- p10/p05 end SOL,
- max drawdown p50/p90,
- ruin probability.

Acceptance criteria:
1. No promoted strategy is chosen by in-sample-only performance.
2. Every promoted strategy has non-trivial participation and acceptable downside under path simulation.

### V2.1 - Exit Calibration and Feature Upgrade

Deliverables:
1. Horizon-conditional TP/SL calibration per regime.
2. TP/SL activation diagnostics.
3. Dataset quick-sample stratification and manifesting.

Acceptance criteria:
1. Time-exit share for promoted profiles is controlled (not blindly dominant).
2. Selected thresholds remain robust under local perturbations.

### V2.2 - Robustness and Promotion Governance

Deliverables:
1. Monte Carlo sequence resampling with regime reweighting.
2. Promotion policy with explicit reject reasons.
3. Canonical/theoretical claim registry in docs.

Acceptance criteria:
1. Positive median end SOL in stressed scenarios.
2. Predefined drawdown/ruin constraints are met.
3. All "facts" in final docs are tier-tagged and traceable to canonical evidence.

## Recommended Immediate Next Actions

1. Patch canonical docs to restore evidence-tier integrity (`PROVABLY_FAIR_VERIFICATION.md`, `CONTEXT.md`).
2. Implement split-aware evaluation and sequential bankroll simulation before any new strategy claims.
3. Re-run the current "best" settings under OOS + path-risk metrics and re-baseline the documented sweet spots.
