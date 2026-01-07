@echo off
echo Rebuilding Development Docker containers...
cd /d "%~dp0"

echo Stopping existing containers...
docker-compose -f docker-compose.dev.yml down

echo Rebuilding images with latest code...
docker-compose -f docker-compose.dev.yml build --no-cache

echo Starting containers...
docker-compose -f docker-compose.dev.yml up -d

echo.
echo Development containers rebuilt and started!
echo Check status with: docker-compose -f docker-compose.dev.yml ps
pause

