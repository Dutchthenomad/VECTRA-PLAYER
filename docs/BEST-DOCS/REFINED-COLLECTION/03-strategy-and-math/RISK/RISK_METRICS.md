# Risk Metrics

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `POSITION_SIZING.md`, `DRAWDOWN_CONTROL.md`
Replaces: risk-metrics sections across source docs

## Purpose

Define canonical risk and performance metrics used for evaluation and signoff.

## Scope

1. Risk-adjusted returns.
2. Tail and drawdown metrics.
3. Trade-quality and stability metrics.

## Source Inputs

1. `risk_management/03_risk_metrics_dashboard.py`
2. `risk_management/SUMMARY.md`
3. `Statistical Opt/STATISTICAL-OPTIMIZATION/18-RISK-METRICS.md`

## Canonical Decisions

### 1) Core Metric Set

1. Sharpe, Sortino, Calmar
2. Max Drawdown, VaR, CVaR
3. Profit Factor, Expectancy
4. Streak stability metrics

### 2) Reporting Rule

All metric outputs must include:

- sample size,
- timeframe,
- mode (`backtest` vs `live-simulator`),
- parameter profile id.

### 3) Acceptance Rule

No single metric is sufficient; rollout decisions require multi-metric gating and drawdown-control compliance.

## Open Questions

1. Should metric threshold bands be canonical or profile-specific defaults maintained in operations config?
