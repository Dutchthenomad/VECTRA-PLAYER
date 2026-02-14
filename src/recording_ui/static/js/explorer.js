/**
 * Game Explorer - Interactive visualization for multi-bet sidebet strategies.
 *
 * Features:
 * - Price curve overlay with color-coded outcomes
 * - Bet window visualization
 * - Cumulative win rate table
 * - Duration histogram
 */

// State
let state = {
    entryTick: 200,
    numBets: 4,
    gameLimit: 50,
    data: null,
    // Bankroll simulation state
    walletBalance: 0.1,
    betSizes: [0.001, 0.001, 0.001, 0.001],
    maxDrawdown: 0.50,  // 50% = wallet halved = failure
    simData: null,
    // Advanced position sizing
    useDynamicSizing: false,
    highConfidenceThreshold: 60,  // 60%
    highConfidenceMultiplier: 2.0,
    reduceOnDrawdown: false,
    takeProfitTarget: null,  // null = no limit
    // Kelly sizing
    useKellySizing: false,
    kellyFraction: 0.25,  // 25% of full Kelly
    // Monte Carlo state
    mcData: null,
    mcSelectedStrategy: null,
    mcRunning: false,
};

// Charts
let priceChart = null;
let histogramChart = null;
let equityChart = null;
let mcDistributionChart = null;
let mcEquityChart = null;

// Colors (Catppuccin Mocha)
const COLORS = {
    green: 'rgba(166, 227, 161, 0.7)',
    greenLine: 'rgba(166, 227, 161, 0.4)',
    red: 'rgba(243, 139, 168, 0.7)',
    redLine: 'rgba(243, 139, 168, 0.4)',
    gray: 'rgba(166, 173, 200, 0.3)',
    grayLine: 'rgba(166, 173, 200, 0.2)',
    blue: 'rgba(137, 180, 250, 0.8)',
    teal: 'rgba(148, 226, 213, 0.8)',
    yellow: 'rgba(249, 226, 175, 0.8)',
    purple: 'rgba(203, 166, 247, 0.8)',
    text: '#cdd6f4',
    subtext: '#a6adc8',
    surface: '#313244',
    overlay: '#45475a',
};

const BET_COLORS = [COLORS.blue, COLORS.teal, COLORS.yellow, COLORS.purple];

/**
 * Initialize the explorer.
 */
async function init() {
    setupEventListeners();
    setupBankrollListeners();
    await fetchAndRender();
    updateRiskDisplay();
}

/**
 * Set up UI event listeners.
 */
function setupEventListeners() {
    // Entry tick slider
    const slider = document.getElementById('entry-tick-slider');
    const valueDisplay = document.getElementById('entry-tick-value');

    slider.addEventListener('input', (e) => {
        state.entryTick = parseInt(e.target.value);
        valueDisplay.textContent = state.entryTick;
    });

    slider.addEventListener('change', () => {
        fetchAndRender();
    });

    // Bet count buttons
    document.querySelectorAll('.bet-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.bet-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            state.numBets = parseInt(e.target.dataset.bets);
            fetchAndRender();
        });
    });

    // Game limit input
    const limitInput = document.getElementById('game-limit');
    limitInput.addEventListener('change', (e) => {
        state.gameLimit = parseInt(e.target.value) || 50;
        fetchAndRender();
    });
}

/**
 * Fetch data and render all visualizations.
 */
async function fetchAndRender() {
    try {
        const params = new URLSearchParams({
            entry_tick: state.entryTick,
            num_bets: state.numBets,
            limit: state.gameLimit,
        });

        const response = await fetch(`/api/explorer/data?${params}`);
        if (!response.ok) throw new Error('Failed to fetch data');

        state.data = await response.json();

        renderWindowsViz();
        renderStats();
        renderCumulativeTable();
        renderPriceChart();
        renderHistogram();

    } catch (error) {
        console.error('Explorer fetch error:', error);
    }
}

/**
 * Render the bet windows visualization bar.
 */
function renderWindowsViz() {
    const container = document.getElementById('windows-viz');
    const windows = state.data.strategy.windows;

    let html = `<span class="window-label">Tick 0</span>`;

    // Add pre-entry space
    const preWidth = Math.min(state.entryTick / 5, 40);
    html += `<div style="width: ${preWidth}px; height: 24px; background: ${COLORS.surface}; border-radius: 3px;"></div>`;

    windows.forEach((w, i) => {
        // Window block
        html += `<div class="window-block bet${i+1}" style="width: 40px;">
            ${w.start_tick}-${w.end_tick}
        </div>`;

        // Cooldown (except after last)
        if (i < windows.length - 1) {
            html += `<div class="window-block cooldown">5</div>`;
        }
    });

    html += `<span class="window-label">Tick ${windows[windows.length-1].end_tick + 50}+</span>`;

    container.innerHTML = html;
}

/**
 * Render summary stats.
 */
function renderStats() {
    const s = state.data.strategy;

    document.getElementById('total-games').textContent = s.total_games;
    document.getElementById('playable-games').textContent = s.playable_games;
    document.getElementById('early-rug-rate').textContent = `${s.early_rug_rate}%`;
}

/**
 * Render cumulative win rate table.
 */
function renderCumulativeTable() {
    const tbody = document.getElementById('cumulative-tbody');
    const stats = state.data.strategy.cumulative_stats;

    let html = '';
    stats.forEach(s => {
        const rowClass = s.profitable ? 'profitable' : 'unprofitable';
        const rateClass = s.win_rate >= 20 ? 'good' : 'bad';
        const evClass = s.ev_per_sequence > 0 ? 'positive' : 'negative';

        html += `<tr class="${rowClass}">
            <td>Bet 1-${s.num_bets}</td>
            <td class="win-rate ${rateClass}">${s.win_rate}%</td>
            <td class="${evClass}">${s.ev_per_sequence > 0 ? '+' : ''}${s.ev_per_sequence}</td>
            <td>${s.coverage_end_tick}</td>
        </tr>`;
    });

    tbody.innerHTML = html;
}

/**
 * Render price curves chart.
 */
function renderPriceChart() {
    const ctx = document.getElementById('price-chart').getContext('2d');
    const games = state.data.games;
    const windows = state.data.strategy.windows;

    // Destroy existing chart
    if (priceChart) {
        priceChart.destroy();
    }

    // Calculate max tick to display
    const maxTick = Math.max(
        windows[windows.length - 1].end_tick + 50,
        ...games.map(g => Math.min(g.duration, 600))
    );

    // Build datasets
    const datasets = [];

    // Add window highlight regions as background datasets
    windows.forEach((w, i) => {
        datasets.push({
            label: `Bet ${i+1} Window`,
            data: Array(maxTick).fill(null).map((_, tick) => {
                if (tick >= w.start_tick && tick <= w.end_tick) {
                    return { x: tick, y: 5 };  // Arbitrary height
                }
                return null;
            }).filter(p => p !== null),
            type: 'bar',
            backgroundColor: BET_COLORS[i].replace('0.8', '0.15'),
            barPercentage: 1.0,
            categoryPercentage: 1.0,
            order: 100,  // Behind lines
            yAxisID: 'y',
        });
    });

    // Add game price lines
    games.forEach((game, i) => {
        let color, borderColor;
        switch (game.color_category) {
            case 'green':
                color = COLORS.green;
                borderColor = COLORS.greenLine;
                break;
            case 'red':
                color = COLORS.red;
                borderColor = COLORS.redLine;
                break;
            default:
                color = COLORS.gray;
                borderColor = COLORS.grayLine;
        }

        // Trim prices to maxTick
        const prices = game.prices.slice(0, maxTick);

        datasets.push({
            label: game.game_id,
            data: prices.map((p, tick) => ({ x: tick, y: p })),
            borderColor: borderColor,
            backgroundColor: 'transparent',
            borderWidth: 1,
            pointRadius: 0,
            tension: 0.1,
            order: game.color_category === 'gray' ? 50 : 10,
        });
    });

    // Add entry tick vertical line
    datasets.push({
        label: 'Entry Tick',
        data: [
            { x: state.entryTick, y: 0 },
            { x: state.entryTick, y: 10 }
        ],
        borderColor: COLORS.text,
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 0,
        type: 'line',
        order: 1,
    });

    priceChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        title: (items) => {
                            if (items[0]) {
                                return `Tick ${items[0].parsed.x}`;
                            }
                            return '';
                        },
                        label: (item) => {
                            if (item.dataset.label.startsWith('Bet')) return null;
                            if (item.dataset.label === 'Entry Tick') return null;
                            return `${item.dataset.label}: ${item.parsed.y.toFixed(3)}x`;
                        },
                    },
                    filter: (item) => {
                        return !item.dataset.label.startsWith('Bet') &&
                               item.dataset.label !== 'Entry Tick';
                    },
                },
            },
            scales: {
                x: {
                    type: 'linear',
                    min: 0,
                    max: maxTick,
                    title: {
                        display: true,
                        text: 'Tick',
                        color: COLORS.subtext,
                    },
                    grid: {
                        color: COLORS.surface,
                    },
                    ticks: {
                        color: COLORS.subtext,
                    },
                },
                y: {
                    type: 'linear',
                    min: 0,
                    max: 5,
                    title: {
                        display: true,
                        text: 'Price (x)',
                        color: COLORS.subtext,
                    },
                    grid: {
                        color: COLORS.surface,
                    },
                    ticks: {
                        color: COLORS.subtext,
                    },
                },
            },
        },
    });
}

/**
 * Render duration histogram.
 */
function renderHistogram() {
    const ctx = document.getElementById('histogram-chart').getContext('2d');
    const hist = state.data.histogram;
    const windows = state.data.strategy.windows;

    if (histogramChart) {
        histogramChart.destroy();
    }

    // Color bars by whether they fall in a coverage window
    const barColors = hist.bin_centers.map(tick => {
        for (const w of windows) {
            if (tick >= w.start_tick && tick <= w.end_tick) {
                return COLORS.green;
            }
        }
        if (tick < state.entryTick) {
            return COLORS.gray;
        }
        return COLORS.red;
    });

    histogramChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hist.bin_centers.map(t => Math.round(t)),
            datasets: [{
                label: 'Games',
                data: hist.counts,
                backgroundColor: barColors,
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        title: (items) => `Tick ~${items[0].label}`,
                        label: (item) => `${item.raw} games`,
                    },
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Duration (ticks)',
                        color: COLORS.subtext,
                    },
                    grid: {
                        display: false,
                    },
                    ticks: {
                        color: COLORS.subtext,
                        maxTicksLimit: 10,
                    },
                },
                y: {
                    title: {
                        display: true,
                        text: 'Count',
                        color: COLORS.subtext,
                    },
                    grid: {
                        color: COLORS.surface,
                    },
                    ticks: {
                        color: COLORS.subtext,
                    },
                },
            },
        },
    });
}

// ============================================================
// BANKROLL SIMULATION FUNCTIONS
// ============================================================

/**
 * Set up bankroll simulation event listeners.
 */
function setupBankrollListeners() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabId = e.target.dataset.tab;
            switchTab(tabId);
        });
    });

    // Wallet balance
    const walletInput = document.getElementById('wallet-balance');
    if (walletInput) {
        walletInput.addEventListener('change', (e) => {
            state.walletBalance = parseFloat(e.target.value) || 0.1;
            updateRiskDisplay();
        });
    }

    // Entry tick for simulation
    const simEntryTick = document.getElementById('sim-entry-tick');
    if (simEntryTick) {
        simEntryTick.addEventListener('change', (e) => {
            state.entryTick = parseInt(e.target.value) || 200;
        });
    }

    // Max drawdown
    const maxDdInput = document.getElementById('max-drawdown');
    if (maxDdInput) {
        maxDdInput.addEventListener('change', (e) => {
            state.maxDrawdown = (parseFloat(e.target.value) || 50) / 100;
        });
    }

    // Bet size inputs
    for (let i = 1; i <= 4; i++) {
        const input = document.getElementById(`bet-size-${i}`);
        if (input) {
            input.addEventListener('change', (e) => {
                state.betSizes[i - 1] = parseFloat(e.target.value) || 0.001;
                updateRiskDisplay();
            });
        }
    }

    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const preset = e.target.dataset.preset;
            applyPreset(preset);
        });
    });

    // Run simulation button
    const runBtn = document.getElementById('run-simulation');
    if (runBtn) {
        runBtn.addEventListener('click', runSimulation);
    }

    // Dynamic sizing checkbox
    const dynamicSizingCheckbox = document.getElementById('use-dynamic-sizing');
    if (dynamicSizingCheckbox) {
        dynamicSizingCheckbox.addEventListener('change', (e) => {
            state.useDynamicSizing = e.target.checked;
            // Show/hide dynamic options
            const dynamicOptions = document.getElementById('dynamic-options');
            if (dynamicOptions) {
                dynamicOptions.style.display = e.target.checked ? 'flex' : 'none';
            }
        });
    }

    // Reduce on drawdown checkbox
    const reduceDrawdownCheckbox = document.getElementById('reduce-on-drawdown');
    if (reduceDrawdownCheckbox) {
        reduceDrawdownCheckbox.addEventListener('change', (e) => {
            state.reduceOnDrawdown = e.target.checked;
        });
    }

    // Confidence threshold slider
    const confidenceSlider = document.getElementById('confidence-threshold');
    const confidenceValue = document.getElementById('confidence-value');
    if (confidenceSlider) {
        confidenceSlider.addEventListener('input', (e) => {
            state.highConfidenceThreshold = parseInt(e.target.value);
            if (confidenceValue) {
                confidenceValue.textContent = `${state.highConfidenceThreshold}%`;
            }
        });
    }

    // Bet multiplier
    const multiplierInput = document.getElementById('bet-multiplier');
    if (multiplierInput) {
        multiplierInput.addEventListener('change', (e) => {
            state.highConfidenceMultiplier = parseFloat(e.target.value) || 2.0;
        });
    }

    // Take profit target
    const takeProfitInput = document.getElementById('take-profit');
    if (takeProfitInput) {
        takeProfitInput.addEventListener('change', (e) => {
            const val = parseFloat(e.target.value);
            // Convert from percentage to multiplier (e.g., 50% = 1.5x)
            state.takeProfitTarget = val > 0 ? 1 + (val / 100) : null;
        });
    }

    // Kelly sizing checkbox
    const kellySizingCheckbox = document.getElementById('use-kelly-sizing');
    if (kellySizingCheckbox) {
        kellySizingCheckbox.addEventListener('change', (e) => {
            state.useKellySizing = e.target.checked;
            // Show/hide Kelly options
            const kellyOptions = document.getElementById('kelly-options');
            if (kellyOptions) {
                kellyOptions.style.display = e.target.checked ? 'flex' : 'none';
            }
        });
    }

    // Kelly fraction slider
    const kellySlider = document.getElementById('kelly-fraction-slider');
    const kellyValue = document.getElementById('kelly-fraction-value');
    if (kellySlider) {
        kellySlider.addEventListener('input', (e) => {
            const pct = parseInt(e.target.value);
            state.kellyFraction = pct / 100;
            if (kellyValue) {
                kellyValue.textContent = `${pct}%`;
            }
        });
    }

    // Save strategy button
    const saveBtn = document.getElementById('btn-save-strategy');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveStrategy);
    }
}

/**
 * Switch between tabs.
 */
function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabId}`);
    });
}

/**
 * Apply a preset bet sizing strategy.
 */
function applyPreset(preset) {
    let sizes;

    switch (preset) {
        case 'fixed':
            sizes = [0.001, 0.001, 0.001, 0.001];
            break;
        case 'progressive':
            // 2x martingale: 0.001, 0.002, 0.004, 0.008
            sizes = [0.001, 0.002, 0.004, 0.008];
            break;
        case 'kelly':
            // Calculate Kelly-based sizing (use current win rate from data)
            const winRate = state.data?.strategy?.cumulative_stats?.[3]?.win_rate || 20;
            const kellyFraction = Math.max(0, (winRate / 100) - (1 - winRate / 100) / 5) * 0.25;
            const perBet = Math.max(0.001, state.walletBalance * kellyFraction / 4);
            sizes = [perBet, perBet, perBet, perBet].map(s => Math.round(s * 10000) / 10000);
            break;
        default:
            sizes = [0.001, 0.001, 0.001, 0.001];
    }

    // Update state and UI
    state.betSizes = sizes;
    for (let i = 1; i <= 4; i++) {
        const input = document.getElementById(`bet-size-${i}`);
        if (input) {
            input.value = sizes[i - 1];
        }
    }
    updateRiskDisplay();
}

/**
 * Update the risk display showing total risk per game.
 */
function updateRiskDisplay() {
    const totalRisk = state.betSizes.reduce((a, b) => a + b, 0);
    const riskPct = (totalRisk / state.walletBalance) * 100;

    const amountEl = document.getElementById('risk-amount');
    const pctEl = document.getElementById('risk-pct');

    if (amountEl) amountEl.textContent = totalRisk.toFixed(4);
    if (pctEl) pctEl.textContent = riskPct.toFixed(1);
}

/**
 * Run the bankroll simulation.
 */
async function runSimulation() {
    const runBtn = document.getElementById('run-simulation');
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Running...';
    }

    try {
        // Build request body with all parameters
        const requestBody = {
            initial_balance: state.walletBalance,
            entry_tick: parseInt(document.getElementById('sim-entry-tick')?.value) || state.entryTick,
            bet_sizes: state.betSizes,
            max_drawdown_pct: state.maxDrawdown,
            // Advanced position sizing
            use_dynamic_sizing: state.useDynamicSizing,
            high_confidence_threshold: state.highConfidenceThreshold,
            high_confidence_multiplier: state.highConfidenceMultiplier,
            reduce_on_drawdown: state.reduceOnDrawdown,
            // Kelly sizing
            use_kelly_sizing: state.useKellySizing,
            kelly_fraction: state.kellyFraction,
        };

        // Only include take_profit_target if set
        if (state.takeProfitTarget !== null) {
            requestBody.take_profit_target = state.takeProfitTarget;
        }

        const response = await fetch('/api/explorer/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) throw new Error('Simulation failed');

        state.simData = await response.json();
        renderSimulationResults();
        renderEquityChart();
        updateSizingAnalysis();

        // Show results card
        const resultsCard = document.getElementById('sim-results-card');
        if (resultsCard) resultsCard.style.display = 'block';

        // Show strategy save section
        showStrategySaveSection();

    } catch (error) {
        console.error('Simulation error:', error);
        alert('Simulation failed: ' + error.message);
    } finally {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.textContent = 'Run Simulation';
        }
    }
}

/**
 * Update the position sizing analysis box with Kelly calculations.
 */
function updateSizingAnalysis() {
    const data = state.simData;
    if (!data) return;

    const winRate = data.summary.win_rate / 100;
    const kellyFraction = Math.max(0, winRate - (1 - winRate) / 5);
    const quarterKelly = kellyFraction * 0.25;
    const suggestedBet = state.walletBalance * quarterKelly / 4;

    const estWinProbEl = document.getElementById('est-win-prob');
    const kellyFractionEl = document.getElementById('kelly-fraction');
    const suggestedBetEl = document.getElementById('suggested-bet');

    if (estWinProbEl) {
        estWinProbEl.textContent = `${(winRate * 100).toFixed(1)}%`;
    }
    if (kellyFractionEl) {
        kellyFractionEl.textContent = `${(kellyFraction * 100).toFixed(2)}%`;
    }
    if (suggestedBetEl) {
        suggestedBetEl.textContent = suggestedBet.toFixed(4);
    }
}

/**
 * Render simulation results.
 */
function renderSimulationResults() {
    const data = state.simData;
    if (!data) return;

    const f = data.financials;
    const r = data.risk_metrics;
    const s = data.summary;

    // Update stat displays
    document.getElementById('sim-starting').textContent = `${f.starting_balance} SOL`;
    document.getElementById('sim-ending').textContent = `${f.ending_balance.toFixed(4)} SOL`;

    const profitEl = document.getElementById('sim-profit');
    const profit = f.total_profit;
    profitEl.textContent = `${profit >= 0 ? '+' : ''}${profit.toFixed(4)} SOL`;
    profitEl.className = `value ${profit >= 0 ? 'profit' : 'loss'}`;

    document.getElementById('sim-winrate').textContent = `${s.win_rate}%`;

    const maxDdEl = document.getElementById('sim-maxdd');
    // Show if max drawdown was reached
    const ddText = r.max_drawdown_reached
        ? `${r.max_drawdown_pct.toFixed(1)}% (LIMIT)`
        : `${r.max_drawdown_pct.toFixed(1)}%`;
    maxDdEl.textContent = ddText;
    maxDdEl.className = `value ${r.max_drawdown_reached ? 'loss' : (r.max_drawdown_pct > 30 ? 'loss' : '')}`;

    const roiEl = document.getElementById('sim-roi');
    // Show if take-profit was reached
    const roiText = r.take_profit_reached
        ? `${f.roi_pct >= 0 ? '+' : ''}${f.roi_pct.toFixed(1)}% (TARGET)`
        : `${f.roi_pct >= 0 ? '+' : ''}${f.roi_pct.toFixed(1)}%`;
    roiEl.textContent = roiText;
    roiEl.className = `value ${r.take_profit_reached ? 'profit' : (f.roi_pct >= 0 ? 'profit' : 'loss')}`;
}

/**
 * Render the equity curve chart.
 */
function renderEquityChart() {
    const ctx = document.getElementById('equity-chart')?.getContext('2d');
    if (!ctx || !state.simData) return;

    const curves = state.simData.curves;

    if (equityChart) {
        equityChart.destroy();
    }

    const labels = curves.equity.map((_, i) => i);

    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Equity (SOL)',
                    data: curves.equity,
                    borderColor: COLORS.blue,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    yAxisID: 'y',
                },
                {
                    label: 'Drawdown (%)',
                    data: curves.drawdown,
                    borderColor: COLORS.red,
                    backgroundColor: 'rgba(243, 139, 168, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: true,
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { color: COLORS.subtext },
                },
                tooltip: {
                    callbacks: {
                        title: (items) => `Game ${items[0].label}`,
                    },
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Game #',
                        color: COLORS.subtext,
                    },
                    grid: { color: COLORS.surface },
                    ticks: { color: COLORS.subtext, maxTicksLimit: 10 },
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Equity (SOL)',
                        color: COLORS.subtext,
                    },
                    grid: { color: COLORS.surface },
                    ticks: { color: COLORS.subtext },
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Drawdown (%)',
                        color: COLORS.subtext,
                    },
                    grid: { drawOnChartArea: false },
                    ticks: { color: COLORS.subtext },
                    min: 0,
                    max: 100,
                },
            },
        },
    });
}

/**
 * Show the strategy save section and populate it with current parameters.
 */
function showStrategySaveSection() {
    const section = document.getElementById('strategy-save-section');
    if (!section) return;

    section.style.display = 'block';

    // Hide success message
    const successEl = document.getElementById('save-success');
    if (successEl) successEl.style.display = 'none';

    // Populate all current parameter values
    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    };

    setText('save-entry-tick', state.entryTick);
    setText('save-num-bets', state.numBets);
    setText('save-initial-balance', state.walletBalance + ' SOL');
    setText('save-bet-sizes', state.betSizes.map(s => s.toFixed(4)).join(', ') + ' SOL');
    setText('save-max-drawdown', (state.maxDrawdown * 100) + '%');
    setText('save-take-profit', state.takeProfitTarget
        ? '+' + ((state.takeProfitTarget - 1) * 100).toFixed(0) + '%'
        : 'None');
    setText('save-kelly-sizing', state.useKellySizing ? 'Yes' : 'No');
    setText('save-kelly-fraction', (state.kellyFraction * 100) + '%');
    setText('save-dynamic-sizing', state.useDynamicSizing ? 'Yes' : 'No');
    setText('save-confidence-threshold', state.highConfidenceThreshold + '%');
    setText('save-confidence-multiplier', state.highConfidenceMultiplier + 'x');
    setText('save-reduce-drawdown', state.reduceOnDrawdown ? 'Yes' : 'No');
}

/**
 * Save the current strategy configuration.
 */
async function saveStrategy() {
    const nameInput = document.getElementById('strategy-name');
    const name = nameInput?.value.trim();

    if (!name) {
        alert('Please enter a strategy name');
        return;
    }

    const payload = {
        name: name,
        initial_balance: state.walletBalance,
        entry_tick: state.entryTick,
        bet_sizes: state.betSizes,
        max_drawdown_pct: state.maxDrawdown,
        take_profit_target: state.takeProfitTarget,
        use_kelly_sizing: state.useKellySizing,
        kelly_fraction: state.kellyFraction,
        use_dynamic_sizing: state.useDynamicSizing,
        high_confidence_threshold: state.highConfidenceThreshold,
        high_confidence_multiplier: state.highConfidenceMultiplier,
        reduce_on_drawdown: state.reduceOnDrawdown,
    };

    try {
        const response = await fetch('/api/explorer/save-strategy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Save failed');
        }

        const result = await response.json();

        // Show success message
        const successEl = document.getElementById('save-success');
        if (successEl) {
            successEl.style.display = 'block';
            successEl.textContent = `Strategy "${result.name}" saved! View in Backtest tab.`;
        }

        // Clear input
        if (nameInput) nameInput.value = '';

    } catch (error) {
        console.error('Save strategy error:', error);
        alert('Failed to save strategy: ' + error.message);
    }
}

// =============================================================================
// MONTE CARLO TAB
// =============================================================================

/**
 * Set up Monte Carlo tab event listeners.
 */
function setupMonteCarloListeners() {
    // Run button
    const runBtn = document.getElementById('btn-run-mc');
    if (runBtn) {
        runBtn.addEventListener('click', runMonteCarloComparison);
    }

    // Table row selection
    const tableBody = document.getElementById('mc-table-body');
    if (tableBody) {
        tableBody.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            if (row && row.dataset.strategy) {
                selectMonteCarloStrategy(row.dataset.strategy);
            }
        });
    }
}

/**
 * Run Monte Carlo comparison across all 8 strategies.
 */
async function runMonteCarloComparison() {
    if (state.mcRunning) return;
    state.mcRunning = true;

    const statusEl = document.getElementById('mc-status');
    const statusText = document.getElementById('mc-status-text');
    const runBtn = document.getElementById('btn-run-mc');

    // Show loading state
    if (statusEl) statusEl.style.display = 'flex';
    if (runBtn) runBtn.disabled = true;

    // Get config from inputs
    const iterations = parseInt(document.getElementById('mc-iterations')?.value || 10000);
    const winRate = parseFloat(document.getElementById('mc-win-rate')?.value || 18.5) / 100;
    const bankroll = parseFloat(document.getElementById('mc-bankroll')?.value || 0.1);

    if (statusText) {
        const timeEst = iterations === 1000 ? '~5s' : iterations === 10000 ? '~45s' : '~7min';
        statusText.textContent = `Running ${iterations.toLocaleString()} iterations per strategy ${timeEst}...`;
    }

    try {
        const response = await fetch('/api/explorer/monte-carlo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                num_iterations: iterations,
                win_rate: winRate,
                initial_bankroll: bankroll,
                num_games: 500,
            }),
        });

        if (!response.ok) {
            throw new Error('Monte Carlo simulation failed');
        }

        state.mcData = await response.json();
        renderMonteCarloResults();

    } catch (error) {
        console.error('Monte Carlo error:', error);
        if (statusText) statusText.textContent = 'Error: ' + error.message;
    } finally {
        state.mcRunning = false;
        if (runBtn) runBtn.disabled = false;
        if (statusEl) statusEl.style.display = 'none';
    }
}

/**
 * Render all Monte Carlo results.
 */
function renderMonteCarloResults() {
    if (!state.mcData) return;

    renderMonteCarloTable();
    renderMonteCarloDistributionChart();
    renderMonteCarloInfo();

    // Select best Sortino by default
    const bestSortino = state.mcData.best_by_metric?.best_sortino;
    if (bestSortino) {
        selectMonteCarloStrategy(bestSortino);
    }
}

/**
 * Render the strategy comparison table.
 */
function renderMonteCarloTable() {
    const tbody = document.getElementById('mc-table-body');
    if (!tbody || !state.mcData) return;

    const strategies = state.mcData.strategies;
    const order = state.mcData.strategy_order || Object.keys(strategies);
    const best = state.mcData.best_by_metric || {};

    let html = '';

    for (const key of order) {
        const data = strategies[key];
        if (!data) continue;

        const summary = data.summary || {};
        const risk = data.risk_metrics || {};
        const perf = data.performance || {};
        const dd = data.drawdown || {};
        const meta = data.metadata || {};

        // Determine risk level class
        const riskLevel = (meta.risk_level || 'Unknown').toLowerCase().replace(/[- ]/g, '-');
        let riskClass = 'risk-low';
        if (riskLevel.includes('very-high')) riskClass = 'risk-very-high';
        else if (riskLevel.includes('high')) riskClass = 'risk-high';
        else if (riskLevel.includes('medium')) riskClass = 'risk-medium';

        // Check if this is best in any category
        const isBestMean = key === best.highest_mean;
        const isBestProfit = key === best.highest_profit_prob;
        const isBest2x = key === best.highest_2x_prob;
        const isBestSortino = key === best.best_sortino;
        const isBestDD = key === best.lowest_drawdown;

        const isSelected = key === state.mcSelectedStrategy;

        html += `
            <tr data-strategy="${key}" class="${isSelected ? 'selected' : ''}">
                <td>
                    <div class="strategy-name">
                        <div class="strategy-dot" style="background: ${meta.color || '#cdd6f4'}"></div>
                        ${meta.name || key}${isBestSortino ? ' ★' : ''}
                    </div>
                </td>
                <td class="${isBestMean ? 'best-cell' : ''}">${summary.mean_final_bankroll?.toFixed(4) || '--'}</td>
                <td>${summary.median_final_bankroll?.toFixed(4) || '--'}</td>
                <td class="${isBestProfit ? 'best-cell' : ''}">${(risk.probability_profit * 100)?.toFixed(1) || '--'}%</td>
                <td class="${isBest2x ? 'best-cell' : ''}">${(risk.probability_2x * 100)?.toFixed(1) || '--'}%</td>
                <td class="${isBestDD ? 'best-cell' : ''}">${(dd.mean_max_drawdown * 100)?.toFixed(1) || '--'}%</td>
                <td class="${isBestSortino ? 'best-cell' : ''}">${perf.sortino_ratio?.toFixed(2) || '--'}</td>
                <td><span class="risk-badge ${riskClass}">${meta.risk_level || 'Unknown'}</span></td>
                <td>
                    <button class="btn btn-sm btn-import" onclick="importAsProfile('${key}')" title="Save as Trading Profile">
                        + Profile
                    </button>
                </td>
            </tr>
        `;
    }

    tbody.innerHTML = html;
}

/**
 * Import a Monte Carlo strategy as a Trading Profile.
 *
 * Calls the /api/profiles/import-mc/{key} endpoint to:
 * 1. Convert MC strategy config to TradingProfile v2 schema
 * 2. Run quick MC simulation to populate metrics
 * 3. Save to profiles directory
 */
async function importAsProfile(strategyKey) {
    if (!strategyKey) return;

    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = 'Saving...';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/profiles/import-mc/${strategyKey}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                // Use strategy key as profile name
                name: strategyKey,
            }),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Import failed');
        }

        // Show success feedback
        btn.innerText = '✓ Saved';
        btn.classList.add('btn-success');

        // Show notification if function exists
        if (typeof showNotification === 'function') {
            showNotification(`Profile "${result.name}" saved successfully`, 'success');
        }

        // Reset button after delay
        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
            btn.classList.remove('btn-success');
        }, 2000);

    } catch (error) {
        console.error('Import error:', error);
        btn.innerText = 'Error';
        btn.classList.add('btn-error');

        if (typeof showNotification === 'function') {
            showNotification(`Import failed: ${error.message}`, 'error');
        }

        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
            btn.classList.remove('btn-error');
        }, 2000);
    }
}

// Make importAsProfile available globally (called from onclick)
window.importAsProfile = importAsProfile;

/**
 * Select a strategy and show detailed metrics.
 */
function selectMonteCarloStrategy(strategyKey) {
    state.mcSelectedStrategy = strategyKey;

    // Update table selection
    document.querySelectorAll('#mc-table-body tr').forEach(row => {
        row.classList.toggle('selected', row.dataset.strategy === strategyKey);
    });

    // Show detail card
    const detailCard = document.getElementById('mc-detail-card');
    if (!detailCard || !state.mcData) return;

    const data = state.mcData.strategies[strategyKey];
    if (!data) {
        detailCard.style.display = 'none';
        return;
    }

    detailCard.style.display = 'block';

    const meta = data.metadata || {};
    const perf = data.performance || {};
    const dd = data.drawdown || {};
    const varMetrics = data.var_metrics || {};

    document.getElementById('mc-selected-strategy').textContent = meta.name || strategyKey;
    document.getElementById('mc-var95').textContent = `${(varMetrics.var_95 * 100)?.toFixed(1) || '--'}%`;
    document.getElementById('mc-cvar95').textContent = `${(varMetrics.cvar_95 * 100)?.toFixed(1) || '--'}%`;
    document.getElementById('mc-sharpe').textContent = perf.sharpe_ratio?.toFixed(3) || '--';
    document.getElementById('mc-calmar').textContent = perf.calmar_ratio?.toFixed(3) || '--';
    document.getElementById('mc-recovery').textContent = `${dd.mean_recovery_time?.toFixed(0) || '--'} games`;
    document.getElementById('mc-risk-level').textContent = meta.risk_level || 'Unknown';
    document.getElementById('mc-description').textContent = meta.description || 'No description available.';

    // Update equity chart with this strategy's sample curves
    renderMonteCarloEquityChart(strategyKey);
}

/**
 * Render the distribution chart (box plot style).
 */
function renderMonteCarloDistributionChart() {
    const canvas = document.getElementById('mc-distribution-chart');
    if (!canvas || !state.mcData) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (mcDistributionChart) {
        mcDistributionChart.destroy();
    }

    const strategies = state.mcData.strategies;
    const order = state.mcData.strategy_order || Object.keys(strategies);

    // Prepare data for bar chart showing percentile ranges
    const labels = [];
    const p5Data = [];
    const p25Data = [];
    const p50Data = [];
    const p75Data = [];
    const p95Data = [];
    const colors = [];

    for (const key of order) {
        const data = strategies[key];
        if (!data) continue;

        const pct = data.percentiles || {};
        const meta = data.metadata || {};

        labels.push(meta.name?.split(' ')[0] || key.split('_')[0]);
        p5Data.push(pct['5'] || 0);
        p25Data.push(pct['25'] || 0);
        p50Data.push(pct['50'] || 0);
        p75Data.push(pct['75'] || 0);
        p95Data.push(pct['95'] || 0);
        colors.push(meta.color || COLORS.blue);
    }

    mcDistributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '5th Percentile',
                    data: p5Data,
                    backgroundColor: 'rgba(243, 139, 168, 0.5)',
                    borderColor: 'rgba(243, 139, 168, 1)',
                    borderWidth: 1,
                },
                {
                    label: '25th Percentile',
                    data: p25Data,
                    backgroundColor: 'rgba(249, 226, 175, 0.5)',
                    borderColor: 'rgba(249, 226, 175, 1)',
                    borderWidth: 1,
                },
                {
                    label: 'Median',
                    data: p50Data,
                    backgroundColor: 'rgba(166, 227, 161, 0.7)',
                    borderColor: 'rgba(166, 227, 161, 1)',
                    borderWidth: 1,
                },
                {
                    label: '75th Percentile',
                    data: p75Data,
                    backgroundColor: 'rgba(137, 180, 250, 0.5)',
                    borderColor: 'rgba(137, 180, 250, 1)',
                    borderWidth: 1,
                },
                {
                    label: '95th Percentile',
                    data: p95Data,
                    backgroundColor: 'rgba(203, 166, 247, 0.5)',
                    borderColor: 'rgba(203, 166, 247, 1)',
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: COLORS.subtext, font: { size: 10 } },
                },
            },
            scales: {
                x: {
                    ticks: { color: COLORS.subtext, font: { size: 10 } },
                    grid: { color: COLORS.surface },
                },
                y: {
                    title: { display: true, text: 'Final Bankroll (SOL)', color: COLORS.subtext },
                    ticks: { color: COLORS.subtext },
                    grid: { color: COLORS.surface },
                },
            },
        },
    });
}

/**
 * Render sample equity curves for selected strategy.
 */
function renderMonteCarloEquityChart(strategyKey) {
    const canvas = document.getElementById('mc-equity-chart');
    if (!canvas || !state.mcData) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (mcEquityChart) {
        mcEquityChart.destroy();
    }

    const data = state.mcData.strategies[strategyKey];
    if (!data || !data.sample_equity_curves || data.sample_equity_curves.length === 0) {
        // Show placeholder
        mcEquityChart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'No sample equity curves available',
                        color: COLORS.subtext,
                    },
                },
            },
        });
        return;
    }

    const curves = data.sample_equity_curves;
    const meta = data.metadata || {};

    // Create datasets for each curve
    const datasets = curves.map((curve, i) => ({
        label: `Sample ${i + 1}`,
        data: curve,
        borderColor: meta.color || COLORS.blue,
        backgroundColor: 'transparent',
        borderWidth: 1,
        pointRadius: 0,
        tension: 0.1,
    }));

    // Add initial bankroll line
    const initialBankroll = state.mcData.config?.initial_bankroll || 0.1;
    const maxLen = Math.max(...curves.map(c => c.length));
    datasets.push({
        label: 'Initial',
        data: Array(maxLen).fill(initialBankroll),
        borderColor: 'rgba(166, 173, 200, 0.5)',
        borderDash: [5, 5],
        borderWidth: 1,
        pointRadius: 0,
    });

    mcEquityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({ length: maxLen }, (_, i) => i),
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Game', color: COLORS.subtext },
                    ticks: { color: COLORS.subtext, maxTicksLimit: 10 },
                    grid: { color: COLORS.surface },
                },
                y: {
                    title: { display: true, text: 'Bankroll (SOL)', color: COLORS.subtext },
                    ticks: { color: COLORS.subtext },
                    grid: { color: COLORS.surface },
                },
            },
        },
    });
}

/**
 * Render computation info.
 */
function renderMonteCarloInfo() {
    const infoEl = document.getElementById('mc-info');
    if (!infoEl || !state.mcData) return;

    infoEl.style.display = 'flex';

    const timeMs = state.mcData.computation_time_ms || 0;
    const timeSec = (timeMs / 1000).toFixed(1);
    document.getElementById('mc-time').textContent = `Computed in ${timeSec} seconds`;

    const bestSortino = state.mcData.best_by_metric?.best_sortino;
    const bestData = state.mcData.strategies[bestSortino];
    const sortinoValue = bestData?.performance?.sortino_ratio?.toFixed(2) || '--';
    const bestName = bestData?.metadata?.name || bestSortino;
    document.getElementById('mc-best').textContent = `Best Sortino: ${bestName} (${sortinoValue})`;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    init();
    setupMonteCarloListeners();
});
