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

echo "Stopping API server and Dashboard..."
kill_port 8000
kill_port 8080
echo "Done."
