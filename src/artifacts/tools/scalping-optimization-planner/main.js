/*
 * Scalping Optimization Planner
 *
 * Purpose:
 * - Visualize and size the exploration workflow before heavy runs
 * - Keep entry-first -> exit-surface -> Monte Carlo sequencing explicit
 * - Generate reproducible kickoff markdown for documentation
 */

const BASELINE = {
    dataset: "scalping_unique_games_min60.jsonl",
    games: 1772,
    returns: {
        h1: { mean: 0.0569, median: 0.4939, p10: -1.9597, p90: 2.9211 },
        h5: { mean: 1.8502, median: 2.1902, p10: -20.0888, p90: 23.7247 },
    },
    mae5: { p10: -21.7930, p25: -9.7748, p50: -1.0696 },
    mfe5: { p50: 3.7411, p75: 10.7467, p90: 24.8136 },
    firstTouch: { sl4tp6: { tpFirst: 34.4229, slFirst: 26.1740, neither: 39.4032 } },
    timeExitPairs: {
        sl4tp6: 1.6908,
        sl6tp8: 1.7555,
        sl8tp10: 1.7694,
        sl12tp15: 1.9939,
    },
};

const els = {
    helpBtn: document.getElementById("helpBtn"),
    helpOverlay: document.getElementById("helpOverlay"),
    helpCloseBtn: document.getElementById("helpCloseBtn"),
    helpTabBtns: Array.from(document.querySelectorAll(".help-tab-btn")),
    helpPanels: Array.from(document.querySelectorAll(".help-panel")),
    statusText: document.getElementById("statusText"),
    generateBtn: document.getElementById("generateBtn"),
    copyBtn: document.getElementById("copyBtn"),
    kickoffText: document.getElementById("kickoffText"),
    baselineText: document.getElementById("baselineText"),
    footTotal: document.getElementById("footTotal"),

    searchMode: document.getElementById("searchMode"),
    promotionPct: document.getElementById("promotionPct"),
    stageATrials: document.getElementById("stageATrials"),
    stageBTrials: document.getElementById("stageBTrials"),
    classifyMin: document.getElementById("classifyMin"),
    classifyMax: document.getElementById("classifyMax"),
    classifyStep: document.getElementById("classifyStep"),
    cutoffMin: document.getElementById("cutoffMin"),
    cutoffMax: document.getElementById("cutoffMax"),
    cutoffStep: document.getElementById("cutoffStep"),
    holdTicks: document.getElementById("holdTicks"),
    thresholdProfiles: document.getElementById("thresholdProfiles"),
    confidenceGateCount: document.getElementById("confidenceGateCount"),
    stageAGames: document.getElementById("stageAGames"),
    stageBGames: document.getElementById("stageBGames"),
    familyChecks: Array.from(document.querySelectorAll(".familyCheck")),
    phase1Summary: document.getElementById("phase1Summary"),

    candidateCount: document.getElementById("candidateCount"),
    tpMin: document.getElementById("tpMin"),
    tpMax: document.getElementById("tpMax"),
    slMin: document.getElementById("slMin"),
    slMax: document.getElementById("slMax"),
    driftRefChecks: Array.from(document.querySelectorAll(".driftRefCheck")),
    phase2Summary: document.getElementById("phase2Summary"),

    mcCandidateCount: document.getElementById("mcCandidateCount"),
    pathsPerCandidate: document.getElementById("pathsPerCandidate"),
    gamesPerPath: document.getElementById("gamesPerPath"),
    stressScenarios: document.getElementById("stressScenarios"),
    phase3Summary: document.getElementById("phase3Summary"),

    step1Value: document.getElementById("step1Value"),
    step2Value: document.getElementById("step2Value"),
    step3Value: document.getElementById("step3Value"),
    step4Value: document.getElementById("step4Value"),
};

function nInt(el, min, max, fallback) {
    const raw = Number(el.value);
    let v = Number.isFinite(raw) ? Math.floor(raw) : fallback;
    v = Math.max(min, Math.min(max, v));
    if (v !== raw) el.value = String(v);
    return v;
}

function parseTickOptions(csv) {
    const parts = String(csv || "")
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((v) => Number.isFinite(v) && v > 0)
        .map((v) => Math.floor(v));
    const unique = [...new Set(parts)].sort((a, b) => a - b);
    return unique.length ? unique : [5];
}

function rangeCount(minV, maxV, stepV) {
    const min = Math.min(minV, maxV);
    const max = Math.max(minV, maxV);
    const step = Math.max(1, stepV);
    return Math.floor((max - min) / step) + 1;
}

function checkedValues(checks) {
    const vals = checks.filter((c) => c.checked).map((c) => c.value);
    return vals.length ? vals : [checks[0].value];
}

function formatNum(v) {
    return new Intl.NumberFormat("en-US").format(v);
}

function computePhase1() {
    const searchMode = els.searchMode.value === "grid" ? "grid" : "bayes";
    const promotionPct = nInt(els.promotionPct, 1, 100, 15);
    const stageATrials = nInt(els.stageATrials, 10, 100000, 300);
    const stageBTrials = nInt(els.stageBTrials, 5, 100000, 120);

    const classifyMin = nInt(els.classifyMin, 5, 200, 20);
    const classifyMax = nInt(els.classifyMax, 5, 300, 40);
    const classifyStep = nInt(els.classifyStep, 1, 50, 5);

    const cutoffMin = nInt(els.cutoffMin, 1, 500, 30);
    const cutoffMax = nInt(els.cutoffMax, 1, 800, 60);
    const cutoffStep = nInt(els.cutoffStep, 1, 50, 5);

    const holdOptions = parseTickOptions(els.holdTicks.value);
    const thresholdProfiles = nInt(els.thresholdProfiles, 1, 200, 6);
    const confidenceGateCount = nInt(els.confidenceGateCount, 1, 50, 3);

    const stageAGames = nInt(els.stageAGames, 10, 100000, 500);
    const stageBGames = nInt(els.stageBGames, 10, 100000, 1772);
    const families = checkedValues(els.familyChecks);

    const classifyCount = rangeCount(classifyMin, classifyMax, classifyStep);
    const cutoffCount = rangeCount(cutoffMin, cutoffMax, cutoffStep);
    const holdCount = holdOptions.length;
    const familyCount = families.length;
    const potentialGrid = classifyCount * cutoffCount * holdCount * familyCount * thresholdProfiles * confidenceGateCount;

    let stageAEvals;
    let promoted;
    let stageBEvals;
    if (searchMode === "grid") {
        stageAEvals = potentialGrid;
        promoted = Math.max(1, Math.ceil(stageAEvals * (promotionPct / 100)));
        stageBEvals = promoted;
    } else {
        stageAEvals = stageATrials;
        promoted = Math.max(1, Math.ceil(stageAEvals * (promotionPct / 100)));
        stageBEvals = Math.min(stageBTrials, potentialGrid);
    }

    const stageAGameEvals = stageAEvals * stageAGames;
    const stageBGameEvals = stageBEvals * stageBGames;

    return {
        searchMode,
        promotionPct,
        stageATrials,
        stageBTrials,
        classifyMin,
        classifyMax,
        classifyStep,
        cutoffMin,
        cutoffMax,
        cutoffStep,
        holdOptions,
        thresholdProfiles,
        confidenceGateCount,
        stageAGames,
        stageBGames,
        families,
        classifyCount,
        cutoffCount,
        holdCount,
        familyCount,
        potentialGrid,
        stageAEvals,
        promoted,
        stageBEvals,
        stageAGameEvals,
        stageBGameEvals,
    };
}

function computePhase2() {
    const candidateCount = nInt(els.candidateCount, 1, 10000, 30);
    const tpMin = nInt(els.tpMin, 1, 20, 1);
    const tpMaxRaw = nInt(els.tpMax, 1, 20, 5);
    const slMin = nInt(els.slMin, 1, 20, 1);
    const slMaxRaw = nInt(els.slMax, 1, 20, 4);
    const driftRefs = checkedValues(els.driftRefChecks);

    const tpMax = Math.max(tpMin, tpMaxRaw);
    if (tpMax !== tpMaxRaw) els.tpMax.value = String(tpMax);
    const slMax = Math.max(slMin, slMaxRaw);
    if (slMax !== slMaxRaw) els.slMax.value = String(slMax);

    const tpCount = tpMax - tpMin + 1;
    const slCount = slMax - slMin + 1;
    const permutationsPerCandidate = driftRefs.length * tpCount * slCount;
    const totalEval = candidateCount * permutationsPerCandidate;

    return {
        candidateCount,
        tpMin,
        tpMax,
        slMin,
        slMax,
        driftRefs,
        tpCount,
        slCount,
        permutationsPerCandidate,
        totalEval,
    };
}

function computePhase3() {
    const mcCandidateCount = nInt(els.mcCandidateCount, 1, 5000, 10);
    const pathsPerCandidate = nInt(els.pathsPerCandidate, 100, 500000, 10000);
    const gamesPerPath = nInt(els.gamesPerPath, 50, 5000, 500);
    const stressScenarios = nInt(els.stressScenarios, 1, 100, 4);

    const totalPaths = mcCandidateCount * pathsPerCandidate * stressScenarios;
    const totalGameSim = totalPaths * gamesPerPath;

    return {
        mcCandidateCount,
        pathsPerCandidate,
        gamesPerPath,
        stressScenarios,
        totalPaths,
        totalGameSim,
    };
}

function renderBaseline() {
    const b = BASELINE;
    const lines = [
        `dataset: ${b.dataset}`,
        `games: ${b.games}`,
        "",
        "return envelope:",
        `- h1 mean/median/p10/p90: ${b.returns.h1.mean.toFixed(4)} / ${b.returns.h1.median.toFixed(4)} / ${b.returns.h1.p10.toFixed(4)} / ${b.returns.h1.p90.toFixed(4)}`,
        `- h5 mean/median/p10/p90: ${b.returns.h5.mean.toFixed(4)} / ${b.returns.h5.median.toFixed(4)} / ${b.returns.h5.p10.toFixed(4)} / ${b.returns.h5.p90.toFixed(4)}`,
        "",
        "5-tick excursions:",
        `- MAE p10/p25/p50: ${b.mae5.p10.toFixed(4)} / ${b.mae5.p25.toFixed(4)} / ${b.mae5.p50.toFixed(4)}`,
        `- MFE p50/p75/p90: ${b.mfe5.p50.toFixed(4)} / ${b.mfe5.p75.toFixed(4)} / ${b.mfe5.p90.toFixed(4)}`,
        "",
        "first-touch (SL4/TP6 within 5 ticks):",
        `- tp_first/sl_first/neither: ${b.firstTouch.sl4tp6.tpFirst.toFixed(4)}% / ${b.firstTouch.sl4tp6.slFirst.toFixed(4)}% / ${b.firstTouch.sl4tp6.neither.toFixed(4)}%`,
        "",
        "time-exit-backstopped mean returns:",
        `- SL4/TP6: ${b.timeExitPairs.sl4tp6.toFixed(4)}%`,
        `- SL6/TP8: ${b.timeExitPairs.sl6tp8.toFixed(4)}%`,
        `- SL8/TP10: ${b.timeExitPairs.sl8tp10.toFixed(4)}%`,
        `- SL12/TP15: ${b.timeExitPairs.sl12tp15.toFixed(4)}%`,
    ];
    els.baselineText.textContent = lines.join("\n");
}

function buildKickoffMarkdown(p1, p2, p3) {
    const now = new Date().toISOString().slice(0, 10);
    return [
        `# Scalping Optimization Kickoff`,
        ``,
        `Date: ${now}`,
        ``,
        `## Phase 1: Entry-First Search`,
        `- mode: ${p1.searchMode}`,
        `- families: ${p1.families.join(", ")}`,
        `- classification ticks: ${p1.classifyMin}..${p1.classifyMax} step ${p1.classifyStep} (${p1.classifyCount} levels)`,
        `- entry cutoff tick: ${p1.cutoffMin}..${p1.cutoffMax} step ${p1.cutoffStep} (${p1.cutoffCount} levels)`,
        `- hold tick options: ${p1.holdOptions.join(", ")} (${p1.holdCount} levels)`,
        `- threshold profiles/family: ${p1.thresholdProfiles}`,
        `- confidence gate levels: ${p1.confidenceGateCount}`,
        `- potential full grid: ${formatNum(p1.potentialGrid)} combinations`,
        `- stage A evals: ${formatNum(p1.stageAEvals)} on ${formatNum(p1.stageAGames)} games each`,
        `- promotion rate: ${p1.promotionPct}% -> ${formatNum(p1.promoted)} promoted candidates (upper bound)`,
        `- stage B evals: ${formatNum(p1.stageBEvals)} on ${formatNum(p1.stageBGames)} games each`,
        ``,
        `## Phase 2: Exit Surface (Drift-Based)`,
        `- candidates entering phase 2: ${formatNum(p2.candidateCount)}`,
        `- drift references: ${p2.driftRefs.join(", ")}`,
        `- TP multipliers: ${p2.tpMin}..${p2.tpMax} (${p2.tpCount} levels)`,
        `- SL multipliers: ${p2.slMin}..${p2.slMax} (${p2.slCount} levels)`,
        `- permutations per candidate: ${formatNum(p2.permutationsPerCandidate)}`,
        `- total phase 2 evaluations: ${formatNum(p2.totalEval)}`,
        ``,
        `## Phase 3: Monte Carlo Robustness`,
        `- candidates entering MC: ${formatNum(p3.mcCandidateCount)}`,
        `- paths/candidate: ${formatNum(p3.pathsPerCandidate)}`,
        `- games/path: ${formatNum(p3.gamesPerPath)}`,
        `- stress scenarios: ${formatNum(p3.stressScenarios)}`,
        `- total MC paths: ${formatNum(p3.totalPaths)}`,
        `- total simulated game episodes: ${formatNum(p3.totalGameSim)}`,
        ``,
        `## Soft Label Policy`,
        `- Explore: high utility + stable neighborhood`,
        `- Avoid: dominated or downside-failure profile`,
        `- Noise: unstable, low-support, or outlier-led profile`,
    ].join("\n");
}

function renderSummaries(p1, p2, p3) {
    const p1Lines = [
        `mode: ${p1.searchMode}`,
        `families: ${p1.families.join(", ")}`,
        `classification levels: ${p1.classifyCount}`,
        `entry cutoff levels: ${p1.cutoffCount}`,
        `hold options: ${p1.holdOptions.join(", ")}`,
        `potential full grid: ${formatNum(p1.potentialGrid)}`,
        `stage A evals: ${formatNum(p1.stageAEvals)} (${formatNum(p1.stageAGameEvals)} game-evals)`,
        `stage B evals: ${formatNum(p1.stageBEvals)} (${formatNum(p1.stageBGameEvals)} game-evals)`,
        `promotion upper bound: ${formatNum(p1.promoted)} (${p1.promotionPct}%)`,
    ];
    els.phase1Summary.textContent = p1Lines.join("\n");

    const p2Lines = [
        `drift refs: ${p2.driftRefs.join(", ")}`,
        `TP levels: ${p2.tpCount} (${p2.tpMin}..${p2.tpMax})`,
        `SL levels: ${p2.slCount} (${p2.slMin}..${p2.slMax})`,
        `permutations/candidate: ${formatNum(p2.permutationsPerCandidate)}`,
        `total phase-2 evals: ${formatNum(p2.totalEval)}`,
    ];
    els.phase2Summary.textContent = p2Lines.join("\n");

    const p3Lines = [
        `MC candidates: ${formatNum(p3.mcCandidateCount)}`,
        `paths/candidate: ${formatNum(p3.pathsPerCandidate)}`,
        `games/path: ${formatNum(p3.gamesPerPath)}`,
        `stress scenarios: ${formatNum(p3.stressScenarios)}`,
        `total paths: ${formatNum(p3.totalPaths)}`,
        `total game episodes: ${formatNum(p3.totalGameSim)}`,
    ];
    els.phase3Summary.textContent = p3Lines.join("\n");

    els.step1Value.textContent = `${formatNum(p1.stageAEvals)} evals`;
    els.step2Value.textContent = `${formatNum(p1.stageBEvals)} evals`;
    els.step3Value.textContent = `${formatNum(p2.totalEval)} evals`;
    els.step4Value.textContent = `${formatNum(p3.totalPaths)} paths`;

    els.footTotal.textContent = `Total weighted work units: ${formatNum(p1.stageAGameEvals + p1.stageBGameEvals + p2.totalEval + p3.totalGameSim)}`;
}

function recalc() {
    const p1 = computePhase1();
    const p2 = computePhase2();
    const p3 = computePhase3();
    renderSummaries(p1, p2, p3);
    return { p1, p2, p3 };
}

function setHelpTab(tabId) {
    let selected = tabId;
    const valid = els.helpPanels.some((p) => p.dataset.helpPanel === tabId);
    if (!valid) selected = "entry";

    for (const panel of els.helpPanels) {
        if (panel.dataset.helpPanel === selected) panel.classList.remove("hidden");
        else panel.classList.add("hidden");
    }
    for (const btn of els.helpTabBtns) {
        if (btn.dataset.helpTab === selected) btn.classList.add("active");
        else btn.classList.remove("active");
    }
}

function openHelp(tab = "entry") {
    setHelpTab(tab);
    els.helpOverlay.classList.remove("hidden");
}

function closeHelp() {
    els.helpOverlay.classList.add("hidden");
}

async function copyKickoffText() {
    const text = els.kickoffText.textContent || "";
    if (!text.trim()) {
        els.statusText.textContent = "Nothing to copy yet. Generate kickoff markdown first.";
        return;
    }

    try {
        await navigator.clipboard.writeText(text);
        els.statusText.textContent = "Kickoff markdown copied to clipboard.";
    } catch (err) {
        els.statusText.textContent = "Clipboard copy failed. Select text manually from the markdown box.";
    }
}

function bindEvents() {
    const controls = [
        els.searchMode,
        els.promotionPct,
        els.stageATrials,
        els.stageBTrials,
        els.classifyMin,
        els.classifyMax,
        els.classifyStep,
        els.cutoffMin,
        els.cutoffMax,
        els.cutoffStep,
        els.holdTicks,
        els.thresholdProfiles,
        els.confidenceGateCount,
        els.stageAGames,
        els.stageBGames,
        ...els.familyChecks,
        els.candidateCount,
        els.tpMin,
        els.tpMax,
        els.slMin,
        els.slMax,
        ...els.driftRefChecks,
        els.mcCandidateCount,
        els.pathsPerCandidate,
        els.gamesPerPath,
        els.stressScenarios,
    ];

    for (const c of controls) {
        c.addEventListener("change", () => {
            recalc();
        });
    }

    els.generateBtn.addEventListener("click", () => {
        const { p1, p2, p3 } = recalc();
        const md = buildKickoffMarkdown(p1, p2, p3);
        els.kickoffText.textContent = md;
        els.statusText.textContent = "Kickoff markdown generated from current controls.";
    });

    els.copyBtn.addEventListener("click", () => {
        copyKickoffText().catch(() => {
            els.statusText.textContent = "Clipboard copy failed.";
        });
    });

    els.helpBtn.addEventListener("click", () => {
        openHelp("entry");
    });

    els.helpCloseBtn.addEventListener("click", () => {
        closeHelp();
    });

    els.helpOverlay.addEventListener("click", (event) => {
        if (event.target === els.helpOverlay) {
            closeHelp();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !els.helpOverlay.classList.contains("hidden")) {
            closeHelp();
        }
    });

    for (const btn of els.helpTabBtns) {
        btn.addEventListener("click", () => {
            setHelpTab(btn.dataset.helpTab || "entry");
        });
    }
}

function boot() {
    renderBaseline();
    bindEvents();
    recalc();
    setHelpTab("entry");
}

document.addEventListener("DOMContentLoaded", boot);
