# VECTRA HTML Artifacts

Browser-based tools that connect to the Foundation Service for real-time data.

## Quick Start

```bash
# 1. Start Foundation Service (provides WebSocket data)
cd /home/devops/Desktop/VECTRA-PLAYER
python -m foundation.launcher

# 2. Open an artifact in browser
# Either directly: file:///path/to/artifact/index.html
# Or via Foundation HTTP server: http://localhost:9001/artifacts/
```

## Directory Structure

```
src/artifacts/
├── README.md                 # This file
├── shared/                   # Shared libraries
│   ├── foundation-ws-client.js   # WebSocket client for Foundation
│   └── vectra-styles.css         # Catppuccin Mocha theme
├── templates/                # Templates for new artifacts
│   ├── artifact-template.html
│   └── artifact-template.js
├── tools/                    # Individual artifacts
│   ├── seed-bruteforce/      # PRNG seed analysis
│   └── prediction-engine/    # Bayesian price predictor
└── orchestrator/             # Tab-based wrapper
```

## Foundation Service Connection

All artifacts connect to the Foundation Service WebSocket:

```javascript
const client = new FoundationWSClient();

client.on('game.tick', (data) => {
    console.log(`Tick ${data.data.tick}: $${data.data.price}`);
});

client.connect();
```

### Event Types

| Event | Description |
|-------|-------------|
| `game.tick` | Price/tick stream (from gameStateUpdate) |
| `player.state` | Balance/position (from playerUpdate) |
| `connection.authenticated` | Auth confirmation |
| `player.trade` | Trade events |
| `sidebet.placed` | Sidebet placed |
| `sidebet.result` | Sidebet outcome |

### Event Data Structure

```javascript
{
    type: "game.tick",
    ts: 1737157200000,        // Server timestamp (ms)
    gameId: "20260117-abc123",
    seq: 42,                  // Sequence number
    data: {
        tick: 150,
        price: 2.3456,
        phase: "LIVE",
        active: true,
        rugged: false
    }
}
```

## Creating New Artifacts

1. Copy templates to `tools/your-artifact/`:
   ```bash
   cp -r templates tools/your-artifact
   cd tools/your-artifact
   mv artifact-template.html index.html
   mv artifact-template.js main.js
   ```

2. Edit `main.js`:
   - Update `ARTIFACT_CONFIG` with your artifact's info
   - Implement `initializeUI()` for setup
   - Implement `processGameTick(data)` for tick handling
   - Implement `processPlayerState(data)` for state handling

3. Test by opening `index.html` in browser (with Foundation running)

## Shared Styles (vectra-styles.css)

Catppuccin Mocha theme with:
- CSS variables for all colors
- Standard artifact layout (header/main/footer)
- Connection status indicator
- Cards, panels, tables
- Form elements
- Stats display components
- Price display with up/down colors
- Game phase badges

### Layout Classes

```html
<div class="artifact-container">
    <header class="artifact-header">...</header>
    <main class="artifact-main">...</main>
    <footer class="artifact-footer">...</footer>
</div>
```

### Color Variables

```css
--color-primary: #89b4fa;  /* Blue */
--color-success: #a6e3a1;  /* Green */
--color-warning: #f9e2af;  /* Yellow */
--color-error: #f38ba8;    /* Red */
--color-info: #74c7ec;     /* Sapphire */
```

## Orchestrator

The orchestrator provides a tabbed interface for multiple artifacts:

```
http://localhost:9001/artifacts/orchestrator/index.html
```

Features:
- Single WebSocket connection shared via postMessage
- Tab switching between artifacts
- Unified status bar
- Artifact registry for dynamic loading

## Port Configuration

| Service | Port | Purpose |
|---------|------|---------|
| Foundation WebSocket | 9000 | Data feed |
| Foundation HTTP | 9001 | Monitor UI + artifact serving |
| Flask Recording UI | 5000 | Dashboard (separate) |
| Chrome CDP | 9222 | Browser automation |

## Troubleshooting

### WebSocket won't connect

1. Ensure Foundation Service is running:
   ```bash
   python -m foundation.launcher
   ```

2. Check browser console for errors

3. Verify ports aren't blocked:
   ```bash
   ss -tlnp | grep -E '9000|9001'
   ```

### Artifacts not loading

1. For file:// URLs, ensure paths in index.html are correct
2. For HTTP serving, ensure Foundation HTTP server is running
3. Check browser's Network tab for 404 errors

### Events not appearing

1. Check connection status indicator
2. Verify Foundation is receiving data from Chrome (check monitor UI)
3. Ensure Chrome is on rugs.fun with game active
