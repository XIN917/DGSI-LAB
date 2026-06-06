#!/bin/bash

kill_port() {
    local pid
    pid=$(lsof -ti :$1 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "  Killing port $1 (pid $pid)..."
        kill "$pid" 2>/dev/null
    else
        echo "  Port $1 already free."
    fi
}

echo "Stopping supply chain services..."
kill_port 8001
kill_port 8002
kill_port 8003
echo "Done."
