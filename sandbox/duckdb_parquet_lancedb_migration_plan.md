# REPLAYER → DuckDB/Parquet + LanceDB Vector Index (Unified Plan Draft)

**Status:** Draft for cross-session coordination  
**Audience:** REPLAYER refactor session + RAG/Socket pipeline session  
**Goal:** Replace today’s scattered JSON/JSONL “recordings” + ad-hoc RAG capture folders with a single, durable, ML-friendly dataset (Parquet) plus a rebuildable semantic index (LanceDB), while preserving a claude-flow compatible retrieval contract.

---

## 1) Executive Summary

REPLAYER currently has multiple recording/capture paths with different schemas and directory conventions (game tick JSONL, demonstrations/sessions JSON, raw WS captures JSONL, CDP “RAG ingester” JSONL). This causes recurring path drift (e.g. `rag_events/` vs `raw_captures/`) and makes downstream RAG + ML pipelines fragile.

**Proposed long-term architecture:**
- **Canonical truth store:** Parquet dataset queried via **DuckDB** (append-only + partitioned).
- **Semantic index:** **LanceDB** built *from* the Parquet dataset (rebuildable, incremental).
- **Compatibility:** An adapter that emits the same `(text, metadata)` chunk contract used by claude-flow, regardless of underlying storage.

**Core principle:** vector index is **derived**, not the canonical store.

---

## 2) Target System Architecture

### 2.1 Canonical Storage: Parquet Dataset (DuckDB query layer)

**Why:** training/analytics-friendly, scalable, easy versioning/backfills, high-quality RL dataset creation.

**One root directory (no hardcoded paths):**
- `RUGS_DATA_DIR/` (new env var; default TBD)
  - `events_parquet/` (canonical)
  - `vectors/` (derived)
  - `exports/` (optional)
  - `manifests/` (schema + ingestion reports)

### 2.2 Derived Vector Index: LanceDB

**Why:** columnar + vector-native, good for large corpora, incremental updates, supports metadata filters that matter for events (type, game_id, time).

Index should be rebuildable from Parquet at any time:
- If schema changes: wipe `vectors/` and rebuild from Parquet.
- If embeddings model changes: rebuild from Parquet.

### 2.3 claude-flow Compatibility Contract

Define a stable contract matching claude-flow retrieval expectations:
- `text: str`
- `metadata: dict` (source, timestamps, event_type, game_id, doc_type, etc.)
- `id: stable hash(text + source)` (compatible with existing claude-flow strategy)

This enables:
- claude-flow “agent knowledge base” retrieval without caring about where events live.
- REPLAYER to export “legacy JSONL” on demand for debugging or external pipelines.

---

## 3) Canonical Event Envelope (Schema Strategy)

### 3.1 Store “structured columns” + “raw payload”

We should not lose fidelity. For each record:
- **common columns**: `ts`, `source`, `doc_type`, `session_id`, `game_id`, `player_id`, `username`, `seq`, `direction`
- **type-specific columns** where stable (e.g. `price`, `tick`, `cash`, `position_qty`)
- **raw JSON** column (string) for the full payload/frame to preserve future decode needs

### 3.2 Partitioning

Partition by high-cardinality keys carefully:
- `doc_type=.../date=YYYY-MM-DD/part-*.parquet`
- Optional: `source=cdp|public|replay` if it helps

Keep partitions simple; avoid `game_id` partitions (too many directories).

### 3.3 Doc Types (initial set)

Minimum viable set to unify today’s systems:
- `ws_event` (Socket.IO events from CDP/public)
- `game_tick` (tick/price stream)
- `player_action` (UI actions + bot actions)
- `server_state` (playerUpdate-derived state snapshots)
- `system_event` (connect/disconnect/source_changed/errors)

---

## 4) Capture / Write Path (REPLAYER integration)

### 4.1 Single Writer API: `EventStore`

Introduce one module responsible for all persistence:
- `services/event_store/`
  - `writer.py` (buffering, atomic parquet writes)
  - `schema.py` (pydantic/dataclasses + version)
  - `duckdb.py` (query helpers)
  - `paths.py` (derive all dirs from config/env)

**All producers publish to EventBus; the store subscribes and persists:**
- `Events.WS_RAW_EVENT` → `ws_event`
- `Events.GAME_TICK` → `game_tick`
- `Events.PLAYER_UPDATE` → `server_state`
- trading/UI action events → `player_action`
- connection/source changes → `system_event`

### 4.2 No UI-thread writes

Writes happen on a background worker thread:
- UI updates via `TkDispatcher.submit()` only.
- Writer flush is batched (time + size thresholds).

---

## 5) Semantic Index (LanceDB) Plan

### 5.1 Chunking

Chunking should be deterministic and consistent across rebuilds:
- `ws_event` chunker (event type specific formatting, similar to claude-flow event_chunker).
- `session` chunker (group actions over a window).
- `game` chunker (episode summaries, transitions, outcomes).

### 5.2 Embeddings

Default: local sentence-transformers model (exact model TBD).
Store embedding model name + dimensions in:
- `manifests/schema_version.json`
- LanceDB table metadata

### 5.3 Incremental indexing

Index job processes only “new parquet files since last checkpoint”:
- checkpoint file in `manifests/vector_index_checkpoint.json`

---

## 6) Migration Strategy (No lingering legacy)

### 6.1 Phased cutover with strict deletion gates

**Phase A: Dual-write (short-lived)**
- Existing recorders continue writing legacy files.
- New `EventStore` writes Parquet simultaneously.
- Add metrics to compare counts per session/game/day.

**Phase B: Backfill**
- Import historical legacy files into Parquet.
- Validate:
  - row counts
  - sample record equality (key fields + raw hash)
  - detect missing event types

**Phase C: Cutover**
- Disable legacy writers behind a single config flag:
  - `REPLAYER_LEGACY_RECORDERS_ENABLED=false`
- Keep only:
  - exporter to JSONL/JSON for debugging/sharing
  - migration tools

**Phase D: Deletion**
- Remove legacy recorders and hardcoded paths.
- Keep a compatibility “export” CLI only.

### 6.2 “No legacy lingering” checklist (hard gates)

- No module writes directly to filesystem except `EventStore`.
- No hardcoded `/home/nomad/...` paths in runtime code.
- No duplicate capture directories (`raw_captures`, `rag_events`, `recordings`, etc.) used implicitly.
- Tests enforce:
  - only `EventStore` touches capture paths
  - schema version is pinned
  - exporters are explicit and opt-in

---

## 7) claude-flow Integration Options (pick one)

### Option 1 (recommended): claude-flow reads Parquet via DuckDB
- Implement a claude-flow ingestion entrypoint:
  - reads Parquet dataset
  - chunks + embeds
  - writes to LanceDB or its preferred vector store

### Option 2: REPLAYER exports claude-flow JSONL “raw captures”
- Keep a deterministic exporter that produces claude-flow’s expected JSONL event schema.
- Still treat export as derived output, not the canonical store.

---

## 8) Implementation Work Breakdown (TDD-first)

### Task 1: Define schema + paths
- Add `RUGS_DATA_DIR` (or similar) to config/env.
- Tests: no hardcoded paths; expected directory layout.

### Task 2: Implement EventStore writer (Parquet)
- Batch writer with atomic commit (tmp file → rename).
- Tests: append N events → parquet exists → DuckDB query returns N.

### Task 3: Subscribe EventStore to EventBus
- Ensure event shapes are normalized once.
- Tests: publish sample Events → persisted rows count increments.

### Task 4: Build vector indexer (LanceDB)
- Read parquet partitions → chunk → embed → upsert vectors.
- Tests (skippable if deps not installed): index small fixture → query returns expected.

### Task 5: Migration/backfill CLI
- Import legacy JSON/JSONL into parquet dataset.
- Tests: fixture legacy dir → parquet row count matches.

### Task 6: Cutover + delete legacy writers
- Config gate dual-write → single-write.
- Delete/replace legacy modules; keep exporter tool.
- Tests: rg-based or import-based guardrails to ensure legacy paths are gone.

---

## 9) Open Decisions (need answers to proceed)

1. **Data root default:** where should `RUGS_DATA_DIR` live by default?
   - `~/rugs_data` vs inside current `recordings_dir` vs repo-local
2. **Vector system choice:** confirm **LanceDB** (recommended) vs **Qdrant** or **Chroma**.
3. **Embedding model:** which model for indexing? (e.g. `all-MiniLM-L6-v2` to match claude-flow today)
4. **Retention:** do we keep raw frames forever? (affects storage and partitions)
5. **Schema versioning policy:** bump rules and rebuild triggers.

---

## 10) “Definition of Done” (operational)

- One command produces a valid Parquet dataset from live capture.
- One command builds/updates the LanceDB index from Parquet.
- One command can generate a training dataset slice (DuckDB query) deterministically.
- No legacy writers remain in runtime path (exporters are explicit only).
- claude-flow retrieval works using the new backend (either reads Parquet or reads exported docs).

