/**
 * Foundation State Manager
 *
 * Provides a centralized, read-only state store for Foundation events.
 * Artifacts subscribe to state changes instead of managing their own state.
 *
 * Design Principles:
 * - Immutable external API (Object.freeze on public interface)
 * - Deep copy on getState() to prevent mutation
 * - Subscription pattern with unsubscribe cleanup
 * - Internal updates only via _processMessage()
 *
 * Usage:
 *   import { FoundationState } from '/shared/foundation-state.js';
 *
 *   // Read current values (fast, no copy)
 *   const price = FoundationState.getPrice();
 *   const tick = FoundationState.getTick();
 *
 *   // Subscribe to updates
 *   const unsub = FoundationState.subscribe('game.tick', (data, eventType, fullState) => {
 *       console.log('New tick:', data.tickCount);
 *   });
 *
 *   // Cleanup on unload
 *   window.addEventListener('beforeunload', unsub);
 */

const FoundationState = (function () {
    'use strict';

    // =========================================================================
    // Internal State (private)
    // =========================================================================

    const _state = {
        game: {
            active: false,
            rugged: false,
            price: 1.0,
            tickCount: 0,
            phase: 'UNKNOWN',
            cooldownTimer: 0,
            allowPreRoundBuys: false,
            tradeCount: 0,
            gameId: null,
            leaderboard: null,
            gameHistory: null,
        },
        user: {
            cash: 0,
            positionQty: 0,
            avgCost: 0,
            totalInvested: 0,
            cumulativePnL: 0,
            username: null,
            playerId: null,
            isAuthenticated: false,
        },
        connection: {
            connected: false,
            lastEventTime: null,
            eventCount: 0,
        },
    };

    // Subscribers map: eventType -> Set<callback>
    const _subscribers = new Map();

    // =========================================================================
    // Deep Clone Utility
    // =========================================================================

    function _deepClone(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        if (Array.isArray(obj)) {
            return obj.map(_deepClone);
        }
        const clone = {};
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                clone[key] = _deepClone(obj[key]);
            }
        }
        return clone;
    }

    function _deepFreeze(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        Object.freeze(obj);
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                _deepFreeze(obj[key]);
            }
        }
        return obj;
    }

    // =========================================================================
    // State Update Handlers (internal)
    // =========================================================================

    function _updateGameState(data) {
        _state.game.active = data.active ?? _state.game.active;
        _state.game.rugged = data.rugged ?? _state.game.rugged;
        _state.game.price = data.price ?? _state.game.price;
        _state.game.tickCount = data.tickCount ?? _state.game.tickCount;
        _state.game.phase = data.phase ?? _state.game.phase;
        _state.game.cooldownTimer = data.cooldownTimer ?? _state.game.cooldownTimer;
        _state.game.allowPreRoundBuys = data.allowPreRoundBuys ?? _state.game.allowPreRoundBuys;
        _state.game.tradeCount = data.tradeCount ?? _state.game.tradeCount;

        // Only update if provided (these can be large)
        if (data.leaderboard !== undefined) {
            _state.game.leaderboard = data.leaderboard;
        }
        if (data.gameHistory !== undefined) {
            _state.game.gameHistory = data.gameHistory;
        }
    }

    function _updateUserState(data) {
        _state.user.cash = data.cash ?? _state.user.cash;
        _state.user.positionQty = data.positionQty ?? _state.user.positionQty;
        _state.user.avgCost = data.avgCost ?? _state.user.avgCost;
        _state.user.totalInvested = data.totalInvested ?? _state.user.totalInvested;
        _state.user.cumulativePnL = data.cumulativePnL ?? _state.user.cumulativePnL;
    }

    function _updateAuthState(data) {
        _state.user.username = data.username ?? _state.user.username;
        _state.user.playerId = data.player_id ?? _state.user.playerId;
        _state.user.isAuthenticated = true;
    }

    function _updateConnectionState(connected) {
        _state.connection.connected = connected;
    }

    // =========================================================================
    // Subscriber Notification
    // =========================================================================

    function _notifySubscribers(eventType, data) {
        // Get frozen state snapshot for subscribers
        const stateSnapshot = _deepFreeze(_deepClone(_state));

        // Notify specific event subscribers
        if (_subscribers.has(eventType)) {
            for (const callback of _subscribers.get(eventType)) {
                try {
                    callback(data, eventType, stateSnapshot);
                } catch (err) {
                    console.error(`[FoundationState] Error in subscriber for ${eventType}:`, err);
                }
            }
        }

        // Notify wildcard subscribers
        if (_subscribers.has('*')) {
            for (const callback of _subscribers.get('*')) {
                try {
                    callback(data, eventType, stateSnapshot);
                } catch (err) {
                    console.error('[FoundationState] Error in wildcard subscriber:', err);
                }
            }
        }
    }

    // =========================================================================
    // Internal API (for foundation-ws-client.js)
    // =========================================================================

    /**
     * Process an incoming message from Foundation WebSocket.
     * INTERNAL USE ONLY - called by foundation-ws-client.js
     *
     * @param {string} eventType - The event type (e.g., 'game.tick')
     * @param {Object} data - The event data
     * @param {string|null} gameId - The game ID
     */
    function _processMessage(eventType, data, gameId) {
        // Update connection metrics
        _state.connection.lastEventTime = Date.now();
        _state.connection.eventCount++;

        // Update game ID if provided
        if (gameId) {
            _state.game.gameId = gameId;
        }

        // Route to appropriate handler
        switch (eventType) {
            case 'game.tick':
                _updateGameState(data);
                break;
            case 'player.state':
                _updateUserState(data);
                break;
            case 'connection.authenticated':
                _updateAuthState(data);
                break;
            case 'connection':
                _updateConnectionState(data.connected);
                break;
            // Other events don't update state but still notify subscribers
        }

        // Notify all subscribers
        _notifySubscribers(eventType, data);
    }

    // =========================================================================
    // Public API
    // =========================================================================

    const publicAPI = {
        // -----------------------------------------------------------------
        // Fast Read-Only Getters (no copy, direct access)
        // -----------------------------------------------------------------

        /**
         * Get current tick count.
         * @returns {number}
         */
        getTick() {
            return _state.game.tickCount;
        },

        /**
         * Get current price.
         * @returns {number}
         */
        getPrice() {
            return _state.game.price;
        },

        /**
         * Get current game phase.
         * @returns {string} 'COOLDOWN'|'PRESALE'|'ACTIVE'|'RUGGED'|'UNKNOWN'
         */
        getPhase() {
            return _state.game.phase;
        },

        /**
         * Get current game ID.
         * @returns {string|null}
         */
        getGameId() {
            return _state.game.gameId;
        },

        /**
         * Get user's SOL balance.
         * @returns {number}
         */
        getBalance() {
            return _state.user.cash;
        },

        /**
         * Get user's token position quantity.
         * @returns {number}
         */
        getPositionQty() {
            return _state.user.positionQty;
        },

        /**
         * Get user's average cost basis.
         * @returns {number}
         */
        getAvgCost() {
            return _state.user.avgCost;
        },

        /**
         * Get user's player ID.
         * @returns {string|null}
         */
        getUserId() {
            return _state.user.playerId;
        },

        /**
         * Get user's display name.
         * @returns {string|null}
         */
        getUsername() {
            return _state.user.username;
        },

        /**
         * Check if connected to Foundation.
         * @returns {boolean}
         */
        isConnected() {
            return _state.connection.connected;
        },

        /**
         * Check if user is authenticated.
         * @returns {boolean}
         */
        isAuthenticated() {
            return _state.user.isAuthenticated;
        },

        /**
         * Check if game is active.
         * @returns {boolean}
         */
        isGameActive() {
            return _state.game.active && !_state.game.rugged;
        },

        // -----------------------------------------------------------------
        // Full State Access (deep copy, use sparingly)
        // -----------------------------------------------------------------

        /**
         * Get full state snapshot (deep frozen copy).
         * Use sparingly - prefer individual getters for performance.
         * @returns {Object}
         */
        getState() {
            return _deepFreeze(_deepClone(_state));
        },

        /**
         * Get game state snapshot.
         * @returns {Object}
         */
        getGameState() {
            return _deepFreeze(_deepClone(_state.game));
        },

        /**
         * Get user state snapshot.
         * @returns {Object}
         */
        getUserState() {
            return _deepFreeze(_deepClone(_state.user));
        },

        // -----------------------------------------------------------------
        // Subscriptions
        // -----------------------------------------------------------------

        /**
         * Subscribe to state changes.
         *
         * @param {string} eventType - Event type to subscribe to, or '*' for all
         * @param {Function} callback - Called with (data, eventType, fullState)
         * @returns {Function} Unsubscribe function
         *
         * @example
         * const unsub = FoundationState.subscribe('game.tick', (data, type, state) => {
         *     console.log('Price:', data.price, 'Tick:', data.tickCount);
         * });
         *
         * // Later: unsub();
         */
        subscribe(eventType, callback) {
            if (typeof callback !== 'function') {
                throw new Error('Callback must be a function');
            }

            if (!_subscribers.has(eventType)) {
                _subscribers.set(eventType, new Set());
            }
            _subscribers.get(eventType).add(callback);

            // Return unsubscribe function
            return function unsubscribe() {
                if (_subscribers.has(eventType)) {
                    _subscribers.get(eventType).delete(callback);
                }
            };
        },

        /**
         * Get subscriber count for debugging.
         * @param {string} [eventType] - Specific event type, or undefined for total
         * @returns {number}
         */
        getSubscriberCount(eventType) {
            if (eventType) {
                return _subscribers.has(eventType) ? _subscribers.get(eventType).size : 0;
            }
            let total = 0;
            for (const subs of _subscribers.values()) {
                total += subs.size;
            }
            return total;
        },

        // -----------------------------------------------------------------
        // Internal (DO NOT USE IN ARTIFACTS)
        // -----------------------------------------------------------------

        /**
         * @private
         * Process message from foundation-ws-client.js
         * DO NOT CALL FROM ARTIFACTS
         */
        _processMessage,

        /**
         * @private
         * Reset state (for testing only)
         */
        _reset() {
            _state.game = {
                active: false,
                rugged: false,
                price: 1.0,
                tickCount: 0,
                phase: 'UNKNOWN',
                cooldownTimer: 0,
                allowPreRoundBuys: false,
                tradeCount: 0,
                gameId: null,
                leaderboard: null,
                gameHistory: null,
            };
            _state.user = {
                cash: 0,
                positionQty: 0,
                avgCost: 0,
                totalInvested: 0,
                cumulativePnL: 0,
                username: null,
                playerId: null,
                isAuthenticated: false,
            };
            _state.connection = {
                connected: false,
                lastEventTime: null,
                eventCount: 0,
            };
            _subscribers.clear();
        },
    };

    // Freeze the public API to prevent modification
    return Object.freeze(publicAPI);
})();

// Export for ES module usage
export { FoundationState };

// Also support CommonJS
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FoundationState };
}
