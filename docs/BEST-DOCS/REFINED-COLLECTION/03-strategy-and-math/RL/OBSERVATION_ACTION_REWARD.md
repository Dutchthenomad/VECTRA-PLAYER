# Observation Action Reward

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `RL_ENVIRONMENT_SPEC.md`, `../../00-governance/CONSTANTS_AND_SEMANTICS.md`
Replaces: O/A/R docs in RL source set

## Purpose

Define canonical observation, action, and reward contracts for RL modules.

## Scope

1. Observation feature groups.
2. Action semantics and constraints.
3. Reward construction and anti-exploit rules.

## Source Inputs

1. `Machine Learning/models/sidebet-v1/design/OBSERVATION_SPACE_v1.md`
2. `Machine Learning/models/sidebet-v1/design/REWARD_FUNCTION_v1.md`
3. `Statistical Opt/RL-TRAINING/19-SIDEBET-RL-ENVIRONMENT.md`
4. `ML_RL_SYSTEM_OVERVIEW_AND_RESEARCH_PROMPT.md`

## Canonical Decisions

### 1) Observation Contract

Observation is composed of grouped features:

1. market state
2. timing/phase context
3. player/position state
4. model-derived signals

Each feature must exist in `FEATURE_DICTIONARY.md` with type and units.

### 2) Action Contract

Actions must be discrete and auditable. Invalid actions must follow explicit environment rule (mask/convert/penalize).

### 3) Reward Contract

1. Financial outcome remains primary objective anchor.
2. Auxiliary shaping terms require justification and ablation evidence.
3. Reward configuration is versioned and linked to run artifacts.

### 4) Anti-Reward-Hacking Rule

Every reward revision requires:

1. action-distribution inspection,
2. profitability sanity checks,
3. exploit-case regression tests.

## Open Questions

1. Should we mandate a canonical minimal reward config for all baseline experiments?
