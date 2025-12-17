# events Module Context

## Purpose
Pydantic schemas for all WebSocket events from rugs.fun backend, enabling type-safe parsing, validation, and serialization for the canonical database.

## Related Scripts
| Script | Relationship |
|--------|--------------|
| `../../services/event_store/schema.py` | EventEnvelope wraps these event models |
| `../../sources/websocket_feed.py` | Receives raw JSON, parses into these models |
| `../../sources/socketio_parser.py` | Extracts event payloads for parsing |
| `../../services/rag_ingester.py` | Indexes validated events to LanceDB |
| `../../../docs/specs/WEBSOCKET_EVENTS_SPEC.md` | Source of truth for field definitions |

## Data Flow
```
[WebSocketFeed/CDP] → raw JSON → [Pydantic validation] → EventEnvelope → [Parquet writer]
                                                                       → [LanceDB indexer]
```

## Key Decisions
- **Decimal for all money/prices** - Float precision issues cause calculation drift
- **Extra='allow' in Config** - Forward compatibility with new server fields
- **Underscore prefix for metadata** - `_ts`, `_seq`, `_source` added by ingestion
- **field_validator for coercion** - Server sends floats, we convert to Decimal
- **Optional defaults** - Handle partial payloads gracefully (server may omit fields)

## Schema Versions
| Event | Version | GitHub Issue | Tests |
|-------|---------|--------------|-------|
| GameStateUpdate | 1.0.0 | #1 | 20 |
| PlayerUpdate | 1.0.0 | #2 | 15 |
| UsernameStatus | 1.0.0 | #3 | 3 |
| PlayerLeaderboardPosition | 1.0.0 | #4 | 3 |
| NewTrade | 1.0.0 | #5 | 2 |
| SidebetRequest/Response | 1.0.0 | #6 | 4 |
| BuyOrder/SellOrder/TradeResponse | 1.0.0 | #7 | 4 |
| SystemEvents | 1.0.0 | #8 | 6 |

**Total Tests: 58** (all passing)

## Status
- [x] All 8 event schemas defined
- [x] All tests written and passing
- [ ] Indexed to LanceDB
- [ ] Relationships verified
