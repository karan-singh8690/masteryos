.PHONY: help up down build rebuild backend frontend lint test format migrate shell logs clean \
	prod-up prod-down prod-build prod-logs prod-shell prod-restart \
	gen-ssl-pg gen-ssl-nginx gen-jwt-keys \
	backup backup-verify restore health prod-health

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ================================
# Docker Compose (Development)
# ================================
up: ## Start all services (dev)
	docker compose up -d

down: ## Stop all services (dev)
	docker compose down

build: ## Build all images (dev)
	docker compose build

rebuild: ## Rebuild all images without cache (dev)
	docker compose build --no-cache

# ================================
# Docker Compose (Production) — Task 025-deploy
# ================================
prod-up: ## Start all services (production) — requires .env.production
	docker compose --env-file .env.production -f docker-compose.prod.yml up -d

prod-down: ## Stop all services (production)
	docker compose -f docker-compose.prod.yml down

prod-build: ## Build all production images
	docker compose --env-file .env.production -f docker-compose.prod.yml build

prod-logs: ## Tail logs from all production services
	docker compose -f docker-compose.prod.yml logs -f

prod-shell: ## Open a shell in the production backend container
	docker compose -f docker-compose.prod.yml exec backend bash

prod-restart: ## Restart backend + worker (e.g. after a feature-flag change)
	docker compose -f docker-compose.prod.yml restart backend worker

# ================================
# Secrets Generation — Task 025-deploy
# ================================
gen-ssl-pg: ## Generate self-signed SSL certificate for PostgreSQL
	./scripts/generate-postgres-ssl.sh

gen-ssl-nginx: ## Generate self-signed TLS certificate for Nginx (use --letsencrypt for prod)
	./scripts/generate-nginx-ssl.sh --self-signed

gen-ssl-nginx-le: ## Generate Let's Encrypt TLS certificate for Nginx (usage: make gen-ssl-nginx-le DOMAIN=app.example.com)
	./scripts/generate-nginx-ssl.sh --letsencrypt $(DOMAIN)

gen-jwt-keys: ## Generate RS256 JWT keypair (4096-bit RSA)
	@mkdir -p keys
	openssl genrsa -out keys/jwt-private.pem 4096
	openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem
	chmod 600 keys/jwt-private.pem
	@echo "✓ Generated keys/jwt-private.pem and keys/jwt-public.pem"

# ================================
# Backup / Restore / Health — Task 025-deploy
# ================================
backup: ## Run a full backup (Postgres + Redis + config)
	./scripts/backup.sh

backup-verify: ## Verify the most recent backup
	./scripts/backup.sh --verify

restore: ## Restore from a backup file (usage: make restore FILE=path/to/backup.tar.gz.enc)
	./scripts/backup.sh --restore $(FILE)

health: ## Run the smoke-test health check (dev)
	./scripts/health-check.sh

prod-health: ## Run the smoke-test health check against the production URL
	BACKEND_URL=https://app.masteryengine.com FRONTEND_URL=https://app.masteryengine.com ./scripts/health-check.sh

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

clean: ## Remove containers, volumes, and build artifacts (DESTRUCTIVE — asks for confirmation)
	@read -p "This will delete ALL volumes including the database. Type 'CLEAN' to confirm: " CONFIRM; \
	if [ "$$CONFIRM" != "CLEAN" ]; then echo "Cancelled."; exit 1; fi
	docker compose down -v --remove-orphans
	rm -rf backend/.venv backend/.ruff_cache backend/.mypy_cache backend/.pytest_cache
	rm -rf frontend/node_modules frontend/.next
	@echo "Clean complete."
