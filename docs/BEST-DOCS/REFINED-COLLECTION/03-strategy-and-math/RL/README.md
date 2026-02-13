# RL

Status: in_review (Section 4)
Class: canonical
Last updated: 2026-02-12
Owner: Strategy and Math Review
Depends on: `RL_ENVIRONMENT_SPEC.md`, `OBSERVATION_ACTION_REWARD.md`
Replaces: RL docs in ML and statistical-opt sources

## Purpose

Define canonical RL interfaces for environment, observation space, action space, and reward semantics.

## Scope

1. Environment contract.
2. Observation/action/reward schema.
3. Evaluation and anti-reward-hacking constraints.

## Canonical Decisions

1. RL docs specify interfaces, not one algorithm implementation.
2. Reward components and weighting must be explicitly versioned.
3. Any reward-shaping changes require regression validation against exploit behaviors.
