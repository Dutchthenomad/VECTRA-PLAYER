#!/usr/bin/env bash
#
# Reliable local control script for the scalping explorer artifact.
#
# Usage:
#   ./scripts/scalping_explorer_ctl.sh start
#   ./scripts/scalping_explorer_ctl.sh status
#   ./scripts/scalping_explorer_ctl.sh smoke
#   ./scripts/scalping_explorer_ctl.sh open
#   ./scripts/scalping_explorer_ctl.sh stop
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/src/artifacts"
RUN_DIR="$ROOT_DIR/.run"
PID_FILE="$RUN_DIR/scalping-explorer.pid"
PORT_FILE="$RUN_DIR/scalping-explorer.port"
LOG_FILE="$RUN_DIR/scalping-explorer.log"

HOST="${SCALPING_EXPLORER_HOST:-127.0.0.1}"
DEFAULT_PORT="${SCALPING_EXPLORER_PORT:-47911}"
URL_PATH="/tools/scalping-explorer/index.html"

mkdir -p "$RUN_DIR"

url_from_port() {
  local port="$1"
  echo "http://$HOST:$port$URL_PATH"
}

read_port() {
  if [[ -f "$PORT_FILE" ]]; then
    cat "$PORT_FILE"
  else
    echo "$DEFAULT_PORT"
  fi
}

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    cat "$PID_FILE"
  else
    echo ""
  fi
}

is_running() {
  local pid
  pid="$(read_pid)"
  if [[ -z "$pid" ]]; then
    return 1
  fi
  kill -0 "$pid" >/dev/null 2>&1
}

port_in_use() {
  local port="$1"
  lsof -i "TCP:$port" -sTCP:LISTEN >/dev/null 2>&1
}

find_open_port() {
  local port="$DEFAULT_PORT"
  while port_in_use "$port"; do
    port=$((port + 1))
  done
  echo "$port"
}

wait_until_healthy() {
  local url="$1"
  local max_wait=30
  local i
  for i in $(seq 1 "$max_wait"); do
    if curl -fsS -I "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

start_server() {
  if is_running; then
    local running_port
    running_port="$(read_port)"
    echo "Already running: PID $(read_pid)"
    echo "URL: $(url_from_port "$running_port")"
    return 0
  fi

  local port
  port="$(find_open_port)"

  setsid python3 -m http.server "$port" --bind "$HOST" --directory "$ARTIFACT_DIR" >"$LOG_FILE" 2>&1 < /dev/null &
  local pid="$!"

  echo "$pid" > "$PID_FILE"
  echo "$port" > "$PORT_FILE"

  local url
  url="$(url_from_port "$port")"
  if ! wait_until_healthy "$url"; then
    echo "Failed to start scalping explorer server."
    echo "PID: $pid"
    echo "Log tail:"
    tail -n 40 "$LOG_FILE" || true
    exit 1
  fi

  echo "Started scalping explorer server."
  echo "PID: $pid"
  echo "URL: $url"
}

stop_server() {
  if ! is_running; then
    echo "Not running."
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid="$(read_pid)"
  kill "$pid" >/dev/null 2>&1 || true
  sleep 0.5
  kill -9 "$pid" >/dev/null 2>&1 || true

  rm -f "$PID_FILE"
  echo "Stopped scalping explorer server (PID $pid)."
}

status_server() {
  local port
  port="$(read_port)"
  local url
  url="$(url_from_port "$port")"

  if is_running; then
    echo "Status: running"
    echo "PID: $(read_pid)"
    echo "URL: $url"
  else
    echo "Status: stopped"
    echo "Expected URL when started: $url"
  fi
}

smoke_test() {
  local port
  port="$(read_port)"
  local url
  url="$(url_from_port "$port")"

  if ! is_running; then
    echo "Server is not running. Start it first."
    exit 1
  fi

  echo "Smoke test URL: $url"
  curl -fsS -I "$url" | sed -n '1,8p'
  if ! curl -fsS "$url" | rg -q "Scalping Strategy Explorer"; then
    echo "Smoke test failed: expected title not found."
    exit 1
  fi
  echo "Smoke test passed."
}

open_browser() {
  start_server

  local port
  port="$(read_port)"
  local url
  url="$(url_from_port "$port")"

  # Preferred path: open tab in existing Chrome CDP session if available.
  if curl -fsS "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
    if curl -fsS -X PUT "http://127.0.0.1:9222/json/new?$url" >/dev/null 2>&1; then
      echo "Opened in existing Chrome via CDP."
      echo "URL: $url"
      return 0
    fi
  fi

  # Fallback: desktop opener.
  if command -v xdg-open >/dev/null 2>&1; then
    (xdg-open "$url" >/dev/null 2>&1 &)
    echo "Opened via xdg-open."
    echo "URL: $url"
    return 0
  fi

  echo "No browser opener available in PATH."
  echo "Open this URL manually: $url"
}

usage() {
  cat <<EOF
Usage: $0 {start|stop|status|smoke|open}

Commands:
  start   Start artifact server (persistent background process)
  stop    Stop artifact server
  status  Show server status
  smoke   Verify artifact endpoint and title
  open    Start server (if needed) and open artifact in browser
EOF
}

CMD="${1:-status}"
case "$CMD" in
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  status)
    status_server
    ;;
  smoke)
    smoke_test
    ;;
  open)
    open_browser
    ;;
  *)
    usage
    exit 1
    ;;
esac
