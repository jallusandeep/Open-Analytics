#!/bin/sh
set -e

cd /app/backend

echo "==========================================="
echo "  STARTING OPEN ANALYTICS BACKEND"
echo "==========================================="
# Remove stale PID file to prevent "Backend Already Running" errors in Docker
rm -f /app/data/backend.pid

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --no-access-log
