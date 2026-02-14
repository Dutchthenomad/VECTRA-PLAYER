/**
 * Backtest Viewer - Visual strategy backtesting with real-time playback.
 *
 * Features:
 * - Tick-by-tick game playback with speed controls
 * - Strategy save/load
 * - Digital ticker showing current tick and price
 * - Wallet status and active bets display
 * - Cumulative statistics and equity curve
 */

// State
let state = {
    sessionId: null,
    strategies: [],
    profiles: [],  // TradingProfiles
    currentStrategy: null,
    currentProfile: null,  // Selected TradingProfile
    isPlaying: false,
    speed: 2,  // 1-5
    tickInterval: null,
    // Current game state
    gameState: null,
    priceHistory: [],
    // Charts
    priceChart: null,
    equityChart: null,
    // Live mode
    mode: 'backtest',  // 'backtest' or 'live'
    socket: null,
    liveConnected: false,
    // Recording state
    isRecording: false,
};

// Colors (Catppuccin Mocha)
const COLORS = {
    green: 'rgba(166, 227, 161, 1)',
    greenFill: 'rgba(166, 227, 161, 0.2)',
    red: 'rgba(243, 139, 168, 1)',
    redFill: 'rgba(243, 139, 168, 0.2)',
    blue: 'rgba(137, 180, 250, 1)',
    blueFill: 'rgba(137, 180, 250, 0.2)',
    teal: 'rgba(148, 226, 213, 1)',
    yellow: 'rgba(249, 226, 175, 1)',
    purple: 'rgba(203, 166, 247, 1)',
    text: '#cdd6f4',
    subtext: '#a6adc8',
    surface: '#313244',
    overlay: '#45475a',
};

const BET_COLORS = [COLORS.blue, COLORS.teal, COLORS.yellow, COLORS.purple];

// Speed to interval mapping (ms)
const SPEED_MAP = {
    1: 250,   // 1x - real-time
    2: 125,   // 2x
    3: 50,    // 5x
    4: 25,    // 10x
    5: 5,     // MAX
};

/**
 * Generate a UUID for session IDs.
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Initialize the backtest viewer.
 */
async function init() {
    setupEventListeners();
    await loadStrategies();
    await loadProfiles();  // Load trading profiles
    await loadValidationInfo();
    await loadRecordingStatus();  // Check recording state
    initCharts();
}

/**
 * Set up UI event listeners.
 */
function setupEventListeners() {
    // Profile selector
    document.getElementById('profile-select').addEventListener('change', (e) => {
        const name = e.target.value;
        // Clear strategy selection when profile is selected
        if (name) {
            document.getElementById('strategy-select').value = '';
        }
        updateLoadButtonState();
    });

    // Strategy selector
    document.getElementById('strategy-select').addEventListener('change', (e) => {
        const name = e.target.value;
        // Clear profile selection when strategy is selected
        if (name) {
            document.getElementById('profile-select').value = '';
        }
        updateLoadButtonState();
    });

    // Refresh button - refresh both profiles and strategies
    document.getElementById('btn-refresh').addEventListener('click', async () => {
        await loadStrategies();
        await loadProfiles();
    });

    // Load button
    document.getElementById('btn-load').addEventListener('click', loadSelectedStrategy);

    // Save button
    document.getElementById('btn-save').addEventListener('click', saveCurrentStrategy);

    // Playback controls
    document.getElementById('btn-start').addEventListener('click', startPlayback);
    document.getElementById('btn-pause').addEventListener('click', togglePause);
    document.getElementById('btn-step').addEventListener('click', stepOneTick);
    document.getElementById('btn-next').addEventListener('click', skipToNextGame);
    document.getElementById('btn-quick-start').addEventListener('click', quickStart);

    // Speed slider
    const speedSlider = document.getElementById('speed-slider');
    speedSlider.addEventListener('input', (e) => {
        state.speed = parseInt(e.target.value);
        updateSpeedDisplay();
        if (state.isPlaying) {
            restartTickInterval();
        }
    });

    // Mode selector
    const modeSelect = document.getElementById('mode-select');
    if (modeSelect) {
        modeSelect.addEventListener('change', (e) => {
            setMode(e.target.value);
        });
    }
}

/**
 * Load available strategies from the API.
 */
async function loadStrategies() {
    try {
        const response = await fetch('/api/backtest/strategies');
        if (!response.ok) throw new Error('Failed to load strategies');

        const data = await response.json();
        state.strategies = data.strategies;

        const select = document.getElementById('strategy-select');
        select.innerHTML = '<option value="">-- Select Strategy --</option>';

        for (const strategy of state.strategies) {
            const option = document.createElement('option');
            // API returns objects with {name, created, file}
            const name = typeof strategy === 'string' ? strategy : strategy.name;
            option.value = name;
            option.textContent = name;
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Failed to load strategies:', error);
    }
}

/**
 * Load validation dataset info.
 */
async function loadValidationInfo() {
    try {
        const response = await fetch('/api/backtest/validation-info');
        if (!response.ok) return;

        const data = await response.json();
        document.getElementById('progress-text').textContent = `0 / ${data.count} games`;
    } catch (error) {
        console.error('Failed to load validation info:', error);
    }
}

/**
 * Load trading profiles from API.
 */
async function loadProfiles() {
    try {
        const response = await fetch('/api/profiles');
        if (!response.ok) throw new Error('Failed to load profiles');

        const data = await response.json();
        state.profiles = data.profiles || [];

        const select = document.getElementById('profile-select');
        select.innerHTML = '<option value="">-- Select Profile --</option>';

        for (const profile of state.profiles) {
            const option = document.createElement('option');
            option.value = profile.name;
            option.textContent = profile.name;
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Failed to load profiles:', error);
    }
}

/**
 * Update Load button state based on selection.
 */
function updateLoadButtonState() {
    const profileName = document.getElementById('profile-select').value;
    const strategyName = document.getElementById('strategy-select').value;
    document.getElementById('btn-load').disabled = !profileName && !strategyName;
    document.getElementById('btn-start').disabled = (!profileName && !strategyName) && !state.sessionId;
}

/**
 * Load recording status from API.
 */
async function loadRecordingStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) return;

        const data = await response.json();
        state.isRecording = data.is_recording || false;
        updateRecordingUI();
    } catch (error) {
        console.error('Failed to load recording status:', error);
    }
}

/**
 * Toggle recording on/off.
 */
async function toggleRecording() {
    try {
        const response = await fetch('/api/recording/toggle', { method: 'POST' });
        if (!response.ok) throw new Error('Toggle failed');

        const data = await response.json();
        state.isRecording = data.is_recording;
        updateRecordingUI();

        showNotification(state.isRecording ? 'Recording started' : 'Recording stopped');
    } catch (error) {
        console.error('Failed to toggle recording:', error);
        showNotification('Failed to toggle recording', 'error');
    }
}

/**
 * Update recording UI elements.
 */
function updateRecordingUI() {
    const indicator = document.getElementById('rec-indicator');
    const text = document.getElementById('rec-text');
    const btn = document.getElementById('rec-btn');

    if (indicator) {
        indicator.className = 'rec-indicator' + (state.isRecording ? ' recording' : '');
    }
    if (text) {
        text.textContent = state.isRecording ? 'REC' : 'OFF';
        text.className = 'rec-text' + (state.isRecording ? ' recording' : '');
    }
    if (btn) {
        btn.textContent = state.isRecording ? 'STOP REC' : 'START REC';
        btn.className = 'rec-btn ' + (state.isRecording ? 'recording' : 'off');
    }
}

/**
 * Load selected strategy or profile.
 */
async function loadSelectedStrategy() {
    // Check if profile is selected
    const profileName = document.getElementById('profile-select').value;
    if (profileName) {
        return await loadSelectedProfile();
    }

    // Otherwise load strategy
    const name = document.getElementById('strategy-select').value;
    if (!name) return;

    try {
        const response = await fetch(`/api/backtest/strategies/${name}`);
        if (!response.ok) throw new Error('Failed to load strategy');

        state.currentStrategy = await response.json();
        state.currentProfile = null;  // Clear profile
        renderStrategyParams();
        document.getElementById('btn-start').disabled = false;

        showNotification(`Loaded strategy: ${name}`);
    } catch (error) {
        console.error('Failed to load strategy:', error);
        showNotification('Failed to load strategy', 'error');
    }
}

/**
 * Load selected profile and convert to strategy format.
 */
async function loadSelectedProfile() {
    const name = document.getElementById('profile-select').value;
    if (!name) return;

    try {
        // Load profile
        const response = await fetch(`/api/profiles/${encodeURIComponent(name)}`);
        if (!response.ok) throw new Error('Failed to load profile');

        const profile = await response.json();
        state.currentProfile = profile;

        // Load legacy format for backtest/live use
        const legacyResponse = await fetch(`/api/profiles/${encodeURIComponent(name)}/legacy`);
        if (!legacyResponse.ok) throw new Error('Failed to get legacy format');

        state.currentStrategy = await legacyResponse.json();
        renderStrategyParams();
        document.getElementById('btn-start').disabled = false;

        showNotification(`Loaded profile: ${name}`);
    } catch (error) {
        console.error('Failed to load profile:', error);
        showNotification('Failed to load profile', 'error');
    }
}

/**
 * Save current strategy.
 */
async function saveCurrentStrategy() {
    const name = prompt('Enter strategy name:', state.currentStrategy?.name || 'New Strategy');
    if (!name) return;

    const strategy = {
        name: name,
        params: state.currentStrategy?.params || getDefaultParams(),
        initial_balance: 0.1,
    };

    try {
        const response = await fetch('/api/backtest/strategies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(strategy),
        });

        if (!response.ok) throw new Error('Failed to save strategy');

        await loadStrategies();
        showNotification(`Saved strategy: ${name}`);
    } catch (error) {
        console.error('Failed to save strategy:', error);
        showNotification('Failed to save strategy', 'error');
    }
}

/**
 * Get default strategy parameters.
 */
function getDefaultParams() {
    return {
        entry_tick: 219,
        num_bets: 4,
        use_kelly_sizing: true,
        kelly_fraction: 0.25,
        use_dynamic_sizing: true,
        high_confidence_threshold: 55,
        high_confidence_multiplier: 2.0,
        reduce_on_drawdown: true,
        max_drawdown_pct: 0.15,
        take_profit_target: 1.3,
    };
}

/**
 * Quick start with default strategy.
 */
async function quickStart() {
    state.currentStrategy = {
        name: 'Default Strategy',
        params: getDefaultParams(),
        initial_balance: 0.1,
    };
    renderStrategyParams();
    await startPlayback();
}

/**
 * Start playback session.
 */
async function startPlayback() {
    if (!state.currentStrategy) {
        showNotification('Please load a strategy first', 'error');
        return;
    }

    try {
        const response = await fetch('/api/backtest/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(state.currentStrategy),
        });

        if (!response.ok) throw new Error('Failed to start playback');

        const data = await response.json();
        state.sessionId = data.session_id;

        // Reset state
        state.priceHistory = [];
        resetCharts();
        hideNoSessionOverlay();

        // Update UI
        enablePlaybackControls();
        setStatus('running');

        // Start playback
        state.isPlaying = true;
        startTickInterval();

    } catch (error) {
        console.error('Failed to start playback:', error);
        showNotification('Failed to start playback', 'error');
    }
}

/**
 * Toggle pause/resume.
 */
async function togglePause() {
    if (!state.sessionId) return;

    const action = state.isPlaying ? 'pause' : 'resume';

    try {
        await fetch(`/api/backtest/control/${state.sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action }),
        });

        state.isPlaying = !state.isPlaying;

        if (state.isPlaying) {
            startTickInterval();
            setStatus('running');
        } else {
            stopTickInterval();
            setStatus('paused');
        }

        updatePauseButton();

    } catch (error) {
        console.error('Failed to toggle pause:', error);
    }
}

/**
 * Step one tick.
 */
async function stepOneTick() {
    if (!state.sessionId) return;

    // Pause if playing
    if (state.isPlaying) {
        state.isPlaying = false;
        stopTickInterval();
        setStatus('paused');
        updatePauseButton();
    }

    await doTick();
}

/**
 * Skip to next game.
 */
async function skipToNextGame() {
    if (!state.sessionId) return;

    try {
        await fetch(`/api/backtest/control/${state.sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'next' }),
        });

        // Fetch new state
        await fetchCurrentState();

        // Reset price history for new game
        state.priceHistory = [];

    } catch (error) {
        console.error('Failed to skip to next game:', error);
    }
}

/**
 * Start the tick interval.
 */
function startTickInterval() {
    stopTickInterval();
    const interval = SPEED_MAP[state.speed] || 125;
    state.tickInterval = setInterval(doTick, interval);
}

/**
 * Stop the tick interval.
 */
function stopTickInterval() {
    if (state.tickInterval) {
        clearInterval(state.tickInterval);
        state.tickInterval = null;
    }
}

/**
 * Restart tick interval with new speed.
 */
function restartTickInterval() {
    stopTickInterval();
    startTickInterval();
}

/**
 * Perform one tick.
 */
async function doTick() {
    if (!state.sessionId) return;

    try {
        const response = await fetch(`/api/backtest/tick/${state.sessionId}`, {
            method: 'POST',
        });

        if (!response.ok) throw new Error('Tick failed');

        const data = await response.json();

        if (data.finished) {
            state.isPlaying = false;
            stopTickInterval();
            setStatus('finished');
            showNotification('Backtest complete!');
            return;
        }

        // Check if we moved to a new game
        if (data.game && data.game.game_id !== state.gameState?.game?.game_id) {
            state.priceHistory = [];
        }

        state.gameState = data;

        // Add current price to history
        if (data.game && data.game.current_tick !== undefined) {
            state.priceHistory.push({
                tick: data.game.current_tick,
                price: data.game.current_price,
            });
        }

        updateUI();

    } catch (error) {
        console.error('Tick error:', error);
        state.isPlaying = false;
        stopTickInterval();
    }
}

/**
 * Fetch current state without advancing.
 */
async function fetchCurrentState() {
    if (!state.sessionId) return;

    try {
        const response = await fetch(`/api/backtest/state/${state.sessionId}`);
        if (!response.ok) return;

        state.gameState = await response.json();
        updateUI();
    } catch (error) {
        console.error('Failed to fetch state:', error);
    }
}

/**
 * Update all UI elements.
 */
function updateUI() {
    const gs = state.gameState;
    if (!gs) return;

    updateDigitalTicker();
    updatePriceChart();
    updateWallet();
    updateActiveBets();
    updateStats();
    updateProgress();
    updateGameInfo();
    updateEquityChart();
}

/**
 * Update digital ticker.
 */
function updateDigitalTicker() {
    const game = state.gameState?.game;
    if (!game) return;

    document.getElementById('ticker-tick').textContent = game.current_tick || 0;
    document.getElementById('ticker-price').textContent = (game.current_price || 1).toFixed(2);
}

/**
 * Update price chart.
 */
function updatePriceChart() {
    if (!state.priceChart || !state.priceHistory.length) return;

    const labels = state.priceHistory.map(p => p.tick);
    const prices = state.priceHistory.map(p => p.price);

    state.priceChart.data.labels = labels;
    state.priceChart.data.datasets[0].data = prices;

    // Add bet markers
    const activeBets = state.gameState?.active_bets || [];
    const betPoints = activeBets.map(bet => ({
        x: bet.entry_tick,
        y: bet.entry_price,
    }));

    state.priceChart.data.datasets[1].data = betPoints;

    state.priceChart.update('none');
}

/**
 * Update wallet display.
 */
function updateWallet() {
    const gs = state.gameState;
    if (!gs) return;

    const balance = gs.wallet || 0.1;
    const initial = gs.strategy?.initial_balance || 0.1;
    const pnl = ((balance - initial) / initial) * 100;

    document.getElementById('wallet-balance').textContent = balance.toFixed(4);

    const pnlEl = document.getElementById('wallet-pnl');
    pnlEl.textContent = (pnl >= 0 ? '+' : '') + pnl.toFixed(2) + '%';
    pnlEl.className = 'value ' + (pnl >= 0 ? 'profit' : 'loss');
}

/**
 * Update active bets display.
 * Sidebets are BINARY - you win 5x if game rugs in your 40-tick window, otherwise lose.
 * Display shows ticks remaining in window, not P&L percentage.
 */
function updateActiveBets() {
    const bets = state.gameState?.active_bets || [];
    const container = document.getElementById('active-bets');
    const currentTick = state.gameState?.game?.current_tick || 0;

    if (bets.length === 0) {
        container.innerHTML = '<div style="color: #a6adc8; font-size: 12px;">No active bets</div>';
        return;
    }

    let html = '';
    bets.forEach((bet, i) => {
        // Calculate ticks remaining in sidebet window (40 ticks total)
        const windowEnd = bet.entry_tick + 40;
        const ticksRemaining = Math.max(0, windowEnd - currentTick);
        const ticksElapsed = Math.min(40, currentTick - bet.entry_tick);

        // Status based on window position
        let statusText, statusClass;
        if (ticksRemaining > 0) {
            statusText = `${ticksRemaining} ticks`;
            statusClass = ticksRemaining > 20 ? '' : 'warn';  // Warn when <20 ticks left
        } else {
            statusText = 'expired';
            statusClass = 'lost';
        }

        html += `
            <div class="bet-item">
                <div class="bet-marker bet${(i % 4) + 1}"></div>
                <div class="bet-info">
                    Bet ${i + 1}: ${bet.amount.toFixed(3)} SOL @ ${bet.entry_price.toFixed(2)}x
                </div>
                <div class="bet-status ${statusClass}">
                    ${statusText}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * Update cumulative statistics.
 */
function updateStats() {
    const stats = state.gameState?.cumulative_stats;
    if (!stats) return;

    document.getElementById('stat-wins').textContent = stats.wins || 0;
    document.getElementById('stat-losses').textContent = stats.losses || 0;

    const winRate = stats.total_games > 0
        ? ((stats.wins / stats.total_games) * 100).toFixed(1)
        : '0';
    document.getElementById('stat-winrate').textContent = winRate + '%';

    document.getElementById('stat-maxdd').textContent =
        ((stats.max_drawdown || 0) * 100).toFixed(1) + '%';
}

/**
 * Update progress bar.
 */
function updateProgress() {
    const gs = state.gameState;
    if (!gs) return;

    const current = gs.current_game_idx || 0;
    const total = gs.total_games || 1;
    const pct = (current / total) * 100;

    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-text').textContent = `${current} / ${total} games`;
}

/**
 * Update game info panel.
 */
function updateGameInfo() {
    const game = state.gameState?.game;
    if (!game) return;

    const gameIdEl = document.getElementById('game-id');
    if (game.game_id) {
        gameIdEl.textContent = game.game_id.substring(0, 12) + '...';
        gameIdEl.title = game.game_id;
    } else {
        gameIdEl.textContent = '--';
    }

    document.getElementById('game-duration').textContent =
        (game.duration || '--') + ' ticks';
}

/**
 * Update equity curve chart.
 */
function updateEquityChart() {
    const equity = state.gameState?.equity_curve;
    if (!state.equityChart || !equity || equity.length === 0) return;

    const labels = equity.map((_, i) => i);
    const values = equity.map(v => v);

    state.equityChart.data.labels = labels;
    state.equityChart.data.datasets[0].data = values;
    state.equityChart.update('none');
}

/**
 * Initialize charts.
 */
function initCharts() {
    // Price chart
    const priceCtx = document.getElementById('price-chart').getContext('2d');
    state.priceChart = new Chart(priceCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Price',
                    data: [],
                    borderColor: COLORS.blue,
                    backgroundColor: COLORS.blueFill,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: 'Bets',
                    data: [],
                    type: 'scatter',
                    pointBackgroundColor: COLORS.yellow,
                    pointBorderColor: COLORS.yellow,
                    pointRadius: 8,
                    pointStyle: 'rectRot',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Tick', color: COLORS.subtext },
                    ticks: { color: COLORS.subtext },
                    grid: { color: COLORS.surface },
                },
                y: {
                    title: { display: true, text: 'Price (x)', color: COLORS.subtext },
                    ticks: { color: COLORS.subtext },
                    grid: { color: COLORS.surface },
                    min: 0,
                },
            },
        },
    });

    // Equity chart
    const equityCtx = document.getElementById('equity-chart').getContext('2d');
    state.equityChart = new Chart(equityCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Equity',
                data: [],
                borderColor: COLORS.green,
                backgroundColor: COLORS.greenFill,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    display: false,
                },
                y: {
                    ticks: {
                        color: COLORS.subtext,
                        callback: (v) => v.toFixed(3),
                    },
                    grid: { color: COLORS.surface },
                },
            },
        },
    });
}

/**
 * Reset charts for new session.
 */
function resetCharts() {
    if (state.priceChart) {
        state.priceChart.data.labels = [];
        state.priceChart.data.datasets[0].data = [];
        state.priceChart.data.datasets[1].data = [];
        state.priceChart.update('none');
    }

    if (state.equityChart) {
        state.equityChart.data.labels = [];
        state.equityChart.data.datasets[0].data = [];
        state.equityChart.update('none');
    }
}

/**
 * Render strategy parameters.
 */
function renderStrategyParams() {
    const params = state.currentStrategy?.params;
    const container = document.getElementById('strategy-params');

    if (!params) {
        container.innerHTML = '<p>No strategy loaded</p>';
        return;
    }

    let html = '<div style="display: grid; gap: 6px;">';

    const items = [
        ['Entry Tick', params.entry_tick],
        ['Num Bets', params.num_bets],
        ['Kelly Sizing', params.use_kelly_sizing ? 'Yes' : 'No'],
        ['Kelly Fraction', (params.kelly_fraction * 100) + '%'],
        ['Dynamic Sizing', params.use_dynamic_sizing ? 'Yes' : 'No'],
        ['Confidence Threshold', params.high_confidence_threshold + '%'],
        ['Confidence Multiplier', params.high_confidence_multiplier + 'x'],
        ['Reduce on Drawdown', params.reduce_on_drawdown ? 'Yes' : 'No'],
        ['Max Drawdown', (params.max_drawdown_pct * 100) + '%'],
        ['Take Profit', params.take_profit_target ? ((params.take_profit_target - 1) * 100) + '%' : 'None'],
    ];

    for (const [label, value] of items) {
        html += `
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #a6adc8;">${label}:</span>
                <span style="color: #cdd6f4;">${value}</span>
            </div>
        `;
    }

    html += '</div>';
    container.innerHTML = html;
}

/**
 * Update speed display.
 */
function updateSpeedDisplay() {
    const speedLabels = { 1: '1x', 2: '2x', 3: '5x', 4: '10x', 5: 'MAX' };
    document.getElementById('speed-value').textContent = speedLabels[state.speed];
}

/**
 * Update pause button text.
 */
function updatePauseButton() {
    const btn = document.getElementById('btn-pause');
    btn.textContent = state.isPlaying ? 'Pause' : 'Resume';
}

/**
 * Set status indicator.
 */
function setStatus(status) {
    const indicator = document.getElementById('status-indicator');
    const text = document.getElementById('status-text');

    indicator.className = 'status-indicator ' + status;

    const labels = {
        paused: 'Paused',
        running: 'Running',
        finished: 'Finished',
    };
    text.textContent = labels[status] || 'Ready';
}

/**
 * Enable playback controls.
 */
function enablePlaybackControls() {
    document.getElementById('btn-pause').disabled = false;
    document.getElementById('btn-step').disabled = false;
    document.getElementById('btn-next').disabled = false;
}

/**
 * Hide the no-session overlay.
 */
function hideNoSessionOverlay() {
    const overlay = document.getElementById('no-session-overlay');
    if (overlay) overlay.style.display = 'none';
}

/**
 * Show a notification.
 */
function showNotification(message, type = 'success') {
    // Simple console notification for now
    console.log(`[${type.toUpperCase()}] ${message}`);

    // Could add toast notification here
}

// ============================================================================
// LIVE FEED MODE
// ============================================================================

/**
 * Set the playback mode (backtest or live).
 */
function setMode(mode) {
    if (state.mode === mode) return;

    state.mode = mode;
    console.log(`Mode changed to: ${mode}`);

    if (mode === 'backtest') {
        // Switch to backtest mode
        disconnectLiveFeed();
        document.getElementById('speed-control-wrapper').style.display = 'flex';
        document.getElementById('live-indicator').classList.add('hidden');
        document.getElementById('btn-next').style.display = '';
        document.getElementById('progress-text').parentElement.style.display = '';
        showNotification('Switched to Backtest mode');
    } else if (mode === 'live') {
        // Switch to live mode
        stopTickInterval();
        state.isPlaying = false;
        document.getElementById('speed-control-wrapper').style.display = 'none';
        document.getElementById('live-indicator').classList.remove('hidden');
        document.getElementById('btn-next').style.display = 'none';
        document.getElementById('progress-text').parentElement.style.display = 'none';

        // Auto-connect if strategy is loaded
        if (state.currentStrategy) {
            connectLiveFeed();
        } else {
            showNotification('Load a strategy to start live feed', 'error');
        }
    }

    updateModeUI();
}

/**
 * Connect to live WebSocket feed via SocketIO.
 */
function connectLiveFeed() {
    if (state.socket && state.liveConnected) {
        console.log('Already connected to live feed');
        return;
    }

    if (!state.currentStrategy) {
        showNotification('Please load a strategy first', 'error');
        return;
    }

    // Generate a new session ID for live mode
    state.sessionId = generateUUID();

    // Connect to SocketIO
    // Using the global io() from socket.io client library
    if (typeof io === 'undefined') {
        showNotification('SocketIO library not loaded', 'error');
        return;
    }

    state.socket = io();

    state.socket.on('connect', () => {
        console.log('Connected to SocketIO server');
        state.liveConnected = true;
        updateLiveConnectionStatus('connecting');

        // Join the live feed room with our strategy
        state.socket.emit('join_live', {
            session_id: state.sessionId,
            strategy: state.currentStrategy,
        });
    });

    state.socket.on('live_joined', (data) => {
        console.log('Joined live feed:', data);
        updateLiveConnectionStatus('connected');
        hideNoSessionOverlay();
        state.isPlaying = true;
        setStatus('running');
        showNotification(`Live feed started: ${data.session_id.substring(0, 8)}...`);
    });

    state.socket.on('live_tick', (data) => {
        // Update state with live data
        state.gameState = data.session;

        // Track price history for current game
        if (data.tick && data.tick.gameId) {
            // Reset price history on new game
            if (!state.currentGameId || state.currentGameId !== data.tick.gameId) {
                state.currentGameId = data.tick.gameId;
                state.priceHistory = [];
            }

            state.priceHistory.push({
                tick: data.tick.tickCount,
                price: data.tick.price,
            });
        }

        updateUI();
        updateLiveIndicators(data.tick);
    });

    // Listen for 'error' event (matches backend emit name)
    state.socket.on('error', (data) => {
        console.error('Live feed error:', data.message || data.error);
        updateLiveConnectionStatus('error');
        showNotification(`Live feed error: ${data.message || data.error}`, 'error');
    });

    state.socket.on('disconnect', () => {
        console.log('Disconnected from SocketIO server');
        state.liveConnected = false;
        updateLiveConnectionStatus('disconnected');
    });
}

/**
 * Disconnect from live WebSocket feed.
 */
function disconnectLiveFeed() {
    if (state.socket) {
        if (state.sessionId) {
            state.socket.emit('leave_live', { session_id: state.sessionId });
        }
        state.socket.disconnect();
        state.socket = null;
    }
    state.liveConnected = false;
    state.currentGameId = null;
    updateLiveConnectionStatus('disconnected');
}

/**
 * Update live connection status indicator.
 */
function updateLiveConnectionStatus(status) {
    const indicator = document.getElementById('live-indicator');
    const dot = indicator?.querySelector('.live-dot');

    if (!indicator || !dot) return;

    // Remove all status classes
    indicator.classList.remove('connecting', 'connected', 'disconnected', 'error');
    indicator.classList.add(status);

    const statusTexts = {
        connecting: 'CONNECTING...',
        connected: 'LIVE',
        disconnected: 'OFFLINE',
        error: 'ERROR',
    };

    const textEl = indicator.querySelector('span:not(.live-dot)');
    if (textEl) {
        textEl.textContent = statusTexts[status] || 'LIVE';
    }
}

/**
 * Update live mode indicators with current tick data.
 */
function updateLiveIndicators(tick) {
    if (!tick) return;

    // Update digital ticker with live data
    document.getElementById('ticker-tick').textContent = tick.tickCount || 0;
    document.getElementById('ticker-price').textContent = (tick.price || 1).toFixed(2);

    // Update game ID display
    const gameIdEl = document.getElementById('game-id');
    if (tick.gameId && gameIdEl) {
        gameIdEl.textContent = tick.gameId.substring(0, 12) + '...';
        gameIdEl.title = tick.gameId;
    }

    // Update game phase in duration field (repurposed for live mode)
    const durationEl = document.getElementById('game-duration');
    if (durationEl && tick.phase) {
        durationEl.textContent = tick.phase.toUpperCase();
    }
}

/**
 * Update UI elements for current mode.
 */
function updateModeUI() {
    const modeSelect = document.getElementById('mode-select');
    if (modeSelect) {
        modeSelect.value = state.mode;
    }

    // Update button states for live mode
    if (state.mode === 'live') {
        document.getElementById('btn-start').textContent = 'Connect';
        document.getElementById('btn-start').disabled = !state.currentStrategy;
    } else {
        document.getElementById('btn-start').textContent = 'Start';
        document.getElementById('btn-start').disabled = !state.currentStrategy && !state.sessionId;
    }
}

/**
 * Override startPlayback for live mode.
 */
const originalStartPlayback = startPlayback;
startPlayback = async function() {
    if (state.mode === 'live') {
        connectLiveFeed();
        return;
    }
    return originalStartPlayback();
};

// =============================================================================
// BROWSER CONNECTION & TRADING CONTROLS
// =============================================================================

let browserConnected = false;
// Note: currentBet is synced from server to avoid client/server state drift
let currentBet = 0.010;

async function fetchBrowserStatus() {
    try {
        const res = await fetch('/api/browser/status');
        if (!res.ok) return null;
        return await res.json();
    } catch (err) {
        console.error('Failed to fetch browser status:', err);
        return null;
    }
}

async function postBrowserConnect() {
    try {
        const res = await fetch('/api/browser/connect', { method: 'POST' });
        return await res.json();
    } catch (err) {
        console.error('Failed to connect browser:', err);
        return null;
    }
}

async function postBrowserDisconnect() {
    try {
        const res = await fetch('/api/browser/disconnect', { method: 'POST' });
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
        return await res.json();
    } catch (err) {
        console.error(`Trade action ${action} failed:`, err);
        return null;
    }
}

function updateBrowserUI(status) {
    if (!status) return;

    browserConnected = status.connected;

    const indicator = document.getElementById('connection-indicator');
    const connText = document.getElementById('connection-text');
    const connectBtn = document.getElementById('connect-btn');
    const tradingSection = document.getElementById('trading-section');
    const playerRow = document.getElementById('player-row');

    if (indicator) {
        indicator.className = 'conn-indicator' + (browserConnected ? ' connected' : '');
    }

    if (connText) {
        connText.textContent = browserConnected ? 'Connected' : 'Disconnected';
        connText.className = 'conn-text' + (browserConnected ? ' connected' : '');
    }

    if (connectBtn) {
        connectBtn.textContent = browserConnected ? 'DISCONNECT' : 'CONNECT';
        connectBtn.className = 'conn-btn ' + (browserConnected ? 'connected' : 'disconnected');
    }

    if (tradingSection) {
        tradingSection.style.display = browserConnected ? 'block' : 'none';
    }

    if (playerRow) {
        playerRow.style.display = browserConnected ? 'flex' : 'none';
    }

    if (status.player) {
        const usernameEl = document.getElementById('player-username');
        const balanceEl = document.getElementById('player-balance');
        if (usernameEl) usernameEl.textContent = status.player.username || '--';
        if (balanceEl) balanceEl.textContent = `${(status.player.balance || 0).toFixed(4)} SOL`;
    }

    // Sync bet amount from server (source of truth)
    if (status.bet_amount !== undefined) {
        currentBet = status.bet_amount;
        updateBetDisplay();
    }

    if (status.game && browserConnected) {
        updateGameStateUI(status.game);
    }
}

function updateGameStateUI(game) {
    const tickEl = document.getElementById('game-tick');
    const priceEl = document.getElementById('game-price');
    const phaseEl = document.getElementById('game-phase');

    if (tickEl) tickEl.textContent = game.tick_count || 0;
    if (priceEl) priceEl.textContent = `${(game.price || 1).toFixed(2)}x`;

    if (phaseEl) {
        const phase = (game.phase || 'UNKNOWN').toUpperCase();
        phaseEl.textContent = phase === 'UNKNOWN' ? '--' : phase;
        phaseEl.className = 'gs-val phase-' + phase.toLowerCase();
    }
}

async function toggleConnection() {
    const connectBtn = document.getElementById('connect-btn');
    if (connectBtn) {
        connectBtn.textContent = 'CONNECTING...';
        connectBtn.className = 'conn-btn connecting';
    }

    if (browserConnected) {
        const result = await postBrowserDisconnect();
        if (result) updateBrowserUI(result);
    } else {
        const result = await postBrowserConnect();
        if (result) {
            setTimeout(async () => {
                const status = await fetchBrowserStatus();
                updateBrowserUI(status);
            }, 500);
        }
    }
}

async function clickBuy() {
    await postTradeAction('buy');
}

async function clickSell() {
    await postTradeAction('sell');
}

async function clickSidebet() {
    await postTradeAction('sidebet');
}

async function clickIncrement(amount) {
    const result = await postTradeAction('increment', { amount });
    if (result && result.success) {
        // Use server's bet_amount (source of truth) instead of local calculation
        if (result.bet_amount !== undefined) {
            currentBet = result.bet_amount;
        }
        updateBetDisplay();
    }
}

async function clickClear() {
    const result = await postTradeAction('clear');
    if (result && result.success) {
        // Use server's bet_amount (source of truth)
        if (result.bet_amount !== undefined) {
            currentBet = result.bet_amount;
        }
        updateBetDisplay();
    }
}

async function clickHalf() {
    const result = await postTradeAction('half');
    if (result && result.success) {
        // Use server's bet_amount (source of truth)
        if (result.bet_amount !== undefined) {
            currentBet = result.bet_amount;
        }
        updateBetDisplay();
    }
}

async function clickDouble() {
    const result = await postTradeAction('double');
    if (result && result.success) {
        // Use server's bet_amount (source of truth)
        if (result.bet_amount !== undefined) {
            currentBet = result.bet_amount;
        }
        updateBetDisplay();
    }
}

async function clickPercentage(pct) {
    const result = await postTradeAction('percentage', { pct });
    if (result && result.success) {
        document.querySelectorAll('.pct-btn-sm').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent === `${pct}%`) btn.classList.add('active');
        });
    }
}

function updateBetDisplay() {
    const betEl = document.getElementById('current-bet');
    if (betEl) betEl.textContent = currentBet.toFixed(3);
}

// Poll browser status when connected
setInterval(async () => {
    if (browserConnected) {
        const status = await fetchBrowserStatus();
        updateBrowserUI(status);
    }
}, 2000);

// Poll recording status every 3 seconds
setInterval(async () => {
    await loadRecordingStatus();
}, 3000);

// Initialize when DOM is ready (consolidated listener)
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize backtest viewer
    await init();

    // Check initial browser status
    const status = await fetchBrowserStatus();
    updateBrowserUI(status);
});
