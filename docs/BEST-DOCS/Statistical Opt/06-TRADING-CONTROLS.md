# 06 - Trading Controls

## Purpose

Map dashboard trading buttons to rugs.fun browser UI:
1. BUY/SELL/SIDEBET execution
2. Bet amount adjustment (+0.001, +0.01, etc.)
3. Percentage buttons for sell (10%, 25%, 50%, 100%)
4. Clear, half, double, max controls

## Dependencies

```python
# From CDP integration
from browser.bridge import BrowserBridge, SelectorStrategy

# Flask wrapper
from recording_ui.services.browser_service import BrowserService
```

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        Trading Control Flow                                │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Dashboard UI                 Flask API              BrowserBridge        │
│  ───────────                 ─────────              ──────────────        │
│                                                                           │
│  [BUY Button] ──────▶ POST /api/trade/buy ──────▶ on_buy_clicked()       │
│                              │                           │                │
│                              │                           ▼                │
│                              │                   _queue_action("BUY")     │
│                              │                           │                │
│                              │                           ▼                │
│                              │                   _do_click_with_retry()   │
│                              │                           │                │
│                              │           ┌───────────────┼───────────────┐│
│                              │           │               │               ││
│                              │           ▼               ▼               ▼│
│                              │      CSS Selector    Text Match    Class Pattern│
│                              │           │               │               ││
│                              │           └───────────────┼───────────────┘│
│                              │                           │                │
│                              │                           ▼                │
│                              │                   element.click()          │
│                              │                           │                │
│                              │                           ▼                │
│                              ◀───────────────── ClickResult              │
│                              │                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Button Selector Configuration

```python
# src/browser/bridge.py

class SelectorStrategy:
    """Multi-strategy selector system for robust button finding"""

    # CSS Selectors - Primary method (rugs.fun specific classes)
    BUTTON_CSS_SELECTORS = {
        "BUY": [
            # rugs.fun v2 UI classes
            'div[class*="_buttonSection_"]:nth-child(1)',
            '[class*="_buttonsRow_"] > div:first-child',
            'button[class*="buy" i]',
            '[data-action="buy"]',
        ],
        "SELL": [
            'div[class*="_buttonSection_"]:nth-child(2)',
            '[class*="_buttonsRow_"] > div:nth-child(2)',
            'button[class*="sell" i]',
        ],
        "SIDEBET": [
            ".bet-button",
            'div.bet-button',
            '[class*="sidebet-banner"] [class*="bet-button"]',
            'button[class*="side" i]',
        ],
        "X": [  # Clear button
            'button[class*="_clearButton_"]',
            '[class*="_inputActions_"] button',
        ],
        "+0.001": [...],
        "+0.01": [...],
        "+0.1": [...],
        "+1": [...],
        "1/2": [...],
        "X2": [...],
        "10%": [
            'button[class*="_percentageBtn_"]:nth-child(1)',
        ],
        "25%": [
            'button[class*="_percentageBtn_"]:nth-child(2)',
        ],
        "50%": [
            'button[class*="_percentageBtn_"]:nth-child(3)',
        ],
        "100%": [
            'button[class*="_percentageBtn_"]:nth-child(4)',
        ],
    }

    # Text patterns for dynamic button text
    BUTTON_TEXT_PATTERNS = {
        "BUY": ["BUY", "Buy", "buy"],
        "SELL": ["SELL", "Sell", "sell"],
        "SIDEBET": ["SIDEBET", "SIDE", "Side", "sidebet"],
        "X": ["×", "✕", "X", "x", "✖"],
        "+0.001": ["+0.001", "+ 0.001"],
        "+0.01": ["+0.01", "+ 0.01"],
        "1/2": ["1/2", "½", "0.5x", "Half"],
        "X2": ["X2", "x2", "2x", "2X", "Double"],
    }
```

### 2. Click Execution with Retry

```python
async def _do_click_with_retry(self, button: str) -> ClickResult:
    """Click button with retry logic and exponential backoff"""
    last_result = ClickResult(success=False, error="No attempts made")

    for attempt in range(1, self.MAX_RETRIES + 1):
        result = await self._do_click(button)
        result.attempt = attempt

        if result.success:
            self._record_click_stat(button, "success", result.method)
            return result

        last_result = result

        if attempt < self.MAX_RETRIES:
            delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(f"Click attempt {attempt} failed: {result.error}")
            await asyncio.sleep(delay)

    self._record_click_stat(button, "failure", last_result.error)
    return last_result
```

### 3. Multi-Strategy Click

```python
async def _do_click(self, button: str) -> ClickResult:
    """
    Click button using multiple strategies.

    Order (prevents X matching X2):
    1. CSS selector (most reliable)
    2. Exact text match
    3. Starts-with text match
    4. Contains text match
    5. Class pattern match
    """
    # Strategy 1: CSS selector FIRST
    result = await self._try_css_selector_click(page, button)
    if result.success:
        return result

    # Strategy 2: Text-based matching
    result = await self._try_text_based_click(page, button)
    if result.success:
        return result

    # Strategy 3: Class pattern matching
    result = await self._try_class_pattern_click(page, button)
    if result.success:
        return result

    # All failed
    available = await self._get_available_buttons(page)
    return ClickResult(
        success=False,
        error=f"Button not found. Available: {available[:5]}"
    )
```

### 4. Text-Based Click with Visibility Check

```python
async def _try_text_based_click(self, page, button: str) -> ClickResult:
    """Click using text matching with visibility detection"""
    patterns = SelectorStrategy.get_text_patterns(button)

    js_code = """
    (patterns) => {
        const allButtons = Array.from(document.querySelectorAll('button'));
        const allClickables = [
            ...allButtons,
            ...Array.from(document.querySelectorAll('div[class*="button"]'))
        ];

        // Visibility check (handles position:fixed)
        const isVisible = (el) => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' &&
                   style.visibility !== 'hidden' &&
                   style.opacity !== '0' &&
                   rect.width > 0 && rect.height > 0 &&
                   rect.top < window.innerHeight &&
                   rect.bottom > 0;
        };

        const isEnabled = (el) => {
            return !el.disabled &&
                   !el.classList.contains('disabled') &&
                   el.getAttribute('aria-disabled') !== 'true';
        };

        const visibleButtons = allClickables.filter(b =>
            isVisible(b) && isEnabled(b)
        );

        // Strategy 1: EXACT match (prevents X matching X2)
        for (const pattern of patterns) {
            let target = visibleButtons.find(b => {
                const text = b.textContent.trim();
                return text === pattern ||
                       text.toUpperCase() === pattern.toUpperCase();
            });
            if (target) {
                target.click();
                return { success: true, text: target.textContent.trim(),
                         method: 'exact' };
            }
        }

        // Strategy 2: Starts-with (skip for single-char patterns)
        for (const pattern of patterns) {
            if (pattern.length === 1) continue;  // Prevent X matching X2

            let target = visibleButtons.find(b => {
                const text = b.textContent.trim();
                return text.startsWith(pattern);
            });
            if (target) {
                target.click();
                return { success: true, text: target.textContent.trim(),
                         method: 'starts-with' };
            }
        }

        return { success: false };
    }
    """

    result = await page.evaluate(js_code, patterns)
    if result.get("success"):
        return ClickResult(
            success=True,
            method=f"text-{result.get('method')}",
            button_text=result.get("text", "")
        )
    return ClickResult(success=False, error="No text match")
```

### 5. BrowserService Flask Wrapper

```python
# src/recording_ui/services/browser_service.py

class BrowserService:
    """Flask-compatible wrapper for BrowserBridge"""

    def click_buy(self) -> dict:
        return self._do_click("buy")

    def click_sell(self) -> dict:
        return self._do_click("sell")

    def click_sidebet(self) -> dict:
        return self._do_click("sidebet")

    def click_increment(self, amount: float) -> dict:
        """Click increment button (+0.001, +0.01, etc.)"""
        button_map = {
            0.001: "+0.001",
            0.01: "+0.01",
            0.1: "+0.1",
            1.0: "+1",
        }
        button = button_map.get(amount)
        if not button:
            return {"success": False, "error": f"Invalid: {amount}"}

        result = self._do_click(button)
        if result.get("success"):
            self._game_state.bet_amount += amount
            result["bet_amount"] = self._game_state.bet_amount
        return result

    def click_percentage(self, pct: int) -> dict:
        """Click sell percentage button (10%, 25%, 50%, 100%)"""
        pct_map = {10: 0.1, 25: 0.25, 50: 0.5, 100: 1.0}
        ratio = pct_map.get(pct)
        if ratio is None:
            return {"success": False, "error": f"Invalid: {pct}"}

        bridge = self._get_bridge()
        bridge.on_percentage_clicked(ratio)
        return {"success": True, "action": f"{pct}%"}

    def click_clear(self) -> dict:
        """Clear bet to 0"""
        result = self._do_click("X")
        if result.get("success"):
            self._game_state.bet_amount = 0.0
        return result

    def click_half(self) -> dict:
        """Halve current bet"""
        result = self._do_click("1/2")
        if result.get("success"):
            self._game_state.bet_amount /= 2
        return result

    def click_double(self) -> dict:
        """Double current bet"""
        result = self._do_click("X2")
        if result.get("success"):
            self._game_state.bet_amount *= 2
        return result
```

### 6. Flask API Endpoints

```python
# src/recording_ui/app.py

@app.route("/api/trade/buy", methods=["POST"])
def trade_buy():
    result = browser_service.click_buy()
    return jsonify(result)

@app.route("/api/trade/sell", methods=["POST"])
def trade_sell():
    result = browser_service.click_sell()
    return jsonify(result)

@app.route("/api/trade/sidebet", methods=["POST"])
def trade_sidebet():
    result = browser_service.click_sidebet()
    return jsonify(result)

@app.route("/api/trade/increment", methods=["POST"])
def trade_increment():
    data = request.get_json() or {}
    amount = data.get("amount", 0.01)
    result = browser_service.click_increment(amount)
    return jsonify(result)

@app.route("/api/trade/percentage", methods=["POST"])
def trade_percentage():
    data = request.get_json() or {}
    pct = data.get("pct", 100)
    result = browser_service.click_percentage(pct)
    return jsonify(result)
```

## Button Mapping Table

| Dashboard Button | API Endpoint | Bridge Method | rugs.fun Selector |
|------------------|--------------|---------------|-------------------|
| BUY | `/api/trade/buy` | `on_buy_clicked()` | `_buttonSection_:nth-child(1)` |
| SELL | `/api/trade/sell` | `on_sell_clicked()` | `_buttonSection_:nth-child(2)` |
| SIDEBET | `/api/trade/sidebet` | `on_sidebet_clicked()` | `.bet-button` |
| +.001 | `/api/trade/increment` | `on_increment_clicked("+0.001")` | Text match |
| +.01 | `/api/trade/increment` | `on_increment_clicked("+0.01")` | Text match |
| +.1 | `/api/trade/increment` | `on_increment_clicked("+0.1")` | Text match |
| +1 | `/api/trade/increment` | `on_increment_clicked("+1")` | Text match |
| 1/2 | `/api/trade/half` | `on_increment_clicked("1/2")` | Text match |
| X2 | `/api/trade/double` | `on_increment_clicked("X2")` | Text match |
| X | `/api/trade/clear` | `on_clear_clicked()` | `_clearButton_` |
| 10% | `/api/trade/percentage` | `on_percentage_clicked(0.1)` | `_percentageBtn_:nth-child(1)` |
| 25% | `/api/trade/percentage` | `on_percentage_clicked(0.25)` | `_percentageBtn_:nth-child(2)` |
| 50% | `/api/trade/percentage` | `on_percentage_clicked(0.5)` | `_percentageBtn_:nth-child(3)` |
| 100% | `/api/trade/percentage` | `on_percentage_clicked(1.0)` | `_percentageBtn_:nth-child(4)` |

## Frontend JavaScript

```javascript
// static/js/backtest.js

// Trading buttons
document.getElementById('btn-buy').addEventListener('click', async () => {
    await fetch('/api/trade/buy', {method: 'POST'});
});

document.getElementById('btn-sell').addEventListener('click', async () => {
    await fetch('/api/trade/sell', {method: 'POST'});
});

document.getElementById('btn-sidebet').addEventListener('click', async () => {
    await fetch('/api/trade/sidebet', {method: 'POST'});
});

// Increment buttons
document.querySelectorAll('.btn-increment').forEach(btn => {
    btn.addEventListener('click', async () => {
        const amount = parseFloat(btn.dataset.amount);
        await fetch('/api/trade/increment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({amount})
        });
    });
});

// Percentage buttons
document.querySelectorAll('.btn-percentage').forEach(btn => {
    btn.addEventListener('click', async () => {
        const pct = parseInt(btn.dataset.pct);
        await fetch('/api/trade/percentage', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({pct})
        });
    });
});
```

## Gotchas

1. **X vs X2**: Single-char pattern "X" matches "X2". CSS selectors must take priority.

2. **Dynamic Button Text**: Buttons show "BUY+0.030 SOL". Use `starts-with` matching.

3. **position: fixed**: Standard visibility checks fail. Use bounding rect check.

4. **div vs button**: rugs.fun uses div containers that act as buttons. Query both.

5. **Optimistic Tracking**: `bet_amount` tracked optimistically. May drift from actual browser value.

6. **Retry Backoff**: Exponential backoff (0.5s, 1s, 2s) prevents hammering.

7. **Click Stats**: Track success/failure by method for debugging selector issues.
