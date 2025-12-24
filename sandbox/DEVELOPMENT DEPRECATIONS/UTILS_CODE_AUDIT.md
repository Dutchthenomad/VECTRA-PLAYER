# Utils Code Audit Report (`src/utils/`)

Date: 2025-12-22
Scope: All source files under `src/utils/`.
Method: Manual static review + `python3 -m compileall -q src/utils` (syntax check).

## Executive Summary

`src/utils/` currently contains a single runtime utility module (`decimal_utils.py`) and an export surface (`__init__.py`). The module is generally solid and provides a consistent “Decimal-first” approach for financial/math operations.

The highest-value improvements are around:

- API edge cases (handling `None`, `bool`, and non-finite values consistently),
- precision/rounding semantics (defaults and naming),
- and log hygiene (conversion warnings can become noisy in hot paths).

No syntax errors were found.

## Inventory (Files Reviewed)

- `src/utils/__init__.py`
- `src/utils/decimal_utils.py`

Non-runtime artifacts present in-tree:
- `src/utils/__pycache__/...` (bytecode cache directory)

## High Priority Findings (Fix Soon)

### 1) `decimal_utils.to_decimal()`: logging can become noisy + may leak values

**Why this matters**
- `to_decimal()` logs a warning on conversion failure when a `default` is provided.
- In hot paths (e.g., parsing feed data or validating many records), this can generate large volumes of logs.
- It also logs the raw `value`, which may include user-provided strings or sensitive identifiers depending on call sites.

**Where**
- `src/utils/decimal_utils.py` (`to_decimal`)

**Recommended remediation**
- Consider making the warning optional (e.g., `log_on_fail: bool = False`), or downgrade to `debug` by default.
- If warnings are desired, consider truncating long strings or sanitizing the logged `value`.

### 2) `Numeric` includes `bool` (via `int` subclass)

**Why this matters**
- `bool` is a subclass of `int`, so `to_decimal(True)` becomes `Decimal("True")` (which fails) and `to_float(True)` becomes `1.0`.
- Passing a boolean by mistake can silently produce valid-looking numeric results in some helpers.

**Where**
- `src/utils/decimal_utils.py` (`Numeric = Union[Decimal, float, str, int]`)

**Recommended remediation**
- Explicitly reject booleans in conversion helpers (e.g., `if isinstance(value, bool): ...`) or adjust the type alias and runtime checks.

## Medium Priority Findings (Fix When Practical)

### 3) `safe_divide()` is not “safe” for `None`

**Why this matters**
- `safe_divide()` calls `to_decimal()` on both inputs; if either is `None`, it raises (unless callers pass a `default` through `to_decimal`, which they cannot here).
- This is fine if upstream types are strict, but the name “safe_divide” suggests a more forgiving behavior.

**Where**
- `src/utils/decimal_utils.py` (`safe_divide`)

**Recommended remediation**
- Either:
  - rename to reflect strict behavior, or
  - accept `Numeric | None` and treat `None` as 0 (or return `default`).

### 4) Rounding defaults are inconsistent with `SOL_PRECISION`

**Why this matters**
- `SOL_PRECISION` is 9 (lamports), but `round_sol()` defaults to 4 dp and `format_sol()` defaults to 4 dp.
- If these utilities are used for actual amounts (not UI display), this can introduce rounding loss.

**Where**
- `src/utils/decimal_utils.py` (`SOL_PRECISION`, `round_sol`, `format_sol`)

**Recommended remediation**
- Clarify the intent: “UI precision” vs “native precision”.
- Consider defaulting `round_sol(..., precision=SOL_PRECISION)` for internal value handling, and keep formatting defaults separate (e.g., `format_sol_display`).

### 5) `percentage_change()` sentinel semantics

**Why this matters**
- When `old == 0` and `new > 0`, it returns `MAX_PERCENTAGE` as a sentinel rather than raising or returning `None/inf`.
- This can quietly distort analytics or UI if not explicitly handled by callers.

**Where**
- `src/utils/decimal_utils.py` (`percentage_change`)

**Recommended remediation**
- Document the sentinel in the docstring and ensure call sites handle it explicitly, or return `None`/raise on division-by-zero semantics.

## Low Priority Findings / Opportunities

### 6) Type hints could be modernized and tightened

**Notes**
- The module mixes `typing.Union` with `|` syntax; it works, but can be simplified to the modern forms consistently.
- Several functions accept `list` without parameterizing element types (e.g., `sum_decimals(values: list)`), which reduces static checking value.

**Where**
- `src/utils/decimal_utils.py`

### 7) `__init__.py` export surface is OK, but keep it stable

**Notes**
- `src/utils/__init__.py` re-exports a large set of identifiers; this becomes a public API surface.
- Any renames should be done carefully (or via deprecations) to avoid churn across the codebase.

## Suggested Validation Checklist (After Fixes)

- Run unit tests (if present): `cd src && python3 -m pytest tests/ -v`
- Add or extend focused tests for:
  - `to_decimal()` conversion edge cases (`None`, `""`, `"nan"`, `"inf"`, `True/False`)
  - rounding behavior at `SOL_PRECISION`
  - `percentage_change()` sentinel handling
