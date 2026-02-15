# Scalping Theoretical Avenues (Hypothesis Backlog)

Date: 2026-02-08

This is the active hypothesis set to test after the current empirical baseline.

## Priority 1: Entry Signal Dominance

Hypothesis:

- Entry signal quality explains more variance in long-run outcome than TP/SL choice.

Test direction:

- Hold exits constant (time-exit first), sweep entry families and thresholds.
- Compare support, median, tail risk, and stability.

## Priority 2: Regime-Conditioned Strategy Routing

Hypothesis:

- Strategy routing by regime (trend_up, expansion, chop, trend_down) dominates global one-policy behavior.

Test direction:

- Evaluate per-regime optimal settings.
- Compare to universal policy and blend policy.

## Priority 3: Early-Tick Classification Utility

Hypothesis:

- First-N tick signatures contain enough information to separate high-opportunity vs low-opportunity games.

Test direction:

- Sweep `classification_ticks` (20..40).
- Measure downstream effect on entry precision, win profile, and SOL outcomes.

## Priority 4: Late-Entry Risk Cutoff Utility

Hypothesis:

- Edge decays with later ticks; adaptive entry cutoffs can improve downside control.

Test direction:

- Sweep `entry_cutoff_tick` (30..60) with fixed entry model.
- Compare marginal SOL contribution of late entries.

## Priority 5: Drift-Scaled Exit Surfaces

Hypothesis:

- One-tick-drift-scaled exits are more transferable than fixed percent exits.

Test direction:

- Compare P50/P75/P90 anchors.
- Evaluate TPx/SLx plateau width and robustness.

## Priority 6: Game-Class Signatures from First 25 Ticks

Hypothesis:

- A compact first-25 tick signature may classify game behavior classes useful for bot decision layer.

Test direction:

- Use first-25 feature vectors (momentum, volatility, sign flips, expansion ratio).
- Evaluate predictive utility for downstream trade quality, not just classification fit.

## Priority 7: Robustness Under Regime-Mix Shifts

Hypothesis:

- Top-performing configs may fail if regime mix shifts materially.

Test direction:

- Monte Carlo with regime-stratified and regime-reweighted sampling.
- Assess probability of preserving positive End SOL under shifted distributions.

## Priority 8: Exit Reason Decomposition and SL Activation

Hypothesis:

- Current strong runs may be over-reliant on time exits, with SL under-activation masking avoidable tail risk.

Test direction:

- Track TP/SL/TIME mix by regime and profile.
- Run strict-SL vs base-SL toggle tests while holding entry logic fixed.
- Measure tail improvement vs trade participation loss.

## Priority 9: Regime Participation Gating

Hypothesis:

- Restricting participation to higher-quality regimes (`trend_up`, `expansion`) may improve downside-adjusted utility.

Test direction:

- Compare `ALL` vs regime-filtered routing in V1 toggle matrix.
- Evaluate effect on p10/worst-game net SOL and net participation rate.

## Classification Rule for Research Outcomes

- `Worth Exploring`: persistent positive utility and stable local neighborhood.
- `Worth Avoiding`: dominated or hard-fail downside behavior.
- `Noise`: unstable, low-support, or outlier-driven effects.
