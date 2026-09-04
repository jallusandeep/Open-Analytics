#!/bin/bash

set -e

echo "=============================="
echo "Open Analytics auto deploy"
echo "Started at: $(date)"
echo "=============================="

PROJECT_DIR="$HOME/Open-Analytics"
DOCKER_DIR="$PROJECT_DIR/server/docker"

echo ""
echo "1. Going to project folder..."
cd "$PROJECT_DIR"

echo ""
echo "2. Checking current branch..."
CURRENT_BRANCH="$(git branch --show-current)"
echo "Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "production" ]; then
  echo "Switching to production branch..."
  git checkout production
fi

echo ""
echo "3. Checking local changes..."
git status --short

if [ -n "$(git status --short)" ]; then
  echo ""
  echo "ERROR: Local changes found. Deployment stopped."
  echo "Fix local changes first using git status."
  git status
  exit 1
fi

echo ""
echo "4. Pulling latest production branch..."
git pull origin production

echo ""
echo "5. Going to Docker compose folder..."
cd "$DOCKER_DIR"

echo ""
echo "6. Checking current containers..."
docker compose ps

echo ""
echo "7. Pulling latest backend and frontend images..."
docker compose pull backend frontend

echo ""
echo "8. Restarting containers using latest images..."
docker compose up -d --remove-orphans

echo ""
echo "9. Pruning unused old Docker images..."
docker image prune -f

echo ""
echo "10. Pruning Docker build cache..."
docker builder prune -f

echo ""
echo "11. Final container status..."
docker compose ps

echo ""
echo "=============================="
echo "Open Analytics auto deploy completed"
echo "Finished at: $(date)"
echo "=============================="
