@echo off
title Open Analytics Starter

echo ========================================
echo Starting Open Analytics Application
echo ========================================

cd /d "%~dp0\.."

echo Starting backend server...
start "Open Analytics Backend" cmd /k "cd /d backend && run_backend.bat"

timeout /t 3 /nobreak > nul

echo Starting frontend server...
start "Open Analytics Frontend" cmd /k "cd /d frontend && run_frontend.bat"

echo ========================================
echo Open Analytics is starting...
echo Backend  : http://127.0.0.1:8000
echo Frontend : http://localhost:5173
echo API Docs : http://127.0.0.1:8000/docs
echo ========================================

timeout /t 2 /nobreak > nul
exit