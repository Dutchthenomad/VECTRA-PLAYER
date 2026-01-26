/**
 * Recording Control - Application Logic
 *
 * Connects to Recording Service API (port 9010) and Foundation WS (port 9000)
 * for real-time stats and control.
 */

import { FoundationWSClient } from '../../shared/foundation-ws-client.js';

// Configuration
const RECORDING_API = 'http://localhost:9010';
const FOUNDATION_WS = 'ws://localhost:9000/feed';

// State
let isRecording = false;  // Default to false until we know the actual state
let serviceAvailable = false;  // Track if recording service is reachable
let foundationClient = null;
let statsInterval = null;
let recentGames = [];
let feedEntries = [];
const MAX_FEED_ENTRIES = 50;

// Debouncing
let recentFetchTimeout = null;
let feedUpdateTimeout = null;
const FEED_DEBOUNCE_MS = 100;

// Valid CSS color pattern for XSS protection
const VALID_COLOR_PATTERN = /^(var\(--[\w-]+\)|#[0-9a-fA-F]{3,8}|rgb\(\d+,\s*\d+,\s*\d+\)|rgba\(\d+,\s*\d+,\s*\d+,\s*[\d.]+\)|[a-zA-Z]+)$/;

// DOM Elements
const elements = {
    statusDot: null,
    statusLabel: null,
    statusMeta: null,
    toggleBtn: null,
    sessionGames: null,
    todayGames: null,
    totalGames: null,
    lastRug: null,
    recentList: null,
    feedList: null,
    connectionDot: null,
    connectionStatus: null,
    storageFill: null,
    containerStatus: null,
    uptime: null,
    memory: null,
    lastError: null,
};

/**
 * Initialize the application
 */
export async function init() {
    // Cache DOM elements
    cacheElements();

    // Initialize Foundation WebSocket client
    initFoundationClient();

    // Start polling Recording Service API
    startPolling();

    // Initial data fetch
    await fetchStatus();
    await fetchStats();
    await fetchHealth();
    await fetchRecent();

    console.log('[Recording Control] Initialized');
}

/**
 * Cleanup function - call before reinitializing or destroying component
 */
export function cleanup() {
    if (statsInterval) {
        clearInterval(statsInterval);
        statsInterval = null;
    }
    if (recentFetchTimeout) {
        clearTimeout(recentFetchTimeout);
        recentFetchTimeout = null;
    }
    if (feedUpdateTimeout) {
        clearTimeout(feedUpdateTimeout);
        feedUpdateTimeout = null;
    }
    if (foundationClient) {
        foundationClient.disconnect();
        foundationClient = null;
    }
    console.log('[Recording Control] Cleaned up');
}

/**
 * Cache DOM element references
 */
function cacheElements() {
    elements.statusDot = document.getElementById('statusDot');
    elements.statusLabel = document.getElementById('statusLabel');
    elements.statusMeta = document.getElementById('statusMeta');
    elements.toggleBtn = document.getElementById('toggleBtn');
    elements.sessionGames = document.getElementById('sessionGames');
    elements.todayGames = document.getElementById('todayGames');
    elements.totalGames = document.getElementById('totalGames');
    elements.lastRug = document.getElementById('lastRug');
    elements.recentList = document.getElementById('recentList');
    elements.feedList = document.getElementById('feedList');
    elements.connectionDot = document.querySelector('.connection-dot');
    elements.connectionStatus = document.querySelector('.connection-status span:last-child');
    elements.storageFill = document.querySelector('.storage-fill');

    // Service Health - use direct IDs instead of complex selectors
    elements.containerStatus = document.getElementById('healthContainer');
    elements.uptime = document.getElementById('healthUptime');
    elements.memory = document.getElementById('healthMemory');
    elements.lastError = document.getElementById('healthLastError');

    // Debug logging
    console.log('[Recording Control] DOM elements cached:', {
        feedList: !!elements.feedList,
        containerStatus: !!elements.containerStatus,
        uptime: !!elements.uptime,
        memory: !!elements.memory,
        lastError: !!elements.lastError
    });
}

/**
 * Initialize Foundation WebSocket client for live feed
 */
function initFoundationClient() {
    try {
        foundationClient = new FoundationWSClient({ url: FOUNDATION_WS });

        foundationClient.on('connection', (event) => {
            const connected = event.connected;
            updateConnectionStatus(connected);
        });

        foundationClient.on('game.tick', (event) => {
            const data = event.data;
            if (!data) return;

            const price = typeof data.price === 'number' ? data.price.toFixed(2) : '0.00';
            const tick = data.tickCount || 0;
            addFeedEntry('game.tick', `price: ${price}x, tick: ${tick}`);

            // Check for RUG event (debounced to prevent race conditions)
            if (data.rugged) {
                addFeedEntry('RUG', `CAPTURED: ${price}x`, 'var(--ctp-red)');

                // Debounced fetch - cancel previous pending fetch
                if (recentFetchTimeout) {
                    clearTimeout(recentFetchTimeout);
                }
                recentFetchTimeout = setTimeout(fetchRecent, 1000);
            }
        });

        foundationClient.connect();
    } catch (e) {
        console.error('[Recording Control] Failed to init Foundation client:', e);
        updateConnectionStatus(false);
    }
}

/**
 * Start polling the Recording Service API
 */
function startPolling() {
    // Poll every 5 seconds
    statsInterval = setInterval(async () => {
        await fetchStatus();
        await fetchStats();
        await fetchHealth();
    }, 5000);
}

/**
 * Fetch recording status from API
 */
async function fetchStatus() {
    try {
        const response = await fetch(`${RECORDING_API}/recording/status`);
        if (!response.ok) throw new Error('Failed to fetch status');

        const data = await response.json();
        serviceAvailable = true;
        updateRecordingStatus(data);
    } catch (e) {
        console.error('[Recording Control] Failed to fetch status:', e);
        serviceAvailable = false;
        updateServiceUnavailable();
    }
}

/**
 * Fetch recording stats from API
 */
async function fetchStats() {
    try {
        const response = await fetch(`${RECORDING_API}/recording/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');

        const data = await response.json();
        updateStats(data);
    } catch (e) {
        console.error('[Recording Control] Failed to fetch stats:', e);
    }
}

/**
 * Fetch recent games from API
 */
async function fetchRecent() {
    try {
        const response = await fetch(`${RECORDING_API}/recording/recent?limit=10`);
        if (!response.ok) throw new Error('Failed to fetch recent');

        recentGames = await response.json();
        updateRecentList();
    } catch (e) {
        console.error('[Recording Control] Failed to fetch recent:', e);
    }
}

/**
 * Fetch health info from API
 */
async function fetchHealth() {
    try {
        const response = await fetch(`${RECORDING_API}/health`);
        if (!response.ok) throw new Error('Failed to fetch health');

        const data = await response.json();
        updateHealthDisplay(data);
    } catch (e) {
        console.error('[Recording Control] Failed to fetch health:', e);
    }
}

/**
 * Toggle recording state
 */
window.toggleRecording = async function() {
    if (!serviceAvailable) {
        addFeedEntry('ERROR', 'Recording service not running (port 9010)', 'var(--ctp-red)');
        return;
    }

    const endpoint = isRecording ? '/recording/stop' : '/recording/start';

    try {
        const response = await fetch(`${RECORDING_API}${endpoint}`, {
            method: 'POST',
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.success) {
            isRecording = data.enabled;
            updateRecordingUI();
            addFeedEntry('TOGGLE', isRecording ? 'Recording STARTED' : 'Recording STOPPED',
                isRecording ? 'var(--ctp-green)' : 'var(--ctp-red)');
        } else {
            addFeedEntry('ERROR', data.error || 'Toggle failed', 'var(--ctp-red)');
        }
    } catch (e) {
        console.error('[Recording Control] Failed to toggle:', e);

        // Only mark service unavailable for network/connection errors
        const isNetworkError = e.name === 'TypeError' || e.message.includes('fetch');
        if (isNetworkError) {
            serviceAvailable = false;
            updateServiceUnavailable();
        }

        // Provide specific error message
        const errorMsg = isNetworkError
            ? 'Recording service not reachable (port 9010)'
            : `Toggle failed: ${e.message}`;
        addFeedEntry('ERROR', errorMsg, 'var(--ctp-red)');
    }
};

/**
 * Clear recent games display
 */
window.clearRecent = function() {
    recentGames = [];
    updateRecentList();
};

/**
 * Update recording status display
 */
function updateRecordingStatus(data) {
    if (!data || typeof data !== 'object') return;

    isRecording = Boolean(data.enabled);
    updateRecordingUI();

    if (elements.statusMeta && data.session_start) {
        try {
            const startTime = new Date(data.session_start);
            if (!isNaN(startTime.getTime())) {
                elements.statusMeta.textContent = `Since: ${startTime.toISOString().replace('T', ' ').slice(0, 19)} UTC`;
            }
        } catch (e) {
            console.warn('[Recording Control] Invalid session_start:', data.session_start);
        }
    }

    if (elements.lastRug && typeof data.last_rug_multiplier === 'number') {
        elements.lastRug.textContent = `${data.last_rug_multiplier.toFixed(2)}x`;
    }
}

/**
 * Update recording UI based on state
 */
function updateRecordingUI() {
    if (isRecording) {
        elements.statusDot.className = 'status-dot recording';
        elements.statusLabel.className = 'status-label recording';
        elements.statusLabel.textContent = 'RECORDING';
        elements.toggleBtn.className = 'toggle-btn stop';
        elements.toggleBtn.textContent = 'STOP';
        elements.toggleBtn.disabled = false;
    } else {
        elements.statusDot.className = 'status-dot stopped';
        elements.statusLabel.className = 'status-label stopped';
        elements.statusLabel.textContent = 'STOPPED';
        elements.toggleBtn.className = 'toggle-btn start';
        elements.toggleBtn.textContent = 'START';
        elements.toggleBtn.disabled = false;
    }
}

/**
 * Update UI when recording service is unavailable
 */
function updateServiceUnavailable() {
    elements.statusDot.className = 'status-dot error';
    elements.statusLabel.className = 'status-label error';
    elements.statusLabel.textContent = 'SERVICE UNAVAILABLE';
    elements.toggleBtn.className = 'toggle-btn disabled';
    elements.toggleBtn.textContent = 'START SERVICE';
    elements.toggleBtn.disabled = true;

    if (elements.statusMeta) {
        elements.statusMeta.textContent = 'Recording service (port 9010) not running';
    }
}

/**
 * Update stats display
 */
function updateStats(data) {
    if (!data || typeof data !== 'object') return;

    // Safely update game counts with null checks
    if (elements.sessionGames) {
        elements.sessionGames.textContent = formatNumber(data.session ?? 0);
    }
    if (elements.todayGames) {
        elements.todayGames.textContent = formatNumber(data.today ?? 0);
    }
    if (elements.totalGames) {
        elements.totalGames.textContent = formatNumber(data.total ?? 0);
    }

    // Update storage display
    if (data.storage && typeof data.storage === 'object') {
        const usedMB = data.storage.total_size_mb ?? 0;
        // Get max from API response or use default
        const maxGB = data.storage.max_size_gb ?? 50;
        const percentage = maxGB > 0 ? (usedMB / 1024 / maxGB) * 100 : 0;

        if (elements.storageFill) {
            elements.storageFill.style.width = `${Math.min(percentage, 100)}%`;

            // Also update the storage info text
            const storageInfo = elements.storageFill.closest('.storage-info')?.querySelector('.font-mono');
            if (storageInfo) {
                storageInfo.textContent = `${usedMB.toFixed(1)} MB / ${maxGB} GB`;
            }
        }
    }
}

/**
 * Update recent games list
 */
function updateRecentList() {
    if (!elements.recentList) return;

    if (!Array.isArray(recentGames) || recentGames.length === 0) {
        elements.recentList.innerHTML = `
            <div style="padding: var(--space-md); color: var(--color-text-muted); text-align: center;">
                No recent captures
            </div>
        `;
        return;
    }

    elements.recentList.innerHTML = recentGames.map(game => {
        if (!game || typeof game !== 'object') return '';

        const gameId = game.game_id || 'unknown';
        // Try multiple field names for ticks (API may use different names)
        const ticks = game.tick_count ?? game.duration_ticks ?? game.ticks ?? game.total_ticks ?? 0;
        const price = game.final_price ?? game.rug_price ?? 0;

        // Safe date parsing with fallback
        let time = '--:--';
        if (game.captured_at) {
            try {
                const capturedDate = new Date(game.captured_at);
                if (!isNaN(capturedDate.getTime())) {
                    time = capturedDate.toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                    });
                }
            } catch (e) {
                console.warn('[Recording Control] Invalid captured_at:', game.captured_at);
            }
        }

        const multiplierClass = price >= 5 ? 'high' : price >= 2 ? 'mid' : 'low';
        // Sanitize gameId to prevent XSS
        const safeGameId = String(gameId).replace(/[<>&"']/g, '');

        return `
            <div class="game-row">
                <span class="game-id">${safeGameId.slice(0, 20)}...</span>
                <span class="ticks">${ticks} ticks</span>
                <span class="multiplier ${multiplierClass}">${Number(price).toFixed(2)}x</span>
                <span class="time">${time}</span>
            </div>
        `;
    }).filter(Boolean).join('');
}

/**
 * Update connection status display
 */
function updateConnectionStatus(connected) {
    if (elements.connectionDot) {
        elements.connectionDot.className = `connection-dot ${connected ? 'connected' : 'disconnected'}`;
    }
    if (elements.connectionStatus) {
        elements.connectionStatus.textContent = connected ? FOUNDATION_WS : 'Disconnected';
    }
}

/**
 * Update health display
 */
function updateHealthDisplay(data) {
    if (!data || typeof data !== 'object') return;

    console.log('[Recording Control] updateHealthDisplay:', data, {
        containerStatus: !!elements.containerStatus,
        uptime: !!elements.uptime,
        memory: !!elements.memory,
        lastError: !!elements.lastError
    });

    if (elements.containerStatus) {
        const isHealthy = data.status === 'healthy';
        elements.containerStatus.textContent = isHealthy ? 'Running' : 'Error';
        elements.containerStatus.style.color = isHealthy ? 'var(--ctp-green)' : 'var(--ctp-red)';
    }

    if (elements.uptime && typeof data.uptime_seconds === 'number') {
        const hours = Math.floor(data.uptime_seconds / 3600);
        const minutes = Math.floor((data.uptime_seconds % 3600) / 60);
        elements.uptime.textContent = `${hours}h ${minutes}m`;
    }

    if (elements.memory && data.memory_mb != null) {
        elements.memory.textContent = `${data.memory_mb} MB`;
    }

    // Bug #2 fix: Display last error
    if (elements.lastError) {
        elements.lastError.textContent = data.last_error || 'None';
        elements.lastError.style.color = data.last_error ? 'var(--ctp-red)' : 'var(--ctp-text)';
    }
}

/**
 * Add entry to live feed
 */
function addFeedEntry(eventType, data, color = null) {
    console.log('[Recording Control] addFeedEntry:', eventType, data);
    const now = new Date();
    const timestamp = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });

    // XSS protection: validate color value
    let safeColor = null;
    if (color && VALID_COLOR_PATTERN.test(color)) {
        safeColor = color;
    } else if (color) {
        console.warn('[Recording Control] Invalid color rejected:', color);
    }

    feedEntries.unshift({ timestamp, eventType, data, color: safeColor });

    // Limit feed size
    if (feedEntries.length > MAX_FEED_ENTRIES) {
        feedEntries = feedEntries.slice(0, MAX_FEED_ENTRIES);
    }

    // Debounced feed display update
    if (feedUpdateTimeout) {
        clearTimeout(feedUpdateTimeout);
    }
    feedUpdateTimeout = setTimeout(updateFeedDisplay, FEED_DEBOUNCE_MS);
}

/**
 * Update feed display
 */
function updateFeedDisplay() {
    if (!elements.feedList) {
        console.warn('[Recording Control] feedList element not found!');
        return;
    }

    // Sanitize data for display (escape HTML entities)
    const escapeHtml = (str) => {
        if (typeof str !== 'string') return String(str);
        return str.replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[char]));
    };

    elements.feedList.innerHTML = feedEntries.slice(0, 20).map(entry => {
        // Color is pre-validated in addFeedEntry, safe to use
        const dataStyle = entry.color ? `style="color: ${entry.color}"` : '';
        const safeTimestamp = escapeHtml(entry.timestamp);
        const safeEventType = escapeHtml(entry.eventType);
        const safeData = escapeHtml(entry.data);

        return `
            <div class="feed-entry">
                <span class="timestamp">${safeTimestamp}</span>
                <span class="event-type">${safeEventType}</span>
                <span class="event-data" ${dataStyle}>${safeData}</span>
            </div>
        `;
    }).join('');
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    return num.toLocaleString();
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
