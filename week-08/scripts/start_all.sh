#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

PROVIDER_PORT=8001
MANUFACTURER_PORT=8002
RETAILER_PORT=8003

kill_port() {
    local pid
    pid=$(lsof -ti :$1 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "  Killing stale process on port $1 (pid $pid)..."
        kill "$pid" 2>/dev/null
        sleep 1
    fi
}

echo "Starting Supply Chain Servers..."
mkdir -p "$ROOT/logs"

kill_port $PROVIDER_PORT
kill_port $MANUFACTURER_PORT
kill_port $RETAILER_PORT

echo "  Starting Provider on port $PROVIDER_PORT..."
python3 -c "import subprocess,os; subprocess.Popen(['$ROOT/provider/venv/bin/provider-cli','serve','--port','$PROVIDER_PORT'], stdout=open('$ROOT/logs/provider.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "  Starting Manufacturer on port $MANUFACTURER_PORT..."
python3 -c "import subprocess,os; subprocess.Popen(['$ROOT/manufacturer/venv/bin/manufacturer-cli','serve','--port','$MANUFACTURER_PORT'], stdout=open('$ROOT/logs/manufacturer.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "  Starting Retailer on port $RETAILER_PORT..."
python3 -c "import subprocess,os; subprocess.Popen(['$ROOT/retailer/venv/bin/retailer-cli','serve','--port','$RETAILER_PORT'], stdout=open('$ROOT/logs/retailer.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "Servers starting. Logs: logs/provider.log, logs/manufacturer.log, logs/retailer.log"
echo "To stop: pkill -f 'cli serve'"
