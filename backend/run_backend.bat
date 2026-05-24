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

echo Starting FastAPI backend...
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause