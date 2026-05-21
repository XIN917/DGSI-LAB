#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/use_pypi.sh"
SCENARIO="${1:-scenarios/holiday-rush.json}"
DAYS="${2:-25}"
CONFIG="${WEEK8_CONFIG:-config/sim.json}"

"$ROOT/scripts/reset_simulation.sh"

mkdir -p "$ROOT/logs"
pids=()
cleanup() {
  for pid in "${pids[@]}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT

if ! lsof -i :8001 >/dev/null 2>&1; then
  (cd "$ROOT/provider" && venv/bin/provider-cli serve --port 8001 > "$ROOT/logs/provider.log" 2>&1) &
  pids+=("$!")
fi
if ! lsof -i :8002 >/dev/null 2>&1; then
  (cd "$ROOT/manufacturer" && venv/bin/manufacturer-cli serve --port 8002 > "$ROOT/logs/manufacturer.log" 2>&1) &
  pids+=("$!")
fi
if ! lsof -i :8003 >/dev/null 2>&1; then
  (cd "$ROOT/retailer" && venv/bin/retailer-cli serve --port 8003 > "$ROOT/logs/retailer.log" 2>&1) &
  pids+=("$!")
fi

for url in \
  "http://127.0.0.1:8001/" \
  "http://127.0.0.1:8002/health" \
  "http://127.0.0.1:8003/api/inventory"
do
  for _ in {1..30}; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
done

"$ROOT/manufacturer/venv/bin/python" "$ROOT/turn_engine.py" "$ROOT/$CONFIG" "$ROOT/$SCENARIO" "$DAYS"
"$ROOT/manufacturer/venv/bin/python" "$ROOT/analysis/generate_charts.py" "$ROOT/$SCENARIO"
