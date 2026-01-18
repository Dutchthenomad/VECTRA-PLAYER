/**
 * Seed Bruteforce Analysis Tool
 *
 * Analyzes game seeds from recorded data to detect patterns:
 * - Hex64 format verification (SHA-256)
 * - Timestamp correlation analysis
 * - Sequential pattern detection
 * - Entropy analysis
 */

const ARTIFACT_CONFIG = {
    id: 'seed-bruteforce',
    name: 'Seed Bruteforce Analysis',
    version: '1.0.0',
    subscriptions: ['game.tick']
};

// =============================================================================
// State
// =============================================================================

const state = {
    games: [],
    analysisResults: null,
    isAnalyzing: false,
    liveGames: []
};

// =============================================================================
// UI Elements
// =============================================================================

const ui = {};

// =============================================================================
// Initialization
// =============================================================================

function init() {
    // Cache DOM elements
    ui.connectionDot = document.getElementById('connectionDot');
    ui.connectionText = document.getElementById('connectionText');
    ui.messageCount = document.getElementById('messageCount');
    ui.avgLatency = document.getElementById('avgLatency');
    ui.fileUpload = document.getElementById('fileUpload');
    ui.fileInput = document.getElementById('fileInput');
    ui.gameCount = document.getElementById('gameCount');
    ui.ruggedCount = document.getElementById('ruggedCount');
    ui.seedPreview = document.getElementById('seedPreview');
    ui.analyzeBtn = document.getElementById('analyzeBtn');
    ui.progressContainer = document.getElementById('progressContainer');
    ui.progressFill = document.getElementById('progressFill');
    ui.progressText = document.getElementById('progressText');
    ui.resultsBody = document.getElementById('resultsBody');
    ui.hexSummary = document.getElementById('hexSummary');
    ui.timestampSummary = document.getElementById('timestampSummary');
    ui.sequentialSummary = document.getElementById('sequentialSummary');
    ui.entropySummary = document.getElementById('entropySummary');
    ui.statusText = document.getElementById('statusText');

    // File upload handlers
    ui.fileUpload.addEventListener('click', () => ui.fileInput.click());
    ui.fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    ui.fileUpload.addEventListener('dragover', (e) => {
        e.preventDefault();
        ui.fileUpload.classList.add('dragover');
    });
    ui.fileUpload.addEventListener('dragleave', () => {
        ui.fileUpload.classList.remove('dragover');
    });
    ui.fileUpload.addEventListener('drop', (e) => {
        e.preventDefault();
        ui.fileUpload.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) loadFile(file);
    });

    // Analysis button
    ui.analyzeBtn.addEventListener('click', runAnalysis);

    // Pattern radio buttons - show/hide sections
    document.querySelectorAll('input[name="pattern"]').forEach(radio => {
        radio.addEventListener('change', updateVisibleSections);
    });

    // Initialize WebSocket client for live data
    window.wsClient = new FoundationWSClient();
    wsClient.on('connection', handleConnectionChange);
    wsClient.on('game.tick', handleGameTick);
    wsClient.connect().catch(console.error);

    setInterval(updateMetrics, 1000);
}

// =============================================================================
// File Loading
// =============================================================================

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) loadFile(file);
}

async function loadFile(file) {
    ui.statusText.textContent = 'Loading...';

    const text = await file.text();
    const lines = text.trim().split('\n');

    state.games = [];
    for (const line of lines) {
        try {
            state.games.push(JSON.parse(line));
        } catch (e) {
            console.warn('Failed to parse line:', line.substring(0, 50));
        }
    }

    // Update UI
    ui.gameCount.textContent = state.games.length;
    ui.ruggedCount.textContent = state.games.filter(g => g.rugged).length;

    // Show seed preview
    const samples = state.games.slice(0, 3).map(g => g.server_seed);
    ui.seedPreview.textContent = samples.join('\n');

    ui.statusText.textContent = `Loaded ${state.games.length} games`;
}

// =============================================================================
// Analysis Functions
// =============================================================================

async function runAnalysis() {
    if (state.games.length === 0) {
        alert('Please load game data first');
        return;
    }

    if (state.isAnalyzing) return;

    state.isAnalyzing = true;
    ui.analyzeBtn.disabled = true;
    ui.progressContainer.style.display = 'block';

    const pattern = document.querySelector('input[name="pattern"]:checked').value;

    try {
        switch (pattern) {
            case 'hex':
                await analyzeHexFormat();
                break;
            case 'timestamp':
                await analyzeTimestampCorrelation();
                break;
            case 'sequential':
                await analyzeSequentialPatterns();
                break;
            case 'entropy':
                await analyzeEntropy();
                break;
        }
    } catch (e) {
        console.error('Analysis error:', e);
        ui.statusText.textContent = 'Analysis failed: ' + e.message;
    }

    state.isAnalyzing = false;
    ui.analyzeBtn.disabled = false;
    ui.progressContainer.style.display = 'none';
}

function updateProgress(percent, text) {
    ui.progressFill.style.width = percent + '%';
    ui.progressText.textContent = text || (percent + '%');
}

// =============================================================================
// Hex Format Analysis
// =============================================================================

async function analyzeHexFormat() {
    const results = {
        valid: 0,
        invalid: 0,
        lengthIssues: [],
        charIssues: []
    };

    const rows = [];

    for (let i = 0; i < state.games.length; i++) {
        const game = state.games[i];
        const seed = game.server_seed;

        // Check length (should be 64 chars for SHA-256)
        const isValidLength = seed.length === 64;

        // Check hex characters
        const isValidHex = /^[0-9a-f]+$/i.test(seed);

        if (!isValidLength || !isValidHex) {
            results.invalid++;
            const issue = !isValidLength ? `Length: ${seed.length}` : 'Invalid chars';
            rows.push({
                game_id: game.game_id,
                timestamp: new Date(game.timestamp_ms).toISOString(),
                seed: seed,
                peak: game.peak_multiplier,
                final: game.final_price,
                finding: issue
            });
        } else {
            results.valid++;
        }

        if (i % 100 === 0) {
            updateProgress(Math.round(i / state.games.length * 100));
            await sleep(0);
        }
    }

    // Update summary
    ui.hexSummary.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">Valid</div>
                <div class="stat-value positive">${results.valid}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Invalid</div>
                <div class="stat-value ${results.invalid > 0 ? 'negative' : ''}">${results.invalid}</div>
            </div>
        </div>
        <p style="margin-top: var(--space-sm);">
            All seeds are ${results.invalid === 0 ? 'valid' : 'NOT valid'} SHA-256 hex format (64 chars).
        </p>
    `;

    renderResults(rows);
    ui.statusText.textContent = `Hex analysis complete: ${results.valid} valid, ${results.invalid} invalid`;
}

// =============================================================================
// Timestamp Correlation Analysis
// =============================================================================

async function analyzeTimestampCorrelation() {
    const correlations = [];
    const rows = [];

    for (let i = 0; i < state.games.length; i++) {
        const game = state.games[i];
        const seed = game.server_seed;
        const ts = game.timestamp_ms;

        // Check if timestamp appears in seed (various encodings)
        const tsStr = ts.toString();
        const tsHex = ts.toString(16);
        const tsSecStr = Math.floor(ts / 1000).toString();
        const tsSecHex = Math.floor(ts / 1000).toString(16);

        let finding = null;

        if (seed.includes(tsHex)) {
            finding = `Contains ts hex: ${tsHex}`;
        } else if (seed.includes(tsSecHex)) {
            finding = `Contains ts_sec hex: ${tsSecHex}`;
        }

        // Check prefix patterns (first 8 chars might be timestamp-derived)
        const seedPrefix = seed.substring(0, 8);
        const seedPrefixInt = parseInt(seedPrefix, 16);

        // Calculate correlation coefficient with timestamp
        correlations.push({
            ts: ts,
            seedPrefix: seedPrefixInt,
            game_id: game.game_id
        });

        if (finding) {
            rows.push({
                game_id: game.game_id,
                timestamp: new Date(ts).toISOString(),
                seed: seed,
                peak: game.peak_multiplier,
                final: game.final_price,
                finding: finding
            });
        }

        if (i % 100 === 0) {
            updateProgress(Math.round(i / state.games.length * 100));
            await sleep(0);
        }
    }

    // Calculate Pearson correlation
    const correlation = calculateCorrelation(
        correlations.map(c => c.ts),
        correlations.map(c => c.seedPrefix)
    );

    ui.timestampSummary.innerHTML = `
        <p>Timestamp-to-seed-prefix correlation: <strong>${correlation.toFixed(4)}</strong></p>
        <p>Found ${rows.length} games with timestamp patterns in seeds.</p>
        <p class="text-muted" style="margin-top: var(--space-sm);">
            Correlation near 0 suggests no direct timestamp seeding.
            Values near 1 or -1 indicate predictable seeding.
        </p>
    `;

    renderResults(rows);
    ui.statusText.textContent = `Timestamp analysis complete: correlation = ${correlation.toFixed(4)}`;
}

function calculateCorrelation(x, y) {
    const n = x.length;
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = y.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((total, xi, i) => total + xi * y[i], 0);
    const sumX2 = x.reduce((total, xi) => total + xi * xi, 0);
    const sumY2 = y.reduce((total, yi) => total + yi * yi, 0);

    const numerator = n * sumXY - sumX * sumY;
    const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

    return denominator === 0 ? 0 : numerator / denominator;
}

// =============================================================================
// Sequential Pattern Analysis
// =============================================================================

async function analyzeSequentialPatterns() {
    const rows = [];
    let sequentialCount = 0;

    // Sort by timestamp
    const sortedGames = [...state.games].sort((a, b) => a.timestamp_ms - b.timestamp_ms);

    for (let i = 1; i < sortedGames.length; i++) {
        const prev = sortedGames[i - 1];
        const curr = sortedGames[i];

        // Check for sequential seed prefixes
        const prevPrefix = parseInt(prev.server_seed.substring(0, 8), 16);
        const currPrefix = parseInt(curr.server_seed.substring(0, 8), 16);

        const diff = currPrefix - prevPrefix;

        // Check if difference is small (sequential)
        if (Math.abs(diff) < 1000000) {
            sequentialCount++;
            rows.push({
                game_id: curr.game_id,
                timestamp: new Date(curr.timestamp_ms).toISOString(),
                seed: curr.server_seed,
                peak: curr.peak_multiplier,
                final: curr.final_price,
                finding: `Diff: ${diff}`
            });
        }

        if (i % 100 === 0) {
            updateProgress(Math.round(i / sortedGames.length * 100));
            await sleep(0);
        }
    }

    ui.sequentialSummary.innerHTML = `
        <p>Found <strong>${sequentialCount}</strong> potentially sequential seeds.</p>
        <p class="text-muted">
            Sequential seeds have small differences between consecutive game prefixes,
            which could indicate predictable seeding.
        </p>
    `;

    renderResults(rows.slice(0, 100));
    ui.statusText.textContent = `Sequential analysis complete: ${sequentialCount} patterns found`;
}

// =============================================================================
// Entropy Analysis
// =============================================================================

async function analyzeEntropy() {
    const entropies = [];
    const rows = [];

    for (let i = 0; i < state.games.length; i++) {
        const game = state.games[i];
        const seed = game.server_seed;

        // Calculate Shannon entropy
        const entropy = calculateEntropy(seed);
        entropies.push(entropy);

        // Flag low entropy seeds (< 3.5 bits per char is suspicious)
        if (entropy < 3.5) {
            rows.push({
                game_id: game.game_id,
                timestamp: new Date(game.timestamp_ms).toISOString(),
                seed: seed,
                peak: game.peak_multiplier,
                final: game.final_price,
                finding: `Entropy: ${entropy.toFixed(2)}`
            });
        }

        if (i % 100 === 0) {
            updateProgress(Math.round(i / state.games.length * 100));
            await sleep(0);
        }
    }

    const avgEntropy = entropies.reduce((a, b) => a + b, 0) / entropies.length;
    const minEntropy = Math.min(...entropies);
    const maxEntropy = Math.max(...entropies);

    ui.entropySummary.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">Avg Entropy</div>
                <div class="stat-value">${avgEntropy.toFixed(2)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Min</div>
                <div class="stat-value">${minEntropy.toFixed(2)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Max</div>
                <div class="stat-value">${maxEntropy.toFixed(2)}</div>
            </div>
        </div>
        <p style="margin-top: var(--space-sm);">
            Expected entropy for random hex: ~4.0 bits/char.
            ${rows.length > 0 ? `Found ${rows.length} low-entropy seeds.` : 'All seeds have good entropy.'}
        </p>
    `;

    renderResults(rows);
    ui.statusText.textContent = `Entropy analysis complete: avg = ${avgEntropy.toFixed(2)} bits/char`;
}

function calculateEntropy(str) {
    const freq = {};
    for (const char of str) {
        freq[char] = (freq[char] || 0) + 1;
    }

    let entropy = 0;
    const len = str.length;
    for (const char in freq) {
        const p = freq[char] / len;
        entropy -= p * Math.log2(p);
    }

    return entropy;
}

// =============================================================================
// UI Helpers
// =============================================================================

function updateVisibleSections() {
    const pattern = document.querySelector('input[name="pattern"]:checked').value;

    document.getElementById('hexAnalysis').style.display = pattern === 'hex' ? 'block' : 'none';
    document.getElementById('timestampAnalysis').style.display = pattern === 'timestamp' ? 'block' : 'none';
    document.getElementById('sequentialAnalysis').style.display = pattern === 'sequential' ? 'block' : 'none';
    document.getElementById('entropyAnalysis').style.display = pattern === 'entropy' ? 'block' : 'none';
}

function renderResults(rows) {
    if (rows.length === 0) {
        ui.resultsBody.innerHTML = '<tr><td colspan="6" class="text-muted">No findings</td></tr>';
        return;
    }

    ui.resultsBody.innerHTML = rows.map(row => `
        <tr>
            <td>${row.game_id.slice(-8)}</td>
            <td>${row.timestamp.substring(11, 19)}</td>
            <td class="seed-cell">${row.seed}</td>
            <td>${row.peak.toFixed(2)}x</td>
            <td>$${row.final.toFixed(4)}</td>
            <td class="highlight-match">${row.finding}</td>
        </tr>
    `).join('');
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// =============================================================================
// WebSocket Handlers
// =============================================================================

function handleConnectionChange(data) {
    if (data.connected) {
        ui.connectionDot.className = 'connection-dot connected';
        ui.connectionText.textContent = 'Connected';
    } else {
        ui.connectionDot.className = 'connection-dot disconnected';
        ui.connectionText.textContent = 'Disconnected';
    }
}

function handleGameTick(data) {
    // Store live game data for comparison
    const tickData = data.data || data;
    if (data.gameId && !state.liveGames.find(g => g.game_id === data.gameId)) {
        state.liveGames.push({
            game_id: data.gameId,
            timestamp_ms: data.ts,
            tick: tickData.tick
        });

        // Keep only last 100
        if (state.liveGames.length > 100) {
            state.liveGames.shift();
        }
    }
}

function updateMetrics() {
    if (window.wsClient) {
        const metrics = wsClient.getMetrics();
        ui.messageCount.textContent = metrics.messageCount;
        ui.avgLatency.textContent = Math.round(metrics.averageLatency);
    }
}

// =============================================================================
// Start
// =============================================================================

document.addEventListener('DOMContentLoaded', init);
