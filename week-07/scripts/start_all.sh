#!/bin/bash

# Configuration
PROVIDER_PORT=8001
MANUFACTURER_PORT=8002
RETAILER_PORT=8003

# Helper to check if a port is in use
check_port() {
    lsof -i :$1 > /dev/null
    return $?
}

echo "🚀 Starting Supply Chain Servers..."
mkdir -p logs

# Start Provider
if check_port $PROVIDER_PORT; then
    echo "⚠️  Port $PROVIDER_PORT (Provider) is already in use."
else
    echo "📦 Starting Provider on port $PROVIDER_PORT..."
    cd provider && source venv/bin/activate && provider-cli serve --port $PROVIDER_PORT > ../logs/provider.log 2>&1 &
fi

# Start Manufacturer
if check_port $MANUFACTURER_PORT; then
    echo "⚠️  Port $MANUFACTURER_PORT (Manufacturer) is already in use."
else
    echo "🏭 Starting Manufacturer on port $MANUFACTURER_PORT..."
    cd manufacturer && source venv/bin/activate && manufacturer-cli serve --port $MANUFACTURER_PORT > ../logs/manufacturer.log 2>&1 &
fi

# Start Retailer
if check_port $RETAILER_PORT; then
    echo "⚠️  Port $RETAILER_PORT (Retailer) is already in use."
else
    echo "🏪 Starting Retailer on port $RETAILER_PORT..."
    cd retailer && source venv/bin/activate && retailer-cli serve --port $RETAILER_PORT > ../logs/retailer.log 2>&1 &
fi

echo "✅ Servers are starting in the background."
echo "📝 Logs: logs/provider.log, logs/manufacturer.log, logs/retailer.log"
echo "🛑 To stop all servers, run: pkill -f 'cli serve'"
