@echo off
title Open Analytics Frontend
echo ========================================
echo Starting Open Analytics Frontend
echo ========================================

cd /d "%~dp0"

if not exist node_modules (
    echo Installing frontend packages...
    npm install
)

:restart_frontend
echo Starting React Vite frontend...
npm run dev

echo.
echo Frontend server stopped. Restarting in 2 seconds...
timeout /t 2 /nobreak > nul
goto restart_frontend

pause
