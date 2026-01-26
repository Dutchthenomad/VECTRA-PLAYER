# Minimal Trading Artifact

HTML port of the Tkinter MinimalWindow for RL training data collection.

## Overview

This artifact provides a browser-based trading interface that mirrors the functionality of the Python Tkinter `MinimalWindow` UI. It connects to the Foundation Service via WebSocket and displays real-time game data.

## Features

- **Status Bar**: TICK, PRICE, PHASE, USER, BALANCE displays
- **Connection Status**: WebSocket connection indicator
- **Recording Toggle**: Start/stop event recording
- **Execute Toggle**: Enable/disable real execution mode
- **Bet Controls**: Increment, utility (1/2, X2, MAX), and percentage buttons
- **Action Buttons**: BUY, SIDEBET, SELL

## Usage

1. Start the Foundation Service:
   ```bash
   python -m foundation.launcher
   ```

2. Open `index.html` in a browser or serve via HTTP:
   ```bash
   cd src/artifacts/tools/minimal-trading
   python -m http.server 8080
   # Open http://localhost:8080
   ```

## Events Consumed

| Event | Purpose |
|-------|---------|
| `game.tick` | Update TICK, PRICE, PHASE |
| `player.state` | Update BALANCE |
| `connection.authenticated` | Update USER |
| `connection` | Update connection status |

## Events Emitted

| Event | Purpose |
|-------|---------|
| `button.press` | ButtonEvent for RL training data |

## Specification

See `docs/specs/MINIMAL-UI-SPEC.md` for complete UI specification.

## Compliance

This artifact follows `docs/specs/MODULE-EXTENSION-SPEC.md`:
- Uses `FoundationWSClient` (no raw WebSocket)
- Imports `vectra-styles.css`
- Has `manifest.json` with required fields
