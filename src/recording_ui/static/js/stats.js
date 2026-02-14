/**
 * VECTRA Stats Page - WebSocket Connection + State Management
 *
 * Connects directly to rugs.fun WebSocket for live server stats.
 * Displays session stats, milestones, daily high, and rugpool data.
 */

// =============================================================================
// STATE
// =============================================================================

const StatsState = {
    socket: null,
    isConnected: false,
    eventCount: 0,
    lastEventTs: null,

    // Cached stats
    stats: {
        averageMultiplier: null,
        connectedPlayers: 0,
        count2x: 0,
        count10x: 0,
        count50x: 0,
        count100x: 0,
        highestToday: null,
        highestTodayTimestamp: null,
        highestTodayPrices: null,
        rugpool: null,
    },

    // Chart instance
    highestTodayChart: null,

    // Expanded sections
    expandedSections: new Set(),
};

const WS_URL = 'wss://rugs.fun';
let localPollingInterval = null;

// =============================================================================
// WEBSOCKET CONNECTION
// =============================================================================

function connect() {
    if (StatsState.socket && StatsState.socket.connected) {
        return;
    }

    updateConnectionStatus('connecting');

    // Check if Socket.IO is available
    if (typeof io === 'undefined') {
        console.warn('[Stats] Socket.IO not available, using local API');
        startLocalPolling();
        return;
    }

    try {
        StatsState.socket = io(WS_URL, {
            transports: ['websocket'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 3,  // Reduced attempts before falling back
            timeout: 5000,
        });

        StatsState.socket.on('connect', () => {
            StatsState.isConnected = true;
            updateConnectionStatus('connected');
            console.log('[Stats] Connected to rugs.fun');
            stopLocalPolling();
        });

        StatsState.socket.on('disconnect', () => {
            StatsState.isConnected = false;
            updateConnectionStatus('disconnected');
            console.log('[Stats] Disconnected from rugs.fun');
        });

        StatsState.socket.on('connect_error', (err) => {
            console.warn('[Stats] WebSocket connection failed, falling back to local API:', err.message);
            updateConnectionStatus('local', 'Using local data');
            startLocalPolling();
        });

        // Listen for gameStateUpdate events
        StatsState.socket.on('gameStateUpdate', handleGameStateUpdate);
    } catch (err) {
        console.warn('[Stats] Failed to initialize WebSocket, using local API:', err);
        startLocalPolling();
    }
}

// =============================================================================
// LOCAL API POLLING (fallback when WebSocket unavailable)
// =============================================================================

function startLocalPolling() {
    if (localPollingInterval) return;  // Already polling

    updateConnectionStatus('local', 'Local mode');

    // Fetch local stats immediately
    fetchLocalStats();

    // Poll every 5 seconds
    localPollingInterval = setInterval(fetchLocalStats, 5000);
}

function stopLocalPolling() {
    if (localPollingInterval) {
        clearInterval(localPollingInterval);
        localPollingInterval = null;
    }
}

async function fetchLocalStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Failed to fetch local stats');

        const data = await response.json();

        // Update stats from local API
        StatsState.eventCount = data.session_event_count || 0;
        StatsState.stats.connectedPlayers = '--';  // Not available locally

        // Render with available data
        renderLocalStats(data);

        updateConnectionStatus('local', 'Local data');
    } catch (err) {
        console.error('[Stats] Failed to fetch local stats:', err);
        updateConnectionStatus('error', 'API unavailable');
    }
}

function renderLocalStats(data) {
    // Session stats from local API
    updateElement('stat-event-count', (data.session_event_count || 0).toLocaleString());
    updateElement('stat-connected-players', '--');
    updateElement('stat-avg-multiplier', '--');

    // Note: Live milestones not available without WebSocket
    // These will show "--" until WebSocket connects

    // Last update time
    updateElement('stat-last-update', new Date().toLocaleTimeString());
}

function disconnect() {
    if (StatsState.socket) {
        StatsState.socket.disconnect();
        StatsState.socket = null;
    }
}

// =============================================================================
// EVENT HANDLING
// =============================================================================

function handleGameStateUpdate(data) {
    StatsState.eventCount++;
    StatsState.lastEventTs = Date.now();

    // Extract stats from gameStateUpdate
    const stats = StatsState.stats;

    // Session stats
    if (data.averageMultiplier !== undefined) {
        stats.averageMultiplier = data.averageMultiplier;
    }
    if (data.connectedPlayers !== undefined) {
        stats.connectedPlayers = data.connectedPlayers;
    }

    // Milestone counts
    if (data.count2x !== undefined) stats.count2x = data.count2x;
    if (data.count10x !== undefined) stats.count10x = data.count10x;
    if (data.count50x !== undefined) stats.count50x = data.count50x;
    if (data.count100x !== undefined) stats.count100x = data.count100x;

    // Today's high
    if (data.highestToday !== undefined) {
        stats.highestToday = data.highestToday;
    }
    if (data.highestTodayTimestamp !== undefined) {
        stats.highestTodayTimestamp = data.highestTodayTimestamp;
    }
    if (data.highestTodayPrices !== undefined) {
        stats.highestTodayPrices = data.highestTodayPrices;
    }

    // Rugpool (nested in data or data.rugpool)
    if (data.rugpool) {
        stats.rugpool = data.rugpool;
    } else if (data.rugpoolAmount !== undefined) {
        // Flat structure fallback
        stats.rugpool = {
            rugpoolAmount: data.rugpoolAmount,
            instarugCount: data.instarugCount,
            threshold: data.threshold,
            totalEntries: data.totalEntries,
            playersWithEntries: data.playersWithEntries,
        };
    }

    // Update UI
    renderStats();
}

// =============================================================================
// UI RENDERING
// =============================================================================

function renderStats() {
    const stats = StatsState.stats;

    // Session stats
    updateElement('stat-avg-multiplier', formatMultiplier(stats.averageMultiplier));
    updateElement('stat-connected-players', stats.connectedPlayers);
    updateElement('stat-event-count', StatsState.eventCount.toLocaleString());

    // Milestones
    updateElement('stat-count-2x', stats.count2x);
    updateElement('stat-count-10x', stats.count10x);
    updateElement('stat-count-50x', stats.count50x);
    updateElement('stat-count-100x', stats.count100x);

    // Today's high - summary
    updateElement('stat-highest-today', stats.highestToday ? formatMultiplier(stats.highestToday) + 'x' : '--');
    updateElement('stat-highest-today-time', stats.highestTodayTimestamp ? '@ ' + formatTime(stats.highestTodayTimestamp) : '@ --');
    updateElement('stat-highest-today-ticks', stats.highestTodayPrices ? `(${stats.highestTodayPrices.length} ticks)` : '(-- ticks)');

    // Today's high - expanded details
    updateElement('stat-highest-today-ts', stats.highestTodayTimestamp || '--');
    updateElement('stat-highest-today-peak', formatMultiplier(stats.highestToday));
    updateElement('stat-highest-today-prices-count', stats.highestTodayPrices ? `${stats.highestTodayPrices.length} values` : '-- values');

    // Render chart if section is expanded and we have prices
    if (StatsState.expandedSections.has('highest-today') && stats.highestTodayPrices) {
        renderHighestTodayChart(stats.highestTodayPrices);
    }

    // Rugpool - summary
    if (stats.rugpool) {
        const rp = stats.rugpool;
        updateElement('stat-rugpool-amount', formatSol(rp.rugpoolAmount) + ' SOL');
        updateElement('stat-rugpool-instarugs', rp.instarugCount ?? '--');
        updateElement('stat-rugpool-threshold', rp.threshold ?? '--');

        // Rugpool - expanded details
        updateElement('stat-rugpool-amount-full', formatSol(rp.rugpoolAmount));
        updateElement('stat-rugpool-instarug-count', rp.instarugCount ?? '--');
        updateElement('stat-rugpool-threshold-full', rp.threshold ?? '--');
        updateElement('stat-rugpool-entries', rp.totalEntries ?? '--');
        updateElement('stat-rugpool-players', rp.playersWithEntries ?? '--');
    }

    // Last update time
    updateElement('stat-last-update', new Date().toLocaleTimeString());
}

function renderHighestTodayChart(prices) {
    const ctx = document.getElementById('highest-today-chart');
    if (!ctx) return;

    // Destroy existing chart
    if (StatsState.highestTodayChart) {
        StatsState.highestTodayChart.destroy();
    }

    // Convert prices to numbers
    const priceData = prices.map(p => parseFloat(p));

    StatsState.highestTodayChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: priceData.map((_, i) => i),
            datasets: [{
                data: priceData,
                borderColor: '#ffcc00',
                backgroundColor: 'rgba(255, 204, 0, 0.1)',
                borderWidth: 1.5,
                pointRadius: 0,
                fill: true,
                tension: 0.1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    display: false,
                },
                y: {
                    display: true,
                    grid: { color: '#333' },
                    ticks: {
                        color: '#666',
                        font: { size: 9 },
                        maxTicksLimit: 4,
                    },
                },
            },
        },
    });
}

// =============================================================================
// UI HELPERS
// =============================================================================

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value ?? '--';
}

function updateConnectionStatus(status, message = '') {
    const dot = document.getElementById('ws-status-dot');
    const text = document.getElementById('ws-status-text');

    if (dot) {
        dot.classList.remove('connected', 'connecting', 'error');
        if (status === 'connected') dot.classList.add('connected');
        else if (status === 'connecting') dot.classList.add('connecting');
        else if (status === 'error') dot.classList.add('error');
        else if (status === 'local') dot.classList.add('connected');  // Local mode is "ok"
    }

    if (text) {
        const labels = {
            connecting: 'rugs.fun (connecting...)',
            connected: 'rugs.fun (live)',
            disconnected: 'rugs.fun (disconnected)',
            error: `rugs.fun (error: ${message})`,
            local: 'Local API (recording stats)',
        };
        text.textContent = labels[status] || 'rugs.fun';
    }

    // Also update header status
    const headerDot = document.querySelector('.status-dot');
    const headerText = document.querySelector('.status-text');
    if (headerDot) {
        headerDot.classList.remove('connected');
        if (status === 'connected') headerDot.classList.add('connected');
    }
    if (headerText) {
        headerText.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
    }
}

function formatMultiplier(value) {
    if (value == null) return '--';
    return parseFloat(value).toFixed(2);
}

function formatTime(timestamp) {
    if (!timestamp) return '--';
    return new Date(timestamp).toLocaleTimeString();
}

function formatSol(value) {
    if (value == null) return '--';
    return parseFloat(value).toFixed(2);
}

// =============================================================================
// COLLAPSIBLE SECTIONS
// =============================================================================

function toggleSection(sectionId) {
    const content = document.getElementById(sectionId + '-content');
    const icon = document.getElementById(sectionId + '-icon');

    if (!content || !icon) return;

    const isExpanded = content.classList.contains('expanded');

    if (isExpanded) {
        content.classList.remove('expanded');
        icon.innerHTML = '&#9654;'; // Right arrow
        StatsState.expandedSections.delete(sectionId);
    } else {
        content.classList.add('expanded');
        icon.innerHTML = '&#9660;'; // Down arrow
        StatsState.expandedSections.add(sectionId);

        // Render chart if this is the highest-today section
        if (sectionId === 'highest-today' && StatsState.stats.highestTodayPrices) {
            setTimeout(() => {
                renderHighestTodayChart(StatsState.stats.highestTodayPrices);
            }, 50);
        }
    }
}

// Make toggleSection available globally for onclick handlers
window.toggleSection = toggleSection;

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    connect();

    // Reconnect on tab focus
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            // Render cached stats immediately
            renderStats();
            // Reconnect if needed
            if (!StatsState.isConnected) {
                connect();
            }
        }
    });
});

// Cleanup on page unload
window.addEventListener('beforeunload', disconnect);
