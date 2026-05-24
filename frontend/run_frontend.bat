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

echo Starting React Vite frontend...
npm run dev

pause