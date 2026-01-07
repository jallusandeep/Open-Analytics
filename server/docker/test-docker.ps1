# PowerShell script to test Docker setup
# This verifies that Docker containers work the same as Windows server

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Rubik Analytics - Docker Test Script" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "[INFO] Checking Docker status..." -ForegroundColor Yellow
if (-not (docker info 2>$null)) {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker is running" -ForegroundColor Green
Write-Host ""

# Navigate to docker directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Stop any existing containers
Write-Host "[INFO] Stopping existing containers..." -ForegroundColor Yellow
docker-compose down 2>$null
Write-Host "[OK] Containers stopped" -ForegroundColor Green
Write-Host ""

# Build and start services
Write-Host "[INFO] Building and starting services..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for services to be healthy
Write-Host "[INFO] Waiting for services to become healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check backend health
Write-Host "[INFO] Checking backend health..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
$backendHealthy = $false

while ($retryCount -lt $maxRetries -and -not $backendHealthy) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            $backendHealthy = $true
            Write-Host "[OK] Backend is healthy" -ForegroundColor Green
            $healthData = $response.Content | ConvertFrom-Json
            Write-Host "  Status: $($healthData.status)" -ForegroundColor Green
            Write-Host "  Database: $($healthData.database)" -ForegroundColor Green
        }
    } catch {
        $retryCount++
        Write-Host "  Attempt $retryCount/$maxRetries..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $backendHealthy) {
    Write-Host "[ERROR] Backend did not become healthy within timeout" -ForegroundColor Red
    Write-Host "[INFO] Checking backend logs..." -ForegroundColor Yellow
    docker-compose logs --tail=50 backend
    exit 1
}

# Check frontend
Write-Host "[INFO] Checking frontend..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
$frontendHealthy = $false

while ($retryCount -lt $maxRetries -and -not $frontendHealthy) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            $frontendHealthy = $true
            Write-Host "[OK] Frontend is responding" -ForegroundColor Green
        }
    } catch {
        $retryCount++
        Write-Host "  Attempt $retryCount/$maxRetries..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $frontendHealthy) {
    Write-Host "[WARNING] Frontend did not respond within timeout" -ForegroundColor Yellow
    Write-Host "[INFO] Checking frontend logs..." -ForegroundColor Yellow
    docker-compose logs --tail=50 frontend
} else {
    Write-Host "[OK] Frontend is healthy" -ForegroundColor Green
}

# Test API endpoint (announcements attachment error handling)
Write-Host ""
Write-Host "[INFO] Testing attachment error handling (404 vs 500)..." -ForegroundColor Yellow
try {
    # Test with a non-existent attachment ID (should return 404, not 500)
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/announcements/999999999/attachment" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    Write-Host "[WARNING] Unexpected success response for non-existent attachment" -ForegroundColor Yellow
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "[OK] Attachment error handling works correctly (404 for missing file)" -ForegroundColor Green
    } elseif ($statusCode -eq 500) {
        Write-Host "[ERROR] Attachment error handling not working (still returns 500)" -ForegroundColor Red
    } else {
        Write-Host "[INFO] Received status code: $statusCode" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "To view logs:  docker-compose logs -f" -ForegroundColor White
Write-Host "To stop:       docker-compose down" -ForegroundColor White
Write-Host ""

