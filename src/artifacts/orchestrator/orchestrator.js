/**
 * VECTRA Artifact Orchestrator
 *
 * Tab-based wrapper that:
 * - Loads artifacts from registry.json
 * - Manages iframe switching
 * - Maintains single Foundation WebSocket connection
 * - Relays events to all artifacts via postMessage
 */

// =============================================================================
// State
// =============================================================================

const state = {
    artifacts: [],
    activeArtifactId: null,
    iframes: {},
    currentGame: {
        id: null,
        tick: 0
    }
};

// =============================================================================
// UI Elements
// =============================================================================

const ui = {};

// =============================================================================
// Initialization
// =============================================================================

async function init() {
    // Cache DOM elements
    ui.tabBar = document.getElementById('tabBar');
    ui.iframeContainer = document.getElementById('iframeContainer');
    ui.loadingOverlay = document.getElementById('loadingOverlay');
    ui.connectionDot = document.getElementById('connectionDot');
    ui.connectionText = document.getElementById('connectionText');
    ui.messageCount = document.getElementById('messageCount');
    ui.avgLatency = document.getElementById('avgLatency');
    ui.currentGameId = document.getElementById('currentGameId');
    ui.currentTick = document.getElementById('currentTick');

    // Load artifact registry
    try {
        const response = await fetch('registry.json');
        const registry = await response.json();
        state.artifacts = registry.artifacts || [];
        console.log(`[Orchestrator] Loaded ${state.artifacts.length} artifacts`);
    } catch (error) {
        console.error('[Orchestrator] Failed to load registry:', error);
        ui.loadingOverlay.textContent = 'Failed to load artifact registry';
        return;
    }

    // Build UI
    buildTabs();
    buildIframes();

    // Initialize WebSocket
    window.wsClient = new FoundationWSClient();
    wsClient.on('connection', handleConnectionChange);
    wsClient.on('game.tick', handleGameTick);
    wsClient.on('player.state', relayToArtifacts);
    wsClient.on('player.trade', relayToArtifacts);
    wsClient.on('connection.authenticated', relayToArtifacts);
    wsClient.connect().catch(console.error);

    // Update metrics periodically
    setInterval(updateMetrics, 1000);

    // Hide loading overlay
    ui.loadingOverlay.classList.add('hidden');

    // Activate first artifact
    if (state.artifacts.length > 0) {
        activateArtifact(state.artifacts[0].id);
    }
}

// =============================================================================
// UI Building
// =============================================================================

function buildTabs() {
    ui.tabBar.innerHTML = '';

    state.artifacts.forEach(artifact => {
        const tab = document.createElement('button');
        tab.className = 'tab';
        tab.dataset.artifactId = artifact.id;
        tab.innerHTML = `
            <span class="tab-icon">${artifact.icon || '📄'}</span>
            <span>${artifact.name}</span>
        `;
        tab.addEventListener('click', () => activateArtifact(artifact.id));
        ui.tabBar.appendChild(tab);
    });
}

function buildIframes() {
    state.artifacts.forEach(artifact => {
        const iframe = document.createElement('iframe');
        iframe.className = 'artifact-iframe';
        iframe.id = `iframe-${artifact.id}`;
        iframe.src = artifact.path;
        iframe.title = artifact.name;

        // Store reference
        state.iframes[artifact.id] = iframe;

        // Listen for iframe load
        iframe.addEventListener('load', () => {
            console.log(`[Orchestrator] Artifact loaded: ${artifact.name}`);
            // Send initial state if we have one
            if (state.currentGame.id) {
                postToIframe(iframe, 'game.tick', {
                    gameId: state.currentGame.id,
                    tick: state.currentGame.tick
                });
            }
        });

        ui.iframeContainer.appendChild(iframe);
    });
}

// =============================================================================
// Tab Management
// =============================================================================

function activateArtifact(artifactId) {
    // Update state
    state.activeArtifactId = artifactId;

    // Update tab styles
    document.querySelectorAll('.tab').forEach(tab => {
        if (tab.dataset.artifactId === artifactId) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    // Show/hide iframes
    Object.entries(state.iframes).forEach(([id, iframe]) => {
        if (id === artifactId) {
            iframe.classList.add('active');
        } else {
            iframe.classList.remove('active');
        }
    });

    console.log(`[Orchestrator] Activated: ${artifactId}`);
}

// =============================================================================
// WebSocket Event Handling
// =============================================================================

function handleConnectionChange(data) {
    if (data.connected) {
        ui.connectionDot.className = 'connection-dot connected';
        ui.connectionText.textContent = 'Connected';
    } else {
        ui.connectionDot.className = 'connection-dot disconnected';
        ui.connectionText.textContent = 'Disconnected';
    }

    // Relay to all artifacts
    relayToArtifacts({ type: 'connection', data });
}

function handleGameTick(event) {
    const data = event.data || event;
    const gameId = event.gameId || data.gameId;

    // Update state
    if (gameId) {
        state.currentGame.id = gameId;
    }
    state.currentGame.tick = data.tick || data.tickCount || state.currentGame.tick;

    // Update footer
    ui.currentGameId.textContent = state.currentGame.id ? state.currentGame.id.slice(-8) : '-';
    ui.currentTick.textContent = state.currentGame.tick;

    // Relay to all artifacts
    relayToArtifacts({ type: 'game.tick', ...event });
}

function relayToArtifacts(event) {
    // Send to all iframes via postMessage
    Object.values(state.iframes).forEach(iframe => {
        postToIframe(iframe, event.type, event);
    });
}

function postToIframe(iframe, type, data) {
    try {
        iframe.contentWindow.postMessage({
            source: 'vectra-orchestrator',
            type: type,
            payload: data
        }, '*');
    } catch (error) {
        // Iframe might not be ready yet
    }
}

// =============================================================================
// Metrics
// =============================================================================

function updateMetrics() {
    if (window.wsClient) {
        const metrics = wsClient.getMetrics();
        ui.messageCount.textContent = metrics.messageCount;
        ui.avgLatency.textContent = Math.round(metrics.averageLatency);
    }
}

// =============================================================================
// Message Listener (for artifacts sending messages back)
// =============================================================================

window.addEventListener('message', (event) => {
    // Validate message source
    if (!event.data || event.data.source !== 'vectra-artifact') {
        return;
    }

    const { artifactId, type, payload } = event.data;

    switch (type) {
        case 'ready':
            console.log(`[Orchestrator] Artifact ready: ${artifactId}`);
            break;
        case 'request-state':
            // Send current state to requesting artifact
            const iframe = state.iframes[artifactId];
            if (iframe && state.currentGame.id) {
                postToIframe(iframe, 'game.tick', {
                    gameId: state.currentGame.id,
                    tick: state.currentGame.tick
                });
            }
            break;
        default:
            console.log(`[Orchestrator] Unknown message type: ${type}`);
    }
});

// =============================================================================
// Start
// =============================================================================

document.addEventListener('DOMContentLoaded', init);
