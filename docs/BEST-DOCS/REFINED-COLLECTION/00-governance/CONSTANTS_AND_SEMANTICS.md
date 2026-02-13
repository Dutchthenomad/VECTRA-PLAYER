# Constants and Semantics

Status: review-ready (Section 1)
Class: canonical
Last updated: 2026-02-12
Owner: Documentation Governance
Depends on: `GLOSSARY.md`, `../PAYOUT_BREAKEVEN_SEMANTICS.md`
Replaces: conflicting constants/wording across source docs

## Purpose

Define canonical numeric constants and semantic rules used across refined docs.

## Scope

Applies to architecture, domain, strategy, systems, and operations docs in `REFINED-COLLECTION/`.

## Source Inputs

1. `rosetta-stone/ROSETTA-STONE.md`
2. `risk_management/README.md`
3. `PROBABILISTIC_REASONING.md`
4. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`
5. `Statistical Opt/STATISTICAL-OPTIMIZATION/15-KELLY-CRITERION.md`
6. `system-extracts/README.md`
7. `REFINED-COLLECTION/PAYOUT_BREAKEVEN_SEMANTICS.md`

## Constant Classes

1. `protocol-observed`: directly observed in protocol or data captures.
2. `mechanics-baseline`: system/game mechanics baseline used in modeling.
3. `modeling-default`: default analytical or simulation assumption.
4. `policy-threshold`: operational rule threshold (subject to strategy policy).

## Canonical Constants

| Constant | Value | Unit | Class | Meaning | Status |
|---|---:|---|---|---|---|
| `SIDEBET_WINDOW_TICKS` | `40` | ticks | mechanics-baseline | Forward window for sidebet win condition. | approved |
| `GAME_TICK_INTERVAL_NOMINAL_MS` | `250` | ms | protocol-observed | Nominal tick cadence for timing conversions and replay speed defaults. | approved (nominal, not hard real-time) |
| `COOLDOWN_TOTAL_MS` | `15000` | ms | protocol-observed | Total cooldown timer window observed in feed lifecycle docs. | approved |
| `PRESALE_WINDOW_MS` | `10000` | ms | protocol-observed | Presale interval where pre-round buys are allowed. | approved |
| `COOLDOWN_SETTLEMENT_BUFFER_MS` | `5000` | ms | protocol-observed | Early cooldown settlement buffer before presale. | approved |
| `SIDEBET_PAYOUT_TOTAL_RETURN_MULTIPLIER_PROGRAMMATIC` | `5` | x | mechanics-baseline | Programmatic settlement interpretation (stake included in return). | approved |
| `SIDEBET_PAYOUT_NET_PROFIT_MULTIPLIER_PROGRAMMATIC` | `4` | x | mechanics-baseline | Net profit under programmatic settlement interpretation. | approved |
| `BREAKEVEN_WIN_RATE_PROGRAMMATIC` | `0.20` | probability | mechanics-baseline | Breakeven under `R_total=5`. | approved |
| `SIDEBET_PAYOUT_NET_PROFIT_MULTIPLIER_COMPREHENSIVE` | `5` | x | modeling-default | Comprehensive odds interpretation (`5:1` net odds). | approved |
| `SIDEBET_PAYOUT_TOTAL_RETURN_MULTIPLIER_COMPREHENSIVE` | `6` | x | modeling-default | Total return implied by comprehensive odds interpretation. | approved |
| `BREAKEVEN_WIN_RATE_COMPREHENSIVE` | `0.1667` | probability | modeling-default | Breakeven under `R_profit=5` / `R_total=6`. | approved |
| `SIDEBET_ENTRY_ZONE_START_TICK` | `200` | ticks | modeling-default | Frequently cited "late-game" entry boundary in source analyses. | provisional |
| `SIDEBET_COOLDOWN_BET_TICKS` | `5` | ticks | policy-threshold | Cooldown between consecutive sidebets in some source modules. | provisional |
| `MAX_GAME_TICKS_PROVISIONAL` | `5000` | ticks | modeling-default | Maximum tick cap cited in PRNG research notes. | provisional |
| `RUG_PROB_BASE_PER_TICK_PROVISIONAL` | `0.005` | probability | modeling-default | Per-tick base rug probability cited in PRNG research notes. | provisional |

## Semantic Rules

### 1) Payout Semantics Must Be Explicit

Always specify one of:

1. `R_total` (total return, includes stake), or
2. `R_profit` (net profit, excludes stake).

Never write only `5:1` or `5x` without this qualifier.

### 2) Breakeven Expressions

Use one of these exact forms:

- `Breakeven (Programmatic/Settlement): 20% (R_total=5)`
- `Breakeven (Comprehensive/Odds): 16.67% (R_profit=5, R_total=6)`

### 2.1) API Contract Representation Rule

For service/API contracts, payout must be represented explicitly as fields, not prose:

1. Required: `r_total`.
2. Optional but recommended: `r_profit`.
3. If both are present, they must satisfy `r_total = r_profit + 1`.

If only one field is provided, consumers must not infer legacy textual odds labels.

### 3) Tick-Time Conversion Rule

When converting ticks to wall time, use:

```text
time_ms = ticks * GAME_TICK_INTERVAL_NOMINAL_MS
```

and explicitly call it nominal timing.

### 4) Provisional Constant Handling

If a constant is marked `provisional`:

1. it may be used in drafts,
2. it must be validated in section review,
3. promotion to `approved` requires decision-log entry.

### 5) Default Interpretation Rule

When a canonical doc needs one default breakeven value without dual presentation:

1. Implementation/runtime contexts default to `BREAKEVEN_WIN_RATE_PROGRAMMATIC` (`0.20`).
2. Theoretical/odds analysis contexts may use comprehensive breakeven, but must label it explicitly.

## Canonical Formula Reference

```text
R_total = R_profit + 1
breakeven_win_rate = 1 / R_total = 1 / (R_profit + 1)
```

## Open Questions

1. Should `SIDEBET_ENTRY_ZONE_START_TICK=200` remain global, or become strategy-specific profile data?
2. Should `SIDEBET_COOLDOWN_BET_TICKS=5` be treated as protocol-level or policy-level after architecture review?
