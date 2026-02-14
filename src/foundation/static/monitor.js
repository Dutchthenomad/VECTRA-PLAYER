/**
 * Foundation System Monitor - WebSocket Client
 *
 * PURE DISPLAY LAYER - No game logic, just visualization
 * All game-specific decisions belong in subscriber systems
 *
 * MCP-friendly: All state exposed via data-* attributes
 * Console logging: All events logged for CDP access
 */

(function() {
    'use strict';

    // Configuration
    const WS_HOST = window.location.hostname || 'localhost';
    const WS_PORT = 9000;
    const WS_URL = `ws://${WS_HOST}:${WS_PORT}/feed`;
    const MAX_LOG_ENTRIES = 500;
    const RECONNECT_DELAY = 3000;

    // State
    let ws = null;
    let eventCount = 0;
    let lastEventTime = 0;
    let eventsPerSecond = 0;
    let rawEventsCapture = [];

    // DOM Elements (cached)
    const elements = {
        // Connection
        connectionIndicator: document.getElementById('connection-indicator'),
        statusDot: document.getElementById('status-dot'),
        statusText: document.getElementById('status-text'),
        wsUrl: document.getElementById('ws-url'),
        connUsername: document.getElementById('conn-username'),
        connPlayerId: document.getElementById('conn-player-id'),
        connLastEvent: document.getElementById('conn-last-event'),
        connEventsRate: document.getElementById('conn-events-rate'),

        // Game
        gamePhase: document.getElementById('game-phase'),
        gameId: document.getElementById('game-id'),
        gamePrice: document.getElementById('game-price'),
        gameTick: document.getElementById('game-tick'),
        gameCooldown: document.getElementById('game-cooldown'),

        // Player
        playerCash: document.getElementById('player-cash'),
        playerPosition: document.getElementById('player-position'),
        playerAvgCost: document.getElementById('player-avg-cost'),
        playerPnl: document.getElementById('player-pnl'),

        // Event Log
        eventLog: document.getElementById('event-log'),
        eventFilter: document.getElementById('event-filter'),
        btnClearLog: document.getElementById('btn-clear-log'),
        chkAutoscroll: document.getElementById('chk-autoscroll'),

        // Discovery
        chkRawEvents: document.getElementById('chk-raw-events'),
        chkHighlightUnknown: document.getElementById('chk-highlight-unknown'),
        btnExportJsonl: document.getElementById('btn-export-jsonl'),
        discoveryCount: document.getElementById('discovery-count'),
        discoveryLog: document.getElementById('discovery-log'),

        // Footer
        footerSeq: document.getElementById('footer-seq')
    };

    /**
     * Initialize the monitor
     */
    function init() {
        console.log('[Foundation Monitor] Initializing...');
        console.log('[Foundation Monitor] WebSocket URL:', WS_URL);

        elements.wsUrl.textContent = WS_URL;
        elements.wsUrl.dataset.value = WS_URL;

        setupEventListeners();
        connect();
        startRateCalculator();
    }

    /**
     * Setup UI event listeners
     */
    function setupEventListeners() {
        elements.btnClearLog.addEventListener('click', clearEventLog);
        elements.btnExportJsonl.addEventListener('click', exportJsonl);
        elements.eventFilter.addEventListener('change', function() {
            console.log('[Foundation Monitor] Filter changed:', this.value);
        });
    }

    /**
     * Connect to Foundation WebSocket
     */
    function connect() {
        console.log('[Foundation Monitor] Connecting to', WS_URL);
        setConnectionStatus('connecting');

        try {
            ws = new WebSocket(WS_URL);
        } catch (e) {
            console.error('[Foundation Monitor] WebSocket creation failed:', e);
            setConnectionStatus('disconnected');
            scheduleReconnect();
            return;
        }

        ws.onopen = function() {
            console.log('[Foundation Monitor] WebSocket connected');
            setConnectionStatus('connected');
        };

        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleEvent(data);
            } catch (e) {
                console.error('[Foundation Monitor] Parse error:', e, event.data);
            }
        };

        ws.onerror = function(error) {
            console.error('[Foundation Monitor] WebSocket error:', error);
        };

        ws.onclose = function(event) {
            console.log('[Foundation Monitor] WebSocket closed. Code:', event.code, 'Reason:', event.reason);
            setConnectionStatus('disconnected');
            scheduleReconnect();
        };
    }

    /**
     * Schedule reconnection
     */
    function scheduleReconnect() {
        console.log('[Foundation Monitor] Reconnecting in', RECONNECT_DELAY, 'ms...');
        setTimeout(connect, RECONNECT_DELAY);
    }

    /**
     * Handle incoming event from Foundation
     * PURE DISPLAY - just update UI, no game logic
     */
    function handleEvent(event) {
        eventCount++;
        lastEventTime = Date.now();

        // Log to console for CDP access
        console.log('[Foundation Event]', event.type, event);

        // Update sequence number
        updateElement(elements.footerSeq, event.seq);

        // Update last event time
        updateElement(elements.connLastEvent, formatTime(new Date()));

        // Route by event type - DISPLAY ONLY
        switch (event.type) {
            case 'game.tick':
                displayGameState(event.data);
                break;
            case 'player.state':
                displayPlayerState(event.data);
                break;
            case 'connection.authenticated':
                displayAuthState(event.data);
                setConnectionStatus('authenticated');
                break;
            case 'connection.status':
                displayConnectionStatus(event.data);
                break;
        }

        // Add to event log
        addToEventLog(event);

        // Protocol discovery capture
        if (elements.chkRawEvents.checked) {
            captureRawEvent(event);
        }
    }

    /**
     * Display game state - PURE DISPLAY
     */
    function displayGameState(data) {
        updateElement(elements.gamePhase, data.phase || '-');
        updateElement(elements.gameId, data.gameId || '-');
        updateElement(elements.gamePrice, data.price ? formatPrice(data.price) : '-');
        updateElement(elements.gameTick, data.tickCount ?? '-');

        // Cooldown display
        if (data.cooldownTimer && data.cooldownTimer > 0) {
            updateElement(elements.gameCooldown, formatCooldown(data.cooldownTimer));
        } else {
            updateElement(elements.gameCooldown, '0s');
        }
    }

    /**
     * Display player state - PURE DISPLAY
     */
    function displayPlayerState(data) {
        updateElement(elements.playerCash, data.cash ? formatCash(data.cash) : '-');
        updateElement(elements.playerPosition, data.positionQty ? formatQty(data.positionQty) : '-');
        updateElement(elements.playerAvgCost, data.avgCost ? formatCash(data.avgCost) : '-');

        // PnL with color
        if (data.cumulativePnL !== undefined) {
            const pnl = data.cumulativePnL;
            const formatted = (pnl >= 0 ? '+' : '') + formatPnl(pnl);
            updateElement(elements.playerPnl, formatted);
            elements.playerPnl.classList.toggle('positive', pnl > 0);
            elements.playerPnl.classList.toggle('negative', pnl < 0);
        }
    }

    /**
     * Display authentication state
     */
    function displayAuthState(data) {
        updateElement(elements.connUsername, data.username || '-');
        updateElement(elements.connPlayerId, data.player_id || '-');
    }

    /**
     * Display connection status changes
     */
    function displayConnectionStatus(data) {
        if (data.state) {
            setConnectionStatus(data.state.toLowerCase());
        }
        if (data.username) {
            updateElement(elements.connUsername, data.username);
        }
        if (data.playerId) {
            updateElement(elements.connPlayerId, data.playerId);
        }
    }

    /**
     * Set connection status (updates indicator)
     */
    function setConnectionStatus(status) {
        elements.connectionIndicator.dataset.status = status;
        elements.statusText.textContent = status.toUpperCase();
        elements.statusText.dataset.value = status.toUpperCase();
    }

    /**
     * Update element text and data-value
     */
    function updateElement(el, value) {
        if (el) {
            el.textContent = value;
            el.dataset.value = value;
        }
    }

    /**
     * Add event to log panel
     */
    function addToEventLog(event) {
        const filter = elements.eventFilter.value;

        // Apply filter
        if (filter) {
            if (filter === 'connection') {
                if (!event.type.startsWith('connection')) return;
            } else if (event.type !== filter) {
                return;
            }
        }

        const entry = document.createElement('div');
        entry.className = 'log-entry';

        const tsSpan = document.createElement('span');
        tsSpan.className = 'timestamp';
        tsSpan.textContent = formatTime(new Date(event.ts));

        const typeSpan = document.createElement('span');
        typeSpan.className = 'type';
        typeSpan.textContent = event.type;

        const dataSpan = document.createElement('span');
        dataSpan.className = 'data';
        dataSpan.textContent = formatLogData(event.data);

        entry.append(tsSpan, typeSpan, dataSpan);

        elements.eventLog.appendChild(entry);

        // Limit entries
        while (elements.eventLog.children.length > MAX_LOG_ENTRIES) {
            elements.eventLog.removeChild(elements.eventLog.firstChild);
        }

        // Auto-scroll
        if (elements.chkAutoscroll.checked) {
            elements.eventLog.scrollTop = elements.eventLog.scrollHeight;
        }
    }

    /**
     * Format log data for display
     */
    function formatLogData(data) {
        if (!data) return '';

        // Show key fields inline
        const parts = [];
        if (data.price !== undefined) parts.push(`<span class="key">price:</span> <span class="value">${formatPrice(data.price)}</span>`);
        if (data.phase !== undefined) parts.push(`<span class="key">phase:</span> <span class="value">${data.phase}</span>`);
        if (data.tickCount !== undefined) parts.push(`<span class="key">tick:</span> <span class="value">${data.tickCount}</span>`);
        if (data.cash !== undefined) parts.push(`<span class="key">cash:</span> <span class="value">${formatCash(data.cash)}</span>`);
        if (data.username !== undefined) parts.push(`<span class="key">user:</span> <span class="value">${data.username}</span>`);

        if (parts.length > 0) {
            return '{' + parts.join(', ') + '}';
        }

        // Fallback to truncated JSON
        const json = JSON.stringify(data);
        return json.length > 80 ? json.slice(0, 80) + '...' : json;
    }

    /**
     * Clear event log
     */
    function clearEventLog() {
        elements.eventLog.innerHTML = '';
        console.log('[Foundation Monitor] Event log cleared');
    }

    /**
     * Capture raw event for protocol discovery
     */
    function captureRawEvent(event) {
        rawEventsCapture.push({
            captured_at: Date.now(),
            event: event
        });

        updateElement(elements.discoveryCount, rawEventsCapture.length);

        // Add to discovery log
        const entry = document.createElement('div');
        entry.className = 'log-entry';

        const tsSpan = document.createElement('span');
        tsSpan.className = 'timestamp';
        tsSpan.textContent = formatTime(new Date());

        const typeSpan = document.createElement('span');
        typeSpan.className = 'type';
        typeSpan.textContent = event.type;

        const dataSpan = document.createElement('span');
        dataSpan.className = 'data';
        dataSpan.textContent = JSON.stringify(event.data);

        entry.append(tsSpan, typeSpan, dataSpan);

        elements.discoveryLog.appendChild(entry);

        // Limit
        while (elements.discoveryLog.children.length > 100) {
            elements.discoveryLog.removeChild(elements.discoveryLog.firstChild);
        }

        // Auto-scroll discovery log
        elements.discoveryLog.scrollTop = elements.discoveryLog.scrollHeight;
    }

    /**
     * Export captured events as JSONL
     */
    function exportJsonl() {
        if (rawEventsCapture.length === 0) {
            alert('No events captured. Enable "Raw Capture" first.');
            return;
        }

        const jsonl = rawEventsCapture.map(e => JSON.stringify(e)).join('\n');
        const blob = new Blob([jsonl], { type: 'application/x-jsonlines' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `foundation-events-${Date.now()}.jsonl`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        URL.revokeObjectURL(url);
        console.log('[Foundation Monitor] Exported', rawEventsCapture.length, 'events');
    }

    /**
     * Calculate events per second
     */
    function startRateCalculator() {
        let lastCount = 0;
        setInterval(function() {
            eventsPerSecond = eventCount - lastCount;
            lastCount = eventCount;
            updateElement(elements.connEventsRate, eventsPerSecond);
        }, 1000);
    }

    // Formatters
    function formatTime(date) {
        return date.toLocaleTimeString('en-US', { hour12: false });
    }

    function formatPrice(price) {
        return Number(price).toFixed(3);
    }

    function formatCash(cash) {
        return Number(cash).toFixed(3) + ' CASH';
    }

    function formatQty(qty) {
        return Number(qty).toFixed(3) + ' RUGS';
    }

    function formatPnl(pnl) {
        return Number(pnl).toFixed(4);
    }

    function formatCooldown(ms) {
        return Math.ceil(ms / 1000) + 's';
    }

    // Start when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
