# Deployment Automation

The production deployment is automated through GitHub Actions and Docker.

## Trigger

Pushing to the `production` branch runs:

```text
.github/workflows/deploy.yaml
```

Without any Rubik server secrets, the workflow still builds and pushes Docker images. Server deployment is opt-in and only runs when the GitHub variable `ENABLE_RUBIK_DEPLOY` is set to `true`.`r`n`r`nThe workflow:

1. Builds the backend Docker image.
2. Builds the frontend Docker image.
3. Pushes both images to GitHub Container Registry.
4. SSHes into the Rubik server.
5. Pulls the latest images with Docker Compose.
6. Restarts backend, frontend, and Watchtower.
7. Waits for backend `/health`.
8. Triggers quant prediction refresh in the background.

## Optional Deploy Toggle`r`n`r`nTo enable SSH deployment to Rubik, add this GitHub Actions variable:`r`n`r`n```text`r`nENABLE_RUBIK_DEPLOY=true`r`n``` `r`n`r`nIf this variable is missing or set to anything else, the Docker build still runs and the deploy job is skipped.`r`n`r`n## Required GitHub Secrets For Deploy

Add these in GitHub repository settings under `Settings -> Secrets and variables -> Actions` only when `ENABLE_RUBIK_DEPLOY=true`:

```text
RUBIK_HOST=192.168.29.103
RUBIK_USER=rubik
RUBIK_PASSWORD=<server password>
RUBIK_DEPLOY_DIR=/opt/open-analytics/server/docker
GHCR_TOKEN=<classic PAT or fine-grained token with package read access>
```

Do not commit the server password or token to the repository.

## Server Requirements

The Rubik server should have:

- Docker installed
- Docker Compose plugin installed
- `server/docker/docker-compose.yaml` deployed under `RUBIK_DEPLOY_DIR`
- A `.env` file in `RUBIK_DEPLOY_DIR` containing the existing Docker Compose values such as ports, container names, JWT keys, data volume, and image names

The workflow overrides `BACKEND_IMAGE` and `FRONTEND_IMAGE` at deploy time, so the server pulls the image produced by the same GitHub push.

## Prediction Refresh

The backend container receives these environment variables from Docker Compose:

```text
QUANT_REFRESH_ON_STARTUP=true
QUANT_REFRESH_LIMIT=1000
QUANT_REFRESH_INCLUDE_DEEP_LEARNING=true
QUANT_REFRESH_TRAIN_MISSING_MODELS=false
QUANT_REFRESH_REBUILD=false
```

When the backend starts, it queues a quant prediction refresh in a background thread. The deploy workflow also calls:

```text
POST /api/v1/quant-research/predictions/refresh
```

This keeps the prediction cache table updated after every deployment without making the browser wait for heavy computation.

