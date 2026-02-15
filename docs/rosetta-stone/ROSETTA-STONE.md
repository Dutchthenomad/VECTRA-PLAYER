# rugs.fun WebSocket Protocol Rosetta Stone

**Status:** REVIEWED - PUBLIC FEED ONLY | **Version:** 0.2.0 | **Date:** 2026-02-06
**Scope:** Unauthenticated public WebSocket feed events
**Reference Game:** `20260206-003482fbeaae4ad5`

---

## Purpose

This document is the **canonical, field-level dictionary** for every data point observable on the rugs.fun public WebSocket feed. It exists to eliminate ambiguity, assumption, and hallucination when building services that consume this data.

Every field definition in this document was produced by **painstaking, line-by-line review of actual captured game data**, cross-referenced against the rugs-expert RAG knowledge base.

### Scope Limitations

This version covers **PUBLIC FEED EVENTS ONLY** (unauthenticated Socket.IO connection):

| Covered (This Document) | NOT YET COVERED (Requires Auth) |
|---|---|
| `gameStateUpdate` | `playerUpdate` |
| `standard/newTrade` | `gameStatePlayerUpdate` |
| | `currentSidebet` |
| | `currentSidebetResult` |
| | `usernameStatus` |
| | `newChatMessage` |
| | `goldenHourUpdate` / `goldenHourDrawing` |
| | `rugPassQuestCompleted` |
| | `rugRoyaleUpdate` / `battleEventUpdate` |
| | `rugpoolDrawing` / `rugpoolStatus` |

**The identical methodology used here MUST be applied to all remaining event types until the entire rugs.fun WebSocket protocol is completely reverse-engineered and canonically recorded.**

### How This Document Was Produced

1. A complete game was captured via the `rugs-feed` service (port 9016, public Socket.IO connection)
2. All 1,311 events were categorized by game phase and event type
3. Every unique field was identified, its presence frequency measured across phases
4. Each field was defined with type, units, range, nullability, and behavioral notes
5. Definitions were cross-referenced against the `rugs-expert` RAG knowledge base (rugipedia canon)
6. Examples are drawn verbatim from the reference game

### Reference Data Files

| File | Contents |
|---|---|
| `reference-data/game-20260206-003482fbeaae4ad5-full.json` | Complete 1,311-event game dump (7.3MB) |
| `reference-data/key-samples.json` | 11 curated samples (one per event type per phase) |

---

## Game Lifecycle Overview

A rugs.fun game follows a fixed phase sequence. Understanding phases is prerequisite to understanding field presence.

```
SETTLEMENT (5s) ──► PRESALE (10s) ──► ACTIVE (variable) ──► RUGGED ──► SETTLEMENT
     │                    │                    │                  │
     │ cooldownTimer      │ allowPreRoundBuys  │ active=true      │ rugged=true
     │ 15000→10000        │ = true             │ tickCount=0+     │ price crashes
     │ server processing  │ timer 10000→0      │ price moves      │ forced liquidation
     │ not player-visible │ players can enter  │ trades happen    │ balance settlement
     │                    │ positions @ 1.00x  │                  │
     ▼                    ▼                    ▼                  ▼
  timer=10000:         timer→0:            PRNG determines    Server forces
  settlement done      active=true         rug tick           all sells, then
  presale opens        tick 0 broadcast                       cooldown restarts
```

**The 15-second cooldown is two phases in one:** The first ~5 seconds (timer 15000→10000) is a server-side settlement buffer for end-game processing. The final ~10 seconds (timer 10000→0) is the player-facing presale countdown. Presale positions are entered at the guaranteed 1.00x starting price and are **irrevocable** once placed.

**Note:** There is no discrete `cooldownTimer=0` event on the wire. The timer counts down and the game start signal is `active=true` + `tickCount=0`. This is a superposition boundary — do not code for a literal zero-timer event.

### Phase Detection Logic

```python
def detect_phase(event_data: dict) -> str:
    """Determine game phase from a gameStateUpdate event.

    Priority: active/rugged booleans are authoritative over timer values.
    The cooldownTimer approaching 0 is NOT a reliable phase boundary —
    use active=true as the definitive game-start signal.
    """
    if event_data.get('active', False) and not event_data.get('rugged', False):
        return 'ACTIVE'
    elif event_data.get('rugged', False):
        return 'RUGGED'
    elif event_data.get('cooldownTimer', 0) > 0:
        if event_data.get('allowPreRoundBuys', False):
            return 'PRESALE'
        return 'COOLDOWN'
    elif event_data.get('allowPreRoundBuys', False):
        return 'PRESALE'  # timer near-zero but game hasn't started yet
    return 'UNKNOWN'
```

### Reference Game Phase Distribution

| Phase | Event Count | Duration | Key Characteristics |
|---|---|---|---|
| COOLDOWN | 150 gameStateUpdate | ~4 seconds | Timer 15000→10100ms |
| PRESALE | 303 gameStateUpdate | ~10 seconds | Timer 10000→0ms, buys enabled |
| ACTIVE | 765 gameStateUpdate + 87 trades | ~64 seconds | 255 ticks, price 1.0→0.0018 |
| RUGGED | 6 gameStateUpdate | <1 second (typically ms) | Rug detected, forced liquidation, brief `active=true`/`rugged=true` overlap |

---

## Event 1: `gameStateUpdate`

**Direction:** Server → Client (broadcast to all connected clients)
**Frequency:** ~4 events/second (~250ms interval)
**Socket.IO frame:** `42["gameStateUpdate", {...}]`
**Purpose:** Primary game state broadcast. Contains current price, phase indicators, leaderboard, and periodic metadata dumps.

### Field Presence Rules

Not all fields are present on every tick. There are two emission patterns:

1. **Standard ticks** (~98%): Core game state fields only
2. **Transition ticks** (~2%): Extended payload with gameHistory, godCandles, daily records, and config. These appear on the first and last few ticks of phase transitions.

---

### Section 1.1: Core Identity

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 1 | `gameId` | string | `"20260206-003482fbeaae4ad5"` | EVERY tick |

**Definition:** Unique identifier for the current game session. One of three elements in the provably fair triplet (`gameId`, `serverSeed`, `serverSeedHash`).

**Format:** `YYYYMMDD-<16-character hex>` — always 25 characters.

**Role in PRNG:** The `gameId` is a direct input to the provably fair algorithm. The game outcome (price sequence + rug tick) is deterministically produced by combining `serverSeed` + `gameId`. This means the same seed with a different gameId produces a completely different game.

**Lifecycle — the two-broadcast rug transition:**
When a game rugs, the server emits **2 back-to-back `gameStateUpdate` events** within milliseconds:

| Broadcast | Purpose | Key Difference |
|---|---|---|
| **First** | Completes the finished game | `provablyFair.serverSeed` revealed — enables verification: `SHA256(serverSeed) === serverSeedHash` |
| **Second** | Genesis of the NEXT game | New `gameId` + new `serverSeedHash` generated from current Unix timestamp + server-side PRNG |

**Generation:** The date prefix (`YYYYMMDD`) comes from the UTC date. The hex suffix is derived from the Unix timestamp at game creation time via the server-side PRNG source code. There is no client/user seed involved.

**Persistence:** Assigned at game creation. Persists across all phases of a single game (cooldown through rug). Changes only at the rug-transition boundary described above.

---

### Section 1.2: Phase Indicators

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 2 | `cooldownTimer` | number | `14900` | EVERY tick |
| 3 | `cooldownPaused` | boolean | `false` | EVERY tick |
| 4 | `allowPreRoundBuys` | boolean | `false` | EVERY tick |
| 5 | `pauseMessage` | string | `""` | Active/Rugged ticks |

**`cooldownTimer`**
**Definition:** Milliseconds remaining until the next game phase transition.
**Units:** Milliseconds.
**Range:** 0 to 15000. Decrements in ~100ms steps during cooldown.

**The 15-second cooldown has two distinct purposes:**

| Window | Timer Range | Duration | Purpose |
|---|---|---|---|
| **Settlement buffer** | 15000 → 10000 | ~5 seconds | Server-side end-game processing: forced liquidations, balance settlements, sidebet payouts, leaderboard finalization. Not visible as a countdown to players. |
| **Presale countdown** | 10000 → 0 | ~10 seconds | Player-facing countdown. Players may enter long positions at the guaranteed 1.00x starting price and/or place sidebets. |

**Behavior:**
- Starts at `15000` immediately after a rug event
- Decrements each tick (~100ms per step)
- At `10000`, triggers `allowPreRoundBuys = true` (presale opens, player-visible countdown begins)
- Counts down toward `0` but there is **no discrete timer=0 event on the wire** — this is a superposition boundary where the timer expires and the game begins simultaneously
- The definitive game-start signal is `active=true` + `tickCount=0`, NOT `cooldownTimer=0`
- Stays at `0` throughout ACTIVE and RUGGED phases

**Presale lock-in rule:** Positions and sidebets entered during presale are **irrevocable**. Players cannot cancel or modify presale orders. They must wait until the game starts (`active=true`, tick 0), at which point all normal gameplay rules apply (sells, short closes, etc. become available).

**Gotcha:** The timer does NOT decrement in exact 100ms steps. Network jitter means you may see 14900, 14800, 14700 but also occasionally skip values. Do NOT wait for a literal `cooldownTimer=0` event — it may never appear. Use `active=true` as the authoritative game-start signal.

**`cooldownPaused`**
**Definition:** Whether an administrator has manually paused the cooldown timer.
**Range:** Boolean. Almost always `false`.
**Behavior:** When `true`, the cooldown timer freezes. Used for maintenance or admin intervention.

**`allowPreRoundBuys`**
**Definition:** Whether the presale phase is active, allowing players to place buy orders before the game officially starts.
**Range:** Boolean.
**Behavior:**
- `false` during early cooldown (timer > 10000)
- Flips to `true` when `cooldownTimer` reaches `10000`
- Remains `true` as timer counts down from 10000 toward 0 (this IS the presale window)
- Ceases to be meaningful once `active=true` + tick 0 broadcasts (game has started)
- Remains `false` during ACTIVE and RUGGED phases
**Gotcha:** This is the authoritative presale indicator. Do NOT derive presale status from timer value alone.

**`pauseMessage`**
**Definition:** Administrator message explaining why the game is paused.
**Range:** String. Usually empty string `""`.
**Presence:** Only present on Active and Rugged phase ticks (~63% of all events). Not present during Cooldown-only ticks.

---

### Section 1.3: Game State

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 6 | `active` | boolean | `true` | Active/Presale/Rugged |
| 7 | `price` | number | `0.4527...` | Active/Presale/Rugged |
| 8 | `rugged` | boolean | `true` | Active/Presale/Rugged |
| 9 | `tickCount` | number | `103` | Active/Presale/Rugged |
| 10 | `tradeCount` | number | `172` | ~98% of Active/Rugged |

**`active`**
**Definition:** Whether the game is currently in the active trading phase.
**Range:** Boolean.
**Behavior:**
- `false` during COOLDOWN and PRESALE
- `true` when game starts (tick 0)
- On rug: there is a brief overlap window where `active=true` and `rugged=true` coexist simultaneously before `active` flips to `false`
- This overlap is on the order of **milliseconds** (sub-100ms under normal server conditions), not seconds
**CRITICAL GOTCHA:** `active=true` does NOT mean the game is safe to trade. You MUST check `rugged` as well. Always evaluate `rugged` FIRST in any phase detection logic.
**Presence:** Not present on minimal cooldown ticks. Present on ~63% of all gameStateUpdate events.

**Security research note:** The sub-100ms window between `rugged=true` appearing and `active=false` being set represents a theoretical attack surface. Under sufficient server stress, this window could potentially be exploited for socket injection of 100% winning sidebets or front-running position liquidation with a sell order to avoid total loss. This remains an **unexplored research vector** — proper stress testing would be required to determine if the window is exploitable in practice.

**`price`**
**Definition:** Current token price expressed as a multiplier of the initial value.
**Units:** Multiplier (dimensionless). 1.0 = entry price. 2.0 = doubled.
**Range:** Starts at exactly `1.0` on tick 0. Can go to 200x+ (theoretical max observed: 1122x). Crashes to near-zero on rug (e.g., `0.0017842710071060424`).
**Precision:** IEEE 754 double-precision float. Up to 19 significant digits observed.
**Behavior:** Changes every tick according to the PRNG drift model: base drift [-2%, +3%] with 12.5% chance of big move [15%, 25%] and 0.001% chance of god candle (10x multiplier).

**The rug price — observable facts:**
- Price at rug is **NEVER zero**. It is always a very small positive number (e.g., `0.0017842710071060424`).
- This non-zero rug price is the price at which all open positions are force-liquidated by the server.
- The rug is an **implied crash to zero** from the player's perspective, but the actual settlement occurs at this remainder price.

**The rug price — research hypothesis (UNVERIFIED):**
The non-zero remainder at rug appears to encode information about whether the round was profitable or unprofitable for the platform treasury. Patterns observed across thousands of games show inverse correlation between aggregate player success and remainder characteristics. This is consistent with a server-side clearinghouse-style function that manages treasury balance and player state settlement. It further suggests the possibility of a meta-algorithm that adjusts probability range parameters across games to maintain platform solvency — a well-documented practice in the gaming industry where individual games remain provably fair per their published seeds while the *parameters feeding into those games* can be tuned. **This remains a research avenue for future analysis campaigns and is NOT confirmed.**

**`rugged`**
**Definition:** Whether the current game has ended via a rug pull event.
**Range:** Boolean.
**Behavior:**
- `false` during COOLDOWN, PRESALE, and ACTIVE
- Flips to `true` at rug tick
- Remains `true` through post-rug ticks until cooldown begins
**Gotcha:** `rugged` flips to `true` BEFORE `active` flips to `false`. Always check `rugged` first for rug detection.

**`tickCount`**
**Definition:** Number of price ticks elapsed since game start.
**Units:** Ticks. ~4 ticks per second (~250ms per tick).
**Range:** 0 to 5000 (theoretical max). Median game: 145 ticks. This reference game: 255 ticks.
**Behavior:** Starts at `0` on game start. Increments by 1 each tick. The rug can happen on any tick (0.5% probability per tick via PRNG).

**`tradeCount`**
**Definition:** Total number of trades executed in the current game.
**Range:** 0 to several hundred. This reference game: 306 total.
**Behavior:** Increments with each buy/sell/short. Persists from previous game during cooldown.
**Presence:** Present on ~98% of Active/Rugged ticks. Missing on a few transition ticks.

---

### Section 1.4: Partial Prices (Rolling Price Window)

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 11 | `partialPrices` | object | `{...}` | Active/Presale/Rugged |
| 11a | `partialPrices.startTick` | number | `251` | (parent present) |
| 11b | `partialPrices.endTick` | number | `255` | (parent present) |
| 11c | `partialPrices.values` | object | `{"251": 0.109...}` | (parent present) |

**`partialPrices`**
**Definition:** The price data for the **current candlestick** being rendered on the game UI. Contains exactly 5 ticks of data — one candle's worth.

**Candlestick rendering model:** The game UI displays a simulated candlestick chart. Each candle spans **5 ticks × ~250ms = 1.25 seconds**. The PRNG source code (`driftPrice()` function) generates tick-by-tick price movements that produce realistic-looking candlestick behavior — open, high, low, close patterns emerge naturally from the drift + volatility model applied at 4 ticks/second.

**Why 1.25 seconds instead of 1.0?** The chart presents as a "1-second candle" to the player, but the actual duration is 25% longer. This discrepancy is suspected to be a deliberate psychological design choice — the slightly extended duration may affect player decision-making around FOMO/FUD emotional responses, a technique consistent with known retention mechanics in the gaming industry. **This is a theory, not confirmed.**

**`partialPrices.startTick`**
**Definition:** First tick number in the current candle.

**`partialPrices.endTick`**
**Definition:** Last tick number in the current candle. Equal to the current `tickCount`.

**`partialPrices.values`**
**Definition:** Map of tick number (as string key) to price (as number value). Contains exactly the ticks from `startTick` to `endTick` inclusive.
**Format:** `{ "251": 0.1097..., "252": 0.1094..., ... }`
**Gotcha:** Keys are STRINGS not numbers. Always 5 ticks wide (one candle). At game start (tick 0), contains only `{"0": 1}` — the first candle has not yet completed.

**Backfill utility:** For clients connecting mid-game, `partialPrices` provides immediate context for the current candle without needing to replay the full tick history. The complete tick-by-tick price array for finished games is available in `gameHistory[].prices`.

**Example (from rug tick 255):**
```json
{
  "startTick": 251,
  "endTick": 255,
  "values": {
    "251": 0.10974594841914126,
    "252": 0.10944535617321477,
    "253": 0.10813627770291478,
    "254": 0.10599876754314011,
    "255": 0.0017842710071060424
  }
}
```
Note the dramatic price crash from tick 254 (0.106) to tick 255 (0.0018) — this IS the rug event, visible as a catastrophic final candle.

---

### Section 1.5: Session Statistics

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 12 | `connectedPlayers` | number | `172` | EVERY tick |
| 13 | `averageMultiplier` | number | `15.037...` | ~98% of Active+ |
| 14 | `count2x` | number | `52` | ~98% of Active+ |
| 15 | `count10x` | number | `9` | ~98% of Active+ |
| 16 | `count50x` | number | `1` | ~98% of Active+ |
| 17 | `count100x` | number | `1` | ~98% of Active+ |

**DATA CATEGORY NOTE:** The fields in this section (and Section 1.11: Daily Records) are **server-computed aggregate statistics** — second and third-order derived data that the rugs.fun game server already tracks and calculates. They do not change during a game; they update only at game boundaries. For downstream systems subscribing to the VECTRA data cleaning API, these fields should be **grouped and broadcast as a distinct statistical layer**, separate from real-time game state. This pre-computed statistical layer is valuable for building higher-order data displays for advanced players seeking elite-level play insights.

**`connectedPlayers`**
**Definition:** Number of WebSocket connections currently active on the server.
**Units:** Count.
**Range:** Typically 100-300. Fluctuates as players connect/disconnect.
**Behavior:** Updates in real-time. Not game-specific — reflects total server load. This is the ONE field in this section that updates continuously rather than at game boundaries.

**`averageMultiplier`**
**Definition:** The mean peak multiplier (rug point) across the last 100 completed games.
**Units:** Multiplier.
**Range:** Typically 2.0 to 20.0. Empirical mean across 10,810 games: 4.76x.
**Window:** 100-game rolling window (confirmed for v1/v2, assumed consistent in v3).
**Behavior:** Updates ONLY when a game completes. Holds steady from tick 0 through rug — it is intrinsically a post-game stat.

**`count2x` / `count10x` / `count50x` / `count100x`**
**Definition:** Number of games out of the last 100 that reached at least the Nx multiplier before rugging.
**Units:** Count (out of 100).
**Window:** Same 100-game rolling window as `averageMultiplier`.
**Behavior:** Updates ONLY when a game completes. These are session-rolling counters, not lifetime.
**Purpose:** Provides players with a statistical window showing recent game behavior distribution. Displayed in the UI as the "Last 100" stats bar.
**Example interpretation:** `count2x: 52` means 52 of the last 100 games reached 2x before rugging. `count100x: 1` means only 1 game reached 100x.

---

### Section 1.6: Provably Fair

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 18 | `provablyFair` | object | `{...}` | EVERY tick |
| 18a | `provablyFair.serverSeedHash` | string | `"2b2bcc8b..."` | EVERY tick |
| 18b | `provablyFair.version` | string | `"v3"` | EVERY tick |

**`provablyFair.serverSeedHash`**
**Definition:** SHA-256 hash of the server seed that determines this game's price sequence and rug point. Second element of the provably fair triplet (see Section 1.1).
**Format:** 64-character lowercase hexadecimal string.
**Behavior:** Published BEFORE the game starts (in the second rug-transition broadcast — see Section 1.1) so players can verify the game wasn't rigged after the fact. The actual `serverSeed` is only revealed AFTER the game ends (in `gameHistory` entries and in the first rug-transition broadcast).
**Verification flow:**
1. Before game: server publishes `serverSeedHash` (commitment)
2. During game: outcome is deterministically produced by `serverSeed + '-' + gameId` fed into `Math.seedrandom()` PRNG
3. After game: server reveals `serverSeed` in `gameHistory[].provablyFair`
4. Verification: `SHA256(serverSeed) === serverSeedHash` — if match, replay PRNG to confirm price sequence was predetermined
5. The rugs.fun UI provides a "Verify This Game" button linking to a third-party verification page

**`provablyFair.version`**
**Definition:** Version of the provably fair game algorithm. Persistent across all games — equivalent to a game patch version, not a per-game setting.
**Current value:** `"v3"` (as of February 2026).
**Version history:**

| Version | Key Change | Volatility Model |
|---|---|---|
| `v1` | Original | `0.005 * Math.sqrt(price)` |
| `v2` | Added God Candles, capped volatility | `0.005 * Math.min(10, Math.sqrt(price))` |
| `v3` | Refined God Candle parameters | Same as v2, God Candle chance = 0.001%, move = 10x |

**Behavior:** Determines which PRNG parameters and game rules apply. When the platform upgrades the algorithm, all subsequent games use the new version. Historical games retain their original version for verification purposes.

---

### Section 1.7: Rugpool

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 19 | `rugpool` | object | `{...}` | ~98% of Active+ |
| 19a | `rugpool.instarugCount` | number | `6` | (parent present) |
| 19b | `rugpool.threshold` | number | `10` | (parent present) |
| 19c | `rugpool.rugpoolAmount` | number | `4.444...` | (parent present) |

**Rugpool overview:** A consolation prize mechanic triggered by "insta-rug" games (games that rug within the first 5 ticks). When a game insta-rugs, all players with active positions (almost exclusively entered during presale) are liquidated. A portion of the liquidated SOL is pooled into the rugpool. Every 10 insta-rugs, 3 winners are chosen at random from the affected players, with entries weighted by lost position size. This mechanic serves as a psychological retention tool — discouraging rage-quitting by offering a lottery-style consolation for what are effectively mass good-faith liquidations (which are highly profitable for the treasury).

**Strategic value: LOW.** The rugpool is a side mechanic with no meaningful optimization potential. Documented here for protocol completeness only.

**`rugpool.instarugCount`**
**Definition:** Number of insta-rug games accumulated toward the next rugpool drawing.
**Range:** 0 to `threshold`. Resets to 0 after payout.
**Insta-rug definition:** Any game that rugs within the first 5 ticks (before meaningful price movement occurs).

**`rugpool.threshold`**
**Definition:** Number of insta-rugs required to trigger the rugpool drawing.
**Range:** Currently observed as `10`.

**`rugpool.rugpoolAmount`**
**Definition:** Total SOL accumulated in the rugpool from liquidated positions across insta-rug games.
**Units:** SOL.
**Behavior:** Accumulates a portion of liquidated SOL from each insta-rug event. When `instarugCount` reaches `threshold`, 3 winners are drawn at random (weighted by position size lost) and the pool is distributed.

---

### Section 1.8: Rug Royale

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 20 | `rugRoyale` | object | `{...}` | ~98% of Active+ |
| 20a | `rugRoyale.status` | string | `"INACTIVE"` | (parent present) |
| 20b | `rugRoyale.activeEventId` | null/string | `null` | (parent present) |
| 20c | `rugRoyale.currentEvent` | null/object | `null` | (parent present) |
| 20d | `rugRoyale.upcomingEvents` | array | `[]` | (parent present) |
| 20e | `rugRoyale.events` | array | `[]` | (parent present) |

**`rugRoyale`**
**Definition:** State of the Rug Royale tournament mode. A legacy competitive event mode, believed to be **effectively deprecated**.
**Status:** Always `"INACTIVE"` in all observed captures. The fields remain in the protocol (status, activeEventId, currentEvent, upcomingEvents, events) but are never populated. The platform has since introduced other event types (Golden Hour, etc.) that appear to have replaced Rug Royale's role. The skeleton likely persists in the codebase as a dormant feature.
**Strategic value: NONE.** No further documentation warranted unless the event is reactivated.

---

### Section 1.9: Leaderboard

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 21 | `leaderboard` | array[object] | `[{...}, ...]` | EVERY tick |

**Definition:** Top 10 players ranked by PnL for the current game. Server-authoritative.
**Length:** 0 to 10 entries. Empty (`[]`) at game start. Populates as players trade.

#### Leaderboard Entry Fields

| # | Field | Type | Example |
|---|---|---|---|
| 21a | `id` | string | `"did:privy:cmcl09j6b00a6l70mq2nunza1"` |
| 21b | `username` | string | `"Syken"` |
| 21c | `level` | number | `57` |
| 21d | `pnl` | number | `0.032391178` |
| 21e | `regularPnl` | number | `0.032391178` |
| 21f | `sidebetPnl` | number | `0` |
| 21g | `shortPnl` | number | `0` |
| 21h | `pnlPercent` | number | `0.850162152230971` |
| 21i | `hasActiveTrades` | boolean | `true` |
| 21j | `positionQty` | number | `0` |
| 21k | `avgCost` | number | `0` |
| 21l | `totalInvested` | number | `3.81` |
| 21m | `position` | number | `1` |
| 21n | `selectedCoin` | null/object | `null` |
| 21o | `sidebetActive` | null/boolean | `true` |
| 21p | `sideBet` | null/object | `{...}` |
| 21q | `shortPosition` | null/object | `{...}` |

**`id`**
**Definition:** Player's unique Privy decentralized identity (DID).
**Format:** `did:privy:<alphanumeric>`. Persistent across games and sessions.

**`username`**
**Definition:** Player's chosen display name.

**`level`**
**Definition:** Player's account level, earned through gameplay experience.
**Range:** 0 to 70+ observed.

**`pnl`**
**Definition:** Total profit/loss for this game across ALL position types (regular + sidebet + short).
**Units:** SOL.
**Calculation:** `pnl = regularPnl + sidebetPnl + shortPnl` (approximate — see fee note below).

**Fee/rake note:** The platform claims a per-tick fee of "roughly" 0.05% (deliberately imprecise language). This rake, combined with the treasury retaining all liquidated positions at rug, means `pnl` may not perfectly equal the sum of its components. The exact fee mechanics are **unverified and require comprehensive autopsy analysis** across large game samples. This is potentially connected to the non-zero rug price remainder discussed in Section 1.3 — the treasury clearinghouse function may settle fees, liquidation profits, and the rug remainder as part of a single end-game calculation.

**`regularPnl`**
**Definition:** PnL from regular long positions only.
**Units:** SOL.

**`sidebetPnl`**
**Definition:** PnL from sidebet wagers only.
**Units:** SOL.

**`shortPnl`**
**Definition:** PnL from short positions only.
**Units:** SOL.

**`pnlPercent`**
**Definition:** PnL as a percentage of total invested capital.
**Units:** Percentage (not decimal). `43.6` means 43.6%.
**Calculation:** `pnlPercent = (pnl / totalInvested) * 100`

**`hasActiveTrades`**
**Definition:** Whether the player currently has any open position (long, short, or sidebet).
**Range:** Boolean.

**`positionQty`**
**Definition:** Current long position size in token units.
**Units:** Token units (not SOL). To get SOL value: `positionQty * price`.
**Range:** 0 when no position. Positive when holding.

**`avgCost`**
**Definition:** Volume-weighted average entry price for the current long position.
**Units:** Multiplier.
**Range:** 0 when no position.
**Behavior:** Recalculated when adding to position. Does NOT change on partial sell.
**Verification status:** TENTATIVE — assumed correct, pending comprehensive autopsy analysis.

**`totalInvested`**
**Definition:** Total SOL committed to positions in this game (cumulative buys).
**Units:** SOL.
**Gotcha:** This is cumulative - it goes UP when buying but does NOT decrease when selling. It represents total capital deployed, not current exposure.
**Verification status:** TENTATIVE — assumed correct, pending comprehensive autopsy analysis.

**`position`**
**Definition:** Leaderboard rank. 1 = highest PnL.
**Range:** 1 to 10 (only top 10 shown).

**`selectedCoin`**
**Definition:** The coin/token the player is trading with. Null for default (SOL).
**Values:** `null` for SOL, or object like `{"address": "0xPractice", "ticker": "FREE", "name": "Free Practice Token", ...}` for practice mode.

**`sidebetActive`**
**Definition:** Whether the player has an active sidebet.
**Range:** `null` (no sidebet), `true` (active sidebet).

**`sideBet`**
**Definition:** Active sidebet details. Null when no sidebet placed.

#### sideBet Sub-Object

| # | Field | Type | Example |
|---|---|---|---|
| 21p-i | `startedAtTick` | number | `0` |
| 21p-ii | `gameId` | string | `"20260206-..."` |
| 21p-iii | `end` | number | `40` |
| 21p-iv | `betAmount` | number | `3.048` |
| 21p-v | `xPayout` | number | `5` |
| 21p-vi | `coinAddress` | string | `"So111...112"` |
| 21p-vii | `bonusPortion` | number | `3.048` |
| 21p-viii | `realPortion` | number | `0` |

**`startedAtTick`** - Tick when sidebet was placed.
**`end`** - Target tick. Always `startedAtTick + 40`. **Hardcoded 40-tick window — not player-configurable.**
**`betAmount`** - Total SOL wagered on the sidebet. **This is the ONLY player-configurable parameter** — bet size can vary, everything else is fixed.
**`xPayout`** - Payout multiplier if sidebet wins. **Always `5`** (5:1 ratio = 400% profit + original bet returned). Hardcoded.
**`coinAddress`** - Token contract address. `So111...112` = native SOL.
**`bonusPortion`** - Portion of bet from bonus/practice balance.
**`realPortion`** - Portion of bet from real SOL balance.

**Sidebet Mechanics:**
- **Bet:** Player wagers the game will rug within 40 ticks of placement.
- **Win condition:** `rugTick < end` (game rugs before the 40-tick window expires). Payout = `betAmount * 5`. Binary outcome — no partial payouts.
- **Loss condition:** `rugTick >= end` (game survives past the window). Player loses 100% of `betAmount`.
- **House edge:** The 40-tick hardcoded window combined with the fixed 5x payout is precisely calibrated to maintain a minimum ~51% house win rate. Given `RUG_PROB = 0.005` per tick, the probability of a rug within any 40-tick window is `1 - (0.995^40) ≈ 18.2%`. At 5x payout, expected value = `0.182 * 5 - 0.818 * 1 = 0.092`, yielding a slight player edge on paper — but this does not account for the per-tick rake or treasury settlement mechanics discussed in the fee note above.

**`shortPosition`**
**Definition:** Active short position details. Null when no short position.

#### shortPosition Sub-Object

| # | Field | Type | Example |
|---|---|---|---|
| 21q-i | `amount` | number | `0.2` |
| 21q-ii | `entryPrice` | number | `1.023...` |
| 21q-iii | `entryTick` | number | `3` |
| 21q-iv | `currentValue` | number | `0.2079...` |
| 21q-v | `pnl` | number | `0.0079...` |
| 21q-vi | `coinAddress` | string | `"So111...112"` |
| 21q-vii | `bonusPortion` | number | `0` |
| 21q-viii | `realPortion` | number | `0.2` |

**`amount`** - SOL committed to the short position.
**`entryPrice`** - Price (multiplier) when the short was opened.
**`entryTick`** - Tick when the short was opened.
**`currentValue`** - Current SOL value of the short position (updates in real-time).
**`pnl`** - Current unrealized profit/loss on the short.
**Short Mechanics:** Profit when price goes DOWN from entry. `pnl = amount * (entryPrice - currentPrice) / entryPrice`.
**Verification status:** TENTATIVE — short PnL formula assumed correct, pending comprehensive autopsy analysis. The interaction between short PnL, per-tick rake, and rug liquidation mechanics has not been fully verified.

---

### Section 1.10: Game History (Rolling Window)

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 22 | `gameHistory` | array[object] | `[{...}, ...]` | RARE (~0.5%) |

**Definition:** Rolling window of the last 10 completed games. Appears on transition ticks only (first few ticks of cooldown, last few ticks of rugged phase).
**Length:** Exactly 10 entries.
**ML Value:** Contains complete tick-by-tick price data and provably fair seeds for historical games. Eliminates need for manual recording — this is the primary mechanism for building historical training datasets from the public feed.

**Collection strategy (IMPORTANT for downstream subscribers):**
Since the window contains exactly 10 games and shifts by 1 on each new game completion, a subscriber that captures `gameHistory` **once every 10 games** (on rug events) will collect all games with zero overlap. This eliminates the deduplication problem entirely. The trigger is simple: maintain a lightweight counter of rugged games and capture the full `gameHistory` payload every 10th rug. Any subscriber built against this Rosetta Stone should implement this pattern by default. A secondary deduplication check by `gameId` should exist only as a redundant safety net against collection errors, not as a primary data integrity mechanism.

#### Game History Entry Fields

| # | Field | Type | Example |
|---|---|---|---|
| 22a | `id` | string | `"20260206-74fb8b07116b4d39"` |
| 22b | `timestamp` | number | `1770347058350` |
| 22c | `peakMultiplier` | number | `7.070...` |
| 22d | `rugged` | boolean | `true` |
| 22e | `gameVersion` | string | `"v3"` |
| 22f | `prices` | array[number] | `[1, 1.0017, 1.0171, ...]` |
| 22g | `globalTrades` | array[object] | `[]` |
| 22h | `globalSidebets` | array[object] | `[{...}, ...]` |
| 22i | `provablyFair` | object | `{serverSeed: "...", serverSeedHash: "..."}` |

**`id`** - Game ID of the completed game.
**`timestamp`** - Unix millisecond timestamp when the game ended (rug event).
**`peakMultiplier`** - Highest price reached during the game before rug.
**`rugged`** - Always `true` (only completed/rugged games appear in history).
**`gameVersion`** - Protocol version. Currently `"v3"`.
**`prices`** - Complete tick-by-tick price array. Starts at `1.0` (index 0 = tick 0). Length = total game ticks. Final value = rug price.
**`globalTrades`** - **ALWAYS null/empty on the public feed.** The per-trade data volume is far too large to include in the rolling history payload. To capture global trade data, you must subscribe to `standard/newTrade` events in real-time and build the trade history manually. This is not a foreseeable priority.
**`globalSidebets`** - All sidebet events from that game. Contains both `"placed"` and `"payout"` entries.

#### provablyFair (in gameHistory - REVEALED)

| # | Field | Type | Example |
|---|---|---|---|
| 22i-i | `serverSeed` | string | `"49f5826e..."` |
| 22i-ii | `serverSeedHash` | string | `"c1709d66..."` |

**`serverSeed`** - The actual server seed. ONLY revealed after game ends. 64-character hex.
**`serverSeedHash`** - SHA-256 hash of the server seed. Matches the hash published before the game.
**Verification:** `SHA256(serverSeed) === serverSeedHash`. Can replay PRNG to confirm price sequence.

#### globalSidebets Entry (placed type)

| # | Field | Type | Example |
|---|---|---|---|
| 22h-i | `playerId` | string | `"did:privy:..."` |
| 22h-ii | `username` | string | `"JJWilliams04"` |
| 22h-iii | `gameId` | string | `"20260206-..."` |
| 22h-iv | `betAmount` | number | `0.002` |
| 22h-v | `xPayout` | number | `5` |
| 22h-vi | `coinAddress` | string | `"So111...112"` |
| 22h-vii | `bonusPortion` | number | `0` |
| 22h-viii | `realPortion` | number | `0.002` |
| 22h-ix | `timestamp` | number | `1770347007162` |
| 22h-x | `type` | string | `"placed"` |
| 22h-xi | `startedAtTick` | number | `2` |
| 22h-xii | `end` | number | `42` |
| 22h-xiii | `id` | string | `"cc028cdf-..."` |

#### globalSidebets Entry (payout type)

| # | Field | Type | Example |
|---|---|---|---|
| 22h-i | `playerId` | string | `"did:privy:..."` |
| 22h-ii | `gameId` | string | `"20260206-..."` |
| 22h-iii | `username` | string | `"Nofear"` |
| 22h-iv | `betAmount` | number | `0.01` |
| 22h-v | `payout` | number | `0` |
| 22h-vi | `profit` | number | `-0.01` |
| 22h-vii | `xPayout` | number | `5` |
| 22h-viii | `coinAddress` | string | `"So111...112"` |
| 22h-ix | `endTick` | number | `40` |
| 22h-x | `startTick` | number | `0` |
| 22h-xi | `tickIndex` | number | `0` |
| 22h-xii | `timestamp` | number | `1770347016603` |
| 22h-xiii | `type` | string | `"payout"` |
| 22h-xiv | `id` | string | `"8f0e4c72-..."` |

**`payout`** - SOL returned to player. 0 = lost the bet.
**`profit`** - Net profit/loss. Negative = lost. `profit = payout - betAmount`.
**`endTick`** - The target tick from the original bet.
**`startTick`** - When the bet was placed (may differ from `startedAtTick` in placed events).
**`tickIndex`** - The tick when the game actually rugged (settlement tick).

---

### Section 1.11: Daily Records & God Candles

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 23 | `highestToday` | number | `1122.278...` | RARE (~0.5%) |
| 24 | `highestTodayTimestamp` | number | `1770346597293` | RARE |
| 25 | `highestTodayGameId` | string | `"20260206-37b5..."` | RARE |
| 26 | `highestTodayServerSeed` | string | `"3b0be421..."` | RARE |

**`highestToday`**
**Definition:** The highest peak multiplier achieved by any game today (UTC day).
**Units:** Multiplier.

**`highestTodayTimestamp`** - Unix ms when the daily record was set.
**`highestTodayGameId`** - Game ID that holds the daily record.
**`highestTodayServerSeed`** - Server seed of the record-holding game (for verification).

#### God Candle Fields (3 tiers: 2x, 10x, 50x)

| # | Pattern | Type | Example |
|---|---|---|---|
| 27-31 | `godCandle{N}x` | null/number | `1122.278...` |
| | `godCandle{N}xTimestamp` | null/number | `1770346598019` |
| | `godCandle{N}xGameId` | null/string | `"20260206-43cb..."` |
| | `godCandle{N}xServerSeed` | null/string | `"bfb75645..."` |
| | `godCandle{N}xMassiveJump` | null/array | `[22.48, 224.85]` |

**Definition:** "God Candles" are extreme single-tick price movements caused by the PRNG's god candle mechanic (see Appendix A). These fields track the most recent god candle at each tier today (UTC day).

**PRNG mechanics (from source code):**
A god candle fires when `randFn() < 0.00001` (0.001% per tick) AND `price <= 100x`. The effect is always `price * 10` — a **10x single-tick multiplier** on the current price. God candles **cannot fire above 100x** — this is a hardcoded ceiling in `driftPrice()`.

**The three tiers (2x, 10x, 50x) classify the resulting price level after the jump:**

| Tier | Meaning | Example |
|---|---|---|
| `godCandle2x` | God candle that pushed price into the 2x+ range | Price was ~0.3x, jumped to ~3x |
| `godCandle10x` | God candle that pushed price into the 10x+ range | Price was ~1.5x, jumped to ~15x |
| `godCandle50x` | God candle that pushed price into the 50x+ range | Price was ~7x, jumped to ~70x |

**`godCandle{N}x`** - The peak multiplier of the god candle game. `null` if no god candle at this tier today.
**`godCandle{N}xMassiveJump`** - Array of two numbers: `[jump_multiplier, resulting_price]`. The single-tick price jump and where it landed.
**`godCandle{N}xTimestamp`**, **`godCandle{N}xGameId`**, **`godCandle{N}xServerSeed`** - Provably fair verification data for the god candle game.

**Presence:** Only on transition ticks (~0.5% of events). All three tiers are **typically null**. A non-null god candle is an **exceptionally rare event**.

**HIGH PRIORITY CAPTURE FLAG:** When any god candle field is non-null, this data MUST be flagged and preserved by any subscriber. God candle events are critical for:
- Statistical arbitrage research (high-payout opportunity patterns)
- Bayesian prediction model training (conditional probability of extreme moves)
- PRNG behavioral analysis (conditions that produce god candle-eligible states)

---

### Section 1.12: Available Coins

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 32 | `availableShitcoins` | array[object] | `[{...}]` | RARE (~0.5%) |

**Definition:** List of tradeable tokens/coins available on the platform. Currently only contains the practice token — a leftover from proto-v1 and earlier codebases.

#### Coin Entry Fields

| # | Field | Type | Example |
|---|---|---|---|
| 32a | `address` | string | `"0xPractice"` |
| 32b | `ticker` | string | `"FREE"` |
| 32c | `name` | string | `"Practice SOL"` |
| 32d | `max_bet` | number | `10000` |
| 32e | `max_win` | number | `100000` |

**Only one practice token exists.** It appears under various monikers in the codebase (`FREE`, `Practice SOL`, etc.) but is a single token. Real SOL trades use the native Solana address (`So11111111111111111111111111111111111111112`).

**CRITICAL FILTERING REQUIREMENT:** The leaderboard (Section 1.9) does **NOT** differentiate between practice token and real SOL players. Both appear side-by-side with identical field structures. Any downstream subscriber that performs:
- **Player profiling / top player tracking** — MUST filter for `realPortion > 0` or `coinAddress != "0xPractice"` to exclude practice trades
- **Treasury PnL estimation** — MUST filter for real SOL only; practice token trades have zero treasury impact
- **Tournament tracking** (e.g., if Rug Royale is resurrected) — MUST filter for practice token plays only, as tournaments are scored by practice token accumulation over a 1-hour window with a prize pot for the highest balance

---

### Section 1.13: Game Version

| # | Field | Type | Example | Presence |
|---|---|---|---|---|
| 33 | `gameVersion` | string | `"v3"` | RARE (~0.7%) |

**Definition:** Protocol version of the current game. Determines PRNG parameters and game rules. See Section 1.6 (Provably Fair) for full version history and behavioral differences between v1/v2/v3.
**Presence:** Only appears on transition ticks (game start, rug).

---

## Event 2: `standard/newTrade`

**Direction:** Server → Client (broadcast to all connected clients)
**Frequency:** Sporadic. Emitted on each trade execution.
**Socket.IO frame:** `42["standard/newTrade", {...}]`
**Purpose:** Broadcasts trade activity (buys, sells, shorts) for all players.

### Always-Present Fields

| # | Field | Type | Example |
|---|---|---|---|
| T1 | `id` | string | `"35b49232-5d50-..."` |
| T2 | `gameId` | string | `"20260206-003482fb..."` |
| T3 | `playerId` | string | `"did:privy:cmj0ke..."` |
| T4 | `username` | string | `"BANDZDAGOD"` |
| T5 | `level` | number | `11` |
| T6 | `price` | number | `1.0232...` |
| T7 | `type` | string | `"buy"` |
| T8 | `tickIndex` | number | `3` |
| T9 | `coin` | string | `"solana"` |
| T10 | `amount` | number | `0.2` |

**`id`**
**Definition:** Unique trade identifier (UUID v4).

**`gameId`**
**Definition:** Game in which this trade occurred.

**`playerId`**
**Definition:** Player's Privy DID.

**`username`** / **`level`**
**Definition:** Player display name and account level at time of trade.

**`price`**
**Definition:** Game price (multiplier) at the moment the trade executed.
**Units:** Multiplier.

**`type`**
**Definition:** Trade action type. One of four values:
- `"buy"` - Opening or adding to a long position
- `"sell"` - Closing or reducing a long position
- `"short_open"` - Opening a short position
- `"short_close"` - Closing a short position

**`tickIndex`**
**Definition:** Game tick when the trade executed.

**`coin`**
**Definition:** The base chain/coin. Always `"solana"` observed.

**`amount`**
**Definition:** SOL value of the trade.
**Units:** SOL.
**For buys:** SOL spent. **For sells:** SOL received. **For shorts:** SOL committed/returned.

### Conditional Fields

| # | Field | Type | Present On | Example |
|---|---|---|---|---|
| T11 | `qty` | number | buy, sell | `0.030389477` |
| T12 | `leverage` | number | buy (sometimes) | `4` |
| T13 | `bonusPortion` | number | buy (sometimes), sell | `0.794391178` |
| T14 | `realPortion` | number | buy (sometimes), sell | `0` |

**`qty`**
**Definition:** Token units transacted.
**For buys:** Token units received. **For sells:** Token units sold.
**Relationship to amount:** `qty ≈ amount / price` (for buys). For sells, `amount ≈ qty * price`.
**Gotcha:** For `short_open` and `short_close`, `qty` is `0` - shorts are denominated in SOL, not token units.

**`leverage`**
**Definition:** Leverage multiplier applied to the buy.
**Range:** 1 to 5 (whole integers only — no fractional leverage). Only available for players at **level 10 and above**. Only present on buy trades.
**Behavior:** When `leverage=N`, the player's position is Nx the SOL committed. Leveraged positions are subject to **forced liquidation thresholds** based on price drop from entry:

| Leverage | Liquidation Threshold |
|---|---|
| 1x | No forced liquidation (only at rug) |
| 2x | Position liquidated at -20% from entry |
| 3x | Position liquidated at -10% from entry |
| 4x | Position liquidated at -2.5% from entry |
| 5x | Position liquidated at -1% from entry |

**Stacking:** A player can enter a leveraged position (e.g., 2x) and then add a separate 1x position on top of it while the leveraged position is still active. This stacking behavior may explain the varying `bonusPortion`/`realPortion` splits observed across trades from the same player. **This is an educated inference — requires verification before canonical.**
**Shorts:** Leverage is NOT available on short positions.

**`bonusPortion`** / **`realPortion`**
**Definition:** How much of the trade amount came from bonus balance vs real SOL.
**Relationship:** `bonusPortion + realPortion = amount` (approximately).
**Use case:** Practice/free tokens use `bonusPortion`. Real money uses `realPortion`.
**Token lock rule:** Players **cannot switch between practice tokens and real SOL during an active game.** The choice must be made before the game begins and is locked until the current game rugs. This means all trades from a single player within one game will consistently use the same token type.

---

### Trade Type Examples (Verbatim from Reference Game)

#### buy (48 occurrences)
```json
{
  "id": "7c10a169-2a5c-4f9a-8e7f-e7d0da4a1b47",
  "gameId": "20260206-003482fbeaae4ad5",
  "playerId": "did:privy:cmfl7ry7000w1ie0ck1ve8oq9",
  "price": 0.9871838027078929,
  "type": "buy",
  "qty": 0.030389477,
  "tickIndex": 37,
  "coin": "solana",
  "amount": 0.03,
  "leverage": 4,
  "bonusPortion": 0,
  "realPortion": 0.03,
  "username": "Aussiegambler",
  "level": 34
}
```

#### sell (30 occurrences)
```json
{
  "id": "f6e59f57-6f35-46db-889c-89ecaea5c672",
  "gameId": "20260206-003482fbeaae4ad5",
  "playerId": "did:privy:cmcl09j6b00a6l70mq2nunza1",
  "type": "sell",
  "price": 1.0425081084067145,
  "tickIndex": 8,
  "coin": "solana",
  "amount": 0.794391178,
  "qty": 0.762,
  "bonusPortion": 0.794391178,
  "realPortion": 0,
  "username": "Syken",
  "level": 57
}
```

#### short_open (6 occurrences)
```json
{
  "id": "35b49232-5d50-4283-8bab-be0aab8129ef",
  "gameId": "20260206-003482fbeaae4ad5",
  "playerId": "did:privy:cmj0kekh0046il80bwjmpe31d",
  "price": 1.0232227021442333,
  "type": "short_open",
  "qty": 0,
  "tickIndex": 3,
  "coin": "solana",
  "amount": 0.2,
  "username": "BANDZDAGOD",
  "level": 11
}
```
Note: `qty` is `0` for shorts. No `bonusPortion`/`realPortion` on this trade (field presence varies).

#### short_close (3 occurrences)
```json
{
  "id": "40c140f3-39ec-45bd-979e-b162842fe190",
  "gameId": "20260206-003482fbeaae4ad5",
  "playerId": "did:privy:cmj0kekh0046il80bwjmpe31d",
  "price": 0.8209533756239946,
  "type": "short_close",
  "qty": 0,
  "tickIndex": 62,
  "coin": "solana",
  "amount": 0.208619772,
  "username": "BANDZDAGOD",
  "level": 11
}
```
Note: `amount` on `short_close` is the SOL returned (principal + profit).

### Forced Sells at Rug (CRITICAL)

When a game rugs, the server emits `standard/newTrade` events with `type: "sell"` for every player with an open position, force-liquidating them at the rug price. **These forced sells are indistinguishable from voluntary sells on the wire** — there is no field, flag, or marker that identifies a trade as server-forced vs player-initiated.

**To identify forced sells, you must infer by correlation:**
- Cross-reference `standard/newTrade` sells with `gameStateUpdate` events where `rugged=true`
- Forced sells cluster within milliseconds of the rug event
- The `price` on forced sells will match the near-zero rug price
- The `tickIndex` will match the final tick of the game

**Research note:** The mechanics of forced liquidation at the rug price — specifically how the non-zero remainder price interacts with position settlement — is a critical area for future reverse-engineering. Understanding precisely how the server calculates the forced sell `amount` at the rug remainder price may reveal treasury settlement mechanics (see Section 1.3 research hypothesis).

### Leverage Liquidation Sells

Similarly, when a leveraged position hits its liquidation threshold (see `leverage` field above), the server emits a `standard/newTrade` with `type: "sell"` that is **also indistinguishable from a voluntary sell**. These can be inferred by checking whether the sell price corresponds to the liquidation threshold relative to the player's `avgCost` from the leaderboard.

---

## Appendix A: PRNG Parameters & Source Code (Provably Fair)

These parameters govern the price curve and are verifiable using the revealed `serverSeed`.

| Parameter | Value | Description |
|---|---|---|
| `RUG_PROB` | 0.005 | 0.5% chance per tick to rug |
| `DRIFT_MIN` | -0.02 | Minimum price drift per tick |
| `DRIFT_MAX` | 0.03 | Maximum price drift per tick |
| `BIG_MOVE_CHANCE` | 0.125 | 12.5% chance of big move per tick |
| `BIG_MOVE_MIN` | 0.15 | Minimum big move size |
| `BIG_MOVE_MAX` | 0.25 | Maximum big move size |
| `GOD_CANDLE_CHANCE` | 0.00001 | 0.001% chance of god candle per tick |
| `GOD_CANDLE_MOVE` | 10.0 | 10x multiplier on god candle |

### Price Drift Function (v3 — verbatim from rugs.fun verification page)

```javascript
function driftPrice(
    price,
    DRIFT_MIN,
    DRIFT_MAX,
    BIG_MOVE_CHANCE,
    BIG_MOVE_MIN,
    BIG_MOVE_MAX,
    randFn,
    version = 'v3',
    GOD_CANDLE_CHANCE = 0.00001,
    GOD_CANDLE_MOVE = 10.0,
    STARTING_PRICE = 1.0
) {
    // v3 adds God Candle feature - rare massive price increase
    // CEILING: God candles CANNOT fire above 100x
    if (version === 'v3' && randFn() < GOD_CANDLE_CHANCE && price <= 100 * STARTING_PRICE) {
        return price * GOD_CANDLE_MOVE;
    }

    let change = 0;

    if (randFn() < BIG_MOVE_CHANCE) {
        const moveSize = BIG_MOVE_MIN + randFn() * (BIG_MOVE_MAX - BIG_MOVE_MIN);
        change = randFn() > 0.5 ? moveSize : -moveSize;
    } else {
        const drift = DRIFT_MIN + randFn() * (DRIFT_MAX - DRIFT_MIN);

        // Version difference is in this volatility calculation
        // v1: unbounded volatility
        // v2/v3: capped at sqrt(10) to prevent extreme swings at high prices
        const volatility = version === 'v1'
            ? 0.005 * Math.sqrt(price)
            : 0.005 * Math.min(10, Math.sqrt(price));

        change = drift + (volatility * (2 * randFn() - 1));
    }

    let newPrice = price * (1 + change);

    if (newPrice < 0) {
        newPrice = 0;
    }

    return newPrice;
}
```

### Game Verification Function (verbatim)

```javascript
function verifyGame(serverSeed, gameId, version = 'v3') {
    const combinedSeed = serverSeed + '-' + gameId;
    const prng = new Math.seedrandom(combinedSeed);

    let price = 1.0;
    let peakMultiplier = 1.0;
    let rugged = false;

    for (let tick = 0; tick < 5000 && !rugged; tick++) {
        // 0.5% chance per tick to rug — checked BEFORE price drift
        if (prng() < RUG_PROB) {
            rugged = true;
            continue;
        }

        const newPrice = driftPrice(
            price,
            DRIFT_MIN,
            DRIFT_MAX,
            BIG_MOVE_CHANCE,
            BIG_MOVE_MIN,
            BIG_MOVE_MAX,
            prng.bind(prng),
            version
        );

        price = newPrice;

        if (price > peakMultiplier) {
            peakMultiplier = price;
        }
    }

    return {
        peakMultiplier: peakMultiplier,
        rugged: rugged
    };
}
```

**Key insights from the source code:**
1. **Rug is purely random** — 0.5% per tick, independent of price or history
2. **Rug check happens BEFORE price drift** — the rug tick does NOT produce a new price via `driftPrice()`
3. **God candles require price <= 100x** — hardcoded ceiling prevents extreme god candles at high multipliers
4. **Max ticks: 5000** — game auto-ends if not rugged naturally (extremely rare)
5. **PRNG is fully deterministic** — given `serverSeed + '-' + gameId`, the entire price sequence and rug tick are reproducible
6. **Combined seed format** — `serverSeed + '-' + gameId` fed into `Math.seedrandom()` (see Section 1.1)

### Empirical Statistics (10,810 games)

| Metric | Value |
|---|---|
| Game duration: min | 2 ticks |
| Game duration: max | 1,815 ticks |
| Game duration: mean | 200.9 ticks |
| Game duration: median | 145 ticks |
| Peak multiplier: min | 1.00x |
| Peak multiplier: max | 246.37x |
| Peak multiplier: mean | 4.76x |
| Peak multiplier: median | 1.89x |

---

## Appendix B: Authenticated Events (NOT YET DOCUMENTED)

The following events require an authenticated WebSocket connection (wallet connected via Phantom) and are **not captured by the public rugs-feed service**. Each requires the same line-by-line canonical treatment applied in this document.

| Event | Direction | Priority | Description |
|---|---|---|---|
| `playerUpdate` | Server→Client | P0 | Server-authoritative player state (balance, positions) |
| `gameStatePlayerUpdate` | Server→Client | P0 | Player's own leaderboard entry with full PnL breakdown |
| `currentSidebet` | Server→Client | P1 | Sidebet placement confirmation |
| `currentSidebetResult` | Server→Client | P1 | Sidebet outcome (win/loss/push) |
| `usernameStatus` | Server→Client | P2 | Username validation response |
| `newChatMessage` | Server→Client | P3 | Chat message broadcast |
| `goldenHourUpdate` | Server→Client | P1 | Golden Hour event status |
| `goldenHourDrawing` | Server→Client | P1 | Golden Hour raffle results |
| `rugPassQuestCompleted` | Server→Client | P2 | Quest completion notification |
| `rugRoyaleUpdate` | Server→Client | P3 | Rug Royale tournament state |
| `battleEventUpdate` | Server→Client | P3 | Battle mode state |
| `rugpoolDrawing` | Server→Client | P2 | Rugpool jackpot drawing |
| `rugpoolStatus` | Server→Client | P2 | Rugpool status update |
| `sidebetEventUpdate` | Server→Client | P2 | Sidebet event state |
| `maintenanceUpdate` | Server→Client | P3 | Server maintenance notices |
| `newSideBet` | Server→Client | P2 | Global sidebet placement broadcast |
| `gameNotification` | Server→Client | P3 | In-game notification |
| `chatHistory` | Server→Client | P3 | Historical chat messages on connect |
| `inboxMessages` | Server→Client | P3 | Player inbox messages |
| Client→Server events | | | `buyOrder`, `sellOrder`, `requestSidebet`, `authenticate`, etc. |

**Total known event types: 29** (from coverage report scanning 19,207 events across 20 recording files)

---

## Appendix C: Socket.IO Wire Format

Raw WebSocket frames from `wss://api.rugs.fun/socket.io/` use Engine.IO message type prefixes:

| Prefix | Type | Description |
|---|---|---|
| `0` | OPEN | Connection handshake |
| `2` | PING | Keep-alive ping |
| `3` | PONG | Keep-alive pong |
| `4` | MESSAGE | Generic message |
| `42` | EVENT | Socket.IO event (most common) |

**Parsing:**
```
Raw frame:  42["gameStateUpdate",{"gameId":"20260206-xxx",...}]
            ^^
            Engine.IO prefix (strip this)

JSON parse: ["gameStateUpdate", {...}]
            [0] = event name
            [1] = event data
```

---

## Appendix D: Reference Game Summary

| Property | Value |
|---|---|
| Game ID | `20260206-003482fbeaae4ad5` |
| Capture Date | 2026-02-06 03:04:19 UTC |
| Total Events | 1,311 |
| gameStateUpdate events | 1,224 |
| standard/newTrade events | 87 |
| Tick Count | 255 |
| Peak Price | ~1.47x (tick ~49) |
| Rug Price | 0.0017842710071060424 |
| Game Duration | ~79 seconds (cooldown to final event) |
| Active Duration | ~64 seconds (tick 0 to rug) |
| Trade Breakdown | 48 buy, 30 sell, 6 short_open, 3 short_close |
| Server Seed Hash | `2b2bcc8b4b71d70a1f69163b18f883acada7d5c12f327fb4624e0df792bee893` |
| Unique Fields (gameStateUpdate) | 43 |
| Unique Fields (standard/newTrade) | 14 |

**Full verbose data:** `reference-data/game-20260206-003482fbeaae4ad5-full.json`
**Curated samples:** `reference-data/key-samples.json`

---

*v0.1.0: Initial draft produced by line-by-line review of captured game data, cross-referenced against the rugs-expert RAG knowledge base.*
*v0.2.0: Section-by-section collaborative review with domain expert. Key additions: provably fair triplet lifecycle, settlement buffer/presale split, timer superposition boundary, candlestick rendering model, treasury clearinghouse hypothesis, per-tick rake, leverage tiers with liquidation thresholds, forced sell inference requirements, god candle capture flags, smart collection strategy, full PRNG source code. Fields marked TENTATIVE where verification is pending.*

*This document covers PUBLIC FEED EVENTS ONLY. The same methodology must be applied to all authenticated event types (Appendix B) to complete the protocol reverse-engineering.*
