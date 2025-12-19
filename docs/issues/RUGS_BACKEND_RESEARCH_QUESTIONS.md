# Rugs.fun Backend Research Questions

**Status:** Open Research
**Created:** December 19, 2025
**Target Repo:** claude-flow (GitHub Issue)
**Related:** VECTRA-PLAYER Phase 12, EventStore Migration

---

## Context

VECTRA-PLAYER is migrating from legacy recorders to EventStore (Parquet). To properly architect the data capture system, we need authoritative answers about the rugs.fun WebSocket backend behavior.

**Critical Data Gap:** Current RAG agent analysis is based on **normalized/parsed data**, not raw server frames. This introduces potential parsing artifacts:

```
Raw rugs.fun WebSocket → Our Parser Layer → Normalized JSONL → Analysis
                              ↑
                     POTENTIAL ARTIFACTS HERE
```

**What's reliable:** Direct field copies (`prices[]`, `rugged`, `peakMultiplier`)
**What's uncertain:** Phase classifications, trade counts, temporal metrics (derived by our logic)

---

## Research Questions

### Q1: gameHistory Count and Structure

**Current Hypothesis:** Rolling window of current game + 10 previous games (11 total)

**Evidence:**
- RAG agent found exactly 10 entries across 26 occurrences (but this is normalized data)
- Aligns with "Provably Fair System" UI which shows recent games for PRNG verification
- Players can verify game outcomes using gameId + server seed hash

**Screenshot Reference:**
![Provably Fair System](../assets/provably_fair_ui.png)
*UI shows Game ID, Server Seed Hash, and "Recent Games" section with verification capability*

**Questions to Answer:**
- [ ] Is count always exactly 10, or variable?
- [ ] Does it include the just-completed game, or only prior games?
- [ ] Is the window based on count or time?

---

### Q2: gameHistory Broadcast Timing

**Current Hypothesis:** Full historical data sent via `gameStateUpdate` at game end, before next presale phase begins.

**RAG Agent Response (normalized data):**
> NOT sent with every tick. Only broadcast at state transitions (~1.2% of ticks):
> - Connection init
> - Game start (tick 0, active=true)
> - Rug event (rugged=true)
> - Post-rug cooldown (tick 0, active=false)

**Open Questions:**
- [ ] Is gameHistory sent during active gameplay, or only at transitions?
- [ ] Why would full tick-by-tick price arrays be broadcast? (Admin tools? Verification?)
- [ ] What's the exact timing window between game end and next presale?

**Suspected Purpose:** Server uses this window to:
1. Close out game calculations for all players
2. Settle ~100s of active player positions
3. Update server-side treasury balancing system
4. Prepare provably fair data for verification

---

### Q3: GameHistoryEntry Field Completeness

**Current Schema:**
```python
class GameHistoryEntry(BaseModel):
    id: str                    # Game ID
    timestamp: int             # Completion timestamp (ms)
    prices: list[Decimal]      # Full price history (tick-by-tick)
    rugged: bool               # Whether game rugged
    rugPoint: Decimal          # Final rug multiplier
```

**RAG Agent Response (normalized data):**

| Field | Completeness | Notes |
|-------|--------------|-------|
| `id` | 100% | Reliable |
| `timestamp` | 100% | Reliable |
| `prices` | 100% | Direct copy - reliable |
| `rugged` | 100% | Direct copy - reliable |
| `peakMultiplier` | 100% | Direct copy - reliable |
| `gameVersion` | 100% | ? |
| `provablyFair` | 100% | ? |
| `globalSidebets` | 100% | ? |
| `globalTrades` | 0% | **ALWAYS EMPTY** |

**Questions to Answer:**
- [ ] Confirm all fields from raw server output
- [ ] Why is `globalTrades` always empty?
- [ ] Are there additional fields we're not capturing?

---

### Q4: playerUpdate Event Triggers

**Current Understanding:** Fires every ~250ms when player profile is connected

**RAG Agent Response (normalized data):**
> Fires on:
> - Server-side trade settlements
> - Game phase transitions (COOLDOWN → PRESALE → ACTIVE)
> - Connection/reconnection events
> - New game cycle initialization

**Questions to Answer:**
- [ ] Is 250ms the actual server interval, or our polling/sampling?
- [ ] Does it fire on a fixed interval, or only on state changes?
- [ ] What exactly triggers the first playerUpdate after connection?

---

## Data Sources

### Available Raw Data
```
/home/nomad/rugs_recordings/raw_captures/
├── [timestamp]_raw_ws_capture.jsonl  # Raw WebSocket frames
└── ...
```

### Processed Data (Current RAG Source)
```
/home/nomad/rugs_recordings_normalized/games/
├── 583 pre-processed game files
└── Contains parsing artifacts
```

### Problem
Raw captures are too large for brute-force LLM analysis. Need:
1. Proper chunking strategy
2. Vector DB ingestion
3. Preserve complete context without missing data

---

## Verification Plan

### Phase 1: Raw Data Ingestion
- [ ] Ingest raw WebSocket captures into vector DB
- [ ] Chunk appropriately (by game session? by event type?)
- [ ] Preserve temporal ordering

### Phase 2: Direct Server Output Analysis
- [ ] Query raw frames for `gameHistory` structure
- [ ] Compare raw vs normalized to identify parsing artifacts
- [ ] Document any discrepancies

### Phase 3: Authoritative Documentation
- [ ] Update claude-flow knowledge base with verified findings
- [ ] Update VECTRA-PLAYER schemas if needed
- [ ] Publish canonical rugs.fun WebSocket spec

---

## Related Files

| File | Purpose |
|------|---------|
| `src/models/events/game_state_update.py` | GameHistoryEntry schema |
| `src/models/events/player_update.py` | PlayerUpdate schema |
| `docs/CROSS_REPO_COORDINATION.md` | Cross-repo integration |
| `docs/specs/WEBSOCKET_EVENTS_SPEC.md` | Event documentation |

---

## Action Items

1. **Create claude-flow GitHub Issue** with this document
2. **Integrate raw captures** into RAG pipeline (in progress)
3. **Re-run analysis** on raw data once ingested
4. **Update this document** with verified findings

---

*This document will be updated as research progresses. claude-flow/rugs-expert agent is the canonical authority once raw data analysis is complete.*
