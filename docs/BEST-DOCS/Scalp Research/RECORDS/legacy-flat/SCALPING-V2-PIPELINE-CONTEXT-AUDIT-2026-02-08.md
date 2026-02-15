# Scalping V2 Pipeline Context Audit

Date: 2026-02-08
Scope: `rugs-data-pipeline` + `knowledge-export` cross-check against current scalping artifacts

## Executive Summary

The pipeline foundation is strong and captures useful live data, but there are critical contract and integration mismatches that currently block trustworthy live decisioning.

Most important finding: the `feature-extractor -> decision-engine` handoff is structurally mismatched, so live recommendations are currently evaluated with missing tick/price/feature context.

## What Is Solid

1. Raw capture and persistence are operating at production scale.
- Local DB snapshot check: `games=981`, `events=421,758`, `game_history=1,016`, all history rows with revealed seeds.
2. Core sanitizer schema and phase model are explicit and well documented.
- `rugs-data-pipeline/docs/SUBSCRIBER-GUIDE.md`
- `rugs-data-pipeline/services/rugs-sanitizer/src/models.py`
3. Feature extractor computes a deterministic 16-feature vector from game ticks.
- `rugs-data-pipeline/services/feature-extractor/src/features.py`

## Critical Findings

### 1) Feature-to-Decision Contract Mismatch (Critical)

`feature-extractor` emits features inside envelope `data`, but `decision-engine` reads tick/price/features from top-level keys.

Evidence:
- Feature envelope shape is nested: `rugs-data-pipeline/services/feature-extractor/src/models.py:37`
- Feature emitter puts vector in `data`: `rugs-data-pipeline/services/feature-extractor/src/processor.py:87`
- Decision parser reads top-level `tick`/`price`: `rugs-data-pipeline/services/decision-engine/src/processor.py:140`
- Decision parser reads top-level feature keys: `rugs-data-pipeline/services/decision-engine/src/processor.py:151`

Runtime verification probe:
- Feature event had `data.tick=42`, no top-level `tick`.
- Decision engine recommendation came out with `tick=0`, `price=0.0`.

Implication:
- Live recommendations are made on incomplete context.
- Model A feature adjustments are effectively bypassed in live flow.

### 2) Rug Detection and Scoring Path Is Broken in Live Chain (Critical)

Decision engine rug detection checks `raw.rugged` at top-level:
- `rugs-data-pipeline/services/decision-engine/src/processor.py:189`

But upstream feature events do not carry top-level `rugged`, so rug detection does not trigger in normal pipeline flow.

Implication:
- Scorer cannot correctly anchor outcomes against real rug timing in live mode.

### 3) Sanitizer History Collection Design vs Implementation Drift (High)

Docs state `/feed/history` is every 10th rug:
- `rugs-data-pipeline/docs/SUBSCRIBER-GUIDE.md:56`
- `rugs-data-pipeline/README.md:94`

Current sanitizer code emits history whenever `gameHistory` exists in a `gameStateUpdate`:
- `rugs-data-pipeline/services/rugs-sanitizer/src/sanitizer.py:173`

Also, `main.py` calls `HistoryCollector` with `game_data.get("game_history")`, but `GameTick` payload does not contain that key:
- `rugs-data-pipeline/services/rugs-sanitizer/src/main.py:124`

Implication:
- The "every 10th rug" contract is not what downstream consumers actually get.
- Duplicate/overlap behavior risk remains unless handled downstream.

### 4) Test Suite Validates Flat Decision Inputs, Not Real Envelope Inputs (High)

Decision tests feed flat dicts with top-level `tick`, `price`, features:
- `rugs-data-pipeline/services/decision-engine/tests/test_processor_decision.py:11`

No integration test validates actual feature service envelope shape into decision processor.

Implication:
- Current tests pass while live integration remains logically broken.

### 5) Event Coverage Gap vs Knowledge Corpus (Medium)

Knowledge corpus reports 29 observed event types and 590 field paths:
- `/home/devops/Desktop/hostinger-vps-infrastructure/knowledge-export/rugipedia/generated/coverage_report.md:9`

Raw feed service currently registers a narrower subset of handlers:
- `rugs-data-pipeline/services/rugs-feed/src/client.py:130`

Implication:
- Fine for current scoped sidebet/stat exploration.
- Not sufficient for full execution-truth, auth-dependent state, and advanced monitoring without additional ingestion paths.

### 6) Canonical Fact/Hypothesis Mixing in Knowledge Base (Medium)

`PROVABLY_FAIR_VERIFICATION.md` mixes deterministic PRNG facts with untagged meta-layer manipulation claims:
- `/home/devops/Desktop/hostinger-vps-infrastructure/knowledge-export/rugipedia/canon/PROVABLY_FAIR_VERIFICATION.md:152`

Implication:
- RAG consumers can ingest speculative claims as hard facts unless tier-tagged.

## Additional Gaps Worth Closing

1. Documentation drift:
- Root README still labels feature/decision as stubs despite substantial implementation.
- `rugs-data-pipeline/README.md:25`
2. Coverage completeness:
- Diff report still shows major undocumented field surface.
- `/home/devops/Desktop/hostinger-vps-infrastructure/knowledge-export/rugipedia/generated/diff_report.md:7`

## Recommendations

## P0 (Do First)

1. Normalize decision input contract:
- Decision processor should parse from `raw.data` envelope payload (and keep backward-compatible fallback).
2. Fix rug detection path:
- Detect rug using phase (`phase == "RUGGED"`) and/or explicit rugged field inside payload.
3. Align history channel behavior with stated contract:
- Either implement collector-gated emission or update docs to match actual continuous behavior.
4. Add one end-to-end integration test:
- `sanitizer -> feature-extractor -> decision-engine` with real envelope payloads.

## P1 (Before V2 Live Experiments)

1. Add contract tests for each boundary:
- envelope schema snapshots for `/feed/game`, `/feed/features`, `/feed/recommendations`.
2. Add event coverage manifest:
- explicit list of captured events vs intentionally ignored events.
3. Split canonical vs theoretical knowledge assertions:
- enforce claim tags (`canonical`, `verified`, `theoretical`) in rugipedia docs.

## P2 (V2+ Enablement)

1. Expand ingestion for execution-aware loop:
- include auth-dependent events needed for fill confirmation and player state reconciliation.
2. Add live/offline parity validator:
- same recorded stream replayed through services must match artifact-level offline metrics within tolerance.

## Recommended V2 Sequence

1. V2.0: Contract hardening and integration correctness.
2. V2.1: Offline-online metric parity (classifier, entries/exits, PnL envelopes).
3. V2.2: Execution-truth and scoring reliability (fill-confirmed outcomes).
4. V2.3: Only then promote adaptive ML/RL layers beyond deterministic playbook baselines.

## Bottom Line

Your current architecture is directionally correct and close to being a strong V2 foundation.
The main blockers are not math; they are interface contracts and truth-of-execution plumbing.
Fix those first, and your scalping optimization stack becomes substantially more reliable for real progression.
