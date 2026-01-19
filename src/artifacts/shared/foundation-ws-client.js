/**
 * Foundation WebSocket Client
 *
 * Connects to Foundation Service (ws://localhost:9000/feed) and provides
 * a unified event interface for HTML artifacts.
 *
 * Event Types (from Foundation normalizer):
 * - game.tick: Price/tick stream from gameStateUpdate
 * - player.state: Balance/position from playerUpdate
 * - connection.authenticated: Auth confirmation from usernameStatus
 * - player.trade: Trade events from standard/newTrade
 * - sidebet.placed: Sidebet placed from currentSidebet
 * - sidebet.result: Sidebet outcome from currentSidebetResult
 *
 * Usage:
 *   const client = new FoundationWSClient();
 *   client.on('game.tick', (data) => console.log(data));
 *   client.connect();
 */

class FoundationWSClient {
    /**
     * Create a new Foundation WebSocket client.
     * @param {Object} options - Configuration options
     * @param {string} [options.url='ws://localhost:9000/feed'] - WebSocket URL
     * @param {number} [options.reconnectDelay=1000] - Initial reconnect delay (ms)
     * @param {number} [options.maxReconnectDelay=30000] - Max reconnect delay (ms)
     * @param {number} [options.reconnectMultiplier=1.5] - Backoff multiplier
     */
    constructor(options = {}) {
        this.url = options.url || 'ws://localhost:9000/feed';
        this.reconnectDelay = options.reconnectDelay || 1000;
        this.maxReconnectDelay = options.maxReconnectDelay || 30000;
        this.reconnectMultiplier = options.reconnectMultiplier || 1.5;

        this.ws = null;
        this.listeners = new Map();
        this.currentReconnectDelay = this.reconnectDelay;
        this.reconnectTimer = null;
        this.isConnecting = false;
        this.intentionalClose = false;

        // Metrics
        this.metrics = {
            connected: false,
            messageCount: 0,
            lastMessageTime: null,
            connectionAttempts: 0,
            lastConnectedTime: null,
            latencies: []
        };

        // Buffer recent events for new subscribers
        this.recentEvents = new Map();
        this.maxBufferSize = 10;
    }

    /**
     * Connect to the Foundation Service.
     * @returns {Promise<void>} Resolves when connected
     */
    connect() {
        return new Promise((resolve, reject) => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                resolve();
                return;
            }

            if (this.isConnecting) {
                // Already connecting, wait for result
                this.once('_connected', () => resolve());
                this.once('_error', (err) => reject(err));
                return;
            }

            this.isConnecting = true;
            this.intentionalClose = false;
            this.metrics.connectionAttempts++;

            console.log(`[Foundation] Connecting to ${this.url}...`);

            try {
                this.ws = new WebSocket(this.url);
            } catch (err) {
                this.isConnecting = false;
                reject(err);
                return;
            }

            this.ws.onopen = () => {
                this.isConnecting = false;
                this.currentReconnectDelay = this.reconnectDelay;
                this.metrics.connected = true;
                this.metrics.lastConnectedTime = Date.now();

                console.log('[Foundation] Connected');
                this.emit('connection', { connected: true });
                this.emit('_connected');
                resolve();
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (err) {
                    console.error('[Foundation] Failed to parse message:', err);
                }
            };

            this.ws.onerror = (err) => {
                console.error('[Foundation] WebSocket error:', err);
                this.emit('error', err);
                if (this.isConnecting) {
                    this.isConnecting = false;
                    this.emit('_error', err);
                    reject(err);
                }
            };

            this.ws.onclose = (event) => {
                this.metrics.connected = false;
                console.log(`[Foundation] Disconnected (code: ${event.code})`);
                this.emit('connection', { connected: false, code: event.code });

                if (!this.intentionalClose) {
                    this.scheduleReconnect();
                }
            };
        });
    }

    /**
     * Handle incoming message from Foundation Service.
     * @param {Object} message - Parsed JSON message
     */
    handleMessage(message) {
        const { type, ts, gameId, seq, data } = message;

        this.metrics.messageCount++;
        this.metrics.lastMessageTime = Date.now();

        // Calculate latency if timestamp available
        if (ts) {
            const latency = Date.now() - ts;
            this.metrics.latencies.push(latency);
            if (this.metrics.latencies.length > 100) {
                this.metrics.latencies.shift();
            }
        }

        // Store in buffer for new subscribers
        if (!this.recentEvents.has(type)) {
            this.recentEvents.set(type, []);
        }
        const buffer = this.recentEvents.get(type);
        buffer.push({ type, ts, gameId, seq, data });
        if (buffer.length > this.maxBufferSize) {
            buffer.shift();
        }

        // Emit to listeners
        this.emit(type, { type, ts, gameId, seq, data });
        this.emit('*', { type, ts, gameId, seq, data });
    }

    /**
     * Schedule a reconnection attempt with exponential backoff.
     */
    scheduleReconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }

        console.log(`[Foundation] Reconnecting in ${this.currentReconnectDelay}ms...`);

        this.reconnectTimer = setTimeout(() => {
            this.connect().catch((err) => {
                console.error('[Foundation] Reconnect failed:', err);
            });
        }, this.currentReconnectDelay);

        // Increase delay for next attempt (exponential backoff)
        this.currentReconnectDelay = Math.min(
            this.currentReconnectDelay * this.reconnectMultiplier,
            this.maxReconnectDelay
        );
    }

    /**
     * Disconnect from the Foundation Service.
     */
    disconnect() {
        this.intentionalClose = true;

        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        this.metrics.connected = false;
    }

    /**
     * Register an event listener.
     * @param {string} event - Event type (e.g., 'game.tick', 'player.state', '*')
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);

        // Return unsubscribe function
        return () => this.off(event, callback);
    }

    /**
     * Register a one-time event listener.
     * @param {string} event - Event type
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    once(event, callback) {
        const wrapper = (data) => {
            this.off(event, wrapper);
            callback(data);
        };
        return this.on(event, wrapper);
    }

    /**
     * Remove an event listener.
     * @param {string} event - Event type
     * @param {Function} callback - Callback function
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }

    /**
     * Emit an event to all listeners.
     * @param {string} event - Event type
     * @param {*} data - Event data
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            for (const callback of this.listeners.get(event)) {
                try {
                    callback(data);
                } catch (err) {
                    console.error(`[Foundation] Error in listener for ${event}:`, err);
                }
            }
        }
    }

    /**
     * Get current connection status.
     * @returns {boolean}
     */
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    /**
     * Get client metrics.
     * @returns {Object}
     */
    getMetrics() {
        const latencies = this.metrics.latencies;
        const avgLatency = latencies.length > 0
            ? latencies.reduce((a, b) => a + b, 0) / latencies.length
            : 0;

        return {
            ...this.metrics,
            averageLatency: avgLatency,
            latencyCount: latencies.length
        };
    }

    /**
     * Get recent events of a specific type (for late subscribers).
     * @param {string} type - Event type
     * @returns {Array}
     */
    getRecentEvents(type) {
        return this.recentEvents.get(type) || [];
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FoundationWSClient };
}
