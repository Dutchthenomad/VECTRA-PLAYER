# Drawdown Control

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `POSITION_SIZING.md`, `RISK_METRICS.md`
Replaces: drawdown-control sections in risk source docs

## Purpose

Define canonical drawdown monitoring and trading-state transitions.

## Scope

1. Drawdown measurements.
2. State machine transitions for risk throttling.
3. Resume/recovery constraints.

## Source Inputs

1. `risk_management/02_drawdown_analysis.py`
2. `risk_management/04_comprehensive_risk_system.py`
3. `risk_management/IMPLEMENTATION_GUIDE.md`

## Canonical Decisions

### 1) Required Drawdown Signals

- current drawdown
- max drawdown
- drawdown duration
- loss-streak indicators

### 2) Risk State Machine

Canonical states:

1. `active`
2. `reduced`
3. `paused`
4. `recovery`

### 3) Transition Rule Baseline

Transitions are threshold-driven and deterministic per config set. All threshold changes are versioned.

### 4) Operational Rule

Live-execution must enforce pause semantics through execution bridge gating, not UI hints only.

## Open Questions

1. Should state-machine defaults be section-level constants or deployment profile values?
