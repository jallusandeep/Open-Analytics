@echo off
title Open Analytics Backend
echo ========================================
echo Starting Open Analytics Backend
echo ========================================

cd /d "%~dp0"

if not exist venv (
    echo Creating backend virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing backend requirements...
pip install -r requirements.txt

:restart_backend
echo Stopping any existing backend server on port 8000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -and $_ -ne $PID } | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

echo Starting FastAPI backend...
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

echo.
echo Backend server stopped. Restarting in 2 seconds...
timeout /t 2 /nobreak > nul
goto restart_backend

pause
