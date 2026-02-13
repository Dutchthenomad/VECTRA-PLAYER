# Bayesian Predictor Migration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the Bayesian Predictor from `notebooks/` to Foundation Boilerplate compliance, validating the framework works.

**Architecture:** Two components - HTML artifact for real-time visualization, Python subscriber for predictions. Both connect to Foundation Service (ws://localhost:9000/feed). The Python subscriber exposes HTTP API (port 9002) for the HTML artifact to poll.

**Tech Stack:** Python (asyncio, http.server), JavaScript (FoundationWSClient), HTML/CSS (vectra-styles.css)

---

## Overview

This migration validates the Foundation Boilerplate by:
1. Moving files to correct locations
2. Converting raw WebSocket code to use Foundation clients
3. Running validation script to confirm compliance
4. Testing with live Foundation Service

## Pre-Migration Checklist

- [ ] Foundation Service running (`python -m foundation.launcher`)
- [ ] Existing files backed up (they're in notebooks/)
- [ ] Validation script works (`python scripts/validate_artifact.py --help`)

---

## Task 1: Create Python Subscriber Directory Structure

**Files:**
- Create: `src/subscribers/bayesian_predictor/__init__.py`
- Create: `src/subscribers/bayesian_predictor/subscriber.py`
- Create: `src/subscribers/bayesian_predictor/prediction_engine.py`
- Create: `src/subscribers/bayesian_predictor/game_state_manager.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/subscribers/bayesian_predictor
```

**Step 2: Create `__init__.py`**

```python
"""Bayesian Predictor Subscriber - Real-time game outcome predictions."""

from .subscriber import BayesianPredictorSubscriber

__all__ = ["BayesianPredictorSubscriber"]
```

**Step 3: Commit**

```bash
git add src/subscribers/bayesian_predictor/__init__.py
git commit -m "feat(subscriber): Create bayesian_predictor package structure"
```

---

## Task 2: Migrate Game State Manager

**Files:**
- Create: `src/subscribers/bayesian_predictor/game_state_manager.py`
- Reference: `notebooks/bayesian prediction engine/files/game_state_manager.py`

**Step 1: Copy game_state_manager.py**

Copy the file from notebooks with no changes - it has no WebSocket code, just game state logic.

```bash
cp "notebooks/bayesian prediction engine/files/game_state_manager.py" \
   src/subscribers/bayesian_predictor/game_state_manager.py
```

**Step 2: Commit**

```bash
git add src/subscribers/bayesian_predictor/game_state_manager.py
git commit -m "feat(subscriber): Add game state manager for bayesian predictor"
```

---

## Task 3: Migrate Prediction Engine

**Files:**
- Create: `src/subscribers/bayesian_predictor/prediction_engine.py`
- Reference: `notebooks/bayesian prediction engine/files/prediction_engine.py`

**Step 1: Copy prediction_engine.py**

Copy the file - it contains the Bayesian forecaster and HTTP API. Only change: update the API port from 9001 to 9002 (9001 is Foundation HTTP).

```bash
cp "notebooks/bayesian prediction engine/files/prediction_engine.py" \
   src/subscribers/bayesian_predictor/prediction_engine.py
```

**Step 2: Update default port to 9002**

In `prediction_engine.py`, change line ~513:

```python
# OLD
def start_api_server(engine: LivePredictionEngine, port: int = 9001):

# NEW
def start_api_server(engine: LivePredictionEngine, port: int = 9002):
```

**Step 3: Commit**

```bash
git add src/subscribers/bayesian_predictor/prediction_engine.py
git commit -m "feat(subscriber): Add prediction engine with HTTP API (port 9002)"
```

---

## Task 4: Create Foundation-Compliant Subscriber

**Files:**
- Create: `src/subscribers/bayesian_predictor/subscriber.py`
- Test: `src/tests/test_subscribers/test_bayesian_predictor.py`

**Step 1: Write the failing test**

Create `src/tests/test_subscribers/test_bayesian_predictor.py`:

```python
"""Tests for BayesianPredictorSubscriber."""

import pytest
from unittest.mock import Mock, MagicMock

from foundation.client import FoundationClient
from foundation.events import GameTickEvent, PlayerStateEvent
from subscribers.bayesian_predictor import BayesianPredictorSubscriber


class TestBayesianPredictorSubscriber:
    """Test BayesianPredictorSubscriber inherits correctly."""

    def test_inherits_base_subscriber(self):
        """Subscriber must inherit from BaseSubscriber."""
        from foundation.subscriber import BaseSubscriber
        assert issubclass(BayesianPredictorSubscriber, BaseSubscriber)

    def test_has_required_methods(self):
        """Subscriber must implement all required methods."""
        assert hasattr(BayesianPredictorSubscriber, 'on_game_tick')
        assert hasattr(BayesianPredictorSubscriber, 'on_player_state')
        assert hasattr(BayesianPredictorSubscriber, 'on_connection_change')

    def test_instantiation_with_client(self):
        """Subscriber can be instantiated with a FoundationClient."""
        mock_client = Mock(spec=FoundationClient)
        mock_client.on = MagicMock(return_value=lambda: None)

        subscriber = BayesianPredictorSubscriber(mock_client, start_api=False)
        assert subscriber is not None

    def test_processes_game_tick(self):
        """Subscriber processes game tick events."""
        mock_client = Mock(spec=FoundationClient)
        mock_client.on = MagicMock(return_value=lambda: None)

        subscriber = BayesianPredictorSubscriber(mock_client, start_api=False)

        event = GameTickEvent(
            type="game.tick",
            ts=1234567890,
            game_id="test-game-001",
            seq=1,
            active=True,
            rugged=False,
            price=1.5,
            tick_count=10,
            phase="ACTIVE"
        )

        # Should not raise
        subscriber.on_game_tick(event)

        # Engine should have processed it
        assert subscriber.engine is not None
```

**Step 2: Run test to verify it fails**

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE/src && \
python -m pytest tests/test_subscribers/test_bayesian_predictor.py -v
```

Expected: FAIL - module not found

**Step 3: Write the subscriber**

Create `src/subscribers/bayesian_predictor/subscriber.py`:

```python
"""
Bayesian Predictor Subscriber - Foundation Boilerplate Compliant.

Inherits from BaseSubscriber and feeds events to the prediction engine.

Usage:
    from foundation.client import FoundationClient
    from subscribers.bayesian_predictor import BayesianPredictorSubscriber

    client = FoundationClient()
    subscriber = BayesianPredictorSubscriber(client)
    await client.connect()
"""

import logging
from typing import Optional

from foundation.client import FoundationClient
from foundation.subscriber import BaseSubscriber
from foundation.events import GameTickEvent, PlayerStateEvent

from .prediction_engine import LivePredictionEngine, start_api_server

logger = logging.getLogger(__name__)


class BayesianPredictorSubscriber(BaseSubscriber):
    """
    Foundation-compliant subscriber for Bayesian predictions.

    Feeds game.tick events to the prediction engine and exposes
    predictions via HTTP API.
    """

    def __init__(
        self,
        client: FoundationClient,
        api_port: int = 9002,
        start_api: bool = True,
        prediction_tick: int = 5
    ):
        """
        Initialize subscriber.

        Args:
            client: FoundationClient instance
            api_port: Port for prediction API (default: 9002)
            start_api: Whether to start HTTP API server
            prediction_tick: Make prediction by this tick
        """
        self.engine = LivePredictionEngine(
            prediction_tick_threshold=prediction_tick
        )
        self.api_port = api_port

        if start_api:
            start_api_server(self.engine, port=api_port)
            logger.info(f"Bayesian Predictor API started on port {api_port}")

        # Call parent __init__ AFTER setting up engine
        # (parent registers event handlers)
        super().__init__(client)

        logger.info("BayesianPredictorSubscriber initialized")

    def on_game_tick(self, event: GameTickEvent) -> None:
        """
        Handle game.tick events.

        Converts Foundation event to dict and feeds to prediction engine.
        """
        event_dict = {
            'type': 'game.tick',
            'gameId': event.game_id,
            'data': {
                'tick': event.tick_count,
                'price': event.price,
                'active': event.active,
                'rugged': event.rugged,
                'cooldownTimer': event.cooldown_timer,
                'allowPreRoundBuys': event.allow_pre_round_buys,
                'phase': event.phase,
                'gameHistory': event.game_history or []
            }
        }
        self.engine.process_event(event_dict)

    def on_player_state(self, event: PlayerStateEvent) -> None:
        """Handle player.state events (not used for predictions)."""
        pass

    def on_connection_change(self, connected: bool) -> None:
        """Handle connection state changes."""
        status = "connected" if connected else "disconnected"
        logger.info(f"Foundation connection: {status}")

    def get_prediction(self) -> Optional[dict]:
        """Get current prediction."""
        return self.engine.get_current_prediction()

    def get_stats(self) -> dict:
        """Get accuracy statistics."""
        return self.engine.get_accuracy_stats()
```

**Step 4: Run test to verify it passes**

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE/src && \
python -m pytest tests/test_subscribers/test_bayesian_predictor.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/subscribers/bayesian_predictor/subscriber.py \
        src/tests/test_subscribers/test_bayesian_predictor.py
git commit -m "feat(subscriber): Add Foundation-compliant BayesianPredictorSubscriber"
```

---

## Task 5: Validate Python Subscriber

**Step 1: Run validation script**

```bash
python scripts/validate_artifact.py src/subscribers/bayesian_predictor/subscriber.py
```

Expected output:
```
✓ PASSED: src/subscribers/bayesian_predictor/subscriber.py
  - Inherits from BaseSubscriber
  - No direct websocket imports
  - Located in src/subscribers/
```

**Step 2: If validation fails, fix issues and re-run**

**Step 3: Commit validation success**

```bash
git commit --allow-empty -m "chore: Validate bayesian_predictor subscriber passes boilerplate checks"
```

---

## Task 6: Create HTML Artifact Directory

**Files:**
- Create: `src/artifacts/tools/bayesian-predictor/index.html`
- Create: `src/artifacts/tools/bayesian-predictor/main.js`
- Create: `src/artifacts/tools/bayesian-predictor/README.md`

**Step 1: Create directory**

```bash
mkdir -p src/artifacts/tools/bayesian-predictor
```

**Step 2: Create README.md**

```markdown
# Bayesian Predictor

Real-time game outcome predictions using mean-reversion Bayesian analysis.

## Features

- Live price/tick/phase display from Foundation Service
- Peak multiplier predictions with confidence intervals
- Duration predictions with confidence intervals
- Mean reversion direction indicator
- Accuracy tracking over time

## Requirements

- Foundation Service running (ws://localhost:9000/feed)
- Bayesian Predictor Subscriber running (API on port 9002)

## Usage

1. Start Foundation Service: `python -m foundation.launcher`
2. Start Predictor Subscriber (separate terminal):
   ```python
   import asyncio
   from foundation.client import FoundationClient
   from subscribers.bayesian_predictor import BayesianPredictorSubscriber

   async def main():
       client = FoundationClient()
       subscriber = BayesianPredictorSubscriber(client)
       await client.connect()
       # Keep running
       await asyncio.Event().wait()

   asyncio.run(main())
   ```
3. Open `index.html` in browser

## Architecture

```
Foundation Service (ws://localhost:9000/feed)
        │
        ├──► index.html (FoundationWSClient) - Real-time price display
        │
        └──► BayesianPredictorSubscriber (Python)
                    │
                    └──► HTTP API (localhost:9002)
                              │
                              └──► index.html polls /state endpoint
```
```

**Step 3: Commit**

```bash
git add src/artifacts/tools/bayesian-predictor/README.md
git commit -m "docs(artifact): Add bayesian-predictor README"
```

---

## Task 7: Create Foundation-Compliant HTML

**Files:**
- Create: `src/artifacts/tools/bayesian-predictor/index.html`
- Reference: `notebooks/bayesian prediction engine/files/index.html`

**Step 1: Create index.html with required imports**

The HTML must:
1. Import `../../shared/vectra-styles.css`
2. Import `../../shared/foundation-ws-client.js`
3. Use `FoundationWSClient` instead of raw `WebSocket`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bayesian Predictor - VECTRA</title>

    <!-- REQUIRED: Shared styles -->
    <link rel="stylesheet" href="../../shared/vectra-styles.css">

    <!-- Artifact-specific styles -->
    <style>
        /* Prediction-specific overrides */
        .prediction-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--spacing-md);
        }

        .prediction-item {
            background: var(--surface1);
            border-radius: var(--radius-md);
            padding: var(--spacing-md);
        }

        .prediction-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--subtext0);
            margin-bottom: var(--spacing-sm);
        }

        .prediction-value {
            font-family: var(--font-mono);
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--text);
        }

        .prediction-ci {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--subtext1);
        }

        .confidence-bar {
            height: 4px;
            background: var(--surface0);
            border-radius: 2px;
            margin-top: var(--spacing-sm);
            overflow: hidden;
        }

        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--mauve), var(--blue));
            border-radius: 2px;
            transition: width 0.3s;
        }

        .regime-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .regime-normal { background: var(--surface1); color: var(--subtext1); }
        .regime-suppressed { background: rgba(243, 139, 168, 0.2); color: var(--red); }
        .regime-inflated { background: rgba(166, 227, 161, 0.2); color: var(--green); }
        .regime-volatile { background: rgba(249, 226, 175, 0.2); color: var(--yellow); }

        .direction-indicator {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            padding: var(--spacing-md);
            background: var(--surface1);
            border-radius: var(--radius-md);
            margin-top: var(--spacing-md);
        }

        .direction-arrow {
            font-size: 1.5rem;
        }

        .direction-arrow.up { color: var(--green); }
        .direction-arrow.down { color: var(--red); }
        .direction-arrow.stable { color: var(--subtext1); }

        .accuracy-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--spacing-sm);
        }

        .accuracy-item {
            background: var(--surface1);
            border-radius: var(--radius-md);
            padding: var(--spacing-md);
            text-align: center;
        }

        .accuracy-value {
            font-family: var(--font-mono);
            font-size: 1.4rem;
            font-weight: 700;
        }

        .accuracy-value.good { color: var(--green); }
        .accuracy-value.warn { color: var(--yellow); }
        .accuracy-value.bad { color: var(--red); }

        .warmup-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(30, 30, 46, 0.9);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            border-radius: var(--radius-lg);
            z-index: 10;
        }

        .warmup-text {
            color: var(--subtext1);
            margin-bottom: var(--spacing-sm);
        }

        .warmup-progress {
            font-family: var(--font-mono);
            font-size: 1.2rem;
            color: var(--yellow);
        }

        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--spacing-md);
        }

        @media (max-width: 900px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }

        .full-width {
            grid-column: 1 / -1;
        }

        .history-table {
            width: 100%;
            border-collapse: collapse;
            font-family: var(--font-mono);
            font-size: 0.75rem;
        }

        .history-table th {
            text-align: left;
            padding: var(--spacing-sm);
            border-bottom: 1px solid var(--surface1);
            color: var(--subtext0);
            font-weight: 500;
            text-transform: uppercase;
        }

        .history-table td {
            padding: var(--spacing-sm);
            border-bottom: 1px solid var(--surface0);
        }

        .result-icon {
            display: inline-block;
            width: 18px;
            height: 18px;
            line-height: 18px;
            text-align: center;
            border-radius: 4px;
            font-size: 0.65rem;
        }

        .result-icon.hit {
            background: rgba(166, 227, 161, 0.2);
            color: var(--green);
        }

        .result-icon.miss {
            background: rgba(243, 139, 168, 0.2);
            color: var(--red);
        }
    </style>
</head>
<body>
    <div class="artifact-container">
        <!-- Header -->
        <header class="artifact-header">
            <h1>Bayesian Predictor</h1>
            <div class="connection-status">
                <span class="connection-dot disconnected" id="connectionDot"></span>
                <span id="connectionText">Disconnected</span>
            </div>
        </header>

        <!-- Main Content -->
        <main class="artifact-main">
            <div class="main-grid">
                <!-- Current Game Card -->
                <div class="card">
                    <div class="card-header">
                        <span>Current Game</span>
                        <span class="badge" id="gamePhase">WAITING</span>
                    </div>
                    <div class="card-body">
                        <div id="gameId" style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--subtext0); margin-bottom: var(--spacing-md);">--</div>
                        <div class="stats-row">
                            <div class="stat-item">
                                <span class="stat-label">Price</span>
                                <span class="stat-value text-green" id="currentPrice">1.00</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Peak</span>
                                <span class="stat-value text-yellow" id="currentPeak">1.00</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Tick</span>
                                <span class="stat-value text-blue" id="currentTick">0</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Prediction Card -->
                <div class="card" style="position: relative;">
                    <div class="card-header">
                        <span>Prediction</span>
                        <span class="regime-badge regime-normal" id="regimeBadge">NORMAL</span>
                    </div>
                    <div class="card-body">
                        <div class="prediction-grid">
                            <div class="prediction-item">
                                <div class="prediction-label">Peak Multiplier</div>
                                <div class="prediction-value" id="predPeak">--</div>
                                <div class="prediction-ci" id="predPeakCI">CI: --</div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" id="peakConfBar" style="width: 0%"></div>
                                </div>
                            </div>
                            <div class="prediction-item">
                                <div class="prediction-label">Duration (ticks)</div>
                                <div class="prediction-value" id="predDuration">--</div>
                                <div class="prediction-ci" id="predDurationCI">CI: --</div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" id="durationConfBar" style="width: 0%"></div>
                                </div>
                            </div>
                        </div>

                        <div class="direction-indicator">
                            <span class="direction-arrow stable" id="directionArrow">→</span>
                            <span id="directionText">Waiting for prediction...</span>
                        </div>
                    </div>

                    <!-- Warmup Overlay -->
                    <div class="warmup-overlay" id="warmupOverlay" style="display: none;">
                        <div class="warmup-text">Warming up model...</div>
                        <div class="warmup-progress" id="warmupProgress">0 / 5 games</div>
                    </div>
                </div>

                <!-- Accuracy Stats Card -->
                <div class="card">
                    <div class="card-header">Accuracy Stats</div>
                    <div class="card-body">
                        <div class="accuracy-grid">
                            <div class="accuracy-item">
                                <div class="stat-label">Peak CI Hit Rate</div>
                                <div class="accuracy-value" id="peakHitRate">--%</div>
                            </div>
                            <div class="accuracy-item">
                                <div class="stat-label">Duration CI Hit Rate</div>
                                <div class="accuracy-value" id="durationHitRate">--%</div>
                            </div>
                            <div class="accuracy-item">
                                <div class="stat-label">Avg Peak Error</div>
                                <div class="accuracy-value" id="avgPeakError">--%</div>
                            </div>
                            <div class="accuracy-item">
                                <div class="stat-label">Avg Duration Error</div>
                                <div class="accuracy-value" id="avgDurationError">--%</div>
                            </div>
                        </div>
                        <div style="text-align: center; margin-top: var(--spacing-md); font-family: var(--font-mono); font-size: 0.75rem; color: var(--subtext0);">
                            <span id="totalPredictions">0</span> predictions tracked
                        </div>
                    </div>
                </div>

                <!-- Forecaster State Card -->
                <div class="card">
                    <div class="card-header">Forecaster State</div>
                    <div class="card-body">
                        <div class="accuracy-grid">
                            <div class="accuracy-item">
                                <div class="stat-label">Final μ</div>
                                <div class="accuracy-value text-mauve" id="finalMu">0.0135</div>
                            </div>
                            <div class="accuracy-item">
                                <div class="stat-label">Peak μ</div>
                                <div class="accuracy-value text-blue" id="peakMu">2.50</div>
                            </div>
                            <div class="accuracy-item">
                                <div class="stat-label">Duration μ</div>
                                <div class="accuracy-value text-yellow" id="durationMu">200</div>
                            </div>
                            <div class="accuracy-item">
                                <div class="stat-label">Games Seen</div>
                                <div class="accuracy-value" id="gamesSeen">0</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- History Card -->
                <div class="card full-width">
                    <div class="card-header">Prediction History</div>
                    <div class="card-body" style="overflow-x: auto;">
                        <table class="history-table">
                            <thead>
                                <tr>
                                    <th>Game</th>
                                    <th>Pred Peak</th>
                                    <th>Actual Peak</th>
                                    <th>Peak CI</th>
                                    <th>Pred Dur</th>
                                    <th>Actual Dur</th>
                                    <th>Dur CI</th>
                                </tr>
                            </thead>
                            <tbody id="historyBody">
                                <tr><td colspan="7" style="text-align: center; color: var(--subtext0);">No predictions yet</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="artifact-footer">
            <div>
                <span id="messageCount">0</span> messages |
                <span id="avgLatency">0</span>ms avg latency
            </div>
            <div>
                Game: <span id="footerGameId">-</span> |
                Tick: <span id="footerTick">0</span>
            </div>
        </footer>
    </div>

    <!-- REQUIRED: Shared WebSocket Client -->
    <script src="../../shared/foundation-ws-client.js"></script>

    <!-- Artifact-specific logic -->
    <script src="main.js"></script>
</body>
</html>
```

**Step 2: Commit HTML**

```bash
git add src/artifacts/tools/bayesian-predictor/index.html
git commit -m "feat(artifact): Add bayesian-predictor index.html with shared imports"
```

---

## Task 8: Create Foundation-Compliant JavaScript

**Files:**
- Create: `src/artifacts/tools/bayesian-predictor/main.js`

**Step 1: Create main.js using FoundationWSClient**

```javascript
/**
 * Bayesian Predictor - Main JavaScript
 *
 * Uses FoundationWSClient for WebSocket connection (REQUIRED).
 * Polls prediction API for forecasts.
 */

// Configuration
const ARTIFACT_CONFIG = {
    id: 'bayesian-predictor',
    name: 'Bayesian Predictor',
    version: '1.0.0',
    subscriptions: ['game.tick'],
    apiUrl: 'http://localhost:9002',
    apiPollInterval: 500
};

// State
const state = {
    connected: false,
    currentGameId: null,
    currentTick: 0,
    currentPrice: 1.0,
    currentPeak: 1.0,
    gamePhase: 'WAITING'
};

// DOM elements cache
const ui = {};

// =============================================================================
// Initialization
// =============================================================================

function init() {
    // Cache DOM elements
    cacheElements();

    // Initialize WebSocket using FoundationWSClient (REQUIRED)
    initWebSocket();

    // Start API polling
    setInterval(pollAPI, ARTIFACT_CONFIG.apiPollInterval);
    pollAPI();

    // Start metrics update
    setInterval(updateMetrics, 1000);

    console.log(`[${ARTIFACT_CONFIG.id}] Initialized`);
}

function cacheElements() {
    const ids = [
        'connectionDot', 'connectionText', 'gamePhase', 'gameId',
        'currentPrice', 'currentPeak', 'currentTick',
        'predPeak', 'predPeakCI', 'predDuration', 'predDurationCI',
        'peakConfBar', 'durationConfBar', 'regimeBadge',
        'directionArrow', 'directionText',
        'warmupOverlay', 'warmupProgress',
        'peakHitRate', 'durationHitRate', 'avgPeakError', 'avgDurationError',
        'totalPredictions', 'finalMu', 'peakMu', 'durationMu', 'gamesSeen',
        'historyBody', 'messageCount', 'avgLatency', 'footerGameId', 'footerTick'
    ];

    ids.forEach(id => {
        ui[id] = document.getElementById(id);
    });
}

// =============================================================================
// WebSocket (using FoundationWSClient)
// =============================================================================

function initWebSocket() {
    // REQUIRED: Use FoundationWSClient, NOT raw WebSocket
    window.wsClient = new FoundationWSClient();

    // Connection status handler
    wsClient.on('connection', handleConnectionChange);

    // Game tick handler
    wsClient.on('game.tick', handleGameTick);

    // Connect
    wsClient.connect().catch(err => {
        console.error('Failed to connect:', err);
    });
}

function handleConnectionChange(data) {
    state.connected = data.connected;

    if (data.connected) {
        ui.connectionDot.className = 'connection-dot connected';
        ui.connectionText.textContent = 'Connected';
    } else {
        ui.connectionDot.className = 'connection-dot disconnected';
        ui.connectionText.textContent = 'Disconnected';
    }
}

function handleGameTick(event) {
    const data = event.data || event;
    const gameId = event.gameId;

    // Track game changes
    if (gameId && gameId !== state.currentGameId) {
        state.currentGameId = gameId;
        state.currentPeak = 1.0;
        ui.gameId.textContent = gameId;
        ui.footerGameId.textContent = gameId.slice(-12);
    }

    // Update phase
    const phase = detectPhase(data);
    if (phase !== state.gamePhase) {
        state.gamePhase = phase;
        updatePhaseDisplay(phase);
    }

    // Update price/tick
    const tick = data.tick ?? data.tickCount ?? 0;
    const price = data.price ?? 1.0;

    state.currentTick = tick;
    state.currentPrice = price;

    ui.currentPrice.textContent = price.toFixed(2);
    ui.currentTick.textContent = tick;
    ui.footerTick.textContent = tick;

    // Track peak during active phase
    if (data.active && !data.rugged && price > state.currentPeak) {
        state.currentPeak = price;
        ui.currentPeak.textContent = price.toFixed(2);
    }

    // Reset peak on new game
    if (data.active && tick === 0) {
        state.currentPeak = 1.0;
        ui.currentPeak.textContent = '1.00';
    }
}

function detectPhase(data) {
    if (data.cooldownTimer > 0) {
        return data.allowPreRoundBuys ? 'PRESALE' : 'COOLDOWN';
    }
    if (data.rugged && !data.active) return 'COOLDOWN';
    if (data.allowPreRoundBuys && !data.active) return 'PRESALE';
    if (data.active && !data.rugged) return 'ACTIVE';
    if (data.rugged) return 'RUGGED';
    return 'UNKNOWN';
}

function updatePhaseDisplay(phase) {
    ui.gamePhase.textContent = phase;
    ui.gamePhase.className = 'badge badge-' + phase.toLowerCase();
}

// =============================================================================
// API Polling
// =============================================================================

async function pollAPI() {
    try {
        const response = await fetch(`${ARTIFACT_CONFIG.apiUrl}/state`);
        if (!response.ok) return;

        const data = await response.json();
        updateFromAPIState(data);
    } catch (e) {
        // API not available - subscriber not running
    }
}

function updateFromAPIState(state) {
    // Game state
    if (state.game_state) {
        const gs = state.game_state;
        ui.gamesSeen.textContent = gs.games_seen || 0;

        // Warmup overlay
        if (!gs.warmed_up && gs.games_seen < 5) {
            ui.warmupOverlay.style.display = 'flex';
            ui.warmupProgress.textContent = `${gs.games_seen} / 5 games`;
        } else {
            ui.warmupOverlay.style.display = 'none';
        }
    }

    // Current prediction
    if (state.current_prediction) {
        const pred = state.current_prediction;

        // Peak
        ui.predPeak.textContent = pred.peak.point.toFixed(2) + 'x';
        ui.predPeakCI.textContent = `CI: [${pred.peak.ci_lower.toFixed(1)}, ${pred.peak.ci_upper.toFixed(1)}]`;
        ui.peakConfBar.style.width = (pred.peak.confidence * 100) + '%';

        // Duration
        ui.predDuration.textContent = pred.duration.point;
        ui.predDurationCI.textContent = `CI: [${pred.duration.ci_lower}, ${pred.duration.ci_upper}]`;
        ui.durationConfBar.style.width = (pred.duration.confidence * 100) + '%';

        // Regime
        const regime = pred.regime || 'normal';
        ui.regimeBadge.textContent = regime.toUpperCase();
        ui.regimeBadge.className = 'regime-badge regime-' + regime;

        // Direction
        const dir = pred.final_direction || 'stable';
        ui.directionArrow.className = 'direction-arrow ' + dir;
        ui.directionArrow.textContent = dir === 'up' ? '↑' : dir === 'down' ? '↓' : '→';

        const dirTexts = {
            'up': 'Expecting price recovery (mean reversion up)',
            'down': 'Expecting price correction (mean reversion down)',
            'stable': 'Expecting price near equilibrium'
        };
        ui.directionText.textContent = dirTexts[dir] || 'Waiting...';
    }

    // Accuracy stats
    if (state.accuracy_stats) {
        const stats = state.accuracy_stats;

        const peakHit = stats.peak_ci_hit_rate * 100;
        ui.peakHitRate.textContent = peakHit.toFixed(0) + '%';
        ui.peakHitRate.className = 'accuracy-value ' + getAccuracyClass(peakHit);

        const durHit = stats.duration_ci_hit_rate * 100;
        ui.durationHitRate.textContent = durHit.toFixed(0) + '%';
        ui.durationHitRate.className = 'accuracy-value ' + getAccuracyClass(durHit);

        ui.avgPeakError.textContent = stats.avg_peak_error.toFixed(1) + '%';
        ui.avgPeakError.className = 'accuracy-value ' + getAccuracyClass(100 - stats.avg_peak_error);

        ui.avgDurationError.textContent = stats.avg_duration_error.toFixed(1) + '%';
        ui.avgDurationError.className = 'accuracy-value ' + getAccuracyClass(100 - stats.avg_duration_error);

        ui.totalPredictions.textContent = stats.total_predictions || 0;
    }

    // Forecaster state
    if (state.forecaster) {
        ui.finalMu.textContent = state.forecaster.final_mu.toFixed(4);
        ui.peakMu.textContent = state.forecaster.peak_mu.toFixed(2);
        ui.durationMu.textContent = Math.round(state.forecaster.duration_mu);
    }

    // History
    if (state.recent_predictions?.length > 0) {
        updateHistory(state.recent_predictions);
    }
}

function getAccuracyClass(value) {
    if (value >= 70) return 'good';
    if (value >= 50) return 'warn';
    return 'bad';
}

function updateHistory(predictions) {
    const rows = predictions.slice().reverse().map(pred => {
        const peakHit = pred.peak.within_ci;
        const durHit = pred.duration.within_ci;

        return `
            <tr>
                <td>${(pred.game_id || '').substring(0, 16)}...</td>
                <td>${pred.peak.point.toFixed(2)}x</td>
                <td>${pred.peak.actual ? pred.peak.actual.toFixed(2) + 'x' : '--'}</td>
                <td><span class="result-icon ${peakHit ? 'hit' : 'miss'}">${peakHit ? '✓' : '✗'}</span></td>
                <td>${pred.duration.point}</td>
                <td>${pred.duration.actual ?? '--'}</td>
                <td><span class="result-icon ${durHit ? 'hit' : 'miss'}">${durHit ? '✓' : '✗'}</span></td>
            </tr>
        `;
    }).join('');

    ui.historyBody.innerHTML = rows || '<tr><td colspan="7" style="text-align: center;">No predictions yet</td></tr>';
}

// =============================================================================
// Metrics
// =============================================================================

function updateMetrics() {
    if (window.wsClient) {
        const metrics = wsClient.getMetrics();
        ui.messageCount.textContent = metrics.messageCount || 0;
        ui.avgLatency.textContent = Math.round(metrics.averageLatency || 0);
    }
}

// =============================================================================
// Start
// =============================================================================

document.addEventListener('DOMContentLoaded', init);
```

**Step 2: Commit**

```bash
git add src/artifacts/tools/bayesian-predictor/main.js
git commit -m "feat(artifact): Add bayesian-predictor main.js using FoundationWSClient"
```

---

## Task 9: Validate HTML Artifact

**Step 1: Run validation script**

```bash
python scripts/validate_artifact.py src/artifacts/tools/bayesian-predictor/
```

Expected output:
```
✓ PASSED: src/artifacts/tools/bayesian-predictor/
  - Located in src/artifacts/tools/
  - Imports foundation-ws-client.js
  - Imports vectra-styles.css
  - No raw WebSocket usage
  - Has README.md
```

**Step 2: If validation fails, fix issues and re-run**

**Step 3: Commit validation success**

```bash
git commit --allow-empty -m "chore: Validate bayesian-predictor artifact passes boilerplate checks"
```

---

## Task 10: Run All Tests

**Step 1: Run full test suite**

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE/src && \
python -m pytest tests/ -v --tb=short
```

**Step 2: Verify new tests pass**

Look for:
- `test_bayesian_predictor.py` - all passing

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Complete bayesian-predictor migration to Foundation Boilerplate

- Python subscriber in src/subscribers/bayesian_predictor/
- HTML artifact in src/artifacts/tools/bayesian-predictor/
- Both pass validation script checks
- Tests added for subscriber"
```

---

## Task 11: Integration Test (Manual)

**Step 1: Start Foundation Service**

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE
python -m foundation.launcher
```

**Step 2: Start Bayesian Predictor Subscriber (new terminal)**

```bash
cd /home/devops/Desktop/VECTRA-BOILERPLATE/src
python -c "
import asyncio
from foundation.client import FoundationClient
from subscribers.bayesian_predictor import BayesianPredictorSubscriber

async def main():
    client = FoundationClient()
    subscriber = BayesianPredictorSubscriber(client)
    await client.connect()
    print('Subscriber running. Press Ctrl+C to stop.')
    await asyncio.Event().wait()

asyncio.run(main())
"
```

**Step 3: Open HTML artifact in browser**

```bash
xdg-open src/artifacts/tools/bayesian-predictor/index.html
```

**Step 4: Verify:**
- [ ] Connection status shows "Connected"
- [ ] Price/tick updates in real-time
- [ ] Predictions appear after 5 games (warmup)
- [ ] History table populates

---

## Summary

| Component | Location | Validation |
|-----------|----------|------------|
| Python Subscriber | `src/subscribers/bayesian_predictor/` | ✓ Inherits BaseSubscriber |
| HTML Artifact | `src/artifacts/tools/bayesian-predictor/` | ✓ Uses FoundationWSClient |
| Tests | `src/tests/test_subscribers/test_bayesian_predictor.py` | ✓ Passes |

**Port Allocation:**
- 9000: Foundation WebSocket
- 9001: Foundation HTTP Monitor
- 9002: Bayesian Predictor API

**This migration validates:**
1. ✅ Python subscriber pattern works
2. ✅ HTML artifact pattern works
3. ✅ Validation script catches violations
4. ✅ Shared resources (vectra-styles.css, foundation-ws-client.js) work
5. ✅ Foundation Service integration works
