# System 08: Containerization + Plugin Patterns (Agnostic Revision)

Legacy source basis: `VECTRA-BOILERPLATE`

## Legacy Extraction Summary

Current platform already has:

- service manifests
- service discovery and lifecycle APIs
- docker-compose service patterns
- reserved port strategy

Representative evidence:

```python
# src/foundation/service_manager.py:126-153
for service_dir in self.services_dir.iterdir():
    manifest_path = service_dir / "manifest.json"
    if not manifest_path.exists():
        continue
    service = self._load_manifest(manifest_path)
    self._validate_service(service)
    self.services[service.name] = service
```

```python
# src/foundation/http_server.py:77-80
self.app.router.add_get("/api/services", self._handle_list_services)
self.app.router.add_post("/api/services/{name}/start", self._handle_start_service)
self.app.router.add_post("/api/services/{name}/stop", self._handle_stop_service)
self.app.router.add_get("/api/services/{name}/status", self._handle_service_status)
```

```yaml
# services/recording/docker-compose.yml:24-32
environment:
  - FOUNDATION_WS_URL=${FOUNDATION_WS_URL:-ws://host.docker.internal:9000/feed}
  - PORT=${PORT:-9010}
  - HOST=0.0.0.0
  - STORAGE_PATH=/data/raw_captures
```

## Agnostic Target Pattern

Use a platform-neutral service spec and adapter runtime.

### Suggested manifest (portable)

```json
{
  "name": "service-name",
  "version": "1.0.0",
  "runtime": "container",
  "interfaces": {
    "http": { "port_env": "SERVICE_PORT", "health": "/health", "ready": "/ready" },
    "events": { "consumes": [], "emits": [] }
  },
  "dependencies": [],
  "config_schema": "./config/schema.json"
}
```

### Suggested lifecycle API

- `GET /platform/services`
- `POST /platform/services/{name}/start`
- `POST /platform/services/{name}/stop`
- `GET /platform/services/{name}/status`

### Suggested operational baseline

- `GET /health`
- `GET /ready`
- `GET /metrics`
- structured logs with correlation IDs

## Recommended Service Split for Rebuild

- `trade-console-ui` (artifact)
- `explorer-ui` (artifact)
- `explorer-data-service`
- `backtest-service`
- `bankroll-service`
- `monte-carlo-service`
- `live-simulator-service`
- `execution-bridge-service`

## Cleanup Checklist

1. Replace fixed ports with env-driven defaults and service discovery.
2. Replace host-specific paths with mounted volumes/object storage IDs.
3. Standardize health/readiness/metrics across all modules.
4. Version all APIs and event envelopes.
5. Add contract tests between UI and services.
6. Add provider adapters (`feed`, `execution`, `storage`) per environment.

## Migration Notes

- Existing service-manager approach is reusable but should be abstracted from Foundation-specific naming.
- Preserve manifest-first registration; it supports plugin discovery and operational control.
