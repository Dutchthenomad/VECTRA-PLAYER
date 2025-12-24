# ML Code Audit Report (`src/ml/`)

Date: 2025-12-22
Scope: All source files under `src/ml/`.
Method: Manual static review + `python3 -m compileall -q src/ml` (syntax check).

## Executive Summary

`src/ml/` implements an ML-based “sidebet / rug prediction” subsystem: feature extraction, dataset building from JSONL recordings, model training (Gradient Boosting), real-time prediction wrapper, and a simple martingale-style backtester.

The code is coherent and readable, but there are several correctness and operational risks:

- The package imports heavy optional dependencies (`numpy`, `scikit-learn`, `joblib`) at import time, which can break environments that don’t install ML extras.
- The backtester’s cooldown/skip-ahead logic appears to be off by 5 ticks (50-tick spacing vs the documented 45).
- The training pipeline assumes both classes exist and will crash or produce misleading output when the dataset is single-class or extremely imbalanced.

No syntax errors were found.

## Inventory (Files Reviewed)

- `src/ml/__init__.py`
- `src/ml/data_processor.py`
- `src/ml/feature_extractor.py`
- `src/ml/model.py`
- `src/ml/predictor.py`
- `src/ml/backtest.py`

Non-runtime artifacts present in-tree:
- `src/ml/__pycache__/...` (bytecode cache directory)

## High Priority Findings (Fix Soon)

### 1) Import-time hard dependency on ML stack (optional dependency not isolated)

**Why this matters**
- `src/ml/__init__.py` imports `SidebetModel`, which imports `sklearn` + `joblib` at module import time.
- If `scikit-learn` or `joblib` aren’t installed (common in lightweight prod builds), `import ml` will fail immediately.
- Even if `src/ml/` is “optional”, accidental imports (or tooling that imports all packages) will break.

**Where**
- `src/ml/__init__.py`
- `src/ml/model.py` (imports `sklearn`, `joblib`)

**Recommended remediation**
- Make ML dependencies truly optional:
  - move heavy imports inside functions/methods (`SidebetModel.__init__`, `train`, `load`, etc.), or
  - provide a clear `ImportError` message pointing to the required extra.
- Consider not re-exporting heavy symbols from `src/ml/__init__.py` unless needed.

### 2) `SidebetBacktester`: cooldown/skip-ahead logic likely off by 5 ticks

**Why this matters**
- The backtester is documented as “40-tick windows + 5-tick cooldown = 45 ticks per attempt”.
- In `backtest_game()`, after placing a bet:
  - it sets `last_bet_tick = sample["tick"]`,
  - then immediately sets `last_bet_tick = sample["tick"] + 45`,
  - and later the cooldown check is `if sample["tick"] - last_bet_tick < 5: continue`.
- This effectively enforces `>= 50` ticks between allowed bets (`tick >= bet_tick + 50`), not 45.

**Where**
- `src/ml/backtest.py` (`SidebetBacktester.backtest_game`)

**Recommended remediation**
- Decide which behavior is intended:
  - If you want *exactly* 45 ticks between bets, set `last_bet_tick = sample["tick"] + 40` (so the `+5` cooldown yields 45), or restructure so “window skip” and “cooldown” aren’t double-counted.

### 3) `SidebetModel.train()`: breaks on single-class datasets and assumes class ordering

**Why this matters**
- `compute_class_weight(..., classes=np.unique(y), y=y)` can return a 1-length array if `y` has only one class (e.g., filtering removed all positives).
- The code then:
  - prints `dict(zip([0, 1], class_weights))` (wrong if classes aren’t `[0,1]`),
  - indexes `class_weights[1]` (crashes if only one class),
  - uses `roc_auc_score(...)` and `classification_report(...)` which can fail or be meaningless with single-class `y`.

**Where**
- `src/ml/model.py` (`SidebetModel.train`)

**Recommended remediation**
- Validate `y` up front (must contain both classes) and raise a clear error with dataset stats if not.
- Track the actual `classes_` ordering and map weights accordingly.

## Medium Priority Findings (Fix When Practical)

### 4) `SidebetPredictor` type hints use `any` instead of `Any`

**Why this matters**
- `dict[str, any]` is not valid typing; `any` is a built-in function, not the typing type.
- This can confuse type checkers and readers.

**Where**
- `src/ml/predictor.py` (`predict_rug_probability`, `get_model_info`)

**Recommended remediation**
- Use `from typing import Any` and annotate as `dict[str, Any]`.

### 5) `SidebetPredictor._calculate_confidence()` ignores `sequence_feasibility` weight

**Why this matters**
- `feature_weights` defines `sequence_feasibility`, but it’s not used in the confidence computation.
- This makes the weighting metadata misleading (and suggests the function is incomplete).

**Where**
- `src/ml/predictor.py` (`feature_weights`, `_calculate_confidence`)

**Recommended remediation**
- Either incorporate `sequence_feasibility` into confidence or remove it from `feature_weights` to avoid false signaling.

### 6) `GameDataProcessor.process_game_file()` is memory-heavy and relies on a specific JSONL schema

**Why this matters**
- It loads the entire JSONL file into a Python list; large recordings can be expensive.
- It filters on `event.get("type") == "tick"` and expects fields like `phase`, `active`, `rugged`, `price/multiplier`.
- If upstream recording format changed during the refactor (common), this silently produces empty datasets or wrong labels.

**Where**
- `src/ml/data_processor.py`

**Recommended remediation**
- Stream JSONL line-by-line (generator) to reduce memory.
- Validate schema and emit a clear summary when zero ticks/labels are produced (instead of returning `[]` silently).

### 7) Feature extractor “baseline volatility == 0” handling is likely incorrect for some cases

**Why this matters**
- If baseline volatility is ~0 but current volatility is >0, `ratio` is forced to `1.0`, losing the “sudden volatility” signal.
- This can hide meaningful patterns if early prices are flat.

**Where**
- `src/ml/feature_extractor.py` (`calculate_volatility_features`)

**Recommended remediation**
- Distinguish:
  - baseline == 0 and current == 0 → ratio = 1.0
  - baseline == 0 and current > 0 → ratio = capped high value (or use epsilon in denominator)

## Low Priority Findings / Opportunities

### 8) Logging vs printing

**Notes**
- Several modules use `print()` heavily (`data_processor.py`, `model.py`, `predictor.py`, `backtest.py`).
- This is fine for notebooks/scripts but noisy in integrated applications and tests.

**Recommendation**
- Use `logging` and/or allow callers to pass a logger/verbosity flag.

### 9) Backtester bookkeeping gaps

**Notes**
- Failed martingale sequences (4 losses) are not recorded as sequences, which skews “sequence success rate”.
- End-of-game partial sequences aren’t summarized.

**Where**
- `src/ml/backtest.py`

## Suggested Validation Checklist (After Fixes)

- Add minimal unit tests for:
  - backtester spacing logic (ensure 45 ticks between bets, or document the intended interval)
  - `SidebetModel.train()` behavior on single-class / tiny datasets (should fail fast with a clear message)
  - `GameDataProcessor.process_game_file()` schema expectations (detect format mismatches early)
