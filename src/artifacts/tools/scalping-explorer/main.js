/*
 * Scalping Strategy Explorer - Prototype Dev Lab (offline)
 *
 * Purpose:
 * - Load prerecorded games with prices[]
 * - Classify each game from configurable baseline ticks
 * - Gate simple playbooks by regime
 * - Simulate deterministic scalp exits by fixed hold ticks
 */

const state = {
    files: [],
    games: [],
    gamesById: new Map(),
    runResult: null,
    botResult: null,
    inspectGameId: null,
};

const PLAYBOOK_IDS = ["P1_MOMENTUM", "P2_PULLBACK_CONT", "P3_MEAN_REVERT", "P4_BREAKOUT"];

const REGIME_PLAYBOOK_MAP = {
    trend_up: ["P1_MOMENTUM", "P2_PULLBACK_CONT"],
    trend_down: ["P3_MEAN_REVERT"],
    expansion: ["P4_BREAKOUT", "P1_MOMENTUM"],
    chop: ["P3_MEAN_REVERT"],
    uncertain: [],
};

const PLAYBOOK_DESCRIPTIONS = {
    P1_MOMENTUM:
        "Enter when short horizon drift aligns positive: m3 > +1.5% and m5 > +2.0%.",
    P2_PULLBACK_CONT:
        "Enter on pullback continuation: m8 trend positive, last tick pullback, bounce confirmation.",
    P3_MEAN_REVERT:
        "Enter after short overreaction down move with reversal hint, aiming quick snapback.",
    P4_BREAKOUT:
        "Enter on local high breakout: current price > previous 12-tick high by >= 1% plus positive m3.",
};

const els = {
    fileInput: document.getElementById("fileInput"),
    loadBtn: document.getElementById("loadBtn"),
    clearBtn: document.getElementById("clearBtn"),
    datasetStats: document.getElementById("datasetStats"),
    holdTicks: document.getElementById("holdTicks"),
    maxGames: document.getElementById("maxGames"),
    minTicks: document.getElementById("minTicks"),
    classifyTicks: document.getElementById("classifyTicks"),
    entryCutoffTick: document.getElementById("entryCutoffTick"),
    botEnabled: document.getElementById("botEnabled"),
    botPlaybookMode: document.getElementById("botPlaybookMode"),
    botStakeSol: document.getElementById("botStakeSol"),
    botStartingBankrollSol: document.getElementById("botStartingBankrollSol"),
    botDriftReference: document.getElementById("botDriftReference"),
    botTpMultMin: document.getElementById("botTpMultMin"),
    botTpMultMax: document.getElementById("botTpMultMax"),
    botSlMultMin: document.getElementById("botSlMultMin"),
    botSlMultMax: document.getElementById("botSlMultMax"),
    botMaxHoldTicks: document.getElementById("botMaxHoldTicks"),
    botCooldownTicks: document.getElementById("botCooldownTicks"),
    botMaxTradesPerGame: document.getElementById("botMaxTradesPerGame"),
    gameSelect: document.getElementById("gameSelect"),
    runBtn: document.getElementById("runBtn"),
    inspectBtn: document.getElementById("inspectBtn"),
    quickStartBtn: document.getElementById("quickStartBtn"),
    controlsGuideBtn: document.getElementById("controlsGuideBtn"),
    resultsGuideBtn: document.getElementById("resultsGuideBtn"),
    glossaryBtn: document.getElementById("glossaryBtn"),
    helpBtn: document.getElementById("helpBtn"),
    controlStatus: document.getElementById("controlStatus"),
    classifierText: document.getElementById("classifierText"),
    resultsBody: document.getElementById("resultsBody"),
    botSummaryText: document.getElementById("botSummaryText"),
    botPermutationBody: document.getElementById("botPermutationBody"),
    botResultsBody: document.getElementById("botResultsBody"),
    regimeText: document.getElementById("regimeText"),
    ruleText: document.getElementById("ruleText"),
    debugLog: document.getElementById("debugLog"),
    gameCanvas: document.getElementById("gameCanvas"),
    tradeBody: document.getElementById("tradeBody"),
    footerInfo: document.getElementById("footerInfo"),
    helpOverlay: document.getElementById("helpOverlay"),
    helpCloseBtn: document.getElementById("helpCloseBtn"),
    helpTabBtns: Array.from(document.querySelectorAll(".help-tab-btn")),
    helpPanels: Array.from(document.querySelectorAll(".help-panel")),
};

function log(msg) {
    const ts = new Date().toISOString().slice(11, 23);
    els.debugLog.textContent = `[${ts}] ${msg}\n` + els.debugLog.textContent;
}

function getClassificationTicks() {
    const raw = Number(els.classifyTicks.value || 25);
    const ticks = Math.max(12, Math.min(800, raw));
    if (ticks !== raw) {
        els.classifyTicks.value = String(ticks);
    }
    return ticks;
}

function getEntryCutoffTick() {
    const raw = Number(els.entryCutoffTick.value || 50);
    const tick = Math.max(1, Math.min(5000, raw));
    if (tick !== raw) {
        els.entryCutoffTick.value = String(tick);
    }
    return tick;
}

function getBotSettings() {
    const enabled = Boolean(els.botEnabled.checked);

    const modeRaw = String(els.botPlaybookMode.value || "AUTO_REGIME");
    const playbookMode = modeRaw === "AUTO_REGIME" || PLAYBOOK_IDS.includes(modeRaw)
        ? modeRaw
        : "AUTO_REGIME";
    if (playbookMode !== modeRaw) {
        els.botPlaybookMode.value = playbookMode;
    }

    const stakeRaw = Number(els.botStakeSol.value || 0.1);
    const stakeSol = Math.max(0.001, Math.min(1000, stakeRaw));
    if (stakeSol !== stakeRaw) {
        els.botStakeSol.value = String(stakeSol);
    }

    const bankrollRaw = Number(els.botStartingBankrollSol.value || 10);
    const startingBankrollSol = Math.max(0.01, Math.min(100000, bankrollRaw));
    if (startingBankrollSol !== bankrollRaw) {
        els.botStartingBankrollSol.value = String(startingBankrollSol);
    }

    const driftRaw = String(els.botDriftReference.value || "P75");
    const driftReference = ["P50", "P75", "P90"].includes(driftRaw) ? driftRaw : "P75";
    if (driftReference !== driftRaw) {
        els.botDriftReference.value = driftReference;
    }

    const tpMinRaw = Number(els.botTpMultMin.value || 1);
    const tpMaxRaw = Number(els.botTpMultMax.value || 3);
    let tpMultMin = Math.max(1, Math.min(8, Math.floor(tpMinRaw)));
    let tpMultMax = Math.max(1, Math.min(8, Math.floor(tpMaxRaw)));
    if (tpMultMax < tpMultMin) {
        const tmp = tpMultMin;
        tpMultMin = tpMultMax;
        tpMultMax = tmp;
    }
    if (tpMultMin !== tpMinRaw) {
        els.botTpMultMin.value = String(tpMultMin);
    }
    if (tpMultMax !== tpMaxRaw) {
        els.botTpMultMax.value = String(tpMultMax);
    }

    const slMinRaw = Number(els.botSlMultMin.value || 1);
    const slMaxRaw = Number(els.botSlMultMax.value || 3);
    let slMultMin = Math.max(1, Math.min(8, Math.floor(slMinRaw)));
    let slMultMax = Math.max(1, Math.min(8, Math.floor(slMaxRaw)));
    if (slMultMax < slMultMin) {
        const tmp = slMultMin;
        slMultMin = slMultMax;
        slMultMax = tmp;
    }
    if (slMultMin !== slMinRaw) {
        els.botSlMultMin.value = String(slMultMin);
    }
    if (slMultMax !== slMaxRaw) {
        els.botSlMultMax.value = String(slMultMax);
    }

    const holdRaw = Number(els.botMaxHoldTicks.value || 5);
    const maxHoldTicks = Math.max(1, Math.min(200, Math.floor(holdRaw)));
    if (maxHoldTicks !== holdRaw) {
        els.botMaxHoldTicks.value = String(maxHoldTicks);
    }

    const cooldownRaw = Number(els.botCooldownTicks.value || 0);
    const cooldownTicks = Math.max(0, Math.min(500, Math.floor(cooldownRaw)));
    if (cooldownTicks !== cooldownRaw) {
        els.botCooldownTicks.value = String(cooldownTicks);
    }

    const maxTradesRaw = Number(els.botMaxTradesPerGame.value || 25);
    const maxTradesPerGame = Math.max(1, Math.min(1000, Math.floor(maxTradesRaw)));
    if (maxTradesPerGame !== maxTradesRaw) {
        els.botMaxTradesPerGame.value = String(maxTradesPerGame);
    }

    return {
        enabled,
        playbookMode,
        stakeSol,
        startingBankrollSol,
        driftReference,
        tpMultMin,
        tpMultMax,
        slMultMin,
        slMultMax,
        maxHoldTicks,
        cooldownTicks,
        maxTradesPerGame,
    };
}

function computeOneTickDriftStats(games) {
    const up = [];
    const downAbs = [];
    const allAbs = [];

    for (const game of games) {
        const prices = game.prices || [];
        for (let i = 1; i < prices.length; i += 1) {
            const retPct = (prices[i] / prices[i - 1] - 1) * 100;
            if (!Number.isFinite(retPct)) continue;
            const absPct = Math.abs(retPct);
            allAbs.push(absPct);
            if (retPct > 0) up.push(retPct);
            else if (retPct < 0) downAbs.push(absPct);
        }
    }

    return {
        upP50: percentile(up, 0.5),
        upP75: percentile(up, 0.75),
        upP90: percentile(up, 0.9),
        downP50: percentile(downAbs, 0.5),
        downP75: percentile(downAbs, 0.75),
        downP90: percentile(downAbs, 0.9),
        absP50: percentile(allAbs, 0.5),
        absP75: percentile(allAbs, 0.75),
        absP90: percentile(allAbs, 0.9),
        sampleCount: allAbs.length,
    };
}

function selectDriftReferenceValues(driftStats, driftReference) {
    if (driftReference === "P50") {
        return { upPct: driftStats.upP50, downPct: driftStats.downP50 };
    }
    if (driftReference === "P90") {
        return { upPct: driftStats.upP90, downPct: driftStats.downP90 };
    }
    return { upPct: driftStats.upP75, downPct: driftStats.downP75 };
}

function buildDriftPermutations(botSettings, driftUpPct, driftDownPct) {
    const perms = [];
    const tpUnit = Math.max(0.05, driftUpPct);
    const slUnit = Math.max(0.05, driftDownPct);

    for (let tpMult = botSettings.tpMultMin; tpMult <= botSettings.tpMultMax; tpMult += 1) {
        for (let slMult = botSettings.slMultMin; slMult <= botSettings.slMultMax; slMult += 1) {
            const takeProfitPct = tpUnit * tpMult;
            const stopLossPct = slUnit * slMult;
            perms.push({
                id: `TPx${tpMult}_SLx${slMult}`,
                tpMult,
                slMult,
                takeProfitPct,
                stopLossPct,
            });
        }
    }

    return perms;
}

function setRulesText(classificationTicks = getClassificationTicks(), entryCutoffTick = getEntryCutoffTick()) {
    const lines = [
        "Regime to playbook gate map:",
        "- trend_up -> P1_MOMENTUM, P2_PULLBACK_CONT",
        "- trend_down -> P3_MEAN_REVERT",
        "- expansion -> P4_BREAKOUT, P1_MOMENTUM",
        "- chop -> P3_MEAN_REVERT",
        "- uncertain -> no trade",
        "",
        "Playbook descriptions:",
    ];

    Object.entries(PLAYBOOK_DESCRIPTIONS).forEach(([id, txt]) => {
        lines.push(`- ${id}: ${txt}`);
    });

    lines.push("", `Classifier uses first ${classificationTicks} ticks only.`);
    lines.push(`Simulation starts at tick ${classificationTicks + 1} with one active trade at a time.`);
    lines.push(`No new entries after tick ${entryCutoffTick}.`);
    if (entryCutoffTick <= classificationTicks) {
        lines.push("Current cutoff is inside the classifier window, so no entries will be attempted.");
    }

    els.ruleText.textContent = lines.join("\n");
}

function resetDataset() {
    state.files = [];
    state.games = [];
    state.gamesById.clear();
    state.runResult = null;
    state.botResult = null;
    state.inspectGameId = null;
    els.resultsBody.innerHTML = "";
    els.botPermutationBody.innerHTML = "";
    els.botResultsBody.innerHTML = "";
    els.tradeBody.innerHTML = "";
    els.botSummaryText.textContent = "Bot not run yet. Click Run Test after loading a dataset.";
    els.classifierText.textContent = "No game inspected yet.";
    els.regimeText.textContent = "No run yet.";
    els.gameSelect.innerHTML = "";
    els.datasetStats.textContent = "no dataset loaded";
    els.footerInfo.textContent = "No dataset";
    els.controlStatus.textContent = "Dataset cleared. Load games, then click Run Test.";
    clearCanvas();
    log("dataset cleared");
}

function clearCanvas() {
    const ctx = els.gameCanvas.getContext("2d");
    ctx.fillStyle = "#11111b";
    ctx.fillRect(0, 0, els.gameCanvas.width, els.gameCanvas.height);
    ctx.fillStyle = "#a6adc8";
    ctx.font = "12px monospace";
    ctx.fillText("No game inspected", 12, 20);
}

function parseJsonLines(text) {
    const rows = [];
    const lines = text.split(/\r?\n/);

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
            rows.push(JSON.parse(trimmed));
        } catch (err) {
            // ignore malformed line
        }
    }

    return rows;
}

function normalizePayloadToObject(payload) {
    if (!payload) return null;
    if (Array.isArray(payload)) {
        if (payload.length === 0) return null;
        if (typeof payload[0] === "object") return payload[0];
        return null;
    }
    if (typeof payload === "object") return payload;
    return null;
}

function addGameCandidate(candidate, sourceLabel) {
    if (!candidate || typeof candidate !== "object") return;
    const prices = Array.isArray(candidate.prices) ? candidate.prices : null;
    if (!prices || prices.length < 30) return;

    const gameId =
        candidate.game_id ||
        candidate.gameId ||
        candidate.id ||
        `${sourceLabel}-game-${state.games.length + 1}`;

    const cleanedPrices = prices
        .map((v) => Number(v))
        .filter((v) => Number.isFinite(v) && v > 0);

    if (cleanedPrices.length < 30) return;
    if (state.gamesById.has(gameId)) return;

    const game = {
        gameId,
        prices: cleanedPrices,
        duration: cleanedPrices.length,
        source: sourceLabel,
        peakMultiplier: Number(candidate.peakMultiplier || Math.max(...cleanedPrices)),
        rugged: candidate.rugged !== undefined ? Boolean(candidate.rugged) : true,
        raw: candidate,
    };

    state.gamesById.set(gameId, game);
    state.games.push(game);
}

function extractGamesFromObject(obj, sourceLabel) {
    if (!obj) return;

    if (Array.isArray(obj)) {
        for (const item of obj) {
            extractGamesFromObject(item, sourceLabel);
        }
        return;
    }

    if (typeof obj !== "object") return;

    // complete_game style
    if (obj.raw_json && typeof obj.raw_json === "string") {
        try {
            const raw = JSON.parse(obj.raw_json);
            addGameCandidate({ ...raw, game_id: obj.game_id || raw.id }, sourceLabel);
        } catch (err) {
            // ignore
        }
    }

    // direct game candidate
    if (Array.isArray(obj.prices)) {
        addGameCandidate(obj, sourceLabel);
    }

    // gameStateUpdate with gameHistory
    const payload = normalizePayloadToObject(obj.data || obj.payload || obj.event_data);
    if (obj.event === "gameStateUpdate" || obj.event_name === "gameStateUpdate") {
        const dataObj = payload || obj.data || obj;
        if (dataObj && Array.isArray(dataObj.gameHistory)) {
            for (const g of dataObj.gameHistory) {
                addGameCandidate(g, sourceLabel);
            }
        }
    }

    // nested known fields
    const nested = ["gameHistory", "games", "items", "records", "data"];
    for (const key of nested) {
        if (obj[key]) {
            extractGamesFromObject(obj[key], sourceLabel);
        }
    }
}

async function loadSelectedFiles() {
    const files = Array.from(els.fileInput.files || []);
    if (!files.length) {
        log("load requested with no files selected");
        return;
    }

    const beforeCount = state.games.length;
    log(`loading ${files.length} file(s)`);

    for (const file of files) {
        const text = await file.text();
        const sourceLabel = file.name;

        if (file.name.endsWith(".jsonl")) {
            const rows = parseJsonLines(text);
            extractGamesFromObject(rows, sourceLabel);
            log(`parsed ${file.name}: ${rows.length} jsonl rows`);
            continue;
        }

        try {
            const json = JSON.parse(text);
            extractGamesFromObject(json, sourceLabel);
            log(`parsed ${file.name}: json root type ${Array.isArray(json) ? "array" : "object"}`);
        } catch (err) {
            const rows = parseJsonLines(text);
            extractGamesFromObject(rows, sourceLabel);
            log(`fallback jsonl parse for ${file.name}: ${rows.length} rows`);
        }
    }

    const added = state.games.length - beforeCount;
    state.games.sort((a, b) => a.gameId.localeCompare(b.gameId));
    refreshGameSelect();

    els.datasetStats.textContent = `${state.games.length} unique games loaded`;
    els.footerInfo.textContent = `${state.games.length} games in memory`;
    els.controlStatus.textContent = added > 0
        ? `Loaded ${added} new games (total ${state.games.length}).`
        : `No new games found in selected files.`;

    log(`dataset load complete: +${added} games, total=${state.games.length}`);
}

function refreshGameSelect() {
    const options = state.games.slice(0, 5000).map((g) => {
        return `<option value="${g.gameId}">${g.gameId} | ticks=${g.duration} | src=${g.source}</option>`;
    });

    els.gameSelect.innerHTML = options.join("");

    if (!state.inspectGameId && state.games.length) {
        state.inspectGameId = state.games[0].gameId;
        els.gameSelect.value = state.inspectGameId;
    }
}

function mean(arr) {
    if (!arr.length) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function std(arr) {
    if (arr.length < 2) return 0;
    const m = mean(arr);
    const variance = mean(arr.map((v) => (v - m) ** 2));
    return Math.sqrt(variance);
}

function percentile(arr, p) {
    if (!arr.length) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    const idx = Math.floor((sorted.length - 1) * p);
    return sorted[idx];
}

function classifyGame(game, classificationTicks = 25) {
    const prices = game.prices;
    const classifierWindow = Math.max(12, classificationTicks);
    const requiredTicks = classifierWindow + 1;
    if (prices.length < requiredTicks) {
        return {
            regime: "uncertain",
            confidence: 0.2,
            reasons: [`insufficient ticks for first-${classifierWindow} classifier`],
            features: { classificationTicks: classifierWindow },
        };
    }

    const first = prices.slice(0, requiredTicks);
    const returns = [];
    for (let i = 1; i < first.length; i += 1) {
        returns.push(first[i] / first[i - 1] - 1);
    }

    const lastIdx = first.length - 1;
    const tailSpan = Math.min(10, lastIdx);
    const tailStart = Math.max(0, lastIdx - tailSpan);
    const momentumWindow = first[lastIdx] / first[0] - 1;
    const momentumTail = first[lastIdx] / first[tailStart] - 1;
    const vol = std(returns);
    const pMin = Math.min(...first);
    const pMax = Math.max(...first);
    const range = pMax / pMin - 1;

    let signFlips = 0;
    for (let i = 1; i < returns.length; i += 1) {
        if (Math.sign(returns[i]) !== 0 && Math.sign(returns[i - 1]) !== 0 && Math.sign(returns[i]) !== Math.sign(returns[i - 1])) {
            signFlips += 1;
        }
    }

    const splitIdx = Math.max(1, Math.floor(returns.length / 2));
    const earlySlice = returns.slice(0, splitIdx);
    const lateSlice = returns.slice(splitIdx);
    const absEarly = mean(earlySlice.map(Math.abs));
    const absLate = lateSlice.length ? mean(lateSlice.map(Math.abs)) : absEarly;
    const expansionRatio = absEarly > 0 ? absLate / absEarly : 1;

    // Scale core momentum/chop thresholds so baseline size changes are more comparable.
    const baselineScale = Math.sqrt(classifierWindow / 25);
    const trendMomentumThreshold = 0.06 * baselineScale;
    const chopMomentumThreshold = 0.025 * baselineScale;
    const trendFlipMax = Math.max(8, Math.round(returns.length * 0.34));
    const downFlipMax = Math.max(9, Math.round(returns.length * 0.36));
    const chopFlipMin = Math.max(12, Math.round(returns.length * 0.50));

    let regime = "uncertain";
    let confidence = 0.5;
    const reasons = [];

    if (momentumWindow > trendMomentumThreshold && signFlips <= trendFlipMax) {
        regime = "trend_up";
        confidence = Math.min(0.95, 0.55 + momentumWindow * 2 + (trendFlipMax - signFlips) * 0.02);
        reasons.push(`positive momentum in first ${classifierWindow} ticks`);
        reasons.push("lower sign-flip count supports continuation");
    } else if (momentumWindow < -trendMomentumThreshold && signFlips <= downFlipMax) {
        regime = "trend_down";
        confidence = Math.min(0.95, 0.55 + Math.abs(momentumWindow) * 2 + (downFlipMax - signFlips) * 0.02);
        reasons.push(`negative momentum in first ${classifierWindow} ticks`);
        reasons.push("directional consistency supports trend-down classification");
    } else if (vol > 0.04 || range > 0.20 || expansionRatio > 1.55) {
        regime = "expansion";
        confidence = Math.min(0.92, 0.52 + vol * 5 + Math.min(0.25, (range - 0.10)) + (expansionRatio - 1) * 0.08);
        reasons.push(`high realized volatility or range growth in first ${classifierWindow} ticks`);
        reasons.push("late/early volatility ratio implies expansion state");
    } else if (signFlips >= chopFlipMin || (Math.abs(momentumWindow) < chopMomentumThreshold && vol > 0.018)) {
        regime = "chop";
        confidence = Math.min(0.9, 0.5 + Math.max(0, signFlips - (chopFlipMin - 2)) * 0.04 + vol * 2.2);
        reasons.push("high sign-flip count indicates oscillatory behavior");
        reasons.push("net momentum small relative to local volatility");
    } else {
        regime = "uncertain";
        confidence = 0.38;
        reasons.push("features do not pass clear trend/chop/expansion thresholds");
    }

    return {
        regime,
        confidence,
        reasons,
        features: {
            classificationTicks: classifierWindow,
            momentumWindow,
            momentumTail,
            vol,
            range,
            signFlips,
            expansionRatio,
            pMin,
            pMax,
        },
    };
}

function playbookSignal(playbookId, prices, t) {
    if (t < 12) return { enter: false, reason: "not enough lookback" };

    const p = prices[t];
    const m1 = p / prices[t - 1] - 1;
    const m2 = p / prices[t - 2] - 1;
    const m3 = p / prices[t - 3] - 1;
    const m5 = p / prices[t - 5] - 1;
    const m8 = p / prices[t - 8] - 1;

    if (playbookId === "P1_MOMENTUM") {
        const enter = m3 > 0.015 && m5 > 0.02;
        return { enter, reason: `m3=${(m3 * 100).toFixed(2)}%, m5=${(m5 * 100).toFixed(2)}%` };
    }

    if (playbookId === "P2_PULLBACK_CONT") {
        const pullback = m1 < -0.005;
        const trend = m8 > 0.03;
        const bounce = m2 > 0.003;
        const enter = trend && pullback && bounce;
        return {
            enter,
            reason: `trend8=${(m8 * 100).toFixed(2)}%, pullback1=${(m1 * 100).toFixed(2)}%, bounce2=${(m2 * 100).toFixed(2)}%`,
        };
    }

    if (playbookId === "P3_MEAN_REVERT") {
        const dump = m3 < -0.03;
        const reflex = m1 > 0.004;
        const enter = dump && reflex;
        return {
            enter,
            reason: `dump3=${(m3 * 100).toFixed(2)}%, reflex1=${(m1 * 100).toFixed(2)}%`,
        };
    }

    if (playbookId === "P4_BREAKOUT") {
        const lookback = prices.slice(t - 12, t);
        const localHigh = Math.max(...lookback);
        const breakout = p > localHigh * 1.01;
        const confirm = m3 > 0.01;
        const enter = breakout && confirm;
        return {
            enter,
            reason: `price=${p.toFixed(4)} > high12*1.01=${(localHigh * 1.01).toFixed(4)}, m3=${(m3 * 100).toFixed(2)}%`,
        };
    }

    return { enter: false, reason: "unknown playbook" };
}

function simulatePlaybookOnGame(game, playbookId, holdTicks, startTick, entryCutoffTick) {
    const prices = game.prices;
    const trades = [];

    for (let t = startTick; t + holdTicks < prices.length && t <= entryCutoffTick; t += 1) {
        const signal = playbookSignal(playbookId, prices, t);
        if (!signal.enter) continue;

        const entryTick = t;
        const exitTick = t + holdTicks;
        const entryPrice = prices[entryTick];
        const exitPrice = prices[exitTick];
        const retPct = (exitPrice / entryPrice - 1) * 100;

        trades.push({
            playbookId,
            gameId: game.gameId,
            entryTick,
            exitTick,
            entryPrice,
            exitPrice,
            retPct,
            reason: signal.reason,
        });

        // one active trade at a time, skip to exit tick
        t = exitTick;
    }

    return trades;
}

function simulateBotOnGame(game, classification, botSettings, startTick, entryCutoffTick, permutation) {
    if (!botSettings.enabled) return [];

    const prices = game.prices;
    const trades = [];
    let nextEligibleTick = startTick;

    const candidatePlaybooks = botSettings.playbookMode === "AUTO_REGIME"
        ? (REGIME_PLAYBOOK_MAP[classification.regime] || [])
        : [botSettings.playbookMode];

    if (!candidatePlaybooks.length) return trades;

    const lastEntryTick = Math.min(entryCutoffTick, prices.length - 2);
    for (let t = startTick; t <= lastEntryTick; t += 1) {
        if (t < nextEligibleTick) continue;
        if (trades.length >= botSettings.maxTradesPerGame) break;

        let chosenPlaybook = null;
        let chosenSignal = null;

        for (const playbookId of candidatePlaybooks) {
            const signal = playbookSignal(playbookId, prices, t);
            if (!signal.enter) continue;
            chosenPlaybook = playbookId;
            chosenSignal = signal;
            break;
        }

        if (!chosenPlaybook || !chosenSignal) continue;

        const entryTick = t;
        const entryPrice = prices[entryTick];
        const maxExitTick = Math.min(prices.length - 1, entryTick + botSettings.maxHoldTicks);

        let exitTick = maxExitTick;
        let exitReason = "TIME";

        for (let k = entryTick + 1; k <= maxExitTick; k += 1) {
            const retPct = (prices[k] / entryPrice - 1) * 100;
            if (retPct >= permutation.takeProfitPct) {
                exitTick = k;
                exitReason = "TP";
                break;
            }
            if (retPct <= -permutation.stopLossPct) {
                exitTick = k;
                exitReason = "SL";
                break;
            }
        }

        const exitPrice = prices[exitTick];
        const retPct = (exitPrice / entryPrice - 1) * 100;
        const pnlSol = (retPct / 100) * botSettings.stakeSol;

        trades.push({
            gameId: game.gameId,
            regime: classification.regime,
            playbookId: chosenPlaybook,
            permutationId: permutation.id,
            tpMult: permutation.tpMult,
            slMult: permutation.slMult,
            takeProfitPct: permutation.takeProfitPct,
            stopLossPct: permutation.stopLossPct,
            entryTick,
            exitTick,
            holdTicks: exitTick - entryTick,
            entryPrice,
            exitPrice,
            retPct,
            pnlSol,
            exitReason,
            reason: chosenSignal.reason,
        });

        nextEligibleTick = exitTick + botSettings.cooldownTicks + 1;
        t = exitTick;
    }

    return trades;
}

function summarizeTrades(trades) {
    const returns = trades.map((t) => t.retPct);
    const wins = returns.filter((r) => r > 0).length;

    return {
        tradeCount: trades.length,
        winRate: trades.length ? (wins / trades.length) * 100 : 0,
        meanRet: mean(returns),
        medianRet: percentile(returns, 0.5),
        p10: percentile(returns, 0.1),
        p90: percentile(returns, 0.9),
    };
}

function runSimulation() {
    if (!state.games.length) {
        log("run aborted: no games loaded");
        els.controlStatus.textContent = "No games loaded yet. Load files first.";
        return;
    }

    const holdTicks = Number(els.holdTicks.value);
    const maxGames = Math.max(1, Number(els.maxGames.value || 500));
    const minTicks = Math.max(30, Number(els.minTicks.value || 60));
    const classificationTicks = getClassificationTicks();
    const entryCutoffTick = getEntryCutoffTick();
    const botSettings = getBotSettings();
    const startTick = classificationTicks + 1;
    const requiredTicks = Math.max(minTicks, startTick + holdTicks + 1);
    setRulesText(classificationTicks, entryCutoffTick);

    const filteredGames = state.games
        .filter((g) => g.prices.length >= requiredTicks)
        .slice(0, maxGames);

    const byPlaybook = {
        P1_MOMENTUM: [],
        P2_PULLBACK_CONT: [],
        P3_MEAN_REVERT: [],
        P4_BREAKOUT: [],
    };

    const regimeCounts = {
        trend_up: 0,
        trend_down: 0,
        expansion: 0,
        chop: 0,
        uncertain: 0,
    };

    const perGame = new Map();
    const driftStats = computeOneTickDriftStats(filteredGames);
    const driftRef = selectDriftReferenceValues(driftStats, botSettings.driftReference);
    const permutations = buildDriftPermutations(botSettings, driftRef.upPct, driftRef.downPct);

    const botAggByPermutation = new Map();
    for (const p of permutations) {
        botAggByPermutation.set(p.id, {
            permutation: p,
            trades: [],
            exitCounts: { TP: 0, SL: 0, TIME: 0 },
            gamesTraded: 0,
            perGameTrades: new Map(),
        });
    }

    for (const game of filteredGames) {
        const cls = classifyGame(game, classificationTicks);
        regimeCounts[cls.regime] += 1;

        const allowed = REGIME_PLAYBOOK_MAP[cls.regime] || [];
        const gameTrades = [];

        for (const playbookId of allowed) {
            const trades = simulatePlaybookOnGame(game, playbookId, holdTicks, startTick, entryCutoffTick);
            byPlaybook[playbookId].push(...trades);
            gameTrades.push(...trades);
        }

        perGame.set(game.gameId, { classification: cls, trades: gameTrades, botTrades: [] });

        for (const p of permutations) {
            const botTrades = simulateBotOnGame(game, cls, botSettings, startTick, entryCutoffTick, p);
            const agg = botAggByPermutation.get(p.id);
            agg.perGameTrades.set(game.gameId, botTrades);

            if (botTrades.length) {
                agg.gamesTraded += 1;
            }

            for (const t of botTrades) {
                agg.trades.push(t);
                if (agg.exitCounts[t.exitReason] !== undefined) {
                    agg.exitCounts[t.exitReason] += 1;
                }
            }
        }
    }

    const summaries = Object.entries(byPlaybook).map(([playbookId, trades]) => {
        const s = summarizeTrades(trades);
        return {
            playbookId,
            ...s,
            regimes: Object.entries(REGIME_PLAYBOOK_MAP)
                .filter(([, arr]) => arr.includes(playbookId))
                .map(([r]) => r)
                .join(", "),
            trades,
        };
    });

    state.runResult = {
        holdTicks,
        minTicks,
        classificationTicks,
        entryCutoffTick,
        botSettings,
        startTick,
        requiredTicks,
        filteredGameCount: filteredGames.length,
        regimeCounts,
        summaries,
        perGame,
    };

    const permutationSummaries = permutations.map((p) => {
        const agg = botAggByPermutation.get(p.id);
        const tradeSummary = summarizeTrades(agg.trades);
        const totalRet = agg.trades.reduce((acc, t) => acc + t.retPct, 0);
        const netSol = agg.trades.reduce((acc, t) => acc + t.pnlSol, 0);

        return {
            id: p.id,
            tpMult: p.tpMult,
            slMult: p.slMult,
            takeProfitPct: p.takeProfitPct,
            stopLossPct: p.stopLossPct,
            tradeCount: tradeSummary.tradeCount,
            winRate: tradeSummary.winRate,
            meanRet: tradeSummary.meanRet,
            medianRet: tradeSummary.medianRet,
            p10: tradeSummary.p10,
            p90: tradeSummary.p90,
            totalRet,
            netSol,
            endSol: botSettings.startingBankrollSol + netSol,
            gamesTraded: agg.gamesTraded,
            exitCounts: agg.exitCounts,
            trades: agg.trades,
            perGameTrades: agg.perGameTrades,
        };
    }).sort((a, b) => {
        if (b.netSol !== a.netSol) return b.netSol - a.netSol;
        if (b.winRate !== a.winRate) return b.winRate - a.winRate;
        return b.tradeCount - a.tradeCount;
    });

    const selectedPermutation = permutationSummaries[0] || null;
    const selectedTrades = selectedPermutation ? selectedPermutation.trades : [];
    const selectedGameRows = [];

    if (selectedPermutation) {
        for (const game of filteredGames) {
            const gameId = game.gameId;
            const gameBotTrades = selectedPermutation.perGameTrades.get(gameId) || [];
            const row = perGame.get(gameId);
            row.botTrades = gameBotTrades;

            if (!gameBotTrades.length) continue;

            const s = summarizeTrades(gameBotTrades);
            const netSol = gameBotTrades.reduce((acc, t) => acc + t.pnlSol, 0);
            const exitCounts = { TP: 0, SL: 0, TIME: 0 };
            for (const t of gameBotTrades) {
                if (exitCounts[t.exitReason] !== undefined) {
                    exitCounts[t.exitReason] += 1;
                }
            }

            selectedGameRows.push({
                gameId,
                tradeCount: gameBotTrades.length,
                winRate: s.winRate,
                netSol,
                endSol: botSettings.startingBankrollSol + netSol,
                exitCounts,
            });
        }
    }

    selectedGameRows.sort((a, b) => b.netSol - a.netSol);

    state.botResult = {
        settings: botSettings,
        driftStats,
        driftReferenceUpPct: driftRef.upPct,
        driftReferenceDownPct: driftRef.downPct,
        permutations: permutationSummaries,
        selectedPermutationId: selectedPermutation ? selectedPermutation.id : null,
        selectedPermutation,
        tradeCount: selectedTrades.length,
        gamesAnalyzed: filteredGames.length,
        gamesTraded: selectedPermutation ? selectedPermutation.gamesTraded : 0,
        winRate: selectedPermutation ? selectedPermutation.winRate : 0,
        meanRet: selectedPermutation ? selectedPermutation.meanRet : 0,
        medianRet: selectedPermutation ? selectedPermutation.medianRet : 0,
        p10: selectedPermutation ? selectedPermutation.p10 : 0,
        p90: selectedPermutation ? selectedPermutation.p90 : 0,
        totalRet: selectedPermutation ? selectedPermutation.totalRet : 0,
        netSol: selectedPermutation ? selectedPermutation.netSol : 0,
        endSol: selectedPermutation ? selectedPermutation.endSol : botSettings.startingBankrollSol,
        exitCounts: selectedPermutation ? selectedPermutation.exitCounts : { TP: 0, SL: 0, TIME: 0 },
        trades: selectedTrades,
        gameRows: selectedGameRows,
    };

    renderRunResult();
    renderBotResult();
    els.controlStatus.textContent = `Run complete: ${filteredGames.length} games analyzed, ${selectedTrades.length} bot trades (best drift permutation).`;
    log(`run complete: games=${filteredGames.length}, classify=${classificationTicks}, startTick=${startTick}, entryCutoff=${entryCutoffTick}, hold=${holdTicks}, driftRef=${botSettings.driftReference}, permutations=${permutationSummaries.length}, selectedBotTrades=${selectedTrades.length}, requiredTicks=${requiredTicks}`);

    if (!state.inspectGameId && filteredGames.length) {
        state.inspectGameId = filteredGames[0].gameId;
    }
}

function renderRunResult() {
    if (!state.runResult) return;

    const rows = state.runResult.summaries.map((s) => {
        return `<tr>
            <td>${s.playbookId}</td>
            <td>${s.tradeCount}</td>
            <td>${s.winRate.toFixed(1)}%</td>
            <td>${s.meanRet.toFixed(2)}%</td>
            <td>${s.medianRet.toFixed(2)}%</td>
            <td>${s.p10.toFixed(2)}% / ${s.p90.toFixed(2)}%</td>
            <td>${s.regimes}</td>
        </tr>`;
    });

    els.resultsBody.innerHTML = rows.join("");

    const rc = state.runResult.regimeCounts;
    const total = state.runResult.filteredGameCount || 1;
    const cTicks = state.runResult.classificationTicks;
    const entryCutoffTick = state.runResult.entryCutoffTick;
    const startTick = state.runResult.startTick;
    const reqTicks = state.runResult.requiredTicks;
    const lines = [
        `games analyzed: ${total}`,
        `classification ticks: ${cTicks}`,
        `simulation start tick: ${startTick}`,
        `no-new-entry after tick: ${entryCutoffTick}`,
        `effective min game length: ${reqTicks}`,
        `trend_up:   ${rc.trend_up} (${((rc.trend_up / total) * 100).toFixed(1)}%)`,
        `trend_down: ${rc.trend_down} (${((rc.trend_down / total) * 100).toFixed(1)}%)`,
        `expansion:  ${rc.expansion} (${((rc.expansion / total) * 100).toFixed(1)}%)`,
        `chop:       ${rc.chop} (${((rc.chop / total) * 100).toFixed(1)}%)`,
        `uncertain:  ${rc.uncertain} (${((rc.uncertain / total) * 100).toFixed(1)}%)`,
    ];
    els.regimeText.textContent = lines.join("\n");
}

function renderBotResult() {
    if (!state.botResult) {
        els.botSummaryText.textContent = "Bot not run yet. Click Run Test after loading a dataset.";
        els.botPermutationBody.innerHTML = "<tr><td colspan='7'>Bot not run yet. Click Run Test.</td></tr>";
        els.botResultsBody.innerHTML = "<tr><td colspan='7'>Bot not run yet. Click Run Test.</td></tr>";
        return;
    }

    const r = state.botResult;
    const s = r.settings;

    if (!s.enabled) {
        els.botSummaryText.textContent = [
            "bot simulator: disabled",
            "Enable the bot in Bot Strategy Menu, then run the test again.",
        ].join("\n");
        els.botPermutationBody.innerHTML = "<tr><td colspan='7'>Bot disabled for this run.</td></tr>";
        els.botResultsBody.innerHTML = "<tr><td colspan='7'>Bot disabled for this run.</td></tr>";
        return;
    }

    const selected = r.selectedPermutation;
    const lines = [
        `games analyzed: ${r.gamesAnalyzed}`,
        `bot signal source: ${s.playbookMode}`,
        `one-tick drift reference (${s.driftReference}): up=${r.driftReferenceUpPct.toFixed(3)}%, down=${r.driftReferenceDownPct.toFixed(3)}%`,
        `tp multiplier range: ${s.tpMultMin}..${s.tpMultMax} | sl multiplier range: ${s.slMultMin}..${s.slMultMax}`,
        `maxHold/cooldown/maxTradesPerGame: ${s.maxHoldTicks} / ${s.cooldownTicks} / ${s.maxTradesPerGame}`,
        `stake per trade: ${s.stakeSol.toFixed(4)} SOL | starting bankroll: ${s.startingBankrollSol.toFixed(4)} SOL`,
        selected ? `selected permutation: TPx${selected.tpMult} / SLx${selected.slMult} => +${selected.takeProfitPct.toFixed(3)}% / -${selected.stopLossPct.toFixed(3)}%` : "selected permutation: n/a",
        `games with >=1 bot trade: ${r.gamesTraded}`,
        `bot trades (selected permutation): ${r.tradeCount}`,
        `win rate: ${r.winRate.toFixed(1)}%`,
        `mean/median return: ${r.meanRet.toFixed(2)}% / ${r.medianRet.toFixed(2)}%`,
        `p10/p90: ${r.p10.toFixed(2)}% / ${r.p90.toFixed(2)}%`,
        `sum of trade returns: ${r.totalRet.toFixed(2)}%`,
        `net pnl: ${r.netSol.toFixed(4)} SOL | ending bankroll: ${r.endSol.toFixed(4)} SOL`,
        `exit reasons (TP/SL/TIME): ${r.exitCounts.TP} / ${r.exitCounts.SL} / ${r.exitCounts.TIME}`,
    ];
    els.botSummaryText.textContent = lines.join("\n");

    if (!r.permutations.length) {
        els.botPermutationBody.innerHTML = "<tr><td colspan='7'>No permutations available under current settings.</td></tr>";
    } else {
        const permRows = r.permutations.slice(0, 120).map((p, idx) => {
            const selectedStyle = p.id === r.selectedPermutationId
                ? " style='background: rgba(166, 227, 161, 0.10);'"
                : "";
            return `<tr${selectedStyle}>
                <td>${idx + 1}</td>
                <td>TPx${p.tpMult} / SLx${p.slMult}</td>
                <td>+${p.takeProfitPct.toFixed(3)}% / -${p.stopLossPct.toFixed(3)}%</td>
                <td>${p.tradeCount}</td>
                <td>${p.winRate.toFixed(1)}%</td>
                <td>${p.netSol.toFixed(4)}</td>
                <td>${p.endSol.toFixed(4)}</td>
            </tr>`;
        });
        els.botPermutationBody.innerHTML = permRows.join("");
    }

    if (!r.gameRows.length) {
        els.botResultsBody.innerHTML = "<tr><td colspan='7'>No end-of-game SOL outcomes under current settings.</td></tr>";
        return;
    }

    const rows = r.gameRows.slice(0, 500).map((g, idx) => {
        return `<tr>
            <td>${idx + 1}</td>
            <td>${g.gameId}</td>
            <td>${g.tradeCount}</td>
            <td>${g.winRate.toFixed(1)}%</td>
            <td>${g.netSol.toFixed(4)}</td>
            <td>${g.endSol.toFixed(4)}</td>
            <td>${g.exitCounts.TP}/${g.exitCounts.SL}/${g.exitCounts.TIME}</td>
        </tr>`;
    });

    els.botResultsBody.innerHTML = rows.join("");
}

function inspectSelectedGame() {
    const gameId = els.gameSelect.value;
    if (!gameId) {
        log("inspect aborted: no game selected");
        return;
    }

    const game = state.gamesById.get(gameId);
    if (!game) {
        log(`inspect aborted: unknown game ${gameId}`);
        return;
    }

    state.inspectGameId = gameId;

    const classificationTicks = state.runResult?.classificationTicks || getClassificationTicks();
    const entryCutoffTick = state.runResult?.entryCutoffTick || getEntryCutoffTick();
    const cls = classifyGame(game, classificationTicks);
    let trades = [];
    let botTrades = [];

    if (state.runResult && state.runResult.perGame.has(gameId)) {
        const row = state.runResult.perGame.get(gameId);
        trades = row.trades;
        botTrades = row.botTrades || [];
    }

    renderClassifier(game, cls, trades.length, botTrades.length, classificationTicks, entryCutoffTick);
    renderTradeTable(botTrades.length ? botTrades : trades);
    drawGameChart(game, botTrades.length ? botTrades : trades, classificationTicks, entryCutoffTick);
    log(`inspected game ${gameId} | classify=${classificationTicks} | entryCutoff=${entryCutoffTick} | regime=${cls.regime} | trades=${trades.length} | botTrades=${botTrades.length}`);
}

function renderClassifier(game, cls, tradeCount, botTradeCount, classificationTicks, entryCutoffTick) {
    const f = cls.features;
    const text = [
        `game: ${game.gameId}`,
        `source: ${game.source}`,
        `ticks: ${game.prices.length}`,
        `peak: ${game.peakMultiplier.toFixed(4)}x`,
        "",
        `classification ticks: ${classificationTicks}`,
        `no-new-entry after tick: ${entryCutoffTick}`,
        `regime: ${cls.regime}`,
        `confidence: ${(cls.confidence * 100).toFixed(1)}%`,
        "",
        `first-${classificationTicks} feature snapshot:`,
        f.momentumWindow !== undefined ? `- momentumWindow: ${(f.momentumWindow * 100).toFixed(2)}%` : "- momentumWindow: n/a",
        f.momentumTail !== undefined ? `- momentumTail: ${(f.momentumTail * 100).toFixed(2)}%` : "- momentumTail: n/a",
        f.vol !== undefined ? `- volatility: ${(f.vol * 100).toFixed(2)}%` : "- volatility: n/a",
        f.range !== undefined ? `- range: ${(f.range * 100).toFixed(2)}%` : "- range: n/a",
        f.signFlips !== undefined ? `- signFlips: ${f.signFlips}` : "- signFlips: n/a",
        f.expansionRatio !== undefined ? `- expansionRatio: ${f.expansionRatio.toFixed(3)}` : "- expansionRatio: n/a",
        "",
        "classification reasons:",
        ...cls.reasons.map((r) => `- ${r}`),
        "",
        `regime-gated simulated trades in current run: ${tradeCount}`,
        `bot simulated trades in current run: ${botTradeCount}`,
    ];

    els.classifierText.textContent = text.join("\n");
}

function renderTradeTable(trades) {
    if (!trades.length) {
        els.tradeBody.innerHTML = "<tr><td colspan='8'>No trades for this game under current run.</td></tr>";
        return;
    }

    const rows = trades.slice(0, 300).map((t, idx) => {
        const reasonParts = [];
        if (t.reason) reasonParts.push(t.reason);
        if (t.exitReason) reasonParts.push(`exit=${t.exitReason}`);
        if (Number.isFinite(t.pnlSol)) reasonParts.push(`pnl=${t.pnlSol.toFixed(4)} SOL`);
        const reasonText = reasonParts.join(" | ");
        return `<tr>
            <td>${idx + 1}</td>
            <td>${t.playbookId}</td>
            <td>${t.entryTick}</td>
            <td>${t.exitTick}</td>
            <td>${t.entryPrice.toFixed(5)}</td>
            <td>${t.exitPrice.toFixed(5)}</td>
            <td>${t.retPct.toFixed(2)}%</td>
            <td>${reasonText}</td>
        </tr>`;
    });

    els.tradeBody.innerHTML = rows.join("");
}

function drawGameChart(game, trades, classificationTicks, entryCutoffTick) {
    const canvas = els.gameCanvas;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = "#11111b";
    ctx.fillRect(0, 0, w, h);

    const margin = { left: 52, right: 16, top: 14, bottom: 28 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    const prices = game.prices;
    const pMin = Math.min(...prices);
    const pMax = Math.max(...prices);
    const xMax = prices.length - 1;

    const xOf = (tick) => margin.left + (tick / xMax) * iw;
    const yOf = (p) => margin.top + (1 - (p - pMin) / (pMax - pMin || 1)) * ih;

    // grid
    ctx.strokeStyle = "#313244";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i += 1) {
        const y = margin.top + (i / 5) * ih;
        ctx.beginPath();
        ctx.moveTo(margin.left, y);
        ctx.lineTo(w - margin.right, y);
        ctx.stroke();
    }

    // classifier baseline region
    ctx.fillStyle = "rgba(249, 226, 175, 0.08)";
    const xClass = xOf(Math.min(classificationTicks, xMax));
    ctx.fillRect(margin.left, margin.top, Math.max(0, xClass - margin.left), ih);

    // no-new-entry region
    if (entryCutoffTick < xMax) {
        const xCut = xOf(Math.max(0, entryCutoffTick));
        ctx.fillStyle = "rgba(243, 139, 168, 0.08)";
        ctx.fillRect(xCut, margin.top, w - margin.right - xCut, ih);

        ctx.strokeStyle = "rgba(243, 139, 168, 0.75)";
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.moveTo(xCut, margin.top);
        ctx.lineTo(xCut, margin.top + ih);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    // price line
    ctx.strokeStyle = "#89b4fa";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let t = 0; t < prices.length; t += 1) {
        const x = xOf(t);
        const y = yOf(prices[t]);
        if (t === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // markers for trades
    for (const t of trades) {
        const xe = xOf(t.entryTick);
        const ye = yOf(t.entryPrice);
        const xx = xOf(t.exitTick);
        const yx = yOf(t.exitPrice);

        ctx.fillStyle = "#a6e3a1";
        ctx.fillRect(xe - 2, ye - 2, 4, 4);
        ctx.fillStyle = "#f38ba8";
        ctx.fillRect(xx - 2, yx - 2, 4, 4);

        ctx.strokeStyle = t.retPct >= 0 ? "rgba(166, 227, 161, 0.35)" : "rgba(243, 139, 168, 0.35)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(xe, ye);
        ctx.lineTo(xx, yx);
        ctx.stroke();
    }

    // axes labels
    ctx.fillStyle = "#a6adc8";
    ctx.font = "12px monospace";
    ctx.fillText(`ticks: 0 -> ${xMax}`, margin.left, h - 10);
    ctx.fillText(`price min=${pMin.toFixed(4)} max=${pMax.toFixed(4)}`, margin.left + 220, h - 10);
    ctx.fillText(`first-${classificationTicks} classifier window`, margin.left + 8, margin.top + 14);
    ctx.fillText(`no-new-entry after tick ${entryCutoffTick}`, margin.left + 8, margin.top + 30);
}

function openHelpOverlay() {
    setHelpTab("quickstart");
    els.helpOverlay.classList.remove("hidden");
}

function setHelpTab(tabId) {
    if (!els.helpTabBtns.length || !els.helpPanels.length) return;

    let resolvedTab = tabId;
    const valid = els.helpPanels.some((p) => p.dataset.helpPanel === tabId);
    if (!valid) {
        resolvedTab = "quickstart";
    }

    for (const panel of els.helpPanels) {
        if (panel.dataset.helpPanel === resolvedTab) {
            panel.classList.remove("hidden");
        } else {
            panel.classList.add("hidden");
        }
    }

    for (const btn of els.helpTabBtns) {
        if (btn.dataset.helpTab === resolvedTab) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    }
}

function openHelpOverlayFor(tabId) {
    setHelpTab(tabId);
    els.helpOverlay.classList.remove("hidden");
}

function closeHelpOverlay() {
    els.helpOverlay.classList.add("hidden");
}

function bindEvents() {
    els.loadBtn.addEventListener("click", () => {
        loadSelectedFiles().catch((err) => {
            log(`load error: ${String(err)}`);
        });
    });

    els.clearBtn.addEventListener("click", resetDataset);

    els.runBtn.addEventListener("click", () => {
        runSimulation();
    });

    els.inspectBtn.addEventListener("click", () => {
        inspectSelectedGame();
    });

    els.helpBtn.addEventListener("click", () => {
        openHelpOverlay();
    });

    els.quickStartBtn.addEventListener("click", () => {
        openHelpOverlayFor("quickstart");
    });

    els.controlsGuideBtn.addEventListener("click", () => {
        openHelpOverlayFor("controls");
    });

    els.resultsGuideBtn.addEventListener("click", () => {
        openHelpOverlayFor("results");
    });

    els.glossaryBtn.addEventListener("click", () => {
        openHelpOverlayFor("glossary");
    });

    els.helpCloseBtn.addEventListener("click", () => {
        closeHelpOverlay();
    });

    for (const btn of els.helpTabBtns) {
        btn.addEventListener("click", () => {
            const tabId = btn.dataset.helpTab || "quickstart";
            setHelpTab(tabId);
        });
    }

    els.helpOverlay.addEventListener("click", (event) => {
        if (event.target === els.helpOverlay) {
            closeHelpOverlay();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !els.helpOverlay.classList.contains("hidden")) {
            closeHelpOverlay();
        }
    });

    els.classifyTicks.addEventListener("change", () => {
        const ticks = getClassificationTicks();
        const cutoff = getEntryCutoffTick();
        setRulesText(ticks, cutoff);
        log(`classification ticks updated: ${ticks}`);
    });

    els.entryCutoffTick.addEventListener("change", () => {
        const ticks = getClassificationTicks();
        const cutoff = getEntryCutoffTick();
        setRulesText(ticks, cutoff);
        log(`entry cutoff updated: ${cutoff}`);
    });

    const botInputs = [
        els.botEnabled,
        els.botPlaybookMode,
        els.botStakeSol,
        els.botStartingBankrollSol,
        els.botDriftReference,
        els.botTpMultMin,
        els.botTpMultMax,
        els.botSlMultMin,
        els.botSlMultMax,
        els.botMaxHoldTicks,
        els.botCooldownTicks,
        els.botMaxTradesPerGame,
    ];
    for (const input of botInputs) {
        input.addEventListener("change", () => {
            const s = getBotSettings();
            log(`bot settings updated: enabled=${s.enabled}, mode=${s.playbookMode}, driftRef=${s.driftReference}, tp=${s.tpMultMin}-${s.tpMultMax}, sl=${s.slMultMin}-${s.slMultMax}, stake=${s.stakeSol} SOL, bankroll=${s.startingBankrollSol} SOL, hold=${s.maxHoldTicks}, cooldown=${s.cooldownTicks}, maxTrades=${s.maxTradesPerGame}`);
        });
    }

    els.gameSelect.addEventListener("change", () => {
        state.inspectGameId = els.gameSelect.value;
    });
}

function boot() {
    bindEvents();
    setRulesText();
    setHelpTab("quickstart");
    clearCanvas();
    log("boot complete");
}

document.addEventListener("DOMContentLoaded", boot);
