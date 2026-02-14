/**
 * Trading Profiles Manager
 *
 * Unified profile management with live WebSocket testing.
 * Handles profile CRUD, live session management, and real-time updates.
 */

// =============================================================================
// STATE
// =============================================================================

const state = {
    profiles: [],
    selectedProfile: null,
    socket: null,
    liveSession: null,
    wsConnected: false,
    decisionLog: [],
};

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Profiles] Initializing...');

    // Load profiles
    await refreshProfiles();

    // Check WebSocket status
    await checkWebSocketStatus();
    setInterval(checkWebSocketStatus, 5000);

    // Initialize SocketIO connection
    initializeSocket();
});

// =============================================================================
// PROFILE MANAGEMENT
// =============================================================================

/**
 * Refresh profiles from API.
 */
async function refreshProfiles() {
    try {
        const response = await fetch('/api/profiles');
        const data = await response.json();

        state.profiles = data.profiles || [];
        renderProfileList();

        console.log(`[Profiles] Loaded ${state.profiles.length} profiles`);
    } catch (error) {
        console.error('[Profiles] Failed to load profiles:', error);
        showNotification('Failed to load profiles', 'error');
    }
}

/**
 * Render the profile list in the sidebar.
 */
function renderProfileList() {
    const container = document.getElementById('profile-list');
    if (!container) return;

    if (state.profiles.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📁</div>
                <div class="empty-state-title">No Profiles</div>
                <div class="empty-state-desc">
                    Import from Monte Carlo or create manually
                </div>
            </div>
        `;
        return;
    }

    let html = '';
    for (const profile of state.profiles) {
        const isSelected = state.selectedProfile?.name === profile.name;
        const hasMc = profile.has_mc_metrics;
        const riskLevel = (profile.risk_level || 'unknown').toLowerCase().replace(/[- ]/g, '-');

        let badgeClass = '';
        if (riskLevel.includes('very-high')) badgeClass = 'very-high';
        else if (riskLevel.includes('high')) badgeClass = 'high';
        else if (riskLevel.includes('medium')) badgeClass = 'medium';
        else badgeClass = 'low';

        html += `
            <div class="profile-item ${isSelected ? 'selected' : ''}"
                 onclick="selectProfile('${profile.name}')"
                 data-profile="${profile.name}">
                <div class="profile-icon ${hasMc ? 'has-mc' : 'no-mc'}">
                    ${hasMc ? '★' : '○'}
                </div>
                <div class="profile-info">
                    <div class="profile-name">${profile.name}</div>
                    <div class="profile-meta">
                        ${profile.source || 'manual'}
                        ${profile.sortino_ratio ? ` | Sortino: ${profile.sortino_ratio.toFixed(2)}` : ''}
                    </div>
                </div>
                ${profile.risk_level ? `<span class="profile-badge ${badgeClass}">${profile.risk_level}</span>` : ''}
            </div>
        `;
    }

    container.innerHTML = html;
}

/**
 * Select a profile and show its details.
 */
async function selectProfile(name) {
    try {
        const response = await fetch(`/api/profiles/${name}`);
        if (!response.ok) {
            throw new Error('Profile not found');
        }

        const profile = await response.json();
        state.selectedProfile = profile;

        // Update UI
        renderProfileList();
        showProfileDetails(profile);

        console.log(`[Profiles] Selected: ${name}`);
    } catch (error) {
        console.error('[Profiles] Failed to load profile:', error);
        showNotification(`Failed to load profile: ${error.message}`, 'error');
    }
}

/**
 * Show profile details in the main content area.
 */
function showProfileDetails(profile) {
    const detailsCard = document.getElementById('profile-details');
    const noProfileCard = document.getElementById('no-profile-selected');
    const testModesCard = document.getElementById('test-modes-card');

    if (!detailsCard || !noProfileCard) return;

    // Show details, hide empty state
    detailsCard.style.display = 'block';
    noProfileCard.style.display = 'none';

    // Update header
    document.getElementById('selected-profile-name').textContent = profile.name;

    // Execution config
    const exec = profile.execution || {};
    document.getElementById('detail-entry-tick').textContent = exec.entry_tick || '--';
    document.getElementById('detail-num-bets').textContent = exec.num_bets || '--';
    document.getElementById('detail-bet-sizes').textContent =
        exec.bet_sizes ? exec.bet_sizes.map(b => b.toFixed(4)).join(', ') : '--';
    document.getElementById('detail-balance').textContent =
        exec.initial_balance ? `${exec.initial_balance.toFixed(4)} SOL` : '--';

    // Scaling config
    const scaling = profile.scaling || {};
    document.getElementById('detail-scaling-mode').textContent =
        (scaling.mode || 'fixed').replace(/_/g, ' ');
    document.getElementById('detail-kelly').textContent =
        scaling.kelly_fraction ? `${(scaling.kelly_fraction * 100).toFixed(0)}%` : '--';
    document.getElementById('detail-theta').textContent =
        scaling.theta_base && scaling.theta_max ?
        `${scaling.theta_base} → ${scaling.theta_max}` : '--';
    document.getElementById('detail-volatility').textContent =
        scaling.use_volatility_scaling ? 'Enabled' : 'Disabled';

    // Risk controls
    const risk = profile.risk_controls || {};
    document.getElementById('detail-max-dd').textContent =
        risk.max_drawdown_pct ? `${(risk.max_drawdown_pct * 100).toFixed(1)}%` : '--';
    document.getElementById('detail-take-profit').textContent =
        risk.take_profit_target ? `${(risk.take_profit_target * 100).toFixed(0)}%` : 'None';

    // Monte Carlo metrics (if available)
    const mcSection = document.getElementById('mc-metrics-section');
    const mc = profile.monte_carlo_metrics;

    if (mc) {
        mcSection.style.display = 'block';
        document.getElementById('mc-prob-profit').textContent =
            mc.probability_profit ? `${(mc.probability_profit * 100).toFixed(1)}%` : '--';
        document.getElementById('mc-sortino').textContent =
            mc.sortino_ratio ? mc.sortino_ratio.toFixed(2) : '--';
        document.getElementById('mc-mean-dd').textContent =
            mc.mean_max_drawdown ? `${(mc.mean_max_drawdown * 100).toFixed(1)}%` : '--';
        document.getElementById('mc-risk-level').textContent = mc.risk_level || 'Unknown';
    } else {
        mcSection.style.display = 'none';
    }

    // Enable test mode buttons
    const backtestBtn = document.getElementById('btn-backtest');
    const liveBtn = document.getElementById('btn-live');

    if (backtestBtn) backtestBtn.disabled = false;
    if (liveBtn) liveBtn.disabled = !state.wsConnected;
}

// =============================================================================
// WEBSOCKET STATUS
// =============================================================================

/**
 * Check WebSocket connection status.
 */
async function checkWebSocketStatus() {
    try {
        const response = await fetch('/api/live/status');
        const data = await response.json();

        state.wsConnected = data.connected;

        // Update UI
        const dot = document.getElementById('ws-status-dot');
        const text = document.getElementById('ws-status-text');
        const sessions = document.getElementById('active-sessions');

        if (dot) {
            dot.classList.toggle('connected', data.connected);
        }
        if (text) {
            text.textContent = data.connected ? 'Connected' : 'Disconnected';
        }
        if (sessions) {
            sessions.textContent = data.active_sessions || 0;
        }

        // Update live button state
        const liveBtn = document.getElementById('btn-live');
        if (liveBtn && state.selectedProfile) {
            liveBtn.disabled = !data.connected;
        }

    } catch (error) {
        console.warn('[Profiles] Failed to check WS status:', error);
        state.wsConnected = false;
    }
}

// =============================================================================
// SOCKET.IO CONNECTION
// =============================================================================

/**
 * Initialize Socket.IO connection.
 */
function initializeSocket() {
    if (state.socket) {
        state.socket.disconnect();
    }

    state.socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 10,
    });

    state.socket.on('connect', () => {
        console.log('[Profiles] Socket connected');
        addLogEntry('Socket connected', 'game');
    });

    state.socket.on('disconnect', () => {
        console.log('[Profiles] Socket disconnected');
        addLogEntry('Socket disconnected', 'game');
    });

    // Live session events
    state.socket.on('live_joined', (data) => {
        console.log('[Profiles] Joined live session:', data);
        state.liveSession = data.session;
        addLogEntry(`Session started: ${data.session_id}`, 'game');
    });

    state.socket.on('live_tick', (data) => {
        handleLiveTick(data);
    });

    state.socket.on('error', (data) => {
        console.error('[Profiles] Socket error:', data);
        showNotification(`Error: ${data.message || data.error}`, 'error');
        addLogEntry(`Error: ${data.message || data.error}`, 'loss');
    });
}

// =============================================================================
// LIVE SESSION MANAGEMENT
// =============================================================================

/**
 * Start a live paper trading session.
 */
function startLiveSession() {
    if (!state.selectedProfile) {
        showNotification('Please select a profile first', 'error');
        return;
    }

    if (!state.socket || !state.socket.connected) {
        showNotification('Socket not connected', 'error');
        return;
    }

    const sessionId = `profile-${Date.now()}`;
    const profile = state.selectedProfile;

    // Convert profile to strategy format for backend
    const strategy = {
        name: profile.name,
        initial_balance: profile.execution?.initial_balance || 0.1,
        params: {
            entry_tick: profile.execution?.entry_tick || 219,
            num_bets: profile.execution?.num_bets || 4,
            bet_sizes: profile.execution?.bet_sizes || [0.001, 0.001, 0.001, 0.001],
            use_kelly_sizing: profile.scaling?.mode === 'kelly' || profile.scaling?.mode === 'theta_bayesian',
            kelly_fraction: profile.scaling?.kelly_fraction || 0.25,
            use_dynamic_sizing: profile.scaling?.mode === 'theta_bayesian',
            reduce_on_drawdown: profile.risk_controls?.reduce_on_drawdown || false,
            max_drawdown_pct: profile.risk_controls?.max_drawdown_pct || 0.15,
            take_profit_target: profile.risk_controls?.take_profit_target,
        }
    };

    // Join live session
    state.socket.emit('join_live', {
        session_id: sessionId,
        strategy: strategy,
    });

    // Show live session UI
    showLiveSessionUI(profile.name);
    addLogEntry(`Starting live session with ${profile.name}`, 'game');

    console.log('[Profiles] Started live session:', sessionId);
}

/**
 * Stop the current live session.
 */
function stopLiveSession() {
    if (!state.socket || !state.liveSession) {
        return;
    }

    state.socket.emit('leave_live', {
        session_id: state.liveSession.session_id,
    });

    state.liveSession = null;
    hideLiveSessionUI();
    addLogEntry('Session stopped', 'game');

    console.log('[Profiles] Stopped live session');
}

/**
 * Show the live session UI.
 */
function showLiveSessionUI(profileName) {
    const liveSession = document.getElementById('live-session');
    const testModes = document.getElementById('test-modes-card');
    const profileDetails = document.getElementById('profile-details');

    if (liveSession) {
        liveSession.classList.add('active');
        document.getElementById('live-profile-name').textContent = profileName;
    }
    if (testModes) testModes.style.display = 'none';
    if (profileDetails) profileDetails.style.display = 'none';

    // Clear decision log
    state.decisionLog = [];
    document.getElementById('decision-log').innerHTML = '';
}

/**
 * Hide the live session UI.
 */
function hideLiveSessionUI() {
    const liveSession = document.getElementById('live-session');
    const testModes = document.getElementById('test-modes-card');
    const profileDetails = document.getElementById('profile-details');

    if (liveSession) liveSession.classList.remove('active');
    if (testModes) testModes.style.display = 'block';
    if (profileDetails && state.selectedProfile) profileDetails.style.display = 'block';
}

// =============================================================================
// LIVE TICK HANDLING
// =============================================================================

/**
 * Handle live tick events.
 */
function handleLiveTick(data) {
    const tick = data.tick;
    const session = data.session;

    if (!tick || !session) return;

    // Update game info
    updateGameInfo(tick, session);

    // Update wallet
    updateWallet(session);

    // Update active bets
    updateActiveBets(session);
}

/**
 * Update game info bar.
 */
function updateGameInfo(tick, session) {
    const game = session.game || {};

    document.getElementById('live-game-id').textContent =
        (game.game_id || tick.gameId || '--').slice(0, 8);
    document.getElementById('live-tick').textContent = game.current_tick || tick.tickCount || '--';
    document.getElementById('live-price').textContent =
        game.current_price ? `${game.current_price.toFixed(2)}x` : '--';
    document.getElementById('live-phase').textContent = session.phase || game.phase || '--';
}

/**
 * Update wallet display.
 */
function updateWallet(session) {
    const wallet = session.wallet || {};
    const initial = session.initial_balance || 0.1;
    const current = wallet.balance || initial;
    const pnl = ((current - initial) / initial) * 100;
    const dd = wallet.current_drawdown || 0;

    const balanceEl = document.getElementById('live-balance');
    const pnlEl = document.getElementById('live-pnl');
    const ddEl = document.getElementById('live-drawdown');

    if (balanceEl) {
        balanceEl.textContent = current.toFixed(4);
        balanceEl.className = 'wallet-stat-value ' + (current >= initial ? 'positive' : 'negative');
    }

    if (pnlEl) {
        pnlEl.textContent = `${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}%`;
        pnlEl.className = 'wallet-stat-value ' + (pnl >= 0 ? 'positive' : 'negative');
    }

    if (ddEl) {
        ddEl.textContent = `${(dd * 100).toFixed(1)}%`;
        ddEl.className = 'wallet-stat-value ' + (dd > 0.05 ? 'negative' : 'neutral');
    }
}

/**
 * Update active bets display.
 */
function updateActiveBets(session) {
    const bets = session.active_bets || [];
    const container = document.getElementById('live-bets');
    if (!container) return;

    let html = '';
    for (let i = 0; i < 4; i++) {
        const bet = bets[i];
        let slotClass = 'bet-slot';
        let amount = '--';
        let status = 'waiting';

        if (bet) {
            slotClass += ' active';
            amount = bet.amount ? bet.amount.toFixed(4) : '--';
            status = `tick ${bet.tick_placed || '--'}`;

            if (bet.result === 'won') {
                slotClass = 'bet-slot won';
                status = 'WON';
            } else if (bet.result === 'lost') {
                slotClass = 'bet-slot lost';
                status = 'LOST';
            }
        }

        html += `
            <div class="${slotClass}">
                <div class="bet-slot-number">Bet ${i + 1}</div>
                <div class="bet-slot-amount">${amount}</div>
                <div class="bet-slot-status">${status}</div>
            </div>
        `;
    }

    container.innerHTML = html;
}

// =============================================================================
// DECISION LOG
// =============================================================================

/**
 * Add an entry to the decision log.
 */
function addLogEntry(message, type = 'game') {
    const now = new Date();
    const time = now.toTimeString().slice(0, 8);

    const entry = { time, message, type };
    state.decisionLog.unshift(entry);

    // Keep only last 50 entries
    if (state.decisionLog.length > 50) {
        state.decisionLog.pop();
    }

    renderDecisionLog();
}

/**
 * Render the decision log.
 */
function renderDecisionLog() {
    const container = document.getElementById('decision-log');
    if (!container) return;

    let html = '';
    for (const entry of state.decisionLog) {
        html += `
            <div class="log-entry ${entry.type}">
                <span class="log-time">${entry.time}</span>
                <span class="log-message">${entry.message}</span>
            </div>
        `;
    }

    container.innerHTML = html || '<div class="log-entry">No events yet</div>';
}

// =============================================================================
// BACKTEST
// =============================================================================

/**
 * Start a historical backtest.
 */
function startBacktest() {
    if (!state.selectedProfile) {
        showNotification('Please select a profile first', 'error');
        return;
    }

    // Navigate to backtest page with profile preselected
    const profileName = state.selectedProfile.name;
    window.location.href = `/backtest?profile=${encodeURIComponent(profileName)}`;
}

// =============================================================================
// NOTIFICATIONS
// =============================================================================

/**
 * Show a notification toast.
 */
function showNotification(message, type = 'info') {
    // Simple console log for now
    console.log(`[Notification] ${type}: ${message}`);

    // Could add toast notification UI here
}

// =============================================================================
// EXPORTS
// =============================================================================

// Make functions available globally
window.refreshProfiles = refreshProfiles;
window.selectProfile = selectProfile;
window.startBacktest = startBacktest;
window.startLiveSession = startLiveSession;
window.stopLiveSession = stopLiveSession;
