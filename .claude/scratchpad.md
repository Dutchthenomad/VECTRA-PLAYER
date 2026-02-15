# VECTRA-BOILERPLATE Session Scratchpad

Last Updated: 2026-01-25 (Current Session)

---

## CURRENT STATUS: Trade API + Minimal Trading UI COMPLETE

**Just Completed:**
- Trade API endpoints in Foundation HTTP server
- Minimal Trading artifact with full button mapping
- Recording Control bug fixes (16 issues)

**Ready for Testing:** `./vectra start` then test Trade API

---

## Session Summary (2026-01-25)

### Trade API Implementation

Added `/api/trade/*` endpoints to Foundation HTTP server (port 9001):

| Endpoint | Action |
|----------|--------|
| `POST /api/trade/buy` | Click BUY in browser |
| `POST /api/trade/sell` | Click SELL (optional percentage) |
| `POST /api/trade/sidebet` | Click SIDEBET |
| `POST /api/trade/increment` | Click +0.001/+0.01/+0.1/+1 |
| `POST /api/trade/percentage` | Click 10%/25%/50%/100% |
| `POST /api/trade/clear` | Click X (clear) |
| `POST /api/trade/half` | Click 1/2 |
| `POST /api/trade/double` | Click X2 |
| `POST /api/trade/max` | Click MAX |

### Files Modified

| File | Change |
|------|--------|
| `src/foundation/http_server.py` | Added Trade API endpoints |
| `src/foundation/launcher.py` | BrowserExecutor injection |
| `src/artifacts/tools/minimal-trading/app.js` | TradeExecutor + button wiring |
| `src/artifacts/tools/minimal-trading/styles.css` | Loading/feedback states |
| `src/artifacts/tools/recording-control/app.js` | 16 bug fixes |

### Recording Control Bug Fixes

**Critical (5):**
1. Wrong ticks field name (now tries multiple)
2. Missing lastError display
3. No interval cleanup (added cleanup())
4. Null refs in updateRecordingStatus
5. Null refs in updateStats

**Logic (4):**
6. Hardcoded 50GB max (now from API)
7. XSS in color param (regex validation)
8. RUG event race condition (debouncing)
9. No API response validation

**Minor (7):**
10-16. Error handling, null checks, debouncing, etc.

---

## Verification Commands

```bash
# Start Foundation with Trade API
./vectra start

# Test API directly
curl -X POST http://localhost:9001/api/trade/buy
curl -X POST http://localhost:9001/api/trade/increment -H "Content-Type: application/json" -d '{"amount": 0.01}'

# Open minimal-trading UI
xdg-open http://localhost:9001/artifacts/minimal-trading/

# Check recording service
curl http://localhost:9010/health
```

---

## Architecture Reference

```
┌─────────────────────────────────────────────────────────────┐
│                    FOUNDATION SERVICE (9000/9001)           │
│  ├── CDP Interceptor → Captures rugs.fun WebSocket         │
│  ├── Normalizer → Converts to game.tick, player.state      │
│  ├── Broadcaster → ws://localhost:9000/feed                │
│  └── Trade API → /api/trade/* (BrowserExecutor)            │
└─────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│minimal-trading  │  │recording-control│  │ Future Tools    │
│/artifacts/...   │  │/artifacts/...   │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Next Steps (Priority Order)

1. **Test Trade API end-to-end**
   - Start `./vectra start`
   - Open minimal-trading artifact
   - Click buttons, verify browser clicks

2. **Build Prediction Engine artifact**
   - Port Bayesian forecaster from Python
   - Real-time price predictions
   - Confidence intervals

3. **Build Seed Bruteforce artifact**
   - Port PRNG analysis
   - Pattern detection UI

4. **Build Orchestrator**
   - Tab wrapper for all artifacts
   - Single WebSocket connection

5. **Pipeline D: Training Data**
   - Observation builder
   - Episode segmenter
   - Training generator

---

## Port Allocation (from PORT-ALLOCATION-SPEC)

| Port | Service | Status |
|------|---------|--------|
| 9000 | Foundation WS | **SACRED** |
| 9001 | Foundation HTTP + Trade API | **SACRED** |
| 9010 | Recording Service | Active |
| 9011-9019 | Future Subscribers | Available |
| 9222 | Chrome CDP | Fixed |

---

## Commit Reference

```
7efa6cc feat(trading): Add Trade API and fix recording-control bugs
```

---

*Scratchpad updated for session continuity*
