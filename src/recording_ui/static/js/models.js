/**
 * ML Models Dashboard - Frontend Logic
 *
 * Fetches training runs from the API and renders them with Chart.js
 */

// State
let runs = [];
let selectedRunId = null;
let trainingChart = null;

// DOM Elements
const runsList = document.getElementById('runs-list');
const runDetails = document.getElementById('run-details');
const noSelection = document.getElementById('no-selection');
const statusText = document.getElementById('models-status-text');

// Metric elements
const metricEpisodes = document.getElementById('metric-episodes');
const metricWinRate = document.getElementById('metric-win-rate');
const metricBetRate = document.getElementById('metric-bet-rate');
const metricWLS = document.getElementById('metric-wls');
const metricFinalReward = document.getElementById('metric-final-reward');
const selectedRunIdEl = document.getElementById('selected-run-id');

/**
 * Initialize the dashboard
 */
async function init() {
    console.log('[Models] Initializing dashboard...');
    await loadRuns();
}

/**
 * Fetch all training runs from API
 */
async function loadRuns() {
    try {
        statusText.textContent = 'Loading...';
        const response = await fetch('/api/models/runs');
        const data = await response.json();
        runs = data.runs || [];
        statusText.textContent = `${runs.length} runs`;
        renderRunsList();
    } catch (error) {
        console.error('[Models] Error loading runs:', error);
        statusText.textContent = 'Error loading';
        runsList.innerHTML = '<div class="models-no-selection">Failed to load runs</div>';
    }
}

/**
 * Render the list of training runs
 */
function renderRunsList() {
    if (runs.length === 0) {
        runsList.innerHTML = '<div class="models-no-selection">No training runs found</div>';
        return;
    }

    runsList.innerHTML = runs.map(run => {
        const winRateClass = getWinRateClass(run.win_rate);
        const steps = formatSteps(run.max_steps);
        const winRate = run.win_rate ? `${run.win_rate.toFixed(1)}%` : '--';
        const betRate = run.bet_rate ? `${run.bet_rate.toFixed(1)}%` : '--';

        return `
            <div class="models-run-item ${run.run_id === selectedRunId ? 'selected' : ''}"
                 onclick="selectRun('${run.run_id}')">
                <span class="models-run-id">${run.run_id}</span>
                <span class="models-run-steps">${steps}</span>
                <span class="models-run-metric ${winRateClass}">win: ${winRate}</span>
                <span class="models-run-metric">bet: ${betRate}</span>
            </div>
        `;
    }).join('');
}

/**
 * Get CSS class for win rate coloring
 */
function getWinRateClass(winRate) {
    if (!winRate) return '';
    if (winRate >= 20) return 'good';  // Above breakeven
    if (winRate >= 17) return 'warn';  // Close to breakeven
    return 'bad';  // Below breakeven
}

/**
 * Format steps for display (e.g., 1000000 -> "1M")
 */
function formatSteps(steps) {
    if (!steps) return '--';
    if (steps >= 1000000) return `${(steps / 1000000).toFixed(1)}M`;
    if (steps >= 1000) return `${(steps / 1000).toFixed(0)}k`;
    return steps.toString();
}

/**
 * Select a run and load its details
 */
async function selectRun(runId) {
    console.log('[Models] Selecting run:', runId);
    selectedRunId = runId;

    // Update selection in list
    renderRunsList();

    // Show details panel
    noSelection.style.display = 'none';
    runDetails.style.display = 'block';

    // Load run details
    try {
        const response = await fetch(`/api/models/runs/${runId}`);
        const data = await response.json();
        renderRunDetails(data);
    } catch (error) {
        console.error('[Models] Error loading run details:', error);
    }
}

/**
 * Render run details and chart
 */
function renderRunDetails(data) {
    // Update title
    selectedRunIdEl.textContent = data.run_id;

    // Update metrics
    metricEpisodes.textContent = data.total_episodes?.toLocaleString() || '--';
    metricWinRate.textContent = data.win_rate ? `${data.win_rate.toFixed(2)}%` : '--';
    metricBetRate.textContent = data.bet_rate ? `${data.bet_rate.toFixed(2)}%` : '--';
    metricWLS.textContent = `${data.wins || 0} / ${data.losses || 0} / ${data.skips || 0}`;
    metricFinalReward.textContent = data.final_avg_reward !== undefined
        ? `${data.final_avg_reward.toFixed(3)} ± ${data.final_std_reward?.toFixed(3) || '?'}`
        : '--';

    // Render chart
    if (data.chart_data && data.chart_data.labels) {
        renderChart(data.chart_data);
    }
}

/**
 * Render the training progress chart
 */
function renderChart(chartData) {
    const ctx = document.getElementById('training-chart').getContext('2d');

    // Destroy existing chart if any
    if (trainingChart) {
        trainingChart.destroy();
    }

    trainingChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'Win Rate %',
                    data: chartData.win_rates,
                    borderColor: '#00ff66',
                    backgroundColor: 'rgba(0, 255, 102, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y',
                },
                {
                    label: 'Bet Rate %',
                    data: chartData.bet_rates,
                    borderColor: '#3399ff',
                    backgroundColor: 'rgba(51, 153, 255, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y',
                },
                {
                    label: 'Mean Reward',
                    data: chartData.mean_rewards,
                    borderColor: '#ffcc00',
                    backgroundColor: 'rgba(255, 204, 0, 0.1)',
                    tension: 0.3,
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
                    labels: {
                        color: '#888888',
                    },
                },
                tooltip: {
                    backgroundColor: '#2a2a2a',
                    titleColor: '#ffffff',
                    bodyColor: '#888888',
                    borderColor: '#666666',
                    borderWidth: 1,
                },
            },
            scales: {
                x: {
                    grid: {
                        color: '#333333',
                    },
                    ticks: {
                        color: '#666666',
                    },
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    min: 0,
                    max: 100,
                    grid: {
                        color: '#333333',
                    },
                    ticks: {
                        color: '#666666',
                    },
                    title: {
                        display: true,
                        text: 'Rate %',
                        color: '#666666',
                    },
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        color: '#666666',
                    },
                    title: {
                        display: true,
                        text: 'Reward',
                        color: '#666666',
                    },
                },
            },
        },
    });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);
