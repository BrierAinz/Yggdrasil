#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# YggdrasilForge — Start script
# Usage: ./start.sh [backend|frontend|all]
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Colors
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' NC='\033[0m'

log()  { echo -e "${G}[Forge]${NC} $1"; }
warn() { echo -e "${Y}[Forge]${NC} $1"; }
err()  { echo -e "${R}[Forge]${NC} $1"; }

MODE="${1:-all}"

install_backend() {
    if [ ! -d "$BACKEND_DIR/.venv" ]; then
        log "Creating Python venv..."
        python3 -m venv "$BACKEND_DIR/.venv"
    fi
    log "Installing backend dependencies..."
    "$BACKEND_DIR/.venv/bin/pip" install -e "$BACKEND_DIR" -q 2>/dev/null || \
        "$BACKEND_DIR/.venv/bin/pip" install fastapi uvicorn httpx aiosqlite pydantic pydantic-settings python-multipart orjson -q
}

install_frontend() {
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        log "Installing frontend dependencies..."
        cd "$FRONTEND_DIR" && npm install
    fi
}

start_backend() {
    log "Starting backend on :8081..."
    cd "$BACKEND_DIR"
    "$BACKEND_DIR/.venv/bin/python" -m uvicorn backend.main:app --host 0.0.0.0 --port 8081 --reload &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$BACKEND_DIR/.backend.pid"
    log "Backend PID: $BACKEND_PID"
}

start_frontend() {
    log "Starting frontend on :5174..."
    cd "$FRONTEND_DIR"
    npx vite --port 5174 --host &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$BACKEND_DIR/.frontend.pid"
    log "Frontend PID: $FRONTEND_PID"
}

stop_all() {
    for pidfile in .backend.pid .frontend.pid; do
        if [ -f "$pidfile" ]; then
            PID=$(cat "$pidfile")
            if kill -0 "$PID" 2>/dev/null; then
                warn "Stopping PID $PID..."
                kill "$PID" 2>/dev/null || true
            fi
            rm "$pidfile"
        fi
    done
    log "All processes stopped."
}

case "$MODE" in
    backend)
        install_backend
        start_backend
        ;;
    frontend)
        install_frontend
        start_frontend
        ;;
    all)
        install_backend
        install_frontend
        start_backend
        start_frontend
        ;;
    stop)
        stop_all
        ;;
    *)
        echo "Usage: $0 [backend|frontend|all|stop]"
        echo ""
        echo "  backend   — Start FastAPI backend only (:8081)"
        echo "  frontend  — Start Vite React frontend only (:5174)"
        echo "  all       — Start both backend and frontend"
        echo "  stop      — Stop all running processes"
        exit 1
        ;;
esac

echo ""
log "⚒️  YggdrasilForge is running!"
echo ""
