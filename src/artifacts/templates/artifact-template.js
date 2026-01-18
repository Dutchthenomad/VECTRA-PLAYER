/**
 * Artifact Template - Main JavaScript
 *
 * This template provides the standard structure for VECTRA artifacts.
 * Copy this file to your artifact directory and implement the required hooks.
 *
 * Required Hooks:
 *   - ARTIFACT_CONFIG: Configuration object with id, name, subscriptions
 *   - initializeUI(): Called once on page load
 *   - processGameTick(data): Called for each game.tick event
 *   - processPlayerState(data): Called for each player.state event
 *
 * Optional Hooks:
 *   - onConnect(): Called when WebSocket connects
 *   - onDisconnect(): Called when WebSocket disconnects
 *   - processEvent(type, data): Called for any event type
 */

// =============================================================================
// Artifact Configuration
// =============================================================================

const ARTIFACT_CONFIG = {
    id: 'artifact-template',
    name: 'Artifact Template',
    version: '1.0.0',

    // Events to subscribe to
    subscriptions: ['game.tick', 'player.state', 'connection.authenticated']
};

// =============================================================================
// State Management
// =============================================================================

const state = {
    connected: false,
    currentGameId: null,
    currentTick: 0,
    currentPrice: 1.0,
    gamePhase: 'BETTING',
    history: []
};

// =============================================================================
// UI Elements
// =============================================================================

const ui = {
    connectionDot: null,
    connectionText: null,
    messageCount: null,
    avgLatency: null,
    currentGameId: null,
    currentTick: null,
    mainContent: null
};

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize UI elements and start WebSocket connection.
 */
function init() {
    // Cache DOM elements
    ui.connectionDot = document.getElementById('connectionDot');
    ui.connectionText = document.getElementById('connectionText');
    ui.messageCount = document.getElementById('messageCount');
    ui.avgLatency = document.getElementById('avgLatency');
    ui.currentGameId = document.getElementById('currentGameId');
    ui.currentTick = document.getElementById('currentTick');
    ui.mainContent = document.getElementById('mainContent');

    // Initialize artifact-specific UI
    initializeUI();

    // Create WebSocket client
    window.wsClient = new FoundationWSClient();

    // Register event handlers
    wsClient.on('connection', handleConnectionChange);

    for (const eventType of ARTIFACT_CONFIG.subscriptions) {
        wsClient.on(eventType, (data) => handleEvent(eventType, data));
    }

    // Connect to Foundation Service
    wsClient.connect().catch(console.error);

    // Start metrics update loop
    setInterval(updateMetrics, 1000);
}

// =============================================================================
// Event Handlers
// =============================================================================

/**
 * Handle connection status changes.
 */
function handleConnectionChange(data) {
    state.connected = data.connected;

    if (data.connected) {
        ui.connectionDot.className = 'connection-dot connected';
        ui.connectionText.textContent = 'Connected';
        if (typeof onConnect === 'function') {
            onConnect();
        }
    } else {
        ui.connectionDot.className = 'connection-dot disconnected';
        ui.connectionText.textContent = 'Disconnected';
        if (typeof onDisconnect === 'function') {
            onDisconnect();
        }
    }
}

/**
 * Handle incoming events.
 */
function handleEvent(type, data) {
    // Update footer stats
    if (data.gameId) {
        state.currentGameId = data.gameId;
        ui.currentGameId.textContent = data.gameId.slice(-8);
    }

    // Route to specific handlers
    switch (type) {
        case 'game.tick':
            handleGameTick(data);
            break;
        case 'player.state':
            handlePlayerState(data);
            break;
        default:
            // Call generic handler if implemented
            if (typeof processEvent === 'function') {
                processEvent(type, data);
            }
    }
}

/**
 * Handle game tick events.
 */
function handleGameTick(data) {
    const tickData = data.data || data;

    state.currentTick = tickData.tick || tickData.tickCount || 0;
    state.currentPrice = tickData.price || 1.0;
    state.gamePhase = tickData.phase || 'BETTING';

    ui.currentTick.textContent = state.currentTick;

    // Detect game change
    if (data.gameId && data.gameId !== state.currentGameId) {
        state.currentGameId = data.gameId;
        state.history = [];
    }

    // Add to history
    state.history.push({
        tick: state.currentTick,
        price: state.currentPrice,
        ts: data.ts
    });

    // Keep history bounded
    if (state.history.length > 1000) {
        state.history.shift();
    }

    // Call artifact-specific handler
    if (typeof processGameTick === 'function') {
        processGameTick(data);
    }
}

/**
 * Handle player state events.
 */
function handlePlayerState(data) {
    // Call artifact-specific handler
    if (typeof processPlayerState === 'function') {
        processPlayerState(data);
    }
}

/**
 * Update metrics display.
 */
function updateMetrics() {
    if (window.wsClient) {
        const metrics = wsClient.getMetrics();
        ui.messageCount.textContent = metrics.messageCount;
        ui.avgLatency.textContent = Math.round(metrics.averageLatency);
    }
}

// =============================================================================
// Artifact-Specific Hooks (IMPLEMENT THESE)
// =============================================================================

/**
 * Initialize artifact-specific UI elements.
 * Called once on page load.
 */
function initializeUI() {
    // IMPLEMENT: Set up your artifact's UI
    console.log(`[${ARTIFACT_CONFIG.id}] Initializing UI...`);
}

/**
 * Process game tick events.
 * @param {Object} data - The event data including { type, ts, gameId, seq, data }
 */
function processGameTick(data) {
    // IMPLEMENT: Handle game tick updates
    // Example:
    // const { tick, price, phase } = data.data;
    // console.log(`Tick ${tick}: $${price.toFixed(4)} (${phase})`);
}

/**
 * Process player state events.
 * @param {Object} data - The event data
 */
function processPlayerState(data) {
    // IMPLEMENT: Handle player state updates
    // Example:
    // const { balance, positionQty } = data.data;
    // console.log(`Balance: $${balance}, Position: ${positionQty}`);
}

// =============================================================================
// Start Application
// =============================================================================

document.addEventListener('DOMContentLoaded', init);
