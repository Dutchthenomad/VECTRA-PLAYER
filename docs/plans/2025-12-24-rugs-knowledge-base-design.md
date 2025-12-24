# Rugs Expert Knowledge Base Design

**Date:** 2025-12-24
**Status:** Approved
**Related:** `docs/plans/2025-12-23-bot-action-interface-design.md`

---

## Overview

Comprehensive knowledge base for the `rugs-expert` RAG agent, expanding from protocol documentation to full game theory expertise.

**Primary Use Case (80%):** Bot development - strategy, ML/RL, feature engineering
**Secondary (20%):** Manual trading guidance, research platform

---

## Architecture

### Location

```
~/Desktop/claude-flow/knowledge/rugs-strategy/
```

### Layer Structure

```
rugs-strategy/
├── CONTEXT.md                    # Agent instructions + layer index
├── _metadata/
│   └── layer-definitions.json    # N8N-filterable taxonomy
│
├── L1-game-mechanics/
│   ├── WHAT-IT-IS-NOT.md         # LLM misconception guard (P0-CRITICAL)
│   ├── game-phases.md
│   ├── prng-system.md
│   ├── provably-fair.md
│   ├── trade-mechanics.md
│   ├── sidebet-mechanics.md
│   └── volatility-model.md
│
├── L2-protocol/
│   ├── websocket-spec.md         # Canonical (synced from VECTRA-PLAYER)
│   ├── browser-connection.md
│   ├── events-index.md
│   ├── field-dictionary.md
│   ├── confirmation-mapping.md   # Generated from bot validation
│   └── event-relationships.md
│
├── L3-ml-rl/
│   ├── feature-design.md
│   ├── reward-engineering.md
│   ├── reward-hacking-vectors.md
│   ├── training-environments.md
│   └── sidebet-predictor.md
│
├── L4-vectra-codebase/
│   ├── architecture.md
│   ├── event-store.md
│   └── trading-bot.md
│
├── L5-strategy-tactics/
│   ├── bankroll-management.md
│   ├── risk-hedging.md
│   ├── probability-framework.md
│   └── betting-systems/
│       ├── martingale.md
│       ├── anti-martingale.md
│       ├── fibonacci.md
│       ├── dalembert.md
│       └── kelly-criterion.md
│
├── L6-statistical-baselines/
│   ├── comprehensive-analysis.md
│   ├── trading-zones.md
│   ├── tick-by-tick.md
│   ├── player-trading-data.md
│   ├── latency-distribution.md   # Generated from bot validation
│   └── action-timing.md          # Generated from bot validation
│
└── L7-advanced-analytics/
    ├── prng-reverse-engineering.md
    ├── bayesian-models.md
    ├── hidden-markov-models.md
    ├── change-point-detection.md
    ├── q-learning-architecture.md
    └── dynamic-sweet-spot.md
```

---

## Validation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG SUPERPACK (staging)                       │
│  ~/Desktop/claude-flow/knowledge/RAG SUPERPACK/                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────────┐
     │  READY   │   │  REVIEW  │   │  THEORETICAL │
     │ (ingest) │   │ (human)  │   │  (validate)  │
     └────┬─────┘   └────┬─────┘   └──────┬───────┘
          │              │                │
          ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    rugs-strategy/ (production)                   │
│  L1-L7 organized, YAML frontmatter, ChromaDB indexed            │
└─────────────────────────────────────────────────────────────────┘
```

### Validation Tiers

| Tier | Source | Process |
|------|--------|---------|
| CANONICAL | CORE ARCHITECTURE | Direct ingest, human approval |
| VERIFIED | Top-level .md | Quick review → ingest |
| REVIEWED | `review data/` | Human review → edit → ingest |
| THEORETICAL | `THEORETICAL.../` | Validate against data → promote |

---

## YAML Frontmatter Schema

```yaml
---
layer: 3
domain: ml-rl/reward-engineering
priority: P0
bot_relevant: true
validation_tier: verified
source_file: "RAG SUPERPACK/review data/bankroll_management.md"
cross_refs:
  - L1-game-mechanics/prng-system.md
  - L6-statistical-baselines/peak-price-distribution.md
last_validated: 2025-12-24
---
```

---

## Critical Document: WHAT-IT-IS-NOT

High-priority retrieval guard preventing LLM hallucinations about financial markets.

**Concepts that DO NOT apply:**
- No whales (price is PRNG, not supply/demand)
- No liquidity pools (no AMM, no bonding curve)
- No technical analysis (no support/resistance, no patterns)
- No market microstructure (no bid-ask, no slippage from size)

**What it IS:** PRNG-based game simulating meme coin trading. Edge comes from timing, bankroll management, and statistical patterns - NOT market analysis.

---

## Source File Mapping

### From RAG SUPERPACK

| Source | Target | Action |
|--------|--------|--------|
| `CORE ARCHITECTURE/WEBSOCKET_EVENTS_SPEC.md` | `L2-protocol/websocket-spec.md` | Sync |
| `CORE ARCHITECTURE/BROWSER_CONNECTION_PROTOCOL.md` | `L2-protocol/browser-connection.md` | Copy |
| `CORE ARCHITECTURE/rugs-game-phases-unified.md` | `L1-game-mechanics/game-phases.md` | Copy |
| `00-RUGSFUN-COMPLETE-GAME-DOCUMENTATION.md` | `L1-game-mechanics/` | Extract |
| `PRNG_REVERSE_ENGINEERING.md` | `L7-advanced-analytics/prng-reverse-engineering.md` | Copy |
| `PROVABLY_FAIR_VERIFICATION.md` | `L1-game-mechanics/provably-fair.md` | Copy |
| `review data/bankroll_management.md` | `L5-strategy-tactics/bankroll-management.md` | Review |
| `review data/risk_hedging_systems.md` | `L5-strategy-tactics/risk-hedging.md` | Review |
| `review data/bayesian-models.md` | `L7-advanced-analytics/bayesian-models.md` | Review |
| `THEORETICAL.../EMPIRICAL_DATA.md` | `L3-ml-rl/feature-design.md` | Validate |
| `THEORETICAL.../REWARD_DESIGN_PROMPT.md` | `L3-ml-rl/reward-engineering.md` | Validate |

### Generated from Bot Validation

| Artifact | Target | Generated By |
|----------|--------|--------------|
| Confirmation mapping | `L2-protocol/confirmation-mapping.md` | BotActionInterface validation |
| Latency distribution | `L6-statistical-baselines/latency-distribution.md` | ConfirmationMonitor |
| Action timing | `L6-statistical-baselines/action-timing.md` | Test script recordings |

---

## ChromaDB Integration

### Index Build

```bash
cd ~/Desktop/claude-flow/rag-pipeline
source .venv/bin/activate

# Full rebuild
python -m ingestion.ingest --paths ../knowledge/rugs-strategy/ --clear

# Incremental add
python -m ingestion.ingest --paths ../knowledge/rugs-strategy/

# Verify
python -m retrieval.retrieve "What confirms a BUY action?" -k 5
```

### Collections

| Collection | Content |
|------------|---------|
| `claude_flow_knowledge` | Existing agent/skills docs |
| `rugs_knowledge` | NEW: rugs-strategy L1-L7 |

---

## N8N Integration (Future)

Layer-based routing for pipeline filtering:

```
Query → N8N Router
           │
           ├─ layer:1-2 → Protocol questions
           ├─ layer:3-4 → Implementation questions
           ├─ layer:5-6 → Strategy questions
           └─ layer:7   → Advanced analytics
```

---

## Implementation Phases

### Phase 1: Foundation (Immediate)
- [x] Create `rugs-strategy/CONTEXT.md`
- [ ] Create directory structure (L1-L7 folders)
- [ ] Move CANONICAL files from RAG SUPERPACK
- [ ] Create `WHAT-IT-IS-NOT.md`

### Phase 2: Review Data (1-2 days)
- [ ] Review and migrate `review data/` files
- [ ] Add YAML frontmatter to all
- [ ] Build initial ChromaDB index

### Phase 3: Theoretical Validation (Ongoing)
- [ ] Validate THEORETICAL files against empirical data
- [ ] Promote valid content to appropriate layers
- [ ] Archive or reject invalid content

### Phase 4: Bot Integration (With BotActionInterface)
- [ ] Generate confirmation-mapping.md from validation
- [ ] Generate latency-distribution.md from stats
- [ ] Re-index ChromaDB after each validation session

---

## Success Criteria

- [ ] rugs-expert correctly answers: "What confirms a BUY action?"
- [ ] rugs-expert surfaces WHAT-IT-IS-NOT when asked about "support levels"
- [ ] Layer filtering works: `--filter "layer:5"` returns only strategy docs
- [ ] Cross-references surface related docs together
- [ ] Bot validation sessions auto-generate indexed documentation

---

*Generated: 2025-12-24*
