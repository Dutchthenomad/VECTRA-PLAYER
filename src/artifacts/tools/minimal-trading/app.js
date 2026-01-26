/**
 * Minimal Trading App
 *
 * HTML port of Tkinter MinimalWindow for RL training data collection.
 * Uses FoundationWSClient for WebSocket connectivity (REQUIRED).
 *
 * See: docs/specs/MINIMAL-UI-SPEC.md for complete specification.
 */

/**
 * Trade Executor - Calls Foundation HTTP API for browser automation
 *
 * Executes trades by sending HTTP requests to Foundation (port 9001)
 * which clicks the corresponding buttons in the rugs.fun browser.
 */
class TradeExecutor {
  constructor(baseUrl = 'http://localhost:9001') {
    this.baseUrl = baseUrl;
    this.pendingRequest = null;
  }

  /**
   * Execute BUY action
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async buy() {
    return this._post('/api/trade/buy');
  }

  /**
   * Execute SELL action
   * @param {number} [percentage] - Optional sell percentage (0.1, 0.25, 0.5, 1.0)
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async sell(percentage = null) {
    return this._post('/api/trade/sell', percentage ? { percentage } : {});
  }

  /**
   * Execute SIDEBET action
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async sidebet() {
    return this._post('/api/trade/sidebet');
  }

  /**
   * Click increment button (+0.001, +0.01, +0.1, +1)
   * @param {number} amount - Amount to increment (0.001, 0.01, 0.1, 1)
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async increment(amount) {
    return this._post('/api/trade/increment', { amount });
  }

  /**
   * Click percentage button (10%, 25%, 50%, 100%)
   * @param {number} pct - Percentage value (10, 25, 50, 100)
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async percentage(pct) {
    return this._post('/api/trade/percentage', { pct });
  }

  /**
   * Click clear (X) button
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async clear() {
    return this._post('/api/trade/clear');
  }

  /**
   * Click half (1/2) button
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async half() {
    return this._post('/api/trade/half');
  }

  /**
   * Click double (X2) button
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async double() {
    return this._post('/api/trade/double');
  }

  /**
   * Click MAX button
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async max() {
    return this._post('/api/trade/max');
  }

  /**
   * Internal POST helper
   * @private
   */
  async _post(path, data = {}) {
    try {
      const response = await fetch(this.baseUrl + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result = await response.json();
      return result;
    } catch (error) {
      console.error(`[TradeExecutor] ${path} failed:`, error);
      return { success: false, error: error.message };
    }
  }
}

/**
 * Button ID mapping for ButtonEvent emission
 */
const BUTTON_MAP = {
  // Action buttons
  'BUY': ['BUY', 'action'],
  'SELL': ['SELL', 'action'],
  'SIDEBET': ['SIDEBET', 'action'],

  // Bet adjustment
  'X': ['CLEAR', 'bet_adjust'],
  '+0.001': ['INC_001', 'bet_adjust'],
  '+0.01': ['INC_01', 'bet_adjust'],
  '+0.1': ['INC_10', 'bet_adjust'],
  '+1': ['INC_1', 'bet_adjust'],
  '1/2': ['HALF', 'bet_adjust'],
  'X2': ['DOUBLE', 'bet_adjust'],
  'MAX': ['MAX', 'bet_adjust'],

  // Percentage
  '10%': ['SELL_10', 'percentage'],
  '25%': ['SELL_25', 'percentage'],
  '50%': ['SELL_50', 'percentage'],
  '100%': ['SELL_100', 'percentage']
};

/**
 * Phase enum values
 */
const PHASE = {
  COOLDOWN: 0,
  PRESALE: 1,
  ACTIVE: 2,
  RUGGED: 3
};

/**
 * Sequence tracker for grouping button presses
 */
class SequenceTracker {
  constructor() {
    this.sequenceId = crypto.randomUUID();
    this.sequencePosition = 0;
    this.lastActionTick = 0;
  }

  /**
   * Update sequence state and return tracking info
   * @param {string} buttonCategory - 'action' | 'bet_adjust' | 'percentage'
   * @param {number} currentTick - Current game tick
   * @returns {Object} Sequence tracking fields for ButtonEvent
   */
  update(buttonCategory, currentTick) {
    const ticksSince = currentTick - this.lastActionTick;

    // New sequence if ACTION button or timeout (>50 ticks)
    if (buttonCategory === 'action' || ticksSince > 50) {
      this.sequenceId = crypto.randomUUID();
      this.sequencePosition = 0;
    } else {
      this.sequencePosition++;
    }

    this.lastActionTick = currentTick;

    return {
      sequence_id: this.sequenceId,
      sequence_position: this.sequencePosition,
      ticks_since_last_action: Math.max(0, ticksSince)
    };
  }
}

/**
 * Minimal Trading Application
 *
 * Uses FoundationWSClient for all WebSocket connectivity.
 */
export class MinimalTradingApp {
  /**
   * @param {FoundationWSClient} client - Foundation WebSocket client instance
   */
  constructor(client) {
    this.client = client;
    this.sequenceTracker = new SequenceTracker();

    // Trade executor for browser automation
    this.tradeExecutor = new TradeExecutor();

    // Application state
    this.state = {
      // Game state (from WebSocket game.tick)
      tick: 0,
      price: 1.0,
      phase: 'UNKNOWN',
      gameId: null,

      // Player state (from WebSocket player.state, AUTH required)
      username: '---',
      balance: 0.0,
      positionQty: 0.0,

      // Connection state
      connected: false,
      authenticated: false,

      // UI state (local)
      executionEnabled: false,
      selectedPercentage: 1.0,
      betAmount: '0.000'
    };

    // DOM element references (populated in init)
    this.elements = {};
  }

  /**
   * Initialize the application
   */
  init() {
    this.cacheElements();
    this.bindEventListeners();
    this.subscribeToWebSocket();
    this.client.connect();

    console.log('[MinimalTrading] Initialized');
  }

  /**
   * Cache DOM element references
   */
  cacheElements() {
    this.elements = {
      // Status displays
      tickValue: document.getElementById('tick-value'),
      priceValue: document.getElementById('price-value'),
      phaseValue: document.getElementById('phase-value'),
      userValue: document.getElementById('user-value'),
      balanceValue: document.getElementById('balance-value'),
      connectionDot: document.getElementById('connection-dot'),

      // Buttons
      connectBtn: document.getElementById('connect-btn'),
      executeToggle: document.getElementById('execute-toggle'),
      btnBuy: document.getElementById('btn-buy'),
      btnSidebet: document.getElementById('btn-sidebet'),
      btnSell: document.getElementById('btn-sell'),
      btnClear: document.getElementById('btn-clear'),
      btnHalf: document.getElementById('btn-half'),
      btnDouble: document.getElementById('btn-double'),
      btnMax: document.getElementById('btn-max'),
      betEntry: document.getElementById('bet-entry'),

      // Button groups
      pctButtons: document.querySelectorAll('.pct-btn'),
      incButtons: document.querySelectorAll('.inc-btn')
    };
  }

  /**
   * Bind UI event listeners
   */
  bindEventListeners() {
    // Action buttons
    this.elements.btnBuy.addEventListener('click', () => this.onActionClick('BUY'));
    this.elements.btnSidebet.addEventListener('click', () => this.onActionClick('SIDEBET'));
    this.elements.btnSell.addEventListener('click', () => this.onActionClick('SELL'));

    // Bet adjustment buttons
    this.elements.btnClear.addEventListener('click', () => this.onClearClick());
    this.elements.btnHalf.addEventListener('click', () => this.onUtilityClick('1/2'));
    this.elements.btnDouble.addEventListener('click', () => this.onUtilityClick('X2'));
    this.elements.btnMax.addEventListener('click', () => this.onUtilityClick('MAX'));

    // Increment buttons
    this.elements.incButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const amount = parseFloat(btn.dataset.amount);
        this.onIncrementClick(amount, btn.textContent, btn);
      });
    });

    // Percentage buttons
    this.elements.pctButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const value = parseFloat(btn.dataset.value);
        this.onPercentageClick(value, btn.textContent, btn);
      });
    });

    // Connect button
    this.elements.connectBtn.addEventListener('click', () => this.onConnectClick());

    // Execute toggle
    this.elements.executeToggle.addEventListener('click', () => this.onExecuteToggle());
  }

  /**
   * Subscribe to WebSocket events via FoundationWSClient
   */
  subscribeToWebSocket() {
    // Game tick events
    this.client.on('game.tick', (event) => this.onGameTick(event.data));

    // Player state events (AUTH required)
    this.client.on('player.state', (event) => this.onPlayerState(event.data));

    // Authentication events
    this.client.on('connection.authenticated', (event) => this.onAuthenticated(event.data));

    // Connection state
    this.client.on('connection', (event) => this.onConnectionChange(event));
  }

  // ==========================================
  // WebSocket Event Handlers
  // ==========================================

  /**
   * Handle game.tick event
   * @param {Object} data - Game tick data
   */
  onGameTick(data) {
    this.state.tick = data.tickCount || 0;
    this.state.price = data.price ?? data.multiplier ?? 1.0;
    this.state.phase = this.detectPhase(data);
    this.state.gameId = data.gameId || null;

    this.updateTickDisplay();
    this.updatePriceDisplay();
    this.updatePhaseDisplay();
  }

  /**
   * Handle player.state event
   * @param {Object} data - Player state data
   */
  onPlayerState(data) {
    this.state.balance = data.cash ?? 0.0;
    this.state.positionQty = data.positionQty ?? 0.0;

    // Extract username as fallback if connection.authenticated hasn't fired
    if (this.state.username === '---') {
      const username = data.username || data.name || data.user;
      if (username) {
        this.state.username = username;
        this.state.authenticated = true;
        this.updateUserDisplay();
      }
    }

    this.updateBalanceDisplay();
  }

  /**
   * Handle connection.authenticated event
   * @param {Object} data - Authentication data
   */
  onAuthenticated(data) {
    this.state.username = data.username || '---';
    this.state.authenticated = true;

    this.updateUserDisplay();
  }

  /**
   * Handle connection state change
   * @param {Object} event - Connection event
   */
  onConnectionChange(event) {
    this.state.connected = event.connected;
    this.updateConnectionDisplay();
  }

  // ==========================================
  // Button Click Handlers
  // ==========================================

  /**
   * Handle action button click (BUY, SELL, SIDEBET)
   * @param {string} action - Action name
   */
  async onActionClick(action) {
    this.emitButtonEvent(action);

    // Get the button element for loading state
    const buttonId = action === 'BUY' ? 'btn-buy' :
                     action === 'SELL' ? 'btn-sell' : 'btn-sidebet';
    const button = document.getElementById(buttonId);

    // Set loading state
    this._setButtonLoading(button, true);

    try {
      let result;
      switch (action) {
        case 'BUY':
          result = await this.tradeExecutor.buy();
          break;
        case 'SELL':
          result = await this.tradeExecutor.sell(this.state.selectedPercentage);
          break;
        case 'SIDEBET':
          result = await this.tradeExecutor.sidebet();
          break;
      }

      console.log(`[MinimalTrading] ${action}:`, result);

      // Show feedback
      if (result.success) {
        this._flashButton(button, 'success');
      } else {
        this._flashButton(button, 'error');
        console.error(`[MinimalTrading] ${action} failed:`, result.error);
      }
    } catch (error) {
      console.error(`[MinimalTrading] ${action} error:`, error);
      this._flashButton(button, 'error');
    } finally {
      this._setButtonLoading(button, false);
    }
  }

  /**
   * Handle clear button click
   */
  async onClearClick() {
    this.emitButtonEvent('X');

    const button = this.elements.btnClear;
    this._setButtonLoading(button, true);

    try {
      const result = await this.tradeExecutor.clear();
      console.log('[MinimalTrading] Clear:', result);

      // Update local state
      this.state.betAmount = '0.000';
      this.elements.betEntry.value = '0.000';

      if (result.success) {
        this._flashButton(button, 'success');
      } else {
        this._flashButton(button, 'error');
      }
    } catch (error) {
      console.error('[MinimalTrading] Clear error:', error);
      this._flashButton(button, 'error');
    } finally {
      this._setButtonLoading(button, false);
    }
  }

  /**
   * Handle increment button click
   * @param {number} amount - Amount to add
   * @param {string} buttonText - Button text for event
   * @param {HTMLElement} button - The button element clicked
   */
  async onIncrementClick(amount, buttonText, button) {
    this.emitButtonEvent(buttonText);

    this._setButtonLoading(button, true);

    try {
      const result = await this.tradeExecutor.increment(amount);
      console.log(`[MinimalTrading] Increment ${amount}:`, result);

      // Update local state
      const current = parseFloat(this.state.betAmount) || 0;
      const newAmount = Math.max(0, current + amount);
      this.state.betAmount = newAmount.toFixed(3);
      this.elements.betEntry.value = this.state.betAmount;

      if (result.success) {
        this._flashButton(button, 'success');
      } else {
        this._flashButton(button, 'error');
      }
    } catch (error) {
      console.error(`[MinimalTrading] Increment ${amount} error:`, error);
      this._flashButton(button, 'error');
    } finally {
      this._setButtonLoading(button, false);
    }
  }

  /**
   * Handle utility button click (1/2, X2, MAX)
   * @param {string} buttonText - Button text
   */
  async onUtilityClick(buttonText) {
    this.emitButtonEvent(buttonText);

    // Get the button element
    const buttonId = buttonText === '1/2' ? 'btn-half' :
                     buttonText === 'X2' ? 'btn-double' : 'btn-max';
    const button = document.getElementById(buttonId);

    this._setButtonLoading(button, true);

    try {
      let result;
      switch (buttonText) {
        case '1/2':
          result = await this.tradeExecutor.half();
          break;
        case 'X2':
          result = await this.tradeExecutor.double();
          break;
        case 'MAX':
          result = await this.tradeExecutor.max();
          break;
      }

      console.log(`[MinimalTrading] ${buttonText}:`, result);

      // Update local state
      const current = parseFloat(this.state.betAmount) || 0;
      let newAmount = current;

      switch (buttonText) {
        case '1/2':
          newAmount = current / 2;
          break;
        case 'X2':
          newAmount = current * 2;
          break;
        case 'MAX':
          newAmount = this.state.balance;
          break;
      }

      this.state.betAmount = Math.max(0, newAmount).toFixed(3);
      this.elements.betEntry.value = this.state.betAmount;

      if (result.success) {
        this._flashButton(button, 'success');
      } else {
        this._flashButton(button, 'error');
      }
    } catch (error) {
      console.error(`[MinimalTrading] ${buttonText} error:`, error);
      this._flashButton(button, 'error');
    } finally {
      this._setButtonLoading(button, false);
    }
  }

  /**
   * Handle percentage button click
   * @param {number} value - Percentage value (0.1 - 1.0)
   * @param {string} buttonText - Button text for event
   * @param {HTMLElement} button - The button element clicked
   */
  async onPercentageClick(value, buttonText, button) {
    this.emitButtonEvent(buttonText);

    this._setButtonLoading(button, true);

    try {
      // Convert to percentage (0.1 -> 10, 0.25 -> 25, etc.)
      const pctValue = value * 100;
      const result = await this.tradeExecutor.percentage(pctValue);
      console.log(`[MinimalTrading] Percentage ${buttonText}:`, result);

      // Update state
      this.state.selectedPercentage = value;

      // Calculate bet amount from balance
      if (this.state.balance > 0) {
        const calculatedBet = this.state.balance * value;
        this.state.betAmount = calculatedBet.toFixed(3);
        this.updateBetDisplay();
      }

      // Update UI - radio-button style
      this.elements.pctButtons.forEach(btn => {
        const btnValue = parseFloat(btn.dataset.value);
        if (btnValue === value) {
          btn.classList.add('selected');
        } else {
          btn.classList.remove('selected');
        }
      });

      if (result.success) {
        this._flashButton(button, 'success');
      } else {
        this._flashButton(button, 'error');
      }
    } catch (error) {
      console.error(`[MinimalTrading] Percentage ${buttonText} error:`, error);
      this._flashButton(button, 'error');
    } finally {
      this._setButtonLoading(button, false);
    }
  }

  /**
   * Update bet amount display
   */
  updateBetDisplay() {
    if (this.elements.betEntry) {
      this.elements.betEntry.value = this.state.betAmount;
    }
  }

  /**
   * Handle connect button click
   */
  onConnectClick() {
    if (!this.state.connected) {
      this.client.connect();
    }
  }

  /**
   * Handle execute toggle click
   */
  onExecuteToggle() {
    this.state.executionEnabled = !this.state.executionEnabled;
    this.updateExecuteDisplay();
  }

  // ==========================================
  // Display Update Methods
  // ==========================================

  updateTickDisplay() {
    this.elements.tickValue.textContent = String(this.state.tick).padStart(4, '0');
  }

  updatePriceDisplay() {
    this.elements.priceValue.textContent = this.state.price.toFixed(2);
  }

  updatePhaseDisplay() {
    const phase = this.state.phase;
    this.elements.phaseValue.textContent = phase;

    // Remove all phase classes
    this.elements.phaseValue.classList.remove('active', 'presale', 'cooldown', 'rugged');

    // Add appropriate class
    switch (phase) {
      case 'ACTIVE':
        this.elements.phaseValue.classList.add('active');
        break;
      case 'PRESALE':
        this.elements.phaseValue.classList.add('presale');
        break;
      case 'COOLDOWN':
        this.elements.phaseValue.classList.add('cooldown');
        break;
      case 'RUGGED':
        this.elements.phaseValue.classList.add('rugged');
        break;
    }
  }

  updateUserDisplay() {
    this.elements.userValue.textContent = this.state.username;
  }

  updateBalanceDisplay() {
    this.elements.balanceValue.textContent = `${this.state.balance.toFixed(3)} SOL`;
  }

  updateConnectionDisplay() {
    const connected = this.state.connected;

    if (connected) {
      this.elements.connectionDot.classList.add('connected');
      this.elements.connectBtn.textContent = 'CONNECTED';
      this.elements.connectBtn.classList.add('connected');
      this.elements.connectBtn.disabled = true;
    } else {
      this.elements.connectionDot.classList.remove('connected');
      this.elements.connectBtn.textContent = 'CONNECT';
      this.elements.connectBtn.classList.remove('connected');
      this.elements.connectBtn.disabled = false;
    }
  }

  updateExecuteDisplay() {
    if (this.state.executionEnabled) {
      this.elements.executeToggle.textContent = 'EXECUTE: ON';
      this.elements.executeToggle.classList.add('enabled');
    } else {
      this.elements.executeToggle.textContent = 'EXECUTE: OFF';
      this.elements.executeToggle.classList.remove('enabled');
    }
  }

  // ==========================================
  // Helper Methods
  // ==========================================

  /**
   * Detect game phase from game state data
   * @param {Object} data - Game state data
   * @returns {string} Phase name
   */
  detectPhase(data) {
    if (data.cooldownTimer > 0) return 'COOLDOWN';
    if (data.rugged && !data.active) return 'RUGGED';
    if (data.allowPreRoundBuys) return 'PRESALE';
    if (data.active && !data.rugged) return 'ACTIVE';
    return 'UNKNOWN';
  }

  /**
   * Get numeric phase value for ButtonEvent
   * @param {string} phase - Phase name
   * @returns {number} Phase enum value
   */
  getPhaseValue(phase) {
    switch (phase) {
      case 'COOLDOWN': return PHASE.COOLDOWN;
      case 'PRESALE': return PHASE.PRESALE;
      case 'ACTIVE': return PHASE.ACTIVE;
      case 'RUGGED': return PHASE.RUGGED;
      default: return PHASE.ACTIVE;
    }
  }

  /**
   * Create and emit ButtonEvent
   * @param {string} buttonText - Button text that was clicked
   */
  emitButtonEvent(buttonText) {
    const mapping = BUTTON_MAP[buttonText];
    if (!mapping) {
      console.warn(`[MinimalTrading] Unknown button: ${buttonText}`);
      return;
    }

    const [buttonId, buttonCategory] = mapping;

    // Update sequence tracking
    const sequence = this.sequenceTracker.update(buttonCategory, this.state.tick);

    // Create ButtonEvent
    const event = {
      ts: new Date().toISOString(),
      server_ts: null,
      button_id: buttonId,
      button_category: buttonCategory,
      tick: this.state.tick,
      price: this.state.price,
      game_phase: this.getPhaseValue(this.state.phase),
      game_id: this.state.gameId,
      balance: this.state.balance,
      position_qty: this.state.positionQty,
      bet_amount: parseFloat(this.state.betAmount) || 0,
      ...sequence,
      client_timestamp: Date.now(),
      time_in_position: 0
    };

    console.log('[MinimalTrading] ButtonEvent:', event);

    // In production, this would be sent via WebSocket or EventBus
    // this.client.send('button.press', event);
  }

  /**
   * Get current bet amount
   * @returns {number} Bet amount
   */
  getBetAmount() {
    return parseFloat(this.elements.betEntry.value) || 0;
  }

  // ==========================================
  // UI Feedback Methods (Trade Execution)
  // ==========================================

  /**
   * Set loading state on a button
   * @param {HTMLElement} button - Button element
   * @param {boolean} loading - Loading state
   */
  _setButtonLoading(button, loading) {
    if (!button) return;

    if (loading) {
      button.classList.add('loading');
      button.disabled = true;
    } else {
      button.classList.remove('loading');
      button.disabled = false;
    }
  }

  /**
   * Flash a button with success or error feedback
   * @param {HTMLElement} button - Button element
   * @param {string} type - 'success' or 'error'
   */
  _flashButton(button, type) {
    if (!button) return;

    const className = type === 'success' ? 'flash-success' : 'flash-error';
    button.classList.add(className);

    // Remove after animation
    setTimeout(() => {
      button.classList.remove(className);
    }, 300);
  }
}
