# Operations

Status: in_review (Section 6)
Class: canonical
Last updated: 2026-02-12
Owner: Operations Review
Depends on: `../01-architecture/CONTRACTS/FOUNDATION_API.md`, `../04-systems/README.md`
Replaces: run/deploy/monitoring notes across source corpus

## Purpose

Define operational practices for running, validating, deploying, and monitoring the system.

## Scope

1. runbooks,
2. deployment patterns,
3. testing/validation pathways,
4. monitoring and alerting conventions.

## Source Inputs

1. `CHROME_PROFILE_SETUP.md`
2. `Scalp Research/HANDBOOK/09_OPERATIONS_RUNBOOK.md`
3. `system-extracts/08-containerization-and-plugin-patterns.md`
4. `PROCESS_FLOWCHARTS.md` (testing/ops notes)

## Canonical Decisions

1. Operations docs are implementation-facing canonical guidance.
2. Every runbook must reference mode and environment assumptions.
3. Deploy/test/monitor docs must align with architecture contracts.
