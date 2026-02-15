(() => {
    "use strict";

    const ARTIFACT_NAME = "scalping-bot-v1-simulator";
    const ARTIFACT_VERSION = "0.1.0";

    const PLAYBOOK_IDS = ["P1_MOMENTUM", "P2_PULLBACK_CONT", "P3_MEAN_REVERT", "P4_BREAKOUT"];

    const REGIME_PLAYBOOK_MAP = {
        trend_up: ["P1_MOMENTUM", "P2_PULLBACK_CONT"],
        trend_down: ["P3_MEAN_REVERT"],
        expansion: ["P4_BREAKOUT", "P1_MOMENTUM"],
        chop: ["P3_MEAN_REVERT"],
        uncertain: [],
    };

    const PLAYBOOK_DESCRIPTIONS = {
        P1_MOMENTUM: "Enter when short-horizon drift aligns positive (m3 > +1.5% and m5 > +2.0%).",
        P2_PULLBACK_CONT: "Enter pullback continuation (m8 trend up + short pullback + bounce).",
        P3_MEAN_REVERT: "Enter after short overreaction down move with reflex up.",
        P4_BREAKOUT: "Enter local breakout (price > prior 12-tick high by >=1% + positive m3).",
    };

    const PROFILE_PRESETS = {
        V1_MOMENTUM_CORE: {
            label: "V1 Momentum Core",
            note: [
                "Primary profile from current optimization frontier.",
                "Focus: momentum-led entries, wider drift anchor, longer hold window.",
                "Good baseline for high-upside exploration before conservative filtering.",
            ].join("\n"),
            values: {
                classificationTicks: 20,
                entryCutoffTick: 55,
                playbookMode: "P1_MOMENTUM",
                driftReference: "P90",
                tpMultMin: 2,
                tpMultMax: 4,
                slMultMin: 2,
                slMultMax: 4,
                maxHoldTicks: 9,
            },
        },
        V1_AUTO_BALANCED: {
            label: "V1 Auto Regime Balanced",
            note: [
                "Regime-gated multi-playbook mode for broader coverage.",
                "Balances upside and stability using P90 drift with medium TP/SL band.",
                "Use when you want to compare system behavior across regime types.",
            ].join("\n"),
            values: {
                classificationTicks: 20,
                entryCutoffTick: 55,
                playbookMode: "AUTO_REGIME",
                driftReference: "P90",
                tpMultMin: 2,
                tpMultMax: 4,
                slMultMin: 2,
                slMultMax: 4,
                maxHoldTicks: 7,
            },
        },
        V1_AUTO_CONSERVATIVE: {
            label: "V1 Auto Conservative",
            note: [
                "More defensive baseline for stress-testing downside controls.",
                "Uses slightly larger baseline window and smaller hold horizon.",
                "Useful for filtering noisy profiles before high-risk experiments.",
            ].join("\n"),
            values: {
                classificationTicks: 25,
                entryCutoffTick: 50,
                playbookMode: "AUTO_REGIME",
                driftReference: "P75",
                tpMultMin: 2,
                tpMultMax: 3,
                slMultMin: 2,
                slMultMax: 3,
                maxHoldTicks: 5,
            },
        },
        V1_BREAKOUT_PROBE: {
            label: "V1 Breakout Probe",
            note: [
                "Single-playbook diagnostic profile for breakout behavior only.",
                "Use as a controlled probe, not as a primary production candidate.",
                "Helpful for measuring whether expansion regimes justify specialization.",
            ].join("\n"),
            values: {
                classificationTicks: 20,
                entryCutoffTick: 60,
                playbookMode: "P4_BREAKOUT",
                driftReference: "P90",
                tpMultMin: 2,
                tpMultMax: 5,
                slMultMin: 2,
                slMultMax: 4,
                maxHoldTicks: 9,
            },
        },
    };

    const state = {
        games: [],
        gamesById: new Map(),
        runResult: null,
        inspectGameId: null,
        applyingPreset: false,
    };

    const els = {
        fileInput: document.getElementById("fileInput"),
        loadBtn: document.getElementById("loadBtn"),
        clearBtn: document.getElementById("clearBtn"),
        datasetStats: document.getElementById("datasetStats"),
        footerInfo: document.getElementById("footerInfo"),
        runStatus: document.getElementById("runStatus"),

        classificationTicks: document.getElementById("classificationTicks"),
        entryCutoffTick: document.getElementById("entryCutoffTick"),
        minTicks: document.getElementById("minTicks"),
        maxGames: document.getElementById("maxGames"),
        windowSummary: document.getElementById("windowSummary"),

        profilePreset: document.getElementById("profilePreset"),
        profileNotes: document.getElementById("profileNotes"),
        playbookMode: document.getElementById("playbookMode"),
        driftReference: document.getElementById("driftReference"),
        stakeSol: document.getElementById("stakeSol"),
        startingBankrollSol: document.getElementById("startingBankrollSol"),
        tpMultMin: document.getElementById("tpMultMin"),
        tpMultMax: document.getElementById("tpMultMax"),
        slMultMin: document.getElementById("slMultMin"),
        slMultMax: document.getElementById("slMultMax"),
        maxHoldTicks: document.getElementById("maxHoldTicks"),
        cooldownTicks: document.getElementById("cooldownTicks"),
        maxTradesPerGame: document.getElementById("maxTradesPerGame"),

        runBtn: document.getElementById("runBtn"),
        inspectBtn: document.getElementById("inspectBtn"),
        gameSelect: document.getElementById("gameSelect"),

        primarySummary: document.getElementById("primarySummary"),
        permutationsBody: document.getElementById("permutationsBody"),
        gameOutcomesBody: document.getElementById("gameOutcomesBody"),
        inspectSummary: document.getElementById("inspectSummary"),
        tradesBody: document.getElementById("tradesBody"),
        chartCanvas: document.getElementById("chartCanvas"),

        debugLog: document.getElementById("debugLog"),

        helpBtn: document.getElementById("helpBtn"),
        helpOverlay: document.getElementById("helpOverlay"),
        helpCloseBtn: document.getElementById("helpCloseBtn"),
    };

    function log(message) {
        const ts = new Date().toISOString().slice(11, 23);
        const line = `[${ts}] ${message}`;
        if (els.debugLog) {
            els.debugLog.textContent = `${line}\n${els.debugLog.textContent}`;
        }
        // Keep console trace for debugging in devtools.
        console.log(`[${ARTIFACT_NAME}] ${message}`);
    }

    function clampNumber(value, min, max, fallback) {
        const raw = Number(value);
        const candidate = Number.isFinite(raw) ? raw : fallback;
        return Math.max(min, Math.min(max, candidate));
    }

    function clampInteger(value, min, max, fallback) {
        return Math.floor(clampNumber(value, min, max, fallback));
    }

    function setInputValue(el, value) {
        if (!el) return;
        el.value = String(value);
    }

    function getClassificationTicks() {
        const ticks = clampInteger(els.classificationTicks.value, 12, 800, 20);
        setInputValue(els.classificationTicks, ticks);
        return ticks;
    }

    function getEntryCutoffTick() {
        const cutoff = clampInteger(els.entryCutoffTick.value, 1, 5000, 55);
        setInputValue(els.entryCutoffTick, cutoff);
        return cutoff;
    }

    function getExplorationSettings() {
        const classificationTicks = getClassificationTicks();
        const entryCutoffTick = getEntryCutoffTick();
        const minTicks = clampInteger(els.minTicks.value, 30, 5000, 60);
        const maxGames = clampInteger(els.maxGames.value, 1, 50000, 500);

        setInputValue(els.minTicks, minTicks);
        setInputValue(els.maxGames, maxGames);

        return {
            classificationTicks,
            entryCutoffTick,
            minTicks,
            maxGames,
        };
    }

    function getBotSettings() {
        const modeRaw = String(els.playbookMode.value || "AUTO_REGIME");
        const playbookMode = modeRaw === "AUTO_REGIME" || PLAYBOOK_IDS.includes(modeRaw)
            ? modeRaw
            : "AUTO_REGIME";
        if (playbookMode !== modeRaw) {
            els.playbookMode.value = playbookMode;
        }

        const driftRaw = String(els.driftReference.value || "P75");
        const driftReference = ["P50", "P75", "P90"].includes(driftRaw) ? driftRaw : "P75";
        if (driftReference !== driftRaw) {
            els.driftReference.value = driftReference;
        }

        const stakeSol = clampNumber(els.stakeSol.value, 0.001, 1000, 0.1);
        setInputValue(els.stakeSol, stakeSol);

        const startingBankrollSol = clampNumber(els.startingBankrollSol.value, 0.01, 100000, 10);
        setInputValue(els.startingBankrollSol, startingBankrollSol);

        let tpMultMin = clampInteger(els.tpMultMin.value, 1, 8, 2);
        let tpMultMax = clampInteger(els.tpMultMax.value, 1, 8, 4);
        if (tpMultMax < tpMultMin) {
            const temp = tpMultMin;
            tpMultMin = tpMultMax;
            tpMultMax = temp;
        }
        setInputValue(els.tpMultMin, tpMultMin);
        setInputValue(els.tpMultMax, tpMultMax);

        let slMultMin = clampInteger(els.slMultMin.value, 1, 8, 2);
        let slMultMax = clampInteger(els.slMultMax.value, 1, 8, 4);
        if (slMultMax < slMultMin) {
            const temp = slMultMin;
            slMultMin = slMultMax;
            slMultMax = temp;
        }
        setInputValue(els.slMultMin, slMultMin);
        setInputValue(els.slMultMax, slMultMax);

        const maxHoldTicks = clampInteger(els.maxHoldTicks.value, 1, 200, 9);
        const cooldownTicks = clampInteger(els.cooldownTicks.value, 0, 500, 0);
        const maxTradesPerGame = clampInteger(els.maxTradesPerGame.value, 1, 1000, 25);

        setInputValue(els.maxHoldTicks, maxHoldTicks);
        setInputValue(els.cooldownTicks, cooldownTicks);
        setInputValue(els.maxTradesPerGame, maxTradesPerGame);

        return {
            profilePreset: String(els.profilePreset.value || "CUSTOM"),
            playbookMode,
            driftReference,
            stakeSol,
            startingBankrollSol,
            tpMultMin,
            tpMultMax,
            slMultMin,
            slMultMax,
            maxHoldTicks,
            cooldownTicks,
            maxTradesPerGame,
        };
    }

    function getPresetNote(presetId) {
        if (presetId === "CUSTOM") {
            const s = getBotSettings();
            return [
                "Custom profile active (manual controls).",
                `mode=${s.playbookMode}, drift=${s.driftReference}, hold=${s.maxHoldTicks}`,
                `TP mult=${s.tpMultMin}..${s.tpMultMax}, SL mult=${s.slMultMin}..${s.slMultMax}`,
                `stake=${s.stakeSol} SOL, bankroll=${s.startingBankrollSol} SOL`,
            ].join("\n");
        }

        const preset = PROFILE_PRESETS[presetId];
        if (!preset) {
            return "Unknown profile preset. Switching to custom mode is recommended.";
        }

        const v = preset.values;
        return [
            preset.note,
            "",
            "Preset controls:",
            `classification=${v.classificationTicks}, cutoff=${v.entryCutoffTick}`,
            `mode=${v.playbookMode}, drift=${v.driftReference}`,
            `TP mult=${v.tpMultMin}..${v.tpMultMax}, SL mult=${v.slMultMin}..${v.slMultMax}, hold=${v.maxHoldTicks}`,
        ].join("\n");
    }

    function updateProfileNotes() {
        if (!els.profileNotes) return;
        const presetId = String(els.profilePreset.value || "CUSTOM");
        els.profileNotes.textContent = getPresetNote(presetId);
    }

    function updateWindowSummary() {
        const c = getClassificationTicks();
        const cutoff = getEntryCutoffTick();
        const startTick = c + 1;
        if (cutoff < startTick) {
            els.windowSummary.textContent = `entry window is disabled (start tick ${startTick} exceeds cutoff tick ${cutoff})`;
            return;
        }
        els.windowSummary.textContent = `entry window starts at tick ${startTick} and ends at tick ${cutoff}`;
    }

    function applyPreset(presetId) {
        if (presetId === "CUSTOM") {
            updateProfileNotes();
            updateWindowSummary();
            return;
        }

        const preset = PROFILE_PRESETS[presetId];
        if (!preset) {
            log(`unknown preset requested: ${presetId}`);
            return;
        }

        state.applyingPreset = true;
        try {
            const values = preset.values;
            setInputValue(els.classificationTicks, values.classificationTicks);
            setInputValue(els.entryCutoffTick, values.entryCutoffTick);
            els.playbookMode.value = values.playbookMode;
            els.driftReference.value = values.driftReference;
            setInputValue(els.tpMultMin, values.tpMultMin);
            setInputValue(els.tpMultMax, values.tpMultMax);
            setInputValue(els.slMultMin, values.slMultMin);
            setInputValue(els.slMultMax, values.slMultMax);
            setInputValue(els.maxHoldTicks, values.maxHoldTicks);

            updateProfileNotes();
            updateWindowSummary();
            log(`preset applied: ${preset.label}`);
        } finally {
            state.applyingPreset = false;
        }
    }

    function markPresetCustomOnManualEdit() {
        if (state.applyingPreset) return;
        if (!els.profilePreset) return;
        if (els.profilePreset.value === "CUSTOM") {
            updateProfileNotes();
            return;
        }
        els.profilePreset.value = "CUSTOM";
        updateProfileNotes();
        log("manual control change detected: preset switched to CUSTOM");
    }

    function mean(arr) {
        if (!arr.length) return 0;
        return arr.reduce((acc, v) => acc + v, 0) / arr.length;
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

    function parseJsonLines(text) {
        const rows = [];
        const lines = text.split(/\r?\n/);
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            try {
                rows.push(JSON.parse(trimmed));
            } catch (_err) {
                // Skip malformed line.
            }
        }
        return rows;
    }

    function normalizePayloadToObject(payload) {
        if (!payload) return null;
        if (Array.isArray(payload)) {
            if (!payload.length) return null;
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

        if (state.gamesById.has(gameId)) return;

        const cleanedPrices = prices
            .map((v) => Number(v))
            .filter((v) => Number.isFinite(v) && v > 0);

        if (cleanedPrices.length < 30) return;

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

        if (obj.raw_json && typeof obj.raw_json === "string") {
            try {
                const raw = JSON.parse(obj.raw_json);
                addGameCandidate({ ...raw, game_id: obj.game_id || raw.id }, sourceLabel);
            } catch (_err) {
                // Ignore invalid JSON string payload.
            }
        }

        if (Array.isArray(obj.prices)) {
            addGameCandidate(obj, sourceLabel);
        }

        const payload = normalizePayloadToObject(obj.data || obj.payload || obj.event_data);
        if (obj.event === "gameStateUpdate" || obj.event_name === "gameStateUpdate") {
            const dataObj = payload || obj.data || obj;
            if (dataObj && Array.isArray(dataObj.gameHistory)) {
                for (const game of dataObj.gameHistory) {
                    addGameCandidate(game, sourceLabel);
                }
            }
        }

        const nestedFields = ["gameHistory", "games", "items", "records", "data"];
        for (const key of nestedFields) {
            if (obj[key]) {
                extractGamesFromObject(obj[key], sourceLabel);
            }
        }
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

    function clearChart() {
        const canvas = els.chartCanvas;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#11111b";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#a6adc8";
        ctx.font = "12px monospace";
        ctx.fillText("No game inspected", 12, 22);
    }

    function resetDataset() {
        state.games = [];
        state.gamesById.clear();
        state.runResult = null;
        state.inspectGameId = null;

        els.datasetStats.textContent = "no dataset loaded";
        els.footerInfo.textContent = "No dataset";
        els.runStatus.textContent = "Dataset cleared. Load files to continue.";

        els.primarySummary.textContent = "No run yet.";
        els.permutationsBody.innerHTML = "<tr><td colspan='8'>No run yet.</td></tr>";
        els.gameOutcomesBody.innerHTML = "<tr><td colspan='8'>No run yet.</td></tr>";
        els.inspectSummary.textContent = "No game inspected yet.";
        els.tradesBody.innerHTML = "<tr><td colspan='8'>No game inspected yet.</td></tr>";
        els.gameSelect.innerHTML = "";

        clearChart();
        log("dataset cleared");
    }

    async function loadSelectedFiles() {
        const files = Array.from(els.fileInput.files || []);
        if (!files.length) {
            els.runStatus.textContent = "No files selected. Choose one or more recording files.";
            log("load requested with no files selected");
            return;
        }

        const before = state.games.length;
        log(`loading ${files.length} file(s)`);

        for (const file of files) {
            const text = await file.text();
            const sourceLabel = file.name;

            if (file.name.endsWith(".jsonl")) {
                const rows = parseJsonLines(text);
                extractGamesFromObject(rows, sourceLabel);
                log(`parsed jsonl ${file.name}: rows=${rows.length}`);
                continue;
            }

            try {
                const json = JSON.parse(text);
                extractGamesFromObject(json, sourceLabel);
                log(`parsed json ${file.name}: root=${Array.isArray(json) ? "array" : "object"}`);
            } catch (_err) {
                const rows = parseJsonLines(text);
                extractGamesFromObject(rows, sourceLabel);
                log(`fallback jsonl parse ${file.name}: rows=${rows.length}`);
            }
        }

        const added = state.games.length - before;
        state.games.sort((a, b) => a.gameId.localeCompare(b.gameId));
        refreshGameSelect();

        els.datasetStats.textContent = `${state.games.length} unique games loaded`;
        els.footerInfo.textContent = `${state.games.length} games in memory`;
        if (added > 0) {
            els.runStatus.textContent = `Loaded ${added} new games. Run V1 simulation when ready.`;
        } else {
            els.runStatus.textContent = "No new games found in selected files.";
        }

        log(`dataset load complete: +${added}, total=${state.games.length}`);
    }

    function classifyGame(game, classificationTicks) {
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

        const baselineScale = Math.sqrt(classifierWindow / 25);
        const trendMomentumThreshold = 0.06 * baselineScale;
        const chopMomentumThreshold = 0.025 * baselineScale;
        const trendFlipMax = Math.max(8, Math.round(returns.length * 0.34));
        const downFlipMax = Math.max(9, Math.round(returns.length * 0.36));
        const chopFlipMin = Math.max(12, Math.round(returns.length * 0.5));

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
        } else if (vol > 0.04 || range > 0.2 || expansionRatio > 1.55) {
            regime = "expansion";
            confidence = Math.min(0.92, 0.52 + vol * 5 + Math.min(0.25, range - 0.1) + (expansionRatio - 1) * 0.08);
            reasons.push(`high realized volatility or range growth in first ${classifierWindow} ticks`);
            reasons.push("late to early volatility ratio implies expansion state");
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

    function playbookSignal(playbookId, prices, tick) {
        if (tick < 12) return { enter: false, reason: "not enough lookback" };

        const p = prices[tick];
        const m1 = p / prices[tick - 1] - 1;
        const m2 = p / prices[tick - 2] - 1;
        const m3 = p / prices[tick - 3] - 1;
        const m5 = p / prices[tick - 5] - 1;
        const m8 = p / prices[tick - 8] - 1;

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
                reason: `trend8=${(m8 * 100).toFixed(2)}%, pull1=${(m1 * 100).toFixed(2)}%, bounce2=${(m2 * 100).toFixed(2)}%`,
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
            const lookback = prices.slice(tick - 12, tick);
            const localHigh = Math.max(...lookback);
            const breakout = p > localHigh * 1.01;
            const confirm = m3 > 0.01;
            const enter = breakout && confirm;
            return {
                enter,
                reason: `px=${p.toFixed(4)} > high12*1.01=${(localHigh * 1.01).toFixed(4)}, m3=${(m3 * 100).toFixed(2)}%`,
            };
        }

        return { enter: false, reason: "unknown playbook" };
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

        for (let tp = botSettings.tpMultMin; tp <= botSettings.tpMultMax; tp += 1) {
            for (let sl = botSettings.slMultMin; sl <= botSettings.slMultMax; sl += 1) {
                perms.push({
                    id: `TPx${tp}_SLx${sl}`,
                    tpMult: tp,
                    slMult: sl,
                    takeProfitPct: tpUnit * tp,
                    stopLossPct: slUnit * sl,
                });
            }
        }

        return perms;
    }

    function simulateBotOnGame(game, classification, botSettings, startTick, entryCutoffTick, permutation) {
        const prices = game.prices;
        const trades = [];
        let nextEligibleTick = startTick;

        const candidatePlaybooks = botSettings.playbookMode === "AUTO_REGIME"
            ? (REGIME_PLAYBOOK_MAP[classification.regime] || [])
            : [botSettings.playbookMode];

        if (!candidatePlaybooks.length) return trades;

        const lastEntryTick = Math.min(entryCutoffTick, prices.length - 2);
        for (let tick = startTick; tick <= lastEntryTick; tick += 1) {
            if (tick < nextEligibleTick) continue;
            if (trades.length >= botSettings.maxTradesPerGame) break;

            let chosenPlaybook = null;
            let chosenSignal = null;

            for (const playbookId of candidatePlaybooks) {
                const signal = playbookSignal(playbookId, prices, tick);
                if (!signal.enter) continue;
                chosenPlaybook = playbookId;
                chosenSignal = signal;
                break;
            }

            if (!chosenPlaybook || !chosenSignal) continue;

            const entryTick = tick;
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
            tick = exitTick;
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

    function summarizeExitCounts(trades) {
        const counts = { TP: 0, SL: 0, TIME: 0 };
        for (const trade of trades) {
            if (counts[trade.exitReason] !== undefined) {
                counts[trade.exitReason] += 1;
            }
        }
        return counts;
    }

    function runSimulation() {
        if (!state.games.length) {
            els.runStatus.textContent = "No dataset loaded. Load game recordings first.";
            log("run aborted: no games loaded");
            return;
        }

        const exploration = getExplorationSettings();
        const bot = getBotSettings();
        const startTick = exploration.classificationTicks + 1;
        const requiredTicks = Math.max(
            exploration.minTicks,
            startTick + bot.maxHoldTicks + 1
        );

        const filteredGames = state.games
            .filter((g) => g.prices.length >= requiredTicks)
            .slice(0, exploration.maxGames);

        if (!filteredGames.length) {
            els.runStatus.textContent = "No games passed current min-length window. Lower filters or load different data.";
            els.primarySummary.textContent = "No run executed because no games passed filter.";
            els.permutationsBody.innerHTML = "<tr><td colspan='8'>No eligible games.</td></tr>";
            els.gameOutcomesBody.innerHTML = "<tr><td colspan='8'>No eligible games.</td></tr>";
            log(`run aborted: no games met requiredTicks=${requiredTicks}`);
            return;
        }

        const regimeCounts = {
            trend_up: 0,
            trend_down: 0,
            expansion: 0,
            chop: 0,
            uncertain: 0,
        };

        const perGame = new Map();
        const driftStats = computeOneTickDriftStats(filteredGames);
        const driftRef = selectDriftReferenceValues(driftStats, bot.driftReference);
        const permutations = buildDriftPermutations(bot, driftRef.upPct, driftRef.downPct);

        const aggByPermutation = new Map();
        for (const perm of permutations) {
            aggByPermutation.set(perm.id, {
                permutation: perm,
                trades: [],
                perGameTrades: new Map(),
            });
        }

        for (const game of filteredGames) {
            const classification = classifyGame(game, exploration.classificationTicks);
            regimeCounts[classification.regime] += 1;

            perGame.set(game.gameId, {
                classification,
                game,
            });

            for (const perm of permutations) {
                const trades = simulateBotOnGame(game, classification, bot, startTick, exploration.entryCutoffTick, perm);
                const agg = aggByPermutation.get(perm.id);
                agg.perGameTrades.set(game.gameId, trades);
                if (trades.length) {
                    agg.trades.push(...trades);
                }
            }
        }

        const permutationSummaries = permutations.map((perm) => {
            const agg = aggByPermutation.get(perm.id);
            const tradeSummary = summarizeTrades(agg.trades);
            const netSol = agg.trades.reduce((acc, t) => acc + t.pnlSol, 0);
            const endSol = bot.startingBankrollSol + netSol;
            const gameNetSol = filteredGames.map((g) => {
                const gameTrades = agg.perGameTrades.get(g.gameId) || [];
                return gameTrades.reduce((acc, t) => acc + t.pnlSol, 0);
            });

            return {
                id: perm.id,
                tpMult: perm.tpMult,
                slMult: perm.slMult,
                takeProfitPct: perm.takeProfitPct,
                stopLossPct: perm.stopLossPct,
                tradeCount: tradeSummary.tradeCount,
                winRate: tradeSummary.winRate,
                meanRet: tradeSummary.meanRet,
                medianRet: tradeSummary.medianRet,
                p10: tradeSummary.p10,
                p90: tradeSummary.p90,
                netSol,
                endSol,
                gamesTraded: gameNetSol.filter((v) => v !== 0).length,
                p10GameNetSol: percentile(gameNetSol, 0.1),
                worstGameNetSol: gameNetSol.length ? Math.min(...gameNetSol) : 0,
                exitCounts: summarizeExitCounts(agg.trades),
                trades: agg.trades,
                perGameTrades: agg.perGameTrades,
            };
        }).sort((a, b) => {
            if (b.netSol !== a.netSol) return b.netSol - a.netSol;
            if (b.winRate !== a.winRate) return b.winRate - a.winRate;
            return b.tradeCount - a.tradeCount;
        });

        const selected = permutationSummaries[0] || null;
        const gameRows = [];

        if (selected) {
            for (const game of filteredGames) {
                const gameState = perGame.get(game.gameId);
                const gameTrades = selected.perGameTrades.get(game.gameId) || [];
                const tradeSummary = summarizeTrades(gameTrades);
                const netSol = gameTrades.reduce((acc, t) => acc + t.pnlSol, 0);
                const exitCounts = summarizeExitCounts(gameTrades);

                gameRows.push({
                    gameId: game.gameId,
                    regime: gameState.classification.regime,
                    tradeCount: gameTrades.length,
                    winRate: tradeSummary.winRate,
                    netSol,
                    endSol: bot.startingBankrollSol + netSol,
                    exitCounts,
                    trades: gameTrades,
                });
            }

            gameRows.sort((a, b) => b.netSol - a.netSol);
        }

        state.runResult = {
            exploration,
            bot,
            startTick,
            requiredTicks,
            filteredGames,
            perGame,
            regimeCounts,
            driftStats,
            driftReferenceUpPct: driftRef.upPct,
            driftReferenceDownPct: driftRef.downPct,
            permutationSummaries,
            selectedPermutation: selected,
            gameRows,
        };

        renderRunResult();

        if (!state.inspectGameId && filteredGames.length) {
            state.inspectGameId = filteredGames[0].gameId;
            els.gameSelect.value = state.inspectGameId;
        }

        els.runStatus.textContent = `Run complete: ${filteredGames.length} games analyzed, ${selected ? selected.tradeCount : 0} trades in selected permutation.`;
        log(`run complete: games=${filteredGames.length}, perms=${permutationSummaries.length}, selected=${selected ? selected.id : "n/a"}`);
    }

    function renderRunResult() {
        if (!state.runResult) return;

        const r = state.runResult;
        const selected = r.selectedPermutation;
        const total = r.filteredGames.length || 1;

        const summaryLines = [
            `dataset games analyzed: ${r.filteredGames.length}`,
            `classification ticks: ${r.exploration.classificationTicks}`,
            `simulation start tick: ${r.startTick}`,
            `no-new-entry after tick: ${r.exploration.entryCutoffTick}`,
            `effective min game length: ${r.requiredTicks}`,
            `profile preset: ${r.bot.profilePreset}`,
            `bot mode: ${r.bot.playbookMode}`,
            `drift reference (${r.bot.driftReference}): up=${r.driftReferenceUpPct.toFixed(3)}% down=${r.driftReferenceDownPct.toFixed(3)}%`,
            `tp mult range: ${r.bot.tpMultMin}..${r.bot.tpMultMax} | sl mult range: ${r.bot.slMultMin}..${r.bot.slMultMax}`,
            `max hold/cooldown/max trades: ${r.bot.maxHoldTicks}/${r.bot.cooldownTicks}/${r.bot.maxTradesPerGame}`,
            `stake: ${r.bot.stakeSol.toFixed(4)} SOL | bankroll: ${r.bot.startingBankrollSol.toFixed(4)} SOL`,
            "",
            `regimes: trend_up=${r.regimeCounts.trend_up} (${((r.regimeCounts.trend_up / total) * 100).toFixed(1)}%) | trend_down=${r.regimeCounts.trend_down} (${((r.regimeCounts.trend_down / total) * 100).toFixed(1)}%)`,
            `         expansion=${r.regimeCounts.expansion} (${((r.regimeCounts.expansion / total) * 100).toFixed(1)}%) | chop=${r.regimeCounts.chop} (${((r.regimeCounts.chop / total) * 100).toFixed(1)}%) | uncertain=${r.regimeCounts.uncertain} (${((r.regimeCounts.uncertain / total) * 100).toFixed(1)}%)`,
            "",
            selected
                ? `selected permutation: TPx${selected.tpMult}/SLx${selected.slMult} => +${selected.takeProfitPct.toFixed(3)}% / -${selected.stopLossPct.toFixed(3)}%`
                : "selected permutation: n/a",
            selected
                ? `selected outcomes: trades=${selected.tradeCount}, win=${selected.winRate.toFixed(1)}%, net=${selected.netSol.toFixed(4)} SOL, end=${selected.endSol.toFixed(4)} SOL`
                : "selected outcomes: n/a",
            selected
                ? `selected downside anchors: p10_game_net=${selected.p10GameNetSol.toFixed(4)} SOL, worst_game_net=${selected.worstGameNetSol.toFixed(4)} SOL`
                : "selected downside anchors: n/a",
        ];

        els.primarySummary.textContent = summaryLines.join("\n");

        if (!r.permutationSummaries.length) {
            els.permutationsBody.innerHTML = "<tr><td colspan='8'>No permutations generated for current settings.</td></tr>";
        } else {
            const rows = r.permutationSummaries.slice(0, 150).map((p, idx) => {
                const selectedStyle = selected && selected.id === p.id
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
                    <td>${p.exitCounts.TP}/${p.exitCounts.SL}/${p.exitCounts.TIME}</td>
                </tr>`;
            });
            els.permutationsBody.innerHTML = rows.join("");
        }

        if (!r.gameRows.length) {
            els.gameOutcomesBody.innerHTML = "<tr><td colspan='8'>No game outcomes under selected permutation.</td></tr>";
        } else {
            const rows = r.gameRows.slice(0, 2000).map((g, idx) => {
                return `<tr>
                    <td>${idx + 1}</td>
                    <td>${g.gameId}</td>
                    <td>${g.regime}</td>
                    <td>${g.tradeCount}</td>
                    <td>${g.winRate.toFixed(1)}%</td>
                    <td>${g.netSol.toFixed(4)}</td>
                    <td>${g.endSol.toFixed(4)}</td>
                    <td>${g.exitCounts.TP}/${g.exitCounts.SL}/${g.exitCounts.TIME}</td>
                </tr>`;
            });
            els.gameOutcomesBody.innerHTML = rows.join("");
        }
    }

    function renderTradeTable(trades) {
        if (!trades.length) {
            els.tradesBody.innerHTML = "<tr><td colspan='8'>No trades for this game under current run settings.</td></tr>";
            return;
        }

        const rows = trades.slice(0, 400).map((trade, idx) => {
            const parts = [];
            if (trade.reason) parts.push(trade.reason);
            if (trade.exitReason) parts.push(`exit=${trade.exitReason}`);
            parts.push(`pnl=${trade.pnlSol.toFixed(4)} SOL`);
            return `<tr>
                <td>${idx + 1}</td>
                <td>${trade.playbookId}</td>
                <td>${trade.entryTick}</td>
                <td>${trade.exitTick}</td>
                <td>${trade.entryPrice.toFixed(5)}</td>
                <td>${trade.exitPrice.toFixed(5)}</td>
                <td>${trade.retPct.toFixed(2)}%</td>
                <td>${parts.join(" | ")}</td>
            </tr>`;
        });

        els.tradesBody.innerHTML = rows.join("");
    }

    function drawGameChart(game, trades, classificationTicks, entryCutoffTick) {
        const canvas = els.chartCanvas;
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

        const xOf = (tick) => margin.left + (tick / (xMax || 1)) * iw;
        const yOf = (p) => margin.top + (1 - (p - pMin) / ((pMax - pMin) || 1)) * ih;

        ctx.strokeStyle = "#313244";
        ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i += 1) {
            const y = margin.top + (i / 5) * ih;
            ctx.beginPath();
            ctx.moveTo(margin.left, y);
            ctx.lineTo(w - margin.right, y);
            ctx.stroke();
        }

        ctx.fillStyle = "rgba(249, 226, 175, 0.08)";
        const xClass = xOf(Math.min(classificationTicks, xMax));
        ctx.fillRect(margin.left, margin.top, Math.max(0, xClass - margin.left), ih);

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

        ctx.strokeStyle = "#89b4fa";
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let i = 0; i < prices.length; i += 1) {
            const x = xOf(i);
            const y = yOf(prices[i]);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        for (const trade of trades) {
            const xe = xOf(trade.entryTick);
            const ye = yOf(trade.entryPrice);
            const xx = xOf(trade.exitTick);
            const yx = yOf(trade.exitPrice);

            ctx.fillStyle = "#a6e3a1";
            ctx.fillRect(xe - 2, ye - 2, 4, 4);
            ctx.fillStyle = "#f38ba8";
            ctx.fillRect(xx - 2, yx - 2, 4, 4);

            ctx.strokeStyle = trade.retPct >= 0 ? "rgba(166, 227, 161, 0.35)" : "rgba(243, 139, 168, 0.35)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(xe, ye);
            ctx.lineTo(xx, yx);
            ctx.stroke();
        }

        ctx.fillStyle = "#a6adc8";
        ctx.font = "12px monospace";
        ctx.fillText(`ticks: 0 -> ${xMax}`, margin.left, h - 10);
        ctx.fillText(`price min=${pMin.toFixed(4)} max=${pMax.toFixed(4)}`, margin.left + 210, h - 10);
        ctx.fillText(`first-${classificationTicks} classifier window`, margin.left + 8, margin.top + 14);
        ctx.fillText(`no-new-entry after tick ${entryCutoffTick}`, margin.left + 8, margin.top + 30);
    }

    function inspectSelectedGame() {
        const gameId = els.gameSelect.value;
        if (!gameId) {
            els.runStatus.textContent = "No game selected for inspection.";
            log("inspect aborted: no game selected");
            return;
        }

        const game = state.gamesById.get(gameId);
        if (!game) {
            els.runStatus.textContent = `Game not found in memory: ${gameId}`;
            log(`inspect aborted: unknown game ${gameId}`);
            return;
        }

        state.inspectGameId = gameId;

        const exploration = state.runResult ? state.runResult.exploration : getExplorationSettings();
        const classification = classifyGame(game, exploration.classificationTicks);

        let trades = [];
        if (state.runResult && state.runResult.selectedPermutation) {
            trades = state.runResult.selectedPermutation.perGameTrades.get(gameId) || [];
        }

        const f = classification.features || {};
        const pctOrNA = (value) => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : "n/a";
        const numOrNA = (value, digits = 3) => Number.isFinite(value) ? value.toFixed(digits) : "n/a";

        const lines = [
            `game: ${game.gameId}`,
            `source: ${game.source}`,
            `ticks: ${game.prices.length}`,
            `classification ticks: ${exploration.classificationTicks}`,
            `no-new-entry tick: ${exploration.entryCutoffTick}`,
            `regime: ${classification.regime} (${(classification.confidence * 100).toFixed(1)}%)`,
            `trade count (selected permutation): ${trades.length}`,
            "",
            "classifier feature snapshot:",
            `- momentumWindow: ${pctOrNA(f.momentumWindow)}`,
            `- momentumTail: ${pctOrNA(f.momentumTail)}`,
            `- volatility: ${pctOrNA(f.vol)}`,
            `- range: ${pctOrNA(f.range)}`,
            `- signFlips: ${Number.isFinite(f.signFlips) ? f.signFlips : "n/a"}`,
            `- expansionRatio: ${numOrNA(f.expansionRatio, 3)}`,
            "",
            "classification reasons:",
            ...classification.reasons.map((r) => `- ${r}`),
            "",
            "playbook rules:",
            ...Object.entries(PLAYBOOK_DESCRIPTIONS).map(([id, txt]) => `- ${id}: ${txt}`),
        ];
        els.inspectSummary.textContent = lines.join("\n");

        renderTradeTable(trades);
        drawGameChart(game, trades, exploration.classificationTicks, exploration.entryCutoffTick);
        els.runStatus.textContent = `Inspected ${gameId} (${trades.length} selected trades).`;
        log(`inspected game: ${gameId}, regime=${classification.regime}, trades=${trades.length}`);
    }

    function openHelpOverlay() {
        els.helpOverlay.classList.remove("hidden");
    }

    function closeHelpOverlay() {
        els.helpOverlay.classList.add("hidden");
    }

    function bindEvents() {
        els.loadBtn.addEventListener("click", () => {
            loadSelectedFiles().catch((err) => {
                log(`load error: ${String(err)}`);
                els.runStatus.textContent = `Load error: ${String(err)}`;
            });
        });

        els.clearBtn.addEventListener("click", () => {
            resetDataset();
        });

        els.runBtn.addEventListener("click", () => {
            try {
                runSimulation();
            } catch (err) {
                log(`run error: ${String(err)}`);
                els.runStatus.textContent = `Run failed: ${String(err)}`;
            }
        });

        els.inspectBtn.addEventListener("click", () => {
            try {
                inspectSelectedGame();
            } catch (err) {
                log(`inspect error: ${String(err)}`);
                els.runStatus.textContent = `Inspect failed: ${String(err)}`;
            }
        });

        els.profilePreset.addEventListener("change", () => {
            const preset = String(els.profilePreset.value || "CUSTOM");
            applyPreset(preset);
        });

        const manualControls = [
            els.classificationTicks,
            els.entryCutoffTick,
            els.playbookMode,
            els.driftReference,
            els.stakeSol,
            els.startingBankrollSol,
            els.tpMultMin,
            els.tpMultMax,
            els.slMultMin,
            els.slMultMax,
            els.maxHoldTicks,
            els.cooldownTicks,
            els.maxTradesPerGame,
        ];

        for (const control of manualControls) {
            control.addEventListener("change", () => {
                markPresetCustomOnManualEdit();
                updateWindowSummary();
            });
        }

        els.gameSelect.addEventListener("change", () => {
            state.inspectGameId = els.gameSelect.value;
        });

        els.helpBtn.addEventListener("click", openHelpOverlay);
        els.helpCloseBtn.addEventListener("click", closeHelpOverlay);
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
    }

    function validateElements() {
        const missing = Object.entries(els)
            .filter(([, el]) => !el)
            .map(([name]) => name);
        if (missing.length) {
            console.error(`[${ARTIFACT_NAME}] missing DOM elements:`, missing);
            return false;
        }
        return true;
    }

    function boot() {
        if (!validateElements()) return;

        bindEvents();
        applyPreset(String(els.profilePreset.value || "V1_MOMENTUM_CORE"));
        updateWindowSummary();
        clearChart();

        els.primarySummary.textContent = "No run yet.";
        els.permutationsBody.innerHTML = "<tr><td colspan='8'>No run yet.</td></tr>";
        els.gameOutcomesBody.innerHTML = "<tr><td colspan='8'>No run yet.</td></tr>";
        els.inspectSummary.textContent = "No game inspected yet.";
        els.tradesBody.innerHTML = "<tr><td colspan='8'>No game inspected yet.</td></tr>";

        log(`boot complete (${ARTIFACT_NAME} v${ARTIFACT_VERSION})`);
    }

    document.addEventListener("DOMContentLoaded", boot);
})();
