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
