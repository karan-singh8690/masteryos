.PHONY: help up down build rebuild backend frontend lint test format migrate shell logs clean

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ================================
# Docker Compose
# ================================
up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build all images
	docker compose build

rebuild: ## Rebuild all images without cache
	docker compose build --no-cache

# ================================
# Development
# ================================
backend: ## Run backend in development mode
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run frontend in development mode
	cd frontend && npm run dev

# ================================
# Quality
# ================================
lint: ## Lint all code (backend + frontend)
	@echo "Linting backend..."
	cd backend && ruff check . && ruff format --check .
	@echo "Linting frontend..."
	cd frontend && npm run lint

format: ## Format all code
	@echo "Formatting backend..."
	cd backend && ruff format . && ruff check --fix .
	@echo "Formatting frontend..."
	cd frontend && npm run format

test: ## Run all tests
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "Running frontend tests..."
	cd frontend && npm test

typecheck: ## Run type checking
	@echo "Type checking backend..."
	cd backend && mypy app
	@echo "Type checking frontend..."
	cd frontend && npm run typecheck

# ================================
# Database
# ================================
migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create m="migration name")
	cd backend && alembic revision --autogenerate -m "$(m)"

# ================================
# Utilities
# ================================
shell: ## Open a shell in the backend container
	docker compose exec backend bash

logs: ## Tail logs from all services
	docker compose logs -f

clean: ## Remove containers, volumes, and build artifacts
	docker compose down -v --remove-orphans
	rm -rf backend/.venv backend/.ruff_cache backend/.mypy_cache backend/.pytest_cache
	rm -rf frontend/node_modules frontend/.next
	@echo "Clean complete."
