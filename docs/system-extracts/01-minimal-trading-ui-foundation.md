# System 01: Trade Console UI (Agnostic Revision)

Legacy source basis: `VECTRA-BOILERPLATE`

## Legacy Extraction Summary

Current `minimal-trading` is a static artifact that:

- subscribes to Foundation events
- renders price/tick/player state
- emits trade commands through Foundation HTTP endpoints

Representative evidence:

```html
<!-- src/artifacts/tools/minimal-trading/index.html:175-183 -->
<script type="module">
  import { FoundationWSClient } from '../../shared/foundation-ws-client.js';
  import { MinimalTradingApp } from './app.js';
  const client = new FoundationWSClient();
  const app = new MinimalTradingApp(client);
  app.init();
</script>
```

```javascript
// src/artifacts/tools/minimal-trading/app.js:16-37
class TradeExecutor {
  constructor(baseUrl = 'http://localhost:9001') {
    this.baseUrl = baseUrl;
  }
  async buy() { return this._post('/api/trade/buy'); }
  async sell(percentage = null) {
    return this._post('/api/trade/sell', percentage ? { percentage } : {});
  }
}
```

```python
# src/foundation/http_server.py:82-91
self.app.router.add_post("/api/trade/buy", self._handle_trade_buy)
self.app.router.add_post("/api/trade/sell", self._handle_trade_sell)
self.app.router.add_post("/api/trade/sidebet", self._handle_trade_sidebet)
...
```

## Agnostic Target Boundary

UI module should be transport-agnostic and provider-agnostic.

- UI responsibility:
  - render state
  - capture user intent
  - show execution outcomes
- Non-UI responsibility (moved out):
  - strategy decisions
  - provider-specific execution
  - feed normalization

## Target Contract (Recommended)

### Inbound state stream

- Protocol: websocket or SSE (implementation choice)
- Channel: `/state/stream`
- Envelope:

```json
{
  "type": "market.tick",
  "ts": 1737830112000,
  "source": "provider-id",
  "data": {}
}
```

### Outbound command API

- `POST /commands/trade`
- `POST /commands/bet-adjust`
- `POST /commands/percentage`

Payload example:

```json
{
  "command_id": "uuid",
  "action": "BUY",
  "amount": 0.01,
  "metadata": { "ui_session": "abc" }
}
```

## Cleanup Checklist

1. Remove hardcoded `http://localhost:9001` from UI code.
2. Replace endpoint paths with configurable command gateway.
3. Move bot/autonomy logic out of UI into separate strategy service.
4. Keep UI event model stable and versioned.
5. Add command acknowledgment state (`pending/succeeded/failed`).

## Migration Notes

- Keep current visual layout and controls; this is a strong operator surface.
- Treat this module as the canonical human-control shell in the new system.
