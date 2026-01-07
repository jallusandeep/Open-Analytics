@echo off
echo Rebuilding Production Docker containers...
cd /d "%~dp0"

echo Stopping existing containers...
docker-compose down

echo Rebuilding images with latest code...
docker-compose build --no-cache

echo Starting containers...
docker-compose up -d

echo.
echo Production containers rebuilt and started!
echo Check status with: docker-compose ps
pause

