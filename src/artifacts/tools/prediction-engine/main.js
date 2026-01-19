/**
 * Prediction Engine - Main JavaScript
 *
 * Real-time price prediction using:
 * - Equilibrium tracking with regime detection
 * - Stochastic oscillation modeling (adaptive AR)
 * - Bayesian forecasting with Kalman filtering
 */

// =============================================================================
// State
// =============================================================================

const state = {
    currentGame: {
        id: null,
        tick: 0,
        price: 1.0,
        peak: 1.0,
        phase: 'BETTING'
    },
    lastCompletedGame: null,
    currentPrediction: null,
    history: []
};

// =============================================================================
// Model Instances
// =============================================================================

let eqTracker = null;
let weighter = null;
let oscModel = null;
let forecaster = null;

// =============================================================================
// UI Elements
// =============================================================================

const ui = {};

// =============================================================================
// Initialization
// =============================================================================

function init() {
    // Cache DOM elements
    ui.connectionDot = document.getElementById('connectionDot');
    ui.connectionText = document.getElementById('connectionText');
    ui.messageCount = document.getElementById('messageCount');
    ui.avgLatency = document.getElementById('avgLatency');
    ui.currentGameId = document.getElementById('currentGameId');
    ui.regimeIndicator = document.getElementById('regimeIndicator');

    // Current game state
    ui.currentTick = document.getElementById('currentTick');
    ui.currentPrice = document.getElementById('currentPrice');
    ui.currentPeak = document.getElementById('currentPeak');
    ui.currentPhase = document.getElementById('currentPhase');

    // Predictions
    ui.predFinal = document.getElementById('predFinal');
    ui.predFinalInterval = document.getElementById('predFinalInterval');
    ui.predFinalConfidence = document.getElementById('predFinalConfidence');
    ui.predFinalConfPct = document.getElementById('predFinalConfPct');

    ui.predPeak = document.getElementById('predPeak');
    ui.predPeakInterval = document.getElementById('predPeakInterval');
    ui.predPeakConfidence = document.getElementById('predPeakConfidence');
    ui.predPeakConfPct = document.getElementById('predPeakConfPct');

    ui.predDuration = document.getElementById('predDuration');
    ui.predDurationInterval = document.getElementById('predDurationInterval');
    ui.predDurationConfidence = document.getElementById('predDurationConfidence');
    ui.predDurationConfPct = document.getElementById('predDurationConfPct');

    // Sidebar stats
    ui.eqCurrent = document.getElementById('eqCurrent');
    ui.eqLongterm = document.getElementById('eqLongterm');
    ui.eqSigma = document.getElementById('eqSigma');
    ui.eqDataPoints = document.getElementById('eqDataPoints');

    ui.arOrder = document.getElementById('arOrder');
    ui.arMSE = document.getElementById('arMSE');
    ui.arUpdates = document.getElementById('arUpdates');

    ui.accFinal = document.getElementById('accFinal');
    ui.accPeak = document.getElementById('accPeak');
    ui.accDuration = document.getElementById('accDuration');
    ui.accCount = document.getElementById('accCount');

    ui.historyList = document.getElementById('historyList');
    ui.resetBtn = document.getElementById('resetBtn');
    ui.autoTrain = document.getElementById('autoTrain');

    // Initialize models
    initModels();

    // Event handlers
    ui.resetBtn.addEventListener('click', resetModels);

    // WebSocket client
    window.wsClient = new FoundationWSClient();
    wsClient.on('connection', handleConnectionChange);
    wsClient.on('game.tick', handleGameTick);
    wsClient.connect().catch(console.error);

    // Update metrics periodically
    setInterval(updateMetricsDisplay, 1000);
}

// =============================================================================
// Model Management
// =============================================================================

function initModels() {
    eqTracker = new EquilibriumTracker({ lambdaDecay: 0.95, thresholdSigma: 2.0 });
    weighter = new DynamicWeighter(eqTracker);
    oscModel = new StochasticOscillationModel({ maxArOrder: 5, lambdaRls: 0.98 });
    forecaster = new BayesianForecaster(eqTracker, oscModel, weighter);

    console.log('[Prediction Engine] Models initialized');
}

function resetModels() {
    eqTracker.reset();
    oscModel.reset();
    forecaster.reset();
    state.history = [];
    state.lastCompletedGame = null;
    state.currentPrediction = null;
    updateHistoryDisplay();
    console.log('[Prediction Engine] Models reset');
}

// =============================================================================
// Event Handlers
// =============================================================================

function handleConnectionChange(data) {
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
    const gameId = event.gameId || data.gameId;

    // Detect new game
    if (gameId && gameId !== state.currentGame.id) {
        // Game completed - train models if auto-train enabled
        if (state.currentGame.id && ui.autoTrain.checked) {
            onGameCompleted();
        }

        // Start new game
        state.currentGame = {
            id: gameId,
            tick: 0,
            price: 1.0,
            peak: 1.0,
            phase: 'BETTING'
        };
    }

    // Update current game state
    state.currentGame.tick = data.tick || data.tickCount || state.currentGame.tick;
    state.currentGame.price = data.price || state.currentGame.price;
    state.currentGame.peak = Math.max(state.currentGame.peak, state.currentGame.price);
    state.currentGame.phase = data.phase || state.currentGame.phase;

    // Update UI
    updateCurrentGameDisplay();
}

function onGameCompleted() {
    const game = state.currentGame;

    // Skip if no meaningful data
    if (game.tick < 5 || game.price === 1.0) return;

    // Record actual for accuracy tracking
    if (state.currentPrediction) {
        forecaster.recordActual({
            final: game.price,
            peak: game.peak,
            duration: game.tick
        });

        // Add to history
        state.history.unshift({
            gameId: game.id,
            predicted: state.currentPrediction.final.point,
            actual: game.price,
            error: Math.abs(state.currentPrediction.final.point - game.price)
        });

        if (state.history.length > 50) {
            state.history.pop();
        }
    }

    // Update models
    eqTracker.update(game.price, game.peak, game.tick);
    oscModel.updateOnline(game.price, game.peak, game.tick, eqTracker.mu);

    // Generate new prediction
    state.lastCompletedGame = {
        final: game.price,
        peak: game.peak,
        duration: game.tick
    };

    state.currentPrediction = forecaster.forecastNextGame(state.lastCompletedGame);

    // Update displays
    updatePredictionDisplay();
    updateModelStatsDisplay();
    updateAccuracyDisplay();
    updateHistoryDisplay();
    updateRegimeDisplay();
}

// =============================================================================
// UI Updates
// =============================================================================

function updateCurrentGameDisplay() {
    ui.currentTick.textContent = state.currentGame.tick;
    ui.currentPrice.textContent = `$${state.currentGame.price.toFixed(4)}`;
    ui.currentPeak.textContent = `${state.currentGame.peak.toFixed(2)}x`;
    ui.currentPhase.textContent = state.currentGame.phase;
    ui.currentGameId.textContent = state.currentGame.id ? state.currentGame.id.slice(-8) : '-';
}

function updatePredictionDisplay() {
    if (!state.currentPrediction) return;

    const pred = state.currentPrediction;

    // Final
    ui.predFinal.textContent = `$${pred.final.point.toFixed(4)}`;
    ui.predFinalInterval.textContent = `[$${pred.final.ciLower.toFixed(4)} - $${pred.final.ciUpper.toFixed(4)}]`;
    const finalConfPct = Math.round(pred.final.confidence * 100);
    ui.predFinalConfPct.textContent = `${finalConfPct}%`;
    ui.predFinalConfidence.style.width = `${finalConfPct}%`;
    ui.predFinalConfidence.className = `confidence-fill ${getConfidenceClass(pred.final.confidence)}`;

    // Peak
    ui.predPeak.textContent = `${pred.peak.point.toFixed(2)}x`;
    ui.predPeakInterval.textContent = `[${pred.peak.ciLower.toFixed(2)}x - ${pred.peak.ciUpper.toFixed(2)}x]`;
    const peakConfPct = Math.round(pred.peak.confidence * 100);
    ui.predPeakConfPct.textContent = `${peakConfPct}%`;
    ui.predPeakConfidence.style.width = `${peakConfPct}%`;
    ui.predPeakConfidence.className = `confidence-fill ${getConfidenceClass(pred.peak.confidence)}`;

    // Duration
    ui.predDuration.textContent = pred.duration.point;
    ui.predDurationInterval.textContent = `[${pred.duration.ciLower} - ${pred.duration.ciUpper}] ticks`;
    const durConfPct = Math.round(pred.duration.confidence * 100);
    ui.predDurationConfPct.textContent = `${durConfPct}%`;
    ui.predDurationConfidence.style.width = `${durConfPct}%`;
    ui.predDurationConfidence.className = `confidence-fill ${getConfidenceClass(pred.duration.confidence)}`;
}

function updateModelStatsDisplay() {
    const eqState = eqTracker.getState();
    ui.eqCurrent.textContent = `$${eqState.muCurrent.toFixed(4)}`;
    ui.eqLongterm.textContent = `$${eqState.muLongterm.toFixed(4)}`;
    ui.eqSigma.textContent = eqState.sigma.toFixed(4);
    ui.eqDataPoints.textContent = eqState.dataPoints;

    const arDiag = oscModel.getDiagnostics();
    ui.arOrder.textContent = arDiag.arOrder;
    ui.arMSE.textContent = arDiag.mse.toFixed(6);
    ui.arUpdates.textContent = arDiag.updateCount;
}

function updateAccuracyDisplay() {
    const acc = forecaster.getAccuracyMetrics();
    ui.accFinal.textContent = acc.finalMAE !== null ? `$${acc.finalMAE.toFixed(4)}` : '-';
    ui.accPeak.textContent = acc.peakMAE !== null ? `${acc.peakMAE.toFixed(2)}x` : '-';
    ui.accDuration.textContent = acc.durationMAE !== null ? `${Math.round(acc.durationMAE)} ticks` : '-';
    ui.accCount.textContent = acc.count;
}

function updateRegimeDisplay() {
    const eqState = eqTracker.getState();
    ui.regimeIndicator.textContent = eqState.regime;
    ui.regimeIndicator.className = `regime-indicator regime-${eqState.regime}`;
}

function updateHistoryDisplay() {
    if (state.history.length === 0) {
        ui.historyList.innerHTML = `
            <div class="history-item" style="font-weight: 600; background: var(--ctp-mantle);">
                <span>Game</span>
                <span>Pred Final</span>
                <span>Actual</span>
                <span>Error</span>
            </div>
            <div class="text-muted" style="padding: var(--space-md); text-align: center;">
                Waiting for game data...
            </div>
        `;
        return;
    }

    const header = `
        <div class="history-item" style="font-weight: 600; background: var(--ctp-mantle);">
            <span>Game</span>
            <span>Pred Final</span>
            <span>Actual</span>
            <span>Error</span>
        </div>
    `;

    const rows = state.history.slice(0, 20).map(h => `
        <div class="history-item">
            <span>${h.gameId ? h.gameId.slice(-6) : '-'}</span>
            <span>$${h.predicted.toFixed(4)}</span>
            <span>$${h.actual.toFixed(4)}</span>
            <span class="${h.error < 0.003 ? 'text-success' : h.error < 0.006 ? 'text-warning' : 'text-error'}">
                $${h.error.toFixed(4)}
            </span>
        </div>
    `).join('');

    ui.historyList.innerHTML = header + rows;
}

function updateMetricsDisplay() {
    if (window.wsClient) {
        const metrics = wsClient.getMetrics();
        ui.messageCount.textContent = metrics.messageCount;
        ui.avgLatency.textContent = Math.round(metrics.averageLatency);
    }
}

function getConfidenceClass(confidence) {
    if (confidence >= 0.75) return 'confidence-high';
    if (confidence >= 0.55) return 'confidence-medium';
    return 'confidence-low';
}

// =============================================================================
// Start
// =============================================================================

document.addEventListener('DOMContentLoaded', init);
