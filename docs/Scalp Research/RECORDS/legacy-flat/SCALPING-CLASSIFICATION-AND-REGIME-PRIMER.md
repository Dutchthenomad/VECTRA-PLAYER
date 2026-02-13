# Scalping Classification and Regime Primer

Last updated: 2026-02-08

This document explains, in plain language, how the current V1 simulator decides:

1. What type of game it is (`regime` classification).
2. Which entry logic is allowed for that game (regime-to-playbook routing).

Source of truth code:

- `src/artifacts/tools/scalping-bot-v1-simulator/main.js`
- `src/artifacts/tools/scalping-explorer/main.js`

## 1) High-Level Mental Model

The system is deterministic and rule-based (not ML).

For each game:

1. Look only at the first `classificationTicks` interval (`classificationTicks + 1` prices).
2. Compute a feature snapshot (momentum, volatility, sign flips, range, expansion ratio).
3. Assign exactly one regime:
- `trend_up`
- `trend_down`
- `expansion`
- `chop`
- `uncertain`
4. Use regime routing to allow one or more playbooks (or none).
5. Start entry scanning at tick `classificationTicks + 1`.

Important: classification is done once per game from the early window only. It is not updated later in the game.

## 2) Classifier Inputs and Features

### Inputs

- `prices[]` tick series for a single game.
- `classificationTicks` (UI setting).
- Effective window: `classifierWindow = max(12, classificationTicks)`.
- Minimum data required: `classifierWindow + 1` prices.

If not enough prices are present, regime is immediately `uncertain` with low confidence.

### Features calculated from the first window

- `momentumWindow`: return from first price to last price in the window.
- `momentumTail`: return from the last up-to-10 ticks of that same window.
- `vol`: standard deviation of per-tick returns in the window.
- `range`: `(max_price / min_price) - 1` inside the window.
- `signFlips`: count of return sign changes (+ to -, or - to +), excluding zero returns.
- `expansionRatio`: average absolute return in late half of window divided by early half.

### Adaptive thresholds (depend on classifier window size)

- `baselineScale = sqrt(classifierWindow / 25)`
- `trendMomentumThreshold = 0.06 * baselineScale`
- `chopMomentumThreshold = 0.025 * baselineScale`
- `trendFlipMax = max(8, round(numReturns * 0.34))`
- `downFlipMax = max(9, round(numReturns * 0.36))`
- `chopFlipMin = max(12, round(numReturns * 0.50))`

This scaling keeps behavior more comparable when `classificationTicks` changes.

## 3) Regime Decision Order (Exact)

Order matters. The first matching rule wins.

1. `trend_up`
- Condition: `momentumWindow > trendMomentumThreshold` and `signFlips <= trendFlipMax`

2. `trend_down`
- Condition: `momentumWindow < -trendMomentumThreshold` and `signFlips <= downFlipMax`

3. `expansion`
- Condition: `vol > 0.04` OR `range > 0.20` OR `expansionRatio > 1.55`

4. `chop`
- Condition: `signFlips >= chopFlipMin` OR (`abs(momentumWindow) < chopMomentumThreshold` AND `vol > 0.018`)

5. `uncertain`
- Fallback if none of the above pass.

So, if a game qualifies for both trend and expansion conditions, trend wins because trend checks are evaluated first.

## 4) What Each Regime Means in Plain Language

- `trend_up`: early movement is directionally up with relatively clean flow (limited back-and-forth flips).
- `trend_down`: early movement is directionally down with relatively clean flow.
- `expansion`: large movement envelope and/or volatility is growing across the baseline.
- `chop`: oscillatory behavior, lots of direction switching, little net directional progress.
- `uncertain`: mixed or weak evidence; not confidently trend/chop/expansion.

## 5) Regime Model vs Playbook Model

These are different layers:

1. Classification model (regime detector)
- Uses early-window features to produce one regime label.

2. Regime routing model (gate)
- Maps that regime to allowed playbook families.

3. Playbook signal model (entry trigger)
- At each tick after classification, checks playbook-specific entry conditions.

4. Exit model
- Uses TP/SL/time rules once in a position.

So "regime model" in this system means routing/gating based on a regime label, not a separate statistical classifier.

## 6) Regime-to-Playbook Routing (AUTO mode)

Current map:

- `trend_up` -> `P1_MOMENTUM`, `P2_PULLBACK_CONT`
- `trend_down` -> `P3_MEAN_REVERT`
- `expansion` -> `P4_BREAKOUT`, `P1_MOMENTUM`
- `chop` -> `P3_MEAN_REVERT`
- `uncertain` -> no trade

In `AUTO_REGIME` mode, the bot tries playbooks in that order and takes the first signal that passes.

In fixed mode (for example `P1_MOMENTUM` only), regime routing is bypassed and only that chosen playbook is evaluated.

## 7) Playbook Entry Rules (Current)

- `P1_MOMENTUM`
- Enter if `m3 > +1.5%` and `m5 > +2.0%`.

- `P2_PULLBACK_CONT`
- Enter if `m8 > +3.0%` and `m1 < -0.5%` and `m2 > +0.3%`.

- `P3_MEAN_REVERT`
- Enter if `m3 < -3.0%` and `m1 > +0.4%`.

- `P4_BREAKOUT`
- Enter if current price > prior 12-tick high by 1% and `m3 > +1.0%`.

All playbooks need at least 12 ticks of lookback.

## 8) Practical Differences You Should Keep in Mind

- Changing `classificationTicks` changes both:
- the amount of data used for classification, and
- threshold scale via `baselineScale`.

- `AUTO_REGIME` can output zero trades for `uncertain` games by design.

- Fixed playbook mode can still trade in games that classifier marked `uncertain`, because it ignores regime gate.

- Regime labels explain "why this game got this playbook family," while playbook conditions explain "why this specific entry fired at this specific tick."

## 9) Minimal Pseudocode

```text
cls = classifyGame(first_window)
allowed = (mode == AUTO_REGIME) ? REGIME_PLAYBOOK_MAP[cls.regime] : [selectedPlaybook]
for tick in [classificationTicks + 1 .. entryCutoff]:
  for pb in allowed:
    if playbookSignal(pb, tick):
      enter trade
      manage TP/SL/time exit
      break
```

## 10) Confidence Output

Classifier also outputs a confidence score and reasons list.

- Confidence is rule-derived (formula-based), not calibrated probability.
- It is best treated as a relative strength signal for diagnostics.

## 11) Where to Edit If We Revise the Model

- Regime map: `REGIME_PLAYBOOK_MAP`
- Classifier logic: `classifyGame(...)`
- Playbook entry rules: `playbookSignal(...)`
- Start-of-trading rule: simulation loop using `startTick = classificationTicks + 1`
