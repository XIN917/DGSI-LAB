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

echo "Starting API server and Dashboard..."
mkdir -p "$ROOT/logs"

kill_port 8000
kill_port 8080

echo "  Starting API server on port 8000..."
python3 -c "import subprocess; subprocess.Popen(['$ROOT/venv/bin/python','$ROOT/api_server.py'], stdout=open('$ROOT/logs/api_server.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "  Starting Dashboard on port 8080..."
python3 -c "import subprocess; subprocess.Popen(['$ROOT/venv/bin/python','$ROOT/dashboard.py'], stdout=open('$ROOT/logs/dashboard.log','a'), stderr=subprocess.STDOUT, start_new_session=True)"

echo "Dashboard started. Logs: logs/api_server.log, logs/dashboard.log"
echo "Open http://localhost:8080"
echo "To stop: ./scripts/stop_dashboard.sh"
