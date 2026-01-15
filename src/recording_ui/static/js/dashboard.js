/**
 * VECTRA Recording Dashboard - Frontend JavaScript
 *
 * Handles:
 * - Recording toggle control
 * - Status polling and display updates
 * - Game list management
 * - Price chart visualization
 */

// =============================================================================
// STATE
// =============================================================================

let isRecording = false;
let startedAt = null;
let priceChart = null;
let lastToggleTime = 0;  // Prevents race condition with status polling
const TOGGLE_DEBOUNCE_MS = 3000;  // Ignore status updates for 3s after toggle

// Browser connection state
let browserConnected = false;
let currentBet = 0.010;
let socket = null;

// =============================================================================
// API FUNCTIONS
// =============================================================================

async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error('Status fetch failed');
        return await res.json();
    } catch (err) {
        console.error('Failed to fetch status:', err);
        return null;
    }
}

async function fetchGames(limit = 50) {
    try {
        const res = await fetch(`/api/games?limit=${limit}`);
        if (!res.ok) throw new Error('Games fetch failed');
        return await res.json();
    } catch (err) {
        console.error('Failed to fetch games:', err);
        return { games: [] };
    }
}

async function fetchGame(gameId) {
    try {
        const res = await fetch(`/api/games/${encodeURIComponent(gameId)}`);
        if (!res.ok) throw new Error('Game fetch failed');
        return await res.json();
    } catch (err) {
        console.error('Failed to fetch game:', err);
        return null;
    }
}

async function postToggle() {
    try {
        const res = await fetch('/api/recording/toggle', { method: 'POST' });
        if (!res.ok) throw new Error('Toggle failed');
        return await res.json();
    } catch (err) {
        console.error('Failed to toggle recording:', err);
        return null;
    }
}

// =============================================================================
// BROWSER CONTROL API
// =============================================================================

async function fetchBrowserStatus() {
    try {
        const res = await fetch('/api/browser/status');
        if (!res.ok) throw new Error('Browser status fetch failed');
        return await res.json();
    } catch (err) {
        console.error('Failed to fetch browser status:', err);
        return null;
    }
}

async function postBrowserConnect() {
    try {
        const res = await fetch('/api/browser/connect', { method: 'POST' });
        if (!res.ok) throw new Error('Browser connect failed');
        return await res.json();
    } catch (err) {
        console.error('Failed to connect browser:', err);
        return null;
    }
}

async function postBrowserDisconnect() {
    try {
        const res = await fetch('/api/browser/disconnect', { method: 'POST' });
        if (!res.ok) throw new Error('Browser disconnect failed');
        return await res.json();
    } catch (err) {
        console.error('Failed to disconnect browser:', err);
        return null;
    }
}

async function postTradeAction(action, data = {}) {
    try {
        const res = await fetch(`/api/trade/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error(`Trade action ${action} failed`);
        return await res.json();
    } catch (err) {
        console.error(`Failed to execute trade action ${action}:`, err);
        return null;
    }
}

// =============================================================================
// UI UPDATE FUNCTIONS
// =============================================================================

function updateStatus(status) {
    if (!status) return;

    // Check if we're in debounce period after a toggle
    const inDebounce = (Date.now() - lastToggleTime) < TOGGLE_DEBOUNCE_MS;

    // Update toggle button (but NOT if we just toggled - prevents race condition)
    const toggleBtn = document.getElementById('toggle-btn');
    if (toggleBtn && !inDebounce) {
        // Only update from server if not in debounce period
        isRecording = status.is_recording;
        startedAt = status.started_at ? new Date(status.started_at) : null;
        toggleBtn.className = `toggle-btn ${isRecording ? 'toggle-on' : 'toggle-off'}`;
        toggleBtn.querySelector('.toggle-label').textContent = isRecording ? 'REC' : 'OFF';
    }

    // Update SESSION metrics (this session only, deduplicated by gameId)
    const sessionGameCount = document.getElementById('session-game-count');
    if (sessionGameCount) sessionGameCount.textContent = formatNumber(status.session_game_count || 0);

    const sessionEventCount = document.getElementById('session-event-count');
    if (sessionEventCount) sessionEventCount.textContent = formatNumber(status.session_event_count || 0);

    // Update TOTAL metrics (all sessions)
    const totalGameCount = document.getElementById('total-game-count');
    if (totalGameCount) totalGameCount.textContent = formatNumber(status.total_game_count || 0);

    const storageSize = document.getElementById('storage-size');
    if (storageSize) storageSize.textContent = `${(status.storage_mb || 0).toFixed(1)} MB`;

    // Legacy fields (backwards compatibility)
    const gameCount = document.getElementById('game-count');
    if (gameCount) gameCount.textContent = formatNumber(status.game_count || status.session_game_count || 0);

    const eventCount = document.getElementById('event-count');
    if (eventCount) eventCount.textContent = formatNumber(status.event_count || status.session_event_count || 0);

    // Update connection status
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    if (statusDot && statusText) {
        statusDot.classList.add('connected');
        statusText.textContent = 'Connected';
    }

    // Update last update time
    const lastUpdate = document.getElementById('last-update');
    if (lastUpdate) {
        lastUpdate.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    }
}

function updateUptime() {
    const uptimeEl = document.getElementById('uptime');
    if (!uptimeEl) return;

    if (!isRecording || !startedAt) {
        uptimeEl.textContent = '00:00:00';
        return;
    }

    const elapsed = Math.floor((Date.now() - startedAt.getTime()) / 1000);
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    uptimeEl.textContent = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

function updateGamesTable(games) {
    const tbody = document.getElementById('games-tbody');
    if (!tbody) return;

    if (!games || games.length === 0) {
        tbody.innerHTML = `
            <tr class="loading-row">
                <td colspan="6">No games recorded yet</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = games.map(game => `
        <tr>
            <td class="game-id">${truncateId(game.game_id)}</td>
            <td>${formatTime(game.timestamp)}</td>
            <td class="${game.peak_multiplier >= 2 ? 'peak-high' : 'peak-low'}">
                ${game.peak_multiplier.toFixed(2)}x
            </td>
            <td>${game.tick_count}</td>
            <td>${game.sidebet_count}</td>
            <td>
                <button class="view-btn" onclick="viewGame('${game.game_id}')">
                    View
                </button>
            </td>
        </tr>
    `).join('');
}

// =============================================================================
// BROWSER CONNECTION UI
// =============================================================================

function updateBrowserStatus(status) {
    if (!status) return;

    browserConnected = status.connected;

    // Update connection indicator
    const indicator = document.getElementById('connection-indicator');
    const statusText = document.getElementById('connection-text');
    const connectBtn = document.getElementById('connect-btn');
    const gameStateSection = document.getElementById('game-state-section');
    const tradingSection = document.getElementById('trading-section');

    if (indicator) {
        indicator.className = 'status-indicator' + (browserConnected ? ' connected' : '');
    }

    if (statusText) {
        statusText.textContent = browserConnected ? 'Connected' : 'Disconnected';
        statusText.className = 'status-text' + (browserConnected ? ' connected' : '');
    }

    if (connectBtn) {
        connectBtn.textContent = browserConnected ? 'DISCONNECT' : 'CONNECT';
        connectBtn.className = 'connect-btn ' + (browserConnected ? 'connected' : 'disconnected');
    }

    // Show/hide game state and trading panels
    if (gameStateSection) {
        gameStateSection.style.display = browserConnected ? 'block' : 'none';
    }
    if (tradingSection) {
        tradingSection.style.display = browserConnected ? 'block' : 'none';
    }

    // Update player info
    if (status.player) {
        const usernameEl = document.getElementById('player-username');
        const balanceEl = document.getElementById('player-balance');
        if (usernameEl) usernameEl.textContent = status.player.username || '--';
        if (balanceEl) balanceEl.textContent = `${(status.player.balance || 0).toFixed(4)} SOL`;
    }

    // Update game state
    if (status.game) {
        updateGameState(status.game);
    }
}

function updateGameState(game) {
    const tickEl = document.getElementById('game-tick');
    const priceEl = document.getElementById('game-price');
    const phaseEl = document.getElementById('game-phase');
    const gameIdEl = document.getElementById('game-id');

    if (tickEl) tickEl.textContent = game.tick_count || 0;
    if (priceEl) priceEl.textContent = `${(game.price || 1).toFixed(2)}x`;
    if (gameIdEl) gameIdEl.textContent = game.game_id || '--------';

    if (phaseEl) {
        const phase = (game.phase || 'UNKNOWN').toUpperCase();
        phaseEl.textContent = phase;
        phaseEl.className = 'state-value phase-' + phase.toLowerCase();
    }
}

// =============================================================================
// TRADING HANDLERS
// =============================================================================

async function toggleConnection() {
    const connectBtn = document.getElementById('connect-btn');
    if (connectBtn) {
        connectBtn.textContent = 'CONNECTING...';
        connectBtn.className = 'connect-btn connecting';
    }

    if (browserConnected) {
        const result = await postBrowserDisconnect();
        if (result) {
            updateBrowserStatus(result);
        }
    } else {
        const result = await postBrowserConnect();
        if (result) {
            // After connect, fetch full status
            setTimeout(async () => {
                const status = await fetchBrowserStatus();
                updateBrowserStatus(status);
            }, 500);
        }
    }
}

async function clickBuy() {
    const result = await postTradeAction('buy');
    if (result && !result.success) {
        console.error('BUY failed:', result.error);
    }
}

async function clickSell() {
    const result = await postTradeAction('sell');
    if (result && !result.success) {
        console.error('SELL failed:', result.error);
    }
}

async function clickSidebet() {
    const result = await postTradeAction('sidebet');
    if (result && !result.success) {
        console.error('SIDEBET failed:', result.error);
    }
}

async function clickIncrement(amount) {
    const result = await postTradeAction('increment', { amount });
    if (result && result.success) {
        currentBet += amount;
        updateBetDisplay();
    }
}

async function clickClear() {
    const result = await postTradeAction('clear');
    if (result && result.success) {
        currentBet = 0;
        updateBetDisplay();
    }
}

async function clickHalf() {
    const result = await postTradeAction('half');
    if (result && result.success) {
        currentBet /= 2;
        updateBetDisplay();
    }
}

async function clickDouble() {
    const result = await postTradeAction('double');
    if (result && result.success) {
        currentBet *= 2;
        updateBetDisplay();
    }
}

async function clickMax() {
    const result = await postTradeAction('max');
    // Can't know max without player balance, just update display
}

async function clickPercentage(pct) {
    const result = await postTradeAction('percentage', { pct });
    if (result && result.success) {
        // Update active button state
        document.querySelectorAll('.pct-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent === `${pct}%`) {
                btn.classList.add('active');
            }
        });
    }
}

function updateBetDisplay() {
    const betEl = document.getElementById('current-bet');
    if (betEl) {
        betEl.textContent = currentBet.toFixed(3);
    }
}

// =============================================================================
// INTERACTION HANDLERS
// =============================================================================

async function toggleRecording() {
    // Set debounce BEFORE toggle to prevent race with status poll
    lastToggleTime = Date.now();

    const result = await postToggle();
    if (result) {
        isRecording = result.is_recording;
        startedAt = isRecording ? new Date() : null;

        // Immediately update UI (optimistic)
        const toggleBtn = document.getElementById('toggle-btn');
        if (toggleBtn) {
            toggleBtn.className = `toggle-btn ${isRecording ? 'toggle-on' : 'toggle-off'}`;
            toggleBtn.querySelector('.toggle-label').textContent = isRecording ? 'REC' : 'OFF';
        }
    }
}

async function refreshGames() {
    const data = await fetchGames(50);
    updateGamesTable(data.games);
}

async function viewGame(gameId) {
    const game = await fetchGame(gameId);
    if (!game) return;

    // Update modal title
    document.getElementById('modal-title').textContent = `Game: ${truncateId(gameId)}`;

    // Update game info
    document.getElementById('game-info').innerHTML = `
        <div class="info-item">
            <div class="info-label">Peak</div>
            <div class="info-value">${game.peak_multiplier.toFixed(2)}x</div>
        </div>
        <div class="info-item">
            <div class="info-label">Ticks</div>
            <div class="info-value">${game.tick_count}</div>
        </div>
        <div class="info-item">
            <div class="info-label">Sidebets</div>
            <div class="info-value">${game.sidebet_count}</div>
        </div>
        <div class="info-item">
            <div class="info-label">Rugged</div>
            <div class="info-value">${game.rugged ? 'Yes' : 'No'}</div>
        </div>
    `;

    // Render price chart
    renderPriceChart(game.prices);

    // Show modal
    document.getElementById('game-modal').classList.add('active');
}

function closeModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('game-modal').classList.remove('active');
}

// =============================================================================
// CHART
// =============================================================================

function renderPriceChart(prices) {
    const ctx = document.getElementById('price-chart');
    if (!ctx) return;

    // Destroy existing chart
    if (priceChart) {
        priceChart.destroy();
    }

    // Create new chart
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: prices.map((_, i) => i),
            datasets: [{
                label: 'Price (Multiplier)',
                data: prices,
                borderColor: '#00ff66',
                backgroundColor: 'rgba(0, 255, 102, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Tick',
                        color: '#888',
                    },
                    grid: {
                        color: '#333',
                    },
                    ticks: {
                        color: '#888',
                    },
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Multiplier',
                        color: '#888',
                    },
                    grid: {
                        color: '#333',
                    },
                    ticks: {
                        color: '#888',
                    },
                },
            },
        },
    });
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function formatNumber(num) {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
}

function formatTime(timestamp) {
    if (!timestamp) return '--';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function truncateId(id) {
    if (!id) return '--';
    if (id.length <= 20) return id;
    return id.slice(0, 8) + '...' + id.slice(-8);
}

function pad(num) {
    return num.toString().padStart(2, '0');
}

// =============================================================================
// SOCKETIO SETUP
// =============================================================================

function setupSocketIO() {
    // Check if SocketIO is available
    if (typeof io === 'undefined') {
        console.warn('SocketIO not available, using polling only');
        return;
    }

    socket = io();

    socket.on('connect', () => {
        console.log('SocketIO connected');
    });

    socket.on('disconnect', () => {
        console.log('SocketIO disconnected');
    });

    // Real-time game state updates
    socket.on('game_state', (data) => {
        updateGameState(data);
    });

    // Real-time player info updates
    socket.on('player_info', (data) => {
        const usernameEl = document.getElementById('player-username');
        const balanceEl = document.getElementById('player-balance');
        if (usernameEl) usernameEl.textContent = data.username || '--';
        if (balanceEl) balanceEl.textContent = `${(data.balance || 0).toFixed(4)} SOL`;
    });

    // Browser status updates
    socket.on('browser_status', (data) => {
        browserConnected = data.connected;
        updateBrowserStatus(data);
    });
}

// =============================================================================
// INITIALIZATION & POLLING
// =============================================================================

// Initial load
document.addEventListener('DOMContentLoaded', async () => {
    // Fetch initial status
    const status = await fetchStatus();
    updateStatus(status);

    // Fetch initial browser status
    const browserStatus = await fetchBrowserStatus();
    updateBrowserStatus(browserStatus);

    // Fetch initial games
    const gamesData = await fetchGames(50);
    updateGamesTable(gamesData.games);

    // Setup SocketIO for real-time updates
    setupSocketIO();
});

// Poll status every 2 seconds
setInterval(async () => {
    const status = await fetchStatus();
    updateStatus(status);
}, 2000);

// Poll browser status every 2 seconds (backup to SocketIO)
setInterval(async () => {
    if (browserConnected) {
        const browserStatus = await fetchBrowserStatus();
        updateBrowserStatus(browserStatus);
    }
}, 2000);

// Update uptime display every second
setInterval(updateUptime, 1000);

// Refresh games every 10 seconds
setInterval(refreshGames, 10000);

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape to close modal
    if (e.key === 'Escape') {
        closeModal();
    }
    // R to toggle recording
    if (e.key === 'r' || e.key === 'R') {
        if (document.activeElement.tagName !== 'INPUT') {
            toggleRecording();
        }
    }
    // C to connect/disconnect browser
    if (e.key === 'c' || e.key === 'C') {
        if (document.activeElement.tagName !== 'INPUT') {
            toggleConnection();
        }
    }
    // B for buy, S for sell, D for sidebet (when connected)
    if (browserConnected && document.activeElement.tagName !== 'INPUT') {
        if (e.key === 'b' || e.key === 'B') {
            clickBuy();
        }
        if (e.key === 's' || e.key === 'S') {
            clickSell();
        }
        if (e.key === 'd' || e.key === 'D') {
            clickSidebet();
        }
    }
});
