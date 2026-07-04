#!/usr/bin/env bash
# Setup script — installs dependencies and prepares the development environment.
# Usage: ./scripts/setup.sh

set -euo pipefail

echo "Mastery Engine — Development Setup"
echo "=================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
echo -n "  Python 3.13... "
if command -v python3.13 &>/dev/null; then
    echo "✓"
else
    echo "✗ (install Python 3.13+)"
    exit 1
fi

echo -n "  Node.js 20+... "
if command -v node && [ "$(node -v | cut -d. -f1 | tr -d v)" -ge 20 ]; then
    echo "✓"
else
    echo "✗ (install Node.js 20+)"
    exit 1
fi

echo -n "  Docker...     "
if command -v docker &>/dev/null; then
    echo "✓"
else
    echo "✗ (install Docker)"
    exit 1
fi

echo ""

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "  ✓ .env created"
fi

# Task 025-deploy: generate RS256 JWT keypair if missing (for prod parity).
# Dev can also use HS256, but generating the keypair lets dev test the prod path.
if [ ! -f keys/jwt-private.pem ]; then
    echo ""
    echo "Generating RS256 JWT keypair (dev)..."
    mkdir -p keys
    openssl genrsa -out keys/jwt-private.pem 4096 2>/dev/null
    openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem 2>/dev/null
    chmod 600 keys/jwt-private.pem
    # Point .env at the keys
    if ! grep -q "^JWT_KEYS_DIR=" .env; then
        echo "JWT_KEYS_DIR=keys" >> .env
    fi
    echo "  ✓ keys/jwt-private.pem and keys/jwt-public.pem generated"
fi

# Task 025-deploy: generate self-signed SSL certs for local Docker testing.
if [ ! -f infrastructure/nginx/ssl/fullchain.pem ]; then
    echo ""
    echo "Generating self-signed Nginx TLS cert (dev)..."
    ./scripts/generate-nginx-ssl.sh --self-signed > /dev/null
    echo "  ✓ Nginx self-signed cert generated"
fi
if [ ! -f infrastructure/postgres/ssl/postgres.pem ]; then
    echo ""
    echo "Generating self-signed PostgreSQL SSL cert (dev)..."
    ./scripts/generate-postgres-ssl.sh > /dev/null
    echo "  ✓ Postgres self-signed cert generated"
fi

# Backend setup
echo ""
echo "Setting up backend..."
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" --quiet
pre-commit install
echo "  ✓ Backend dependencies installed"

# Frontend setup
echo ""
echo "Setting up frontend..."
cd ../frontend
npm install --silent
echo "  ✓ Frontend dependencies installed"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start services:     docker compose up -d"
echo "  2. Or run locally:"
echo "     Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "     Frontend: cd frontend && npm run dev"
echo "  3. Check health:       ./scripts/health-check.sh"
echo ""
echo "Production deployment:"
echo "  1. Copy .env.example to .env.production and fill in real secrets"
echo "  2. Generate prod keys: make gen-jwt-keys"
echo "  3. Generate prod SSL:  ./scripts/generate-nginx-ssl.sh --letsencrypt app.masteryengine.com"
echo "  4. Start prod stack:   make prod-up"
echo "  5. Verify:             make prod-health"
