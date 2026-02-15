# Deployment

Status: in_review (Section 6)
Class: canonical
Last updated: 2026-02-12
Owner: Operations Review
Depends on: `../README.md`, `../../01-architecture/SERVICE_BOUNDARIES.md`
Replaces: deployment notes in source docs

## Purpose

Define deployment patterns, environment profiles, and release workflow documentation.

## Scope

1. environment profiles,
2. service startup orchestration,
3. release and rollback process,
4. config and secrets handling guidance.

## Canonical Decisions

1. Deployment docs are environment-profiled (dev/stage/prod).
2. Health/readiness checks gate rollout progress.
3. Manifest/service registration remains deployment baseline.
