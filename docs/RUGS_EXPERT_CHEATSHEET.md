# rugs-expert Agent Cheat Sheet

**Agent Role:** Protocol knowledge specialist for rugs.fun WebSocket events
**Knowledge Base:** `/home/nomad/Desktop/claude-flow/knowledge/rugs-events/`

---

## Quick Questions

### Event Schema Queries

```
"What fields are in playerUpdate?"
"Explain the gameStateUpdate event"
"Which events fire during PRESALE phase?"
"What is the difference between playerUpdate and gameStatePlayerUpdate?"
"Show me the buyOrderResponse schema"
```

### Real-Time Data Queries

```
"Show me the last 10 events"
"What events fired in the last 30 seconds?"
"Show me all playerUpdate events from this session"
"What is my current balance according to the server?"
"Show me the last trade I executed"
```

### Protocol Analysis

```
"What is the typical latency for BUY trades?"
"How many different event types are in the protocol?"
"Which events require authentication?"
"What events indicate a game has rugged?"
"Explain the game phase detection logic"
```

### Button/UI Queries

```
"What is the XPath for the SELL button?"
"Show me all button selectors in BrowserBridge"
"How does the multi-strategy selector work?"
"What CSS classes are used for the BUY button?"
```

### Debugging Support

```
"Why is my balance not updating in the UI?"
"I see gameStateUpdate but not playerUpdate - why?"
"How can I verify the WebSocket connection is authenticated?"
"Show me the event sequence for a typical trade"
```

---

## Common Workflows

### 1. Discovering Event Fields

**You:** "I see a new event called `priceAlert`. What fields does it have?"

**rugs-expert will:**
1. Query EventStore for recent samples
2. Extract unique field names and types
3. Show example payloads
4. Propose adding to canonical spec (if confirmed)

### 2. Analyzing Trade Latency

**You:** "What is the latency breakdown for my last trade?"

**rugs-expert will:**
1. Query last buyOrder/sellOrder event
2. Find corresponding response event
3. Calculate:
   - Send latency (client → server)
   - Confirmation latency (server → response)
   - Total roundtrip
4. Compare to historical average

### 3. Understanding Auth Events

**You:** "Why am I not seeing playerUpdate events?"

**rugs-expert will:**
1. Check if usernameStatus was received (indicates auth)
2. Verify WebSocket connection source (CDP vs direct)
3. Check if wallet is connected in browser
4. Provide troubleshooting steps

### 4. Button Automation Help

**You:** "How do I click the SIDEBET button reliably?"

**rugs-expert will:**
1. Show SelectorStrategy.BUTTON_CSS_SELECTORS['SIDEBET']
2. Explain multi-strategy priority order:
   - CSS selectors (most reliable)
   - Exact text match
   - Starts-with text match
   - Class pattern matching
3. Provide test code snippet

---

## DuckDB Query Templates

**rugs-expert** can generate these for you, but here are templates:

### Recent Events (Last N)
```sql
SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
ORDER BY timestamp DESC LIMIT 10
```

### Events by Type
```sql
SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
WHERE data->>'event' = 'playerUpdate'
ORDER BY timestamp DESC LIMIT 20
```

### Event Type Distribution
```sql
SELECT
  data->>'event' as event_type,
  COUNT(*) as count,
  MIN(timestamp) as first_seen,
  MAX(timestamp) as last_seen
FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
GROUP BY data->>'event'
ORDER BY count DESC
```

### Latency Analysis
```sql
SELECT
  AVG(CAST(data->>'latency' as FLOAT)) as avg_latency_ms,
  MIN(CAST(data->>'latency' as FLOAT)) as min_latency_ms,
  MAX(CAST(data->>'latency' as FLOAT)) as max_latency_ms,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY CAST(data->>'latency' as FLOAT)) as p95_latency_ms
FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
WHERE data->>'event' = 'gameStateUpdate'
```

### Time Range Query
```sql
SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
WHERE timestamp BETWEEN '2025-12-24 12:00:00' AND '2025-12-24 13:00:00'
ORDER BY timestamp ASC
```

### Trade History
```sql
SELECT
  timestamp,
  data->>'event' as event_type,
  data->'data'->>'type' as trade_type,
  data->'data'->>'amount' as amount,
  data->'data'->>'price' as price
FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
WHERE data->>'event' IN ('buyOrderResponse', 'sellOrderResponse')
ORDER BY timestamp DESC
LIMIT 20
```

---

## Validation Tier System

**CRITICAL:** rugs-expert checks validation tiers before citing claims.

| Tier | Symbol | Meaning |
|------|--------|---------|
| canonical | ✓ | Verified against live protocol |
| verified | ✓ | Validated against 1000+ games |
| reviewed | † | Human reviewed, not validated |
| theoretical | * | Hypothesis, needs validation |

**Example output with tier markers:**

```
The rug probability is 0.5% per tick (RUG_PROB = 0.005). ✓
Volatility increases ~78% in final 5 ticks before rug.*
The 25-50x zone offers optimal risk/reward ratios.†

---
Validation Notes:
- † 1 reviewed claim (L5-strategy-tactics/probability-framework.md)
- * 1 theoretical claim (L7-advanced-analytics/prng-analysis.md)
Use `/validation-report` for detailed source analysis.
```

---

## RAG Query Commands

**rugs-expert** uses these internally, but you can run them too:

```bash
# Semantic search of event documentation
cd ~/Desktop/claude-flow/rag-pipeline
source .venv/bin/activate
python -m retrieval.retrieve "What fields are in playerUpdate?" -k 5

# Search phase matrix
cat ~/Desktop/claude-flow/knowledge/rugs-events/generated/phase_matrix.json | jq '.ACTIVE'

# Search field index
cat ~/Desktop/claude-flow/knowledge/rugs-events/generated/field_index.json | jq '.price'
```

---

## Knowledge Base Files

**Canonical Spec (Single Source of Truth):**
```
~/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md
```

**Generated Indexes (Derived):**
```
~/Desktop/claude-flow/knowledge/rugs-events/generated/events.jsonl
~/Desktop/claude-flow/knowledge/rugs-events/generated/phase_matrix.json
~/Desktop/claude-flow/knowledge/rugs-events/generated/field_index.json
```

**Reference Sources:**
```
~/rugs_recordings/raw_captures/          # Raw protocol data
~/Desktop/REPLAYER/src/                  # Implementation code
~/Desktop/VECTRA-PLAYER/src/             # Browser automation
~/Desktop/claude-flow/knowledge/rugs-events/RUGS_BROWSER_CONNECTION.md
```

**Strategy Knowledge Base (L1-L7):**
```
~/Desktop/claude-flow/knowledge/rugs-strategy/
├── L1-game-mechanics/         # Core game rules
├── L2-protocol/               # WebSocket events
├── L5-strategy-tactics/       # Trading strategies
├── L6-statistical-baselines/  # Empirical data
└── L7-advanced-analytics/     # PRNG analysis
```

---

## Anti-Patterns (What NOT to Ask)

**DON'T:**
- "Guess the field names" - rugs-expert checks spec first
- "Assume all events are in raw captures" - auth events require CDP
- "Modify WEBSOCKET_EVENTS_SPEC.md" - requires explicit approval
- "Cite theoretical content as fact" - must mark with *

**DO:**
- "Check the canonical spec for field definitions"
- "Query live EventStore data for examples"
- "Explain auth requirements for events"
- "Mark unverified claims with validation tiers"

---

## Example Debugging Session

**You:** "I'm not seeing my balance update after buying 1 SOL"

**rugs-expert:**
```
Let me investigate:

1. Checking recent events:
   [Query EventStore for last 30 seconds]

   Found events:
   - 12:45:30.123 buyOrder (amount: 1.0 SOL)
   - 12:45:30.245 buyOrderResponse (success: true)
   - 12:45:30.267 playerUpdate (balance: 8.876 SOL) ✓

2. Server says your balance is 8.876 SOL.

3. Checking UI state:
   [Query LiveStateProvider]

   LiveStateProvider shows: 9.876 SOL (STALE)

4. Diagnosis:
   - Server updated correctly (playerUpdate received)
   - UI not subscribed to EventBus.PLAYER_UPDATE
   - Fix: LiveFeedController needs to handle PLAYER_UPDATE event

5. Workaround:
   - Refresh VECTRA-PLAYER UI
   - Or reconnect to browser (forces state sync)
```

---

## Commands Reference

### Start Debugging Workflow
```bash
cd /home/nomad/Desktop/VECTRA-PLAYER
./start_debugging.sh
```

### Query Recent Events
```bash
duckdb -c "SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
           ORDER BY timestamp DESC LIMIT 10"
```

### Check CDP Connection
```bash
curl -s http://localhost:9222/json/version | jq .Browser
```

### View Live Logs
```bash
tail -f /tmp/vectra_player.log
```

### Export Events to JSONL
```bash
duckdb -c "COPY (
    SELECT * FROM '~/rugs_data/events_parquet/doc_type=ws_event/**/*.parquet'
) TO '~/rugs_data/exports/events.jsonl' (FORMAT JSON, ARRAY false)"
```

---

## Tips for Effective Queries

1. **Be Specific:** Instead of "How does trading work?", ask "What events fire when I place a BUY order?"

2. **Provide Context:** "I just clicked BUY and nothing happened" vs "Show me the last 10 events"

3. **Ask for Examples:** "Show me an example playerUpdate payload" gets real data

4. **Request Validation:** "Is this field documented in the spec?" checks canonical source

5. **Chain Questions:**
   - "What fields are in playerUpdate?"
   - "Show me the last 5 playerUpdate events"
   - "Why is my balance different from the server?"

---

**Quick Start:** See `/home/nomad/Desktop/VECTRA-PLAYER/docs/DEBUGGING_QUICKSTART.md`
**Full Workflow:** See `/home/nomad/Desktop/VECTRA-PLAYER/docs/WEBSOCKET_DEBUGGING_WORKFLOW.md`
