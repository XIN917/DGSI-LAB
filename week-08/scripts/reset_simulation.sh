#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/use_pypi.sh"

rm -f "$ROOT/provider/data/provider.db"
rm -f "$ROOT/manufacturer/data/simulation.db"
rm -f "$ROOT/retailer/data/retailer.db"
mkdir -p "$ROOT/logs"

(
  cd "$ROOT/provider"
  venv/bin/provider-cli seed
)

(
  cd "$ROOT/manufacturer"
  venv/bin/manufacturer-cli seed
  venv/bin/python - <<'PY'
import sqlite3

with sqlite3.connect("data/simulation.db") as conn:
    conn.execute("UPDATE simulation_state SET current_day = 0")
    conn.commit()
PY
)

(
  cd "$ROOT/retailer"
  venv/bin/retailer-cli init
)

echo "Simulation databases reset and seeded."
