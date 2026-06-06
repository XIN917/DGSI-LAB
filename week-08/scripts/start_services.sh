#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

kill_port() {
    local pid
    pid=$(lsof -ti :$1 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "  Killing stale process on port $1 (pid $pid)..."
        kill "$pid" 2>/dev/null
        sleep 1
    fi
}

echo "Starting supply chain services..."
mkdir -p "$ROOT/logs"

kill_port 8001
kill_port 8002
kill_port 8003

echo "  Starting Provider on port 8001..."
python3 -c "import subprocess; subprocess.Popen(['$ROOT/provider/venv/bin/provider-cli','serve','--port','8001'], stdout=open('$ROOT/logs/provider.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "  Starting Manufacturer on port 8002..."
python3 -c "import subprocess; subprocess.Popen(['$ROOT/manufacturer/venv/bin/manufacturer-cli','serve','--port','8002'], stdout=open('$ROOT/logs/manufacturer.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "  Starting Retailer on port 8003..."
python3 -c "import subprocess; subprocess.Popen(['$ROOT/retailer/venv/bin/retailer-cli','serve','--port','8003'], stdout=open('$ROOT/logs/retailer.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "Services started. Logs: logs/provider.log, logs/manufacturer.log, logs/retailer.log"
echo "To stop: ./scripts/stop_services.sh"
