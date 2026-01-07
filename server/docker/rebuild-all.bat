@echo off
echo Rebuilding ALL Docker containers (Production and Development)...
cd /d "%~dp0"

echo.
echo ========================================
echo Rebuilding PRODUCTION containers...
echo ========================================
call rebuild-prod.bat

echo.
echo ========================================
echo Rebuilding DEVELOPMENT containers...
echo ========================================
call rebuild-dev.bat

echo.
echo All containers rebuilt!
pause

