#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Atalaya OSINT Platform — Native Linux Installer
# Tested on: Ubuntu 22.04 LTS, Debian 12 Bookworm
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

ATALAYA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_MIN="3.11"
NODE_MIN="18"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

banner() {
  echo -e "${BLUE}"
  echo "  ╔═══════════════════════════════════════╗"
  echo "  ║     Atalaya OSINT Platform             ║"
  echo "  ║     Open Intelligence Platform         ║"
  echo "  ╚═══════════════════════════════════════╝"
  echo -e "${NC}"
}

check_root() {
  if [[ $EUID -eq 0 ]]; then
    warn "Running as root. Consider using a dedicated user."
  fi
}

check_os() {
  if [[ ! -f /etc/os-release ]]; then
    error "Cannot detect OS. This installer supports Ubuntu/Debian only."
  fi
  . /etc/os-release
  case "$ID" in
    ubuntu|debian) success "OS: $PRETTY_NAME" ;;
    *) warn "Untested OS: $PRETTY_NAME. Proceeding anyway." ;;
  esac
}

check_python() {
  if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Install python3.11+ first: sudo apt install python3.11"
  fi
  PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    success "Python $PY_VER"
  else
    error "Python $PYTHON_MIN+ required, found $PY_VER. Install: sudo apt install python3.11"
  fi
}

check_node() {
  if ! command -v node &>/dev/null; then
    error "Node.js not found. Install via: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
  fi
  NODE_VER=$(node --version | tr -d 'v' | cut -d. -f1)
  if [[ "$NODE_VER" -ge "$NODE_MIN" ]]; then
    success "Node.js $(node --version)"
  else
    error "Node.js $NODE_MIN+ required. Update via NodeSource."
  fi
}

check_postgres() {
  if command -v psql &>/dev/null; then
    success "PostgreSQL client found"
  else
    warn "PostgreSQL client not found. Install: sudo apt install postgresql-client"
  fi
}

check_redis() {
  if command -v redis-cli &>/dev/null; then
    success "Redis client found"
  else
    warn "Redis CLI not found (optional for local check)"
  fi
}

install_system_deps() {
  info "Installing system dependencies..."
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    python3-dev \
    libmagic1 \
    libpq-dev \
    gcc \
    curl \
    git \
    2>/dev/null
  success "System dependencies installed"
}

setup_backend() {
  info "Setting up Python virtual environment..."
  cd "$ATALAYA_DIR/backend"
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip --quiet
  pip install -r requirements.txt --quiet
  success "Backend dependencies installed"
}

setup_frontend() {
  info "Installing frontend dependencies..."
  cd "$ATALAYA_DIR/frontend"
  npm ci --silent
  npm run build --silent
  success "Frontend built"
}

setup_env() {
  if [[ ! -f "$ATALAYA_DIR/.env" ]]; then
    cp "$ATALAYA_DIR/.env.example" "$ATALAYA_DIR/.env"
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    sed -i "s/CHANGE_ME_generate_with_script/$SECRET_KEY/" "$ATALAYA_DIR/.env"
    success ".env created with generated SECRET_KEY"
  else
    warn ".env already exists, skipping"
  fi
}

setup_storage() {
  info "Creating storage directories..."
  sudo mkdir -p /var/atalaya/evidence /var/atalaya/reports /var/log/atalaya
  sudo chown -R "$USER":"$USER" /var/atalaya /var/log/atalaya
  success "Storage directories created"
}

run_migrations() {
  info "Running database migrations..."
  cd "$ATALAYA_DIR/backend"
  source .venv/bin/activate
  if alembic upgrade head 2>&1; then
    success "Database migrations complete"
  else
    warn "Migrations failed — ensure PostgreSQL is running and DATABASE_URL is set in .env"
  fi
}

seed_db() {
  info "Seeding default admin user..."
  cd "$ATALAYA_DIR/backend"
  source .venv/bin/activate
  if python scripts/seed_data.py 2>&1; then
    success "Database seeded"
  else
    warn "Seeding failed — run 'make seed' after fixing .env"
  fi
}

print_summary() {
  echo ""
  echo -e "${GREEN}══════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  Atalaya installed successfully!             ${NC}"
  echo -e "${GREEN}══════════════════════════════════════════════${NC}"
  echo ""
  echo "  Next steps:"
  echo "  1. Edit .env and configure DATABASE_URL, REDIS_URL"
  echo "  2. Start databases: make db-up"
  echo "  3. Start everything: make dev"
  echo ""
  echo "  Default credentials:"
  echo "    Username: admin"
  echo "    Password: admin (change immediately!)"
  echo ""
  echo "  Frontend:  http://localhost:3000"
  echo "  Backend:   http://localhost:8000"
  echo "  API docs:  http://localhost:8000/docs"
  echo ""
  echo "  Run 'make help' to see all available commands."
}

banner
check_root
check_os
check_python
check_node
install_system_deps
setup_env
setup_backend
setup_frontend
setup_storage
run_migrations
seed_db
print_summary
