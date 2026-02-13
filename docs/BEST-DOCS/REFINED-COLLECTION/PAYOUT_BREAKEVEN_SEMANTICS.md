# Payout and Breakeven Semantics

Last updated: 2026-02-12
Status: canonical (math glossary)

## Purpose

This project uses two valid breakeven interpretations. Both are correct when their payout model is stated explicitly.

## Canonical Variables

- `stake`: amount risked on one sidebet
- `R_total`: total return multiple on win (includes returned stake)
- `R_profit`: net profit multiple on win (excludes returned stake)

Relationship:

```text
R_total = R_profit + 1
```

Breakeven win probability:

```text
p* = 1 / R_total = 1 / (R_profit + 1)
```

## Model A: Programmatic / Settlement Math

Use when the system treats payout as total return multiplier.

Example:

- Win returns `5x` total (stake included)
- Therefore `R_total = 5`, `R_profit = 4`
- Breakeven:

```text
p* = 1 / 5 = 0.20 = 20%
```

## Model B: Comprehensive / Odds Math

Use when payout is expressed as net odds.

Example:

- Odds are `5:1` net profit
- Therefore `R_profit = 5`, `R_total = 6`
- Breakeven:

```text
p* = 1 / 6 = 0.1667 = 16.67%
```

## Documentation Rules

1. Never state only `5:1` or `5x` without defining whether it is `R_total` or `R_profit`.
2. For every breakeven claim, include the model and variable form.
3. If both values appear in the same doc, label them explicitly:
   - `Breakeven (Programmatic/Settlement): 20%`
   - `Breakeven (Comprehensive/Odds): 16.67%`

## Recommended Shared Constants

```text
BREAKEVEN_PROGRAMMATIC = 0.20
BREAKEVEN_COMPREHENSIVE = 0.1667
```
