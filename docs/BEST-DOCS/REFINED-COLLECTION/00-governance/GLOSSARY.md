# Glossary

Status: review-ready (Section 1)
Class: canonical
Last updated: 2026-02-12
Owner: Documentation Governance
Depends on: `DOC_STANDARDS.md`, `CONSTANTS_AND_SEMANTICS.md`
Replaces: mixed terminology across source docs

## Purpose

Normalize terminology so architecture, strategy, operations, and research docs use consistent language.

## Scope

Applies to all documentation in `REFINED-COLLECTION/`.

## Source Inputs

1. `system-extracts/README.md`
2. `Scalp Research/README.md`
3. `Scalp Research/HANDBOOK/README.md`
4. `Scalp Research/RECORDS/README.md`
5. `PROCESS_FLOWCHARTS.md`
6. `Statistical Opt/00-ARCHITECTURE-OVERVIEW.md`
7. `rosetta-stone/ROSETTA-STONE.md`
8. `risk_management/README.md`

## Canonical Terms

| Term | Definition | Notes |
|---|---|---|
| `canonical` | Normative source of truth used for build decisions. | If a source conflicts with canonical, canonical wins until revalidated. |
| `reference` | Supporting technical explanation, not normative by itself. | May inform canonical docs but does not override them. |
| `evidence` | Dated record of what happened in runs, tests, audits, experiments. | Immutable history class. |
| `legacy` | Historical material retained for traceability, not active guidance. | No new canonical claims should originate here. |
| `source corpus` | Original reference materials outside `REFINED-COLLECTION/`. | Currently `147` files. |
| `refined workspace` | New unified docs under `REFINED-COLLECTION/`. | Active migration target. |
| `tick` | Smallest game-time step in stream updates. | Nominally ~250ms; use nominal value, not strict real-time guarantee. |
| `tickCount` | Running tick index for active game state. | Protocol field in `gameStateUpdate`. |
| `cooldown` | Post-rug interval before next active game. | In source observations, total is 15s with presale inside final 10s. |
| `presale` | Pre-active phase where pre-round buys are allowed. | Signaled by `allowPreRoundBuys=true`. |
| `active` | Main trading phase with live price updates and trade activity. | Ends at rug event. |
| `rugged` | Terminal state for game round after rug event. | Followed by settlement and next cooldown. |
| `sidebet` | Bet that wins if rug occurs in a fixed forward tick window. | Window currently treated as 40 ticks baseline. |
| `sidebet window` | Number of ticks after entry considered for sidebet win. | Baseline constant: `40` ticks. |
| `payout (total return)` | Win return including returned stake (`R_total`). | Example: 5x total return means net +4x profit. |
| `payout (net odds)` | Win profit excluding returned stake (`R_profit`). | Example: 5:1 net odds means total return 6x. |
| `breakeven (programmatic)` | Win probability threshold under total-return model. | For `R_total=5`, breakeven is `20%`. |
| `breakeven (comprehensive)` | Win probability threshold under net-odds model. | For `R_profit=5`, breakeven is `16.67%`. |
| `event bus` | Internal pub/sub channel for event fanout among services. | Common in architecture and process docs. |
| `event schema` | Versioned payload contract for published events. | Required for API/event stability. |
| `foundation service` | Normalization and distribution layer for market/game events. | Upstream for UI and analytics services. |
| `explorer` | Analytics-oriented UI/service for strategy inspection. | Distinct from core execution shell. |
| `backtest` | Deterministic simulation over historical data sessions. | No live feed dependency. |
| `replay` | Tick-by-tick playback of recorded sequences for inspection/debug. | May be part of backtest tooling but not identical to strategy backtest. |
| `live-simulator` | Paper-trading simulation driven by live incoming feed. | Not real-money execution. |
| `paper-trading` | Simulated fills and PnL without real execution. | Can run in live-simulator or backtest contexts. |
| `live-execution` | Real order execution against production environment. | Must remain separate from simulator process. |
| `survival analysis` | Modeling probability a game survives beyond tick `t`. | Used for rug timing probability estimates. |
| `hazard rate` | Conditional probability of rug at tick `t` given survival to `t`. | Key derived quantity in timing models. |
| `Kelly criterion` | Position sizing formula from edge and odds. | Input semantics depend on payout definition. |
| `checkpoint` | Saved run configuration/output artifact for reproducibility. | Stored under evidence. |

## Legacy-to-Canonical Mode Mapping

Use this map when migrating source language into refined docs:

| Source Phrase (Legacy) | Canonical Term | Rule |
|---|---|---|
| `live mode` | `live-execution` or `live-simulator` | Must be disambiguated by execution intent. |
| `paper mode` / `paper trading mode` | `paper-trading` | If feed is live, also label parent mode `live-simulator`. |
| `replay mode` | `replay` | Use for tick-by-tick playback/inspection. |
| `backtest mode` | `backtest` | Use for deterministic strategy evaluation over historical data. |
| `simulator` (unspecified) | `live-simulator` or `backtest` | Never leave unqualified in canonical docs. |

## Canonical Notation Tokens

| Token | Meaning |
|---|---|
| `R_total` | Total return multiplier on win, including returned stake. |
| `R_profit` | Net profit multiplier on win, excluding returned stake. |
| `p*` | Breakeven win probability. |

## Open Questions

1. Should `replay` be reserved strictly for visualization tooling, with `backtest` reserved for strategy evaluation only?
2. Should `live-simulator` and `paper-trading` be collapsed into one term to reduce overlap?
