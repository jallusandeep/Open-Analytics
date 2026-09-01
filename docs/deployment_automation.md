# Open Analytics Deployment Automation

The production deployment is automated through GitHub Actions, GitHub Container Registry (GHCR), Docker Compose, and Watchtower.

## Deployment flow

Pushing to the `production` branch, or manually running the workflow, executes:

```text
.github/workflows/deploy.yaml
```

The workflow:

1. Builds the Open Analytics backend image.
2. Builds the Open Analytics frontend image.
3. Pushes both images to GHCR with the `latest` tag.
4. Leaves deployment to Watchtower on the Open Analytics server.

Watchtower polls GHCR every 60 seconds by default. When it detects a new image digest, it pulls the image, performs a rolling restart of the labeled backend and frontend containers, and removes the replaced image.

## Server requirements

The Open Analytics server must have:

- Docker and the Docker Compose plugin installed.
- `server/docker/docker-compose.yaml` deployed on the server.
- A `.env` file containing the required ports, container names, JWT keys, data volume, image names, and GHCR credentials.
- The Watchtower service running as part of the Docker Compose stack.

For private GHCR packages, configure these values in the server `.env` file:

```text
GHCR_USERNAME=<GitHub username or organization>
GHCR_TOKEN=<token with package read access>
```

Do not commit credentials to the repository.

## Images

The workflow publishes:

```text
ghcr.io/<repository-owner>/openanalytics-backend2:latest
ghcr.io/<repository-owner>/openanalytics-frontend2:latest
```

Set `BACKEND_IMAGE` and `FRONTEND_IMAGE` in the server `.env` file to these image names.

## Prediction refresh

The backend container supports these startup settings:

```text
QUANT_REFRESH_ON_STARTUP=true
QUANT_REFRESH_LIMIT=1000
QUANT_REFRESH_INCLUDE_DEEP_LEARNING=true
QUANT_REFRESH_TRAIN_MISSING_MODELS=false
QUANT_REFRESH_REBUILD=false
```

When enabled, the backend queues the quant prediction refresh after the updated container starts.
