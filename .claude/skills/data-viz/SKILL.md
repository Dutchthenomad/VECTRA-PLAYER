---
name: data-viz
description: Create dashboards, charts, and queries using Grafana, Metabase, and TimescaleDB on the VPS. Handles port discovery (Hostinger uses dynamic ports), SQL query generation for trading analytics, Grafana dashboard provisioning via API, and Metabase question creation. Use for any data visualization, analytics dashboard, or database query task.
allowed-tools: mcp__rugs-expert__get_docker_status, mcp__rugs-expert__get_system_info, mcp__rugs-expert__get_network_info, mcp__rugs-expert__get_service_logs, mcp__rugs-expert__run_health_checks, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__read_page, mcp__claude-in-chrome__find, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__form_input, mcp__claude-in-chrome__get_page_text, mcp__claude-in-chrome__read_console_messages, mcp__claude-in-chrome__read_network_requests, Bash, Read, Write, Grep, Glob, WebFetch
---

# Data Visualization Skill — Grafana + Metabase + TimescaleDB

## Overview

Create dashboards, charts, and analytics queries using the VPS visualization stack. This skill handles the full workflow from raw SQL to production dashboards.

**Announce:** "Setting up data visualization — discovering VPS service ports first."

## Architecture

```
Local Machine                          VPS (72.62.160.2 / Tailscale: 100.113.138.27)
┌────────────┐                        ┌────────────────────────────┐
│ Claude Code │─── Tailscale VPN ────→│ TimescaleDB :5433          │
│            │                        │ Grafana     :dynamic→3000  │
│ Browser    │─── Chrome ───────────→│ Metabase    :dynamic→3000  │
│            │                        │ Apprise API :dynamic→8000  │
└────────────┘                        └────────────────────────────┘
```

## Step 1: Port Discovery (MANDATORY FIRST STEP)

Hostinger templates assign **dynamic host ports** that change on container restart. Always discover current ports before connecting.

```
mcp__rugs-expert__get_docker_status()
```

Parse the PORTS column to find current mappings:
- `grafana-*`: Look for `0.0.0.0:XXXXX->3000/tcp` — XXXXX is the Grafana host port
- `metabase-*`: Look for `0.0.0.0:XXXXX->3000/tcp` — XXXXX is the Metabase host port
- `apprise-*`: Look for `0.0.0.0:XXXXX->8000/tcp` — XXXXX is the Apprise host port

**Access URLs** (replace PORT with discovered values):
- Grafana: `http://100.113.138.27:PORT` (Tailscale) or `http://72.62.160.2:PORT` (public)
- Metabase: `http://100.113.138.27:PORT`
- TimescaleDB: `postgresql://user:pass@100.113.138.27:5433/rugs_analytics` (fixed port)

## Step 2: Choose Your Approach

### Approach A: Grafana API (Programmatic — preferred for repeatable dashboards)

Grafana has a full HTTP API for dashboard CRUD. Use this when you want version-controlled, reproducible dashboards.

```bash
# Get current Grafana port
GRAFANA_PORT=$(docker inspect grafana-*-grafana-1 --format='{{range $p, $conf := .NetworkSettings.Ports}}{{if eq $p "3000/tcp"}}{{(index $conf 0).HostPort}}{{end}}{{end}}' 2>/dev/null)

# Or from the get_docker_status output, parse the port number

# Create a datasource (TimescaleDB)
curl -X POST http://100.113.138.27:$GRAFANA_PORT/api/datasources \
  -H "Content-Type: application/json" \
  -u admin:PASSWORD \
  -d '{
    "name": "TimescaleDB",
    "type": "postgres",
    "url": "timescaledb:5432",
    "database": "rugs_analytics",
    "user": "n8n_tsdb",
    "secureJsonData": {"password": "PASSWORD"},
    "jsonData": {
      "sslmode": "disable",
      "postgresVersion": 1500,
      "timescaledb": true
    }
  }'

# Create a dashboard
curl -X POST http://100.113.138.27:$GRAFANA_PORT/api/dashboards/db \
  -H "Content-Type: application/json" \
  -u admin:PASSWORD \
  -d @dashboard.json
```

### Approach B: Chrome Browser (Visual — preferred for exploration)

Use the chrome-agent pattern to visually interact with Grafana or Metabase:

```
1. tabs_context_mcp(createIfEmpty: true)
2. tabs_create_mcp()
3. navigate(url: "http://100.113.138.27:GRAFANA_PORT", tabId: X)
4. read_page(tabId: X, filter: "interactive")
5. form_input / computer(left_click) to interact
```

### Approach C: SQL Queries Only (Fastest for ad-hoc analysis)

Connect directly to TimescaleDB via SSH tunnel or psql:

```bash
# Via Tailscale
psql postgresql://n8n_tsdb:PASSWORD@100.113.138.27:5433/rugs_analytics

# Via SSH tunnel
ssh -L 5433:localhost:5433 root@100.113.138.27 -N &
psql postgresql://n8n_tsdb:PASSWORD@localhost:5433/rugs_analytics
```

## TimescaleDB SQL Templates

### Create the metrics schema (if not exists)

```sql
-- Service metrics hypertable
CREATE TABLE IF NOT EXISTS service_metrics (
    time TIMESTAMPTZ NOT NULL,
    service TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION,
    labels JSONB
);
SELECT create_hypertable('service_metrics', 'time', if_not_exists => TRUE);

-- Execution results hypertable
CREATE TABLE IF NOT EXISTS execution_results (
    time TIMESTAMPTZ NOT NULL,
    trade_id TEXT NOT NULL,
    token_address TEXT,
    side TEXT NOT NULL,
    strategy TEXT NOT NULL,
    amount_sol NUMERIC(20,8) NOT NULL,
    pnl_sol NUMERIC(20,8),
    pnl_pct NUMERIC(10,4),
    outcome TEXT,
    confidence NUMERIC(5,4),
    feature_vector JSONB,
    decision_latency_ms INTEGER,
    pipeline_version TEXT
);
SELECT create_hypertable('execution_results', 'time', if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 days');

-- Compression policies
ALTER TABLE service_metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'service,metric_name'
);
SELECT add_compression_policy('service_metrics', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_retention_policy('service_metrics', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE execution_results SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'strategy,side'
);
SELECT add_compression_policy('execution_results', INTERVAL '14 days', if_not_exists => TRUE);
```

### Common Queries

```sql
-- Pipeline latency over time (5-min buckets)
SELECT
    time_bucket('5 minutes', time) AS bucket,
    service,
    avg(value) AS avg_latency_ms,
    max(value) AS max_latency_ms,
    count(*) AS tick_count
FROM service_metrics
WHERE metric_name = 'processing_time_ms'
  AND time > NOW() - INTERVAL '1 hour'
GROUP BY bucket, service
ORDER BY bucket DESC;

-- Daily P&L by strategy
SELECT
    time_bucket('1 day', time) AS day,
    strategy,
    count(*) AS trades,
    count(*) FILTER (WHERE outcome = 'win') AS wins,
    ROUND(count(*) FILTER (WHERE outcome = 'win')::numeric / NULLIF(count(*), 0) * 100, 1) AS win_rate_pct,
    SUM(pnl_sol) AS net_pnl_sol,
    AVG(decision_latency_ms) AS avg_latency_ms
FROM execution_results
WHERE time > NOW() - INTERVAL '30 days'
GROUP BY day, strategy
ORDER BY day DESC;

-- Rolling win rate (last 20 trades)
SELECT
    time, trade_id, outcome, pnl_sol,
    AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END)
        OVER (ORDER BY time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS rolling_win_rate
FROM execution_results
ORDER BY time DESC
LIMIT 100;

-- Service health over last 24h
SELECT
    time_bucket('15 minutes', time) AS bucket,
    service,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value
FROM service_metrics
WHERE metric_name = 'health_check_response_ms'
  AND time > NOW() - INTERVAL '24 hours'
GROUP BY bucket, service
ORDER BY bucket;
```

### Continuous Aggregates (pre-computed views)

```sql
-- Daily P&L continuous aggregate
CREATE MATERIALIZED VIEW daily_pnl
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    strategy,
    count(*) AS total_trades,
    count(*) FILTER (WHERE outcome = 'win') AS wins,
    count(*) FILTER (WHERE outcome = 'loss') AS losses,
    SUM(pnl_sol) AS net_pnl,
    AVG(amount_sol) AS avg_bet_size,
    AVG(decision_latency_ms) AS avg_latency
FROM execution_results
GROUP BY day, strategy
WITH NO DATA;

SELECT add_continuous_aggregate_policy('daily_pnl',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Hourly service metrics aggregate
CREATE MATERIALIZED VIEW hourly_metrics
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS hour,
    service,
    metric_name,
    avg(value) AS avg_val,
    max(value) AS max_val,
    count(*) AS samples
FROM service_metrics
GROUP BY hour, service, metric_name
WITH NO DATA;

SELECT add_continuous_aggregate_policy('hourly_metrics',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

## Grafana Dashboard JSON Templates

### Trading Overview Dashboard

```json
{
  "dashboard": {
    "title": "VECTRA Trading Overview",
    "tags": ["vectra", "trading"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Net P&L (SOL)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [{
          "rawSql": "SELECT day AS time, net_pnl AS \"Net P&L\" FROM daily_pnl WHERE $__timeFilter(day) ORDER BY day",
          "format": "time_series"
        }]
      },
      {
        "title": "Win Rate %",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
        "targets": [{
          "rawSql": "SELECT ROUND(SUM(wins)::numeric / NULLIF(SUM(total_trades), 0) * 100, 1) AS \"Win Rate\" FROM daily_pnl WHERE day > NOW() - INTERVAL '7 days'"
        }],
        "fieldConfig": {
          "defaults": {"min": 0, "max": 100, "unit": "percent",
            "thresholds": {"steps": [
              {"value": 0, "color": "red"},
              {"value": 50, "color": "yellow"},
              {"value": 60, "color": "green"}
            ]}
          }
        }
      },
      {
        "title": "Pipeline Latency",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [{
          "rawSql": "SELECT time_bucket('5 minutes', time) AS time, service, avg(value) AS latency FROM service_metrics WHERE metric_name = 'processing_time_ms' AND $__timeFilter(time) GROUP BY 1, 2 ORDER BY 1",
          "format": "time_series"
        }]
      },
      {
        "title": "Trades Today",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
        "targets": [{
          "rawSql": "SELECT count(*) AS \"Trades\" FROM execution_results WHERE time > date_trunc('day', NOW())"
        }]
      }
    ],
    "time": {"from": "now-7d", "to": "now"},
    "refresh": "30s"
  },
  "overwrite": true
}
```

## Metabase Quick Setup

Metabase is best for ad-hoc exploration with a no-code interface.

1. **Connect to TimescaleDB:** Admin -> Databases -> Add Database
   - Type: PostgreSQL
   - Host: `timescaledb` (Docker network name)
   - Port: `5432` (internal)
   - Database: `rugs_analytics`
   - Username/Password from .env

2. **Create saved questions** for common queries (P&L, win rate, latency)
3. **Build a dashboard** combining multiple questions
4. **Set up alerts** for threshold violations

## Apprise API Integration

Send notifications from dashboards via the Apprise API container:

```bash
# Discover Apprise port
APPRISE_PORT=$(# from get_docker_status output)

# Send a notification
curl -X POST http://100.113.138.27:$APPRISE_PORT/notify \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["tgram://BOT_TOKEN/CHAT_ID"],
    "title": "Trading Alert",
    "body": "Daily P&L: +0.15 SOL | Win Rate: 62%",
    "type": "success"
  }'
```

## Workflow: End-to-End Dashboard Creation

1. **Discover ports:** `mcp__rugs-expert__get_docker_status()`
2. **Verify TimescaleDB schema:** SSH/psql to check tables exist
3. **Create/update schema:** Run SQL templates if tables missing
4. **Add Grafana datasource:** API call or browser
5. **Create dashboard:** Import JSON template or build visually
6. **Set up alerts:** Grafana alerting rules or n8n workflows
7. **Test with sample data:** Insert test records, verify visualization
8. **Configure refresh:** Set appropriate auto-refresh interval

## Troubleshooting

**Can't connect to Grafana/Metabase:**
1. Run `mcp__rugs-expert__get_docker_status()` — is the container "Up"?
2. Check the dynamic port hasn't changed
3. Try both public IP and Tailscale IP
4. Check `mcp__rugs-expert__get_service_logs(service: "grafana-*")` for errors

**TimescaleDB connection refused:**
1. Port 5433 is fixed (not dynamic) — verify `timescaledb` container is Up
2. Check credentials in the rag-stack .env file
3. Test: `psql postgresql://n8n_tsdb:PASS@100.113.138.27:5433/rugs_analytics`

**Dashboard shows "No data":**
1. Check the time range selector (top right in Grafana)
2. Verify the hypertables have data: `SELECT count(*) FROM execution_results;`
3. Check the SQL query independently in psql
4. Verify the datasource connection in Grafana (Settings -> Datasources -> Test)

**Dynamic port changed after restart:**
1. Run `mcp__rugs-expert__get_docker_status()` to find new port
2. Update bookmarks/tunnel aliases
3. Consider setting up Nginx Proxy Manager for fixed ports (container exists but not running)

## VPS Service Quick Reference

| Service | Fixed Port | Dynamic | Container Pattern |
|---------|-----------|---------|-------------------|
| TimescaleDB | 5433 | No | `timescaledb` |
| RabbitMQ | 5672, 15672 | No | `rabbitmq` |
| Qdrant | 6333, 6334 | No | `qdrant` |
| n8n | 5678 | No | `n8n` |
| RAG API | 8000 | No | `rag-api` |
| Rugs MCP | 8001 | No | `rugs-mcp` |
| Open WebUI | 3000 | No | `open-webui` |
| OpenClaw Memory | 8002 (localhost) | No | `openclaw-memory` |
| **Grafana** | — | **Yes** | `grafana-*-grafana-1` |
| **Metabase** | — | **Yes** | `metabase-*-metabase-1` |
| **Uptime Kuma** | — | **Yes** | `uptime-kuma-*` |
| **Dozzle** | — | **Yes** | `dozzle-*` |
| **Apprise API** | — | **Yes** | `apprise-api-*` |
| **Nginx PM** | — | **Created** | `nginx-proxy-manager-*` |
