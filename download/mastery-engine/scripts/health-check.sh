#!/usr/bin/env bash
# Health check script — verifies that all services are running and healthy.
# Usage: ./scripts/health-check.sh

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

echo "Checking services..."
echo "=================="

# Backend health
echo -n "Backend (health)...  "
if RESPONSE=$(curl -sf "$BACKEND_URL/api/v1/health" 2>/dev/null); then
    STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
    echo "✓ $STATUS"
else
    echo "✗ FAILED"
fi

# Backend readiness
echo -n "Backend (ready)...    "
if RESPONSE=$(curl -sf "$BACKEND_URL/api/v1/health/ready" 2>/dev/null); then
    STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
    echo "✓ $STATUS"
else
    echo "✗ FAILED"
fi

# Frontend
echo -n "Frontend...            "
if curl -sf -o /dev/null "$FRONTEND_URL" 2>/dev/null; then
    echo "✓ Running"
else
    echo "✗ FAILED"
fi

echo "=================="
echo "Done."
