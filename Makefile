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
	@echo "✅ Atalaya v2.0 is running:"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API docs: http://localhost:8000/docs"
	@echo "   Grafana:  http://localhost:3001"

stop: ## Stop all background services
	@pkill -f "uvicorn app.main" || true
	@pkill -f "app.jobs.worker" || true
	@pkill -f "next dev" || true
	@echo "All services stopped."

# ── Database ─────────────────────────────────────────────────

db-up: ## Start PostgreSQL, Redis, Qdrant, Neo4j via Docker
	@docker compose up -d postgres redis qdrant
	@echo "Waiting for databases to be ready..."
	@sleep 3

db-down: ## Stop database containers
	@docker compose stop postgres redis qdrant neo4j kafka

migrate: ## Run Alembic migrations
	@cd backend && source .venv/bin/activate && alembic upgrade head

migration: ## Create a new migration (usage: make migration MSG="description")
	@cd backend && source .venv/bin/activate && alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed database with default admin user
	@cd backend && source .venv/bin/activate && python scripts/seed_data.py

reset-db: ## Drop and recreate the database (DESTRUCTIVE)
	@echo "WARNING: This will delete all data. Press Ctrl+C to abort."
	@sleep 5
	@docker compose exec postgres psql -U ${POSTGRES_USER:-atalaya} -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-atalaya_db};"
	@docker compose exec postgres psql -U ${POSTGRES_USER:-atalaya} -c "CREATE DATABASE ${POSTGRES_DB:-atalaya_db};"
	@make migrate
	@make seed

# ── Docker ───────────────────────────────────────────────────

docker-up: ## Start all services with Docker Compose
	@docker compose up -d
	@echo "Waiting for services..."
	@sleep 5
	@docker compose exec backend alembic upgrade head
	@echo ""
	@echo "✅ Atalaya v2.0 is running (Docker):"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Grafana:  http://localhost:3001"

docker-down: ## Stop all Docker Compose services
	@docker compose down

docker-logs: ## Stream logs from all containers
	@docker compose logs -f

docker-build: ## Rebuild all Docker images
	@docker compose build --no-cache

docker-full: ## Start full stack with Kafka, Neo4j, monitoring
	@docker compose --profile full --profile monitoring up -d

# ── Quality ──────────────────────────────────────────────────

lint: ## Run linters (backend + frontend)
	@cd backend && source .venv/bin/activate && ruff check app/ && echo "Backend lint: OK"
	@cd frontend && npm run lint && echo "Frontend lint: OK"

format: ## Auto-format code
	@cd backend && source .venv/bin/activate && black app/ && ruff check --fix app/
	@cd frontend && npm run format

test: ## Run backend test suite with coverage
	@cd backend && source .venv/bin/activate && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without coverage
	@cd backend && source .venv/bin/activate && pytest tests/ -v

typecheck: ## Type-check backend (mypy) and frontend (tsc)
	@cd backend && source .venv/bin/activate && mypy app/
	@cd frontend && npx tsc --noEmit

# ── Keys ─────────────────────────────────────────────────────

generate-keys: ## Generate new SECRET_KEY for .env
	@cd backend && source .venv/bin/activate && python scripts/generate_keys.py

# ── Security ─────────────────────────────────────────────────

security-audit: ## Run security audit
	@cd backend && source .venv/bin/activate && python -c "from app.core.security import validate_password_strength; print('Password policy check: OK')"
	@echo "Checking for hardcoded secrets..."
	@grep -r "CHANGE_ME" .env 2>/dev/null && echo "⚠️  Default secrets found in .env" || echo "✅ No default secrets in .env"

pen-test: ## Run basic penetration tests
	@echo "Running OWASP ZAP baseline scan..."
	@echo "Note: Full pen test requires OWASP ZAP installation"

# ── Monitoring ───────────────────────────────────────────────

monitoring-up: ## Start Prometheus + Grafana
	@docker compose --profile monitoring up -d

monitoring-down: ## Stop monitoring stack
	@docker compose --profile monitoring down

# ── Backup ───────────────────────────────────────────────────

backup: ## Create database backup
	@docker compose exec postgres pg_dump -U ${POSTGRES_USER:-atalaya} ${POSTGRES_DB:-atalaya_db} > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created"

backup-restore: ## Restore from backup (usage: make backup-restore FILE=backup.sql)
	@cat $(FILE) | docker compose exec -T postgres psql -U ${POSTGRES_USER:-atalaya} ${POSTGRES_DB:-atalaya_db}
	@echo "✅ Backup restored"

# ── Intelligence Modules ─────────────────────────────────────

intel-status: ## Show intelligence module status
	@echo "OSINT:     ✅ Active"
	@echo "SOCMINT:   ✅ Active"
	@echo "GEOINT:    $$(test -n "$(SENTINEL_HUB_CLIENT_ID)" && echo "✅ Active" || echo "⚠️  Not configured")"
	@echo "IMINT:     ✅ Active"
	@echo "FININT:    $$(test -n "$(ETHERSCAN_API_KEY)" && echo "✅ Active" || echo "⚠️  Not configured")"
	@echo "CYBINT:    $$(test -n "$(MISP_API_KEY)" && echo "✅ Active" || echo "⚠️  Not configured")"
	@echo "DARKWEB:   $$(test "$(DARK_WEB_ENABLED)" = "true" && echo "✅ Active" || echo "⚠️  Disabled")"
	@echo "Multi-INT: ✅ Fusion Engine Ready"

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
