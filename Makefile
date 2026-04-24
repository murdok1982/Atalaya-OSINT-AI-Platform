.PHONY: help install dev stop clean db-up db-down migrate seed logs test lint format check

SHELL := /bin/bash
PYTHON := python3
PIP := pip3
NPM := npm

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────

install: ## Full installation (native Linux)
	@bash scripts/install.sh

check: ## Verify system requirements
	@bash scripts/check_system.sh

# ── Development ──────────────────────────────────────────────

dev: ## Start all services for development
	@echo "Starting Atalaya in development mode..."
	@make db-up
	@sleep 2
	@make migrate
	@echo "Starting backend..."
	@cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting ARQ worker..."
	@cd backend && source .venv/bin/activate && python -m app.jobs.worker &
	@echo "Starting frontend..."
	@cd frontend && npm run dev &
	@echo ""
	@echo "✅ Atalaya is running:"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API docs: http://localhost:8000/docs"

stop: ## Stop all background services
	@pkill -f "uvicorn app.main" || true
	@pkill -f "app.jobs.worker" || true
	@pkill -f "next dev" || true
	@echo "All services stopped."

# ── Database ─────────────────────────────────────────────────

db-up: ## Start PostgreSQL and Redis via Docker
	@docker compose up -d postgres redis qdrant
	@echo "Waiting for databases to be ready..."
	@sleep 3

db-down: ## Stop database containers
	@docker compose stop postgres redis qdrant

migrate: ## Run Alembic migrations
	@cd backend && source .venv/bin/activate && alembic upgrade head

migration: ## Create a new migration (usage: make migration MSG="description")
	@cd backend && source .venv/bin/activate && alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed database with default admin user
	@cd backend && source .venv/bin/activate && python scripts/seed_data.py

reset-db: ## Drop and recreate the database (DESTRUCTIVE)
	@echo "WARNING: This will delete all data. Press Ctrl+C to abort."
	@sleep 5
	@docker compose exec postgres psql -U atalaya -c "DROP DATABASE IF EXISTS atalaya_db;"
	@docker compose exec postgres psql -U atalaya -c "CREATE DATABASE atalaya_db;"
	@make migrate
	@make seed

# ── Docker ───────────────────────────────────────────────────

docker-up: ## Start all services with Docker Compose
	@docker compose up -d
	@echo "Waiting for services..."
	@sleep 5
	@docker compose exec backend alembic upgrade head
	@echo ""
	@echo "✅ Atalaya is running (Docker):"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"

docker-down: ## Stop all Docker Compose services
	@docker compose down

docker-logs: ## Stream logs from all containers
	@docker compose logs -f

docker-build: ## Rebuild all Docker images
	@docker compose build --no-cache

# ── Quality ──────────────────────────────────────────────────

lint: ## Run linters (backend + frontend)
	@cd backend && source .venv/bin/activate && ruff check app/ && echo "Backend lint: OK"
	@cd frontend && npm run lint && echo "Frontend lint: OK"

format: ## Auto-format code
	@cd backend && source .venv/bin/activate && black app/ && ruff check --fix app/
	@cd frontend && npm run format

test: ## Run backend test suite
	@cd backend && source .venv/bin/activate && pytest tests/ -v

typecheck: ## Type-check backend (mypy) and frontend (tsc)
	@cd backend && source .venv/bin/activate && mypy app/
	@cd frontend && npx tsc --noEmit

# ── Keys ─────────────────────────────────────────────────────

generate-keys: ## Generate new SECRET_KEY for .env
	@cd backend && source .venv/bin/activate && python scripts/generate_keys.py

# ── Logs ─────────────────────────────────────────────────────

logs: ## Tail backend logs
	@tail -f /var/log/atalaya/backend.log 2>/dev/null || journalctl -u atalaya -f

clean: ## Remove build artifacts and caches
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/.next frontend/out
	@echo "Clean complete."
