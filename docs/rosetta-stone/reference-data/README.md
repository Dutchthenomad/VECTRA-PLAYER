# Rosetta Stone Reference Data

Machine-readable reference data for the rugs.fun WebSocket protocol Rosetta Stone.

## Files

| File | Format | Size | Description |
|---|---|---|---|
| `game-20260206-003482fbeaae4ad5-full.json` | JSON | 7.3MB | Complete 1,311-event game dump |
| `key-samples.json` | JSON | ~200KB | 11 curated samples (one per event type per phase) |

## Reference Game

- **Game ID:** `20260206-003482fbeaae4ad5`
- **Captured:** 2026-02-06 03:04:19 UTC via rugs-feed service (port 9016)
- **Connection:** Public unauthenticated Socket.IO feed
- **Events:** 1,224 gameStateUpdate + 87 standard/newTrade = 1,311 total
- **Lifecycle:** Cooldown (15s) -> Presale (10s) -> Active (255 ticks) -> Rug

## Key Samples Index

| Sample | Phase | Description |
|---|---|---|
| `01_cooldown_early_minimal` | COOLDOWN | Typical cooldown tick - minimal fields |
| `02_cooldown_early_full` | COOLDOWN | First tick with gameHistory, godCandles |
| `03_presale_transition` | PRESALE | allowPreRoundBuys flips true |
| `04_game_start_tick0` | ACTIVE | Game begins - active=true, price=1 |
| `05_active_midgame` | ACTIVE | Typical active tick, tick 103 |
| `06_trade_buy` | ACTIVE | standard/newTrade buy |
| `07_trade_sell` | ACTIVE | standard/newTrade sell |
| `08_trade_short_close` | ACTIVE | standard/newTrade short_close |
| `09_trade_short_open` | ACTIVE | standard/newTrade short_open |
| `10_rug_event` | RUGGED | rugged=true, price crash |
| `11_postrug_final` | RUGGED | Final event with gameHistory |

## Usage

```python
import json

# Load all samples
with open('key-samples.json') as f:
    samples = json.load(f)

# Access specific sample
cooldown = samples['01_cooldown_early_minimal']
print(cooldown['data']['cooldownTimer'])  # 14900
```
