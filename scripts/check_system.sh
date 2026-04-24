#!/usr/bin/env bash
# Quick system requirements check
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

ok()   { echo -e "  ${GREEN}✓${NC} $*"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${NC} $*"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}!${NC} $*"; ((WARN++)); }

echo ""
echo "Atalaya System Requirements Check"
echo "──────────────────────────────────"

# Python
if command -v python3 &>/dev/null; then
  if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    ok "Python $(python3 --version 2>&1 | cut -d' ' -f2)"
  else
    fail "Python 3.11+ required (found $(python3 --version 2>&1))"
  fi
else
  fail "Python 3 not found"
fi

# Node.js
if command -v node &>/dev/null; then
  NODE_MAJ=$(node --version | tr -d 'v' | cut -d. -f1)
  [[ "$NODE_MAJ" -ge 18 ]] && ok "Node.js $(node --version)" || fail "Node.js 18+ required (found $(node --version))"
else
  fail "Node.js not found"
fi

# npm
command -v npm &>/dev/null && ok "npm $(npm --version)" || fail "npm not found"

# PostgreSQL
if command -v psql &>/dev/null; then
  ok "PostgreSQL client $(psql --version | cut -d' ' -f3)"
else
  warn "PostgreSQL client not found (only needed for manual DB ops)"
fi

# Redis
if command -v redis-cli &>/dev/null; then
  ok "Redis CLI $(redis-cli --version | cut -d' ' -f2)"
else
  warn "Redis CLI not found (optional)"
fi

# Docker
if command -v docker &>/dev/null; then
  ok "Docker $(docker --version | cut -d' ' -f3 | tr -d ',')"
else
  warn "Docker not found (only needed for docker-compose setup)"
fi

# libmagic
python3 -c "import magic" 2>/dev/null && ok "python-magic (libmagic)" || warn "python-magic not found (install: sudo apt install libmagic1)"

# disk space
AVAIL=$(df -BG . | tail -1 | awk '{print $4}' | tr -d 'G')
[[ "$AVAIL" -ge 5 ]] && ok "Disk space: ${AVAIL}GB available" || warn "Low disk space: ${AVAIL}GB (recommend 5GB+)"

# ports
for PORT in 3000 8000 5432 6379 6333; do
  if ss -tlnp 2>/dev/null | grep -q ":$PORT " || netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
    warn "Port $PORT already in use"
  else
    ok "Port $PORT available"
  fi
done

echo ""
echo "──────────────────────────────────"
echo -e "  Passed: ${GREEN}$PASS${NC}  Failed: ${RED}$FAIL${NC}  Warnings: ${YELLOW}$WARN${NC}"
echo ""
[[ $FAIL -eq 0 ]] && echo -e "  ${GREEN}System is ready. Run 'make install' to proceed.${NC}" || echo -e "  ${RED}Fix the failures above before installing.${NC}"
echo ""
