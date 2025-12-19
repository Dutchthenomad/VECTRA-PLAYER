# Convert Print Statements to Logging

**Labels:** `refactor`, `good-first-issue`, `copilot-safe`
**Assignee:** Copilot Subagent

## Summary

Replace `print()` statements with proper `logging` calls in production code files.

## Files to Update

### `src/ml/backtest.py`

Search for `print(` statements and convert to appropriate log levels:

```python
# BEFORE
print(f"Running backtest: {strategy_name}")

# AFTER
import logging
logger = logging.getLogger(__name__)

logger.info(f"Running backtest: {strategy_name}")
```

### Log Level Guidelines

| Print Pattern | Log Level |
|---------------|-----------|
| Status/progress messages | `logger.info()` |
| Debug/diagnostic output | `logger.debug()` |
| Warnings | `logger.warning()` |
| Errors | `logger.error()` |

## Acceptance Criteria

- [ ] All `print()` calls in `src/ml/backtest.py` converted to logging
- [ ] Logger initialized at module level: `logger = logging.getLogger(__name__)`
- [ ] No functional behavior changes
- [ ] All tests pass: `cd src && python -m pytest tests/test_ml/ -v`

## Verification

```bash
# Should find no print statements in production code
grep -r "print(" src/ml/backtest.py | grep -v "test_" | wc -l
# Expected: 0
```

## Notes

- Do NOT convert print statements in test files
- Do NOT change the message content, only the output method
- Preserve f-string formatting
