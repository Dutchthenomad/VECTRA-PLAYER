# Monitoring

Status: in_review (Section 6)
Class: canonical
Last updated: 2026-02-12
Owner: Operations Review
Depends on: `../README.md`, `../../01-architecture/CONTRACTS/FOUNDATION_API.md`
Replaces: monitoring notes in source docs

## Purpose

Define observability model for service health, throughput, and strategy runtime behavior.

## Scope

1. liveness/readiness and service metrics,
2. event throughput and lag signals,
3. alerting thresholds and escalation paths,
4. dashboard ownership.

## Canonical Decisions

1. Monitoring must track both system health and model/risk behavior.
2. Metrics and logs include correlation identifiers where available.
3. Alerts map to runbook procedures and evidence capture expectations.
