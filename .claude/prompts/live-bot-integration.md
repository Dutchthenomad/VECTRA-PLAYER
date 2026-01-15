# Fresh Session Prompt: Live Bot Integration

Copy everything below the line to start a new Claude Code session:

---

## Context

I'm working on VECTRA-PLAYER, a trading bot system for rugs.fun (a Solana-based game where you bet on price movements with sidebets).

**Current State:**
- Recording Dashboard running at `http://localhost:5005`
- Backtest Viewer functional - can simulate strategies on recorded game data
- Strategy profiles save/load working at `Machine Learning/strategies/`
- Chrome browser with `rugs_bot` profile has Phantom wallet connected to rugs.fun

**What's Working:**
- Game data recording to Parquet files (`~/rugs_data/events_parquet/`)
- Backtest simulation with visual playback
- Strategy parameter configuration (Kelly sizing, entry tick, bet sizes, etc.)
- CDP browser control via MCP tools

## Goal: Wire Live WebSocket to Bot System

I want to discuss and plan how to connect the live rugs.fun WebSocket feed to VECTRA so a bot can:
1. **Observe** real games in real-time (price ticks, game state)
2. **Decide** when to place sidebets based on loaded strategy
3. **Execute** actual bets via Phantom wallet in the browser
4. **Track** results and update wallet state

## Key Technical Details

### Sidebet Mechanics
- Place bet at current tick, 40-tick window
- If game rugs within window: WIN 5x bet
- If window expires: LOSE bet
- UI precision: 3 decimal places (0.XXX SOL)

### WebSocket Events (rugs.fun)
- `gameStateUpdate` - tick data, price, game phase
- `playerUpdate` - our wallet/position state
- `newTrade` - other players' trades
- Connection: `wss://rugs.fun` via Socket.IO

### Existing Code Locations
```
src/recording_ui/
├── app.py                    # Flask dashboard
├── services/
│   ├── backtest_service.py   # Strategy execution logic
│   └── chrome_tab.py         # CDP browser control
├── static/js/
│   └── backtest.js           # Frontend playback

src/services/
├── event_store/              # Parquet storage
└── websocket_client.py       # (if exists) WS connection
```

### Chrome Profile
- Profile: `~/.gamebot/chrome_profiles/rugs_bot/`
- Phantom wallet installed and connected
- CDP available on port 9222

## Questions to Discuss

1. **Architecture**: Should the bot run in Python (backend) or JavaScript (browser)?
2. **Execution**: How to trigger Phantom wallet transactions via CDP?
3. **Safety**: What guardrails needed for live trading (max loss, position limits)?
4. **State Sync**: How to reconcile bot state with actual wallet balance?
5. **Latency**: WebSocket → Decision → Execution timing considerations?

## Commands

```bash
# Start dashboard
.venv/bin/python src/recording_ui/app.py --port 5005

# Read scratchpad for more context
cat .claude/scratchpad.md

# Check strategy files
ls -la "Machine Learning/strategies/"

# View backtest service (strategy execution logic)
cat src/recording_ui/services/backtest_service.py
```

## Start Here

Read `.claude/scratchpad.md` first, then let's discuss the architecture for wiring live WebSocket data to enable real-time bot execution. I want to understand the tradeoffs before writing code.

---

*End of prompt - copy everything above*
