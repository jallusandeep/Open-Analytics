#!/bin/sh
set -e

cd /app/backend

echo "==========================================="
echo "  INITIALIZING DATABASE..."
echo "==========================================="

# Get admin credentials from environment variables (if provided)
ADMIN_USERNAME=${ADMIN_USERNAME:-}
ADMIN_EMAIL=${ADMIN_EMAIL:-}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-}

# Run database initialization
# Run database initialization
echo "[INFO] initializing database (running init_db.py)..."
python init_db.py

echo "==========================================="
echo "  STARTING OPEN ANALYTICS BACKEND"
echo "==========================================="
# Remove stale PID file to prevent "Backend Already Running" errors in Docker
rm -f /app/data/backend.pid

# Match Windows server behavior: use --reload for development parity
# Note: We don't force --env-file here because Docker Compose injects environment variables directly,
# but we add --reload to see detailed logs and enable hot-reloading as requested ("same as Windows")
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-access-log