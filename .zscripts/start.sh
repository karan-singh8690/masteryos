#!/bin/sh

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR"

# Store all child process PIDs
pids=""

# Cleanup function: gracefully shut down all services
cleanup() {
    echo ""
    echo "Shutting down all services..."
    
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            service_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            echo "   Stopping process $pid ($service_name)..."
            kill -TERM "$pid" 2>/dev/null
        fi
    done
    
    sleep 1
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            timeout=4
            while [ $timeout -gt 0 ] && kill -0 "$pid" 2>/dev/null; do
                sleep 1
                timeout=$((timeout - 1))
            done
            if kill -0 "$pid" 2>/dev/null; then
                echo "   Force killing process $pid..."
                kill -KILL "$pid" 2>/dev/null
            fi
        fi
    done
    
    echo "All services stopped"
    exit 0
}

echo "Starting all services..."
echo ""

# Switch to build directory
cd "$BUILD_DIR" || exit 1

ls -lah

DEFAULT_PACKAGED_DB_PATH="/app/db/custom.db"
DEFAULT_PACKAGED_DATABASE_URL="file:$DEFAULT_PACKAGED_DB_PATH"

# Start Next.js server
if [ -f "./next-service-dist/server.js" ]; then
    echo "Starting Next.js server..."
    cd next-service-dist/ || exit 1
    
    export NODE_ENV=production
    export PORT="${PORT:-3000}"
    export HOSTNAME="${HOSTNAME:-0.0.0.0}"
    export DATABASE_URL="${DATABASE_URL:-$DEFAULT_PACKAGED_DATABASE_URL}"

    if [ "$DATABASE_URL" = "$DEFAULT_PACKAGED_DATABASE_URL" ]; then
        if [ ! -f "$DEFAULT_PACKAGED_DB_PATH" ]; then
            echo "ERROR: Packaged database file not found at $DEFAULT_PACKAGED_DB_PATH"
            echo "   Cannot start with empty database, aborting"
            exit 1
        fi
        echo "Using packaged database: $DEFAULT_PACKAGED_DB_PATH"
    else
        echo "Using external database: $DATABASE_URL"
    fi
    
    # Start Next.js in background
    bun server.js &
    NEXT_PID=$!
    pids="$NEXT_PID"
    
    # Wait and check if process started successfully
    sleep 1
    if ! kill -0 "$NEXT_PID" 2>/dev/null; then
        echo "ERROR: Next.js server failed to start"
        exit 1
    else
        echo "Next.js server started (PID: $NEXT_PID, Port: $PORT)"
    fi
    
    cd ../
else
    echo "WARNING: Next.js server file not found: ./next-service-dist/server.js"
fi

# Start mini-services
if [ -f "./mini-services-start.sh" ]; then
    echo "Starting mini-services..."
    sh ./mini-services-start.sh &
    MINI_PID=$!
    pids="$pids $MINI_PID"
    
    sleep 1
    if ! kill -0 "$MINI_PID" 2>/dev/null; then
        echo "WARNING: mini-services may have failed to start, continuing..."
    else
        echo "mini-services started (PID: $MINI_PID)"
    fi
elif [ -d "./mini-services-dist" ]; then
    echo "WARNING: mini-services directory exists but start script not found"
else
    echo "mini-services not found, skipping"
fi

# Start Caddy
echo "Starting Caddy..."
echo "Caddy started (foreground)"
echo ""
echo "All services started!"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Caddy runs as the main foreground process
exec caddy run --config Caddyfile --adapter caddyfile
