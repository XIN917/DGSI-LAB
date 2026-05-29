#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

echo "Resetting all services..."

echo "  Stopping running services..."
pkill -f 'cli serve' 2>/dev/null

# Wait until all three ports are free
for port in 8001 8002 8003; do
    for i in $(seq 1 10); do
        lsof -i :$port > /dev/null 2>&1 || break
        sleep 1
    done
done

echo "  Deleting databases..."
rm -f "$ROOT/manufacturer/data/manufacturer.db"
rm -f "$ROOT/retailer/data/retailer.db"
rm -f "$ROOT/provider/data/provider.db"

echo "  Clearing agent and service logs..."
rm -f "$ROOT/logs/run.csv"
rm -f "$ROOT/logs/manufacturer.log" "$ROOT/logs/provider.log" "$ROOT/logs/retailer.log"
# Keep logs/{scenario}/ archives — day logs are cleared per-scenario when a new run starts

echo "  Seeding fresh state..."
"$ROOT/provider/venv/bin/provider-cli" seed
"$ROOT/manufacturer/venv/bin/manufacturer-cli" seed
"$ROOT/retailer/venv/bin/retailer-cli" init

echo "  Restarting services..."
"$SCRIPT_DIR/start_all.sh"
sleep 3

echo "Done. All services reset to Day 0 with clean databases."
