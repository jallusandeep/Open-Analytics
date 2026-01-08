# Docker Setup for Rubik Analytics

This directory contains Docker configuration files for running Rubik Analytics in a containerized environment.

## Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose 2.0+

## Quick Start

1. **Create a `.env` file** (optional, for custom configuration):
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up -d --build
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f
   ```

4. **Stop all services**:
   ```bash
   docker-compose down
   ```

## Environment Variables

### Backend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/app/data` | Directory for all data files (databases, logs, etc.) |
| `DATABASE_URL` | `sqlite:////app/data/auth/sqlite/auth.db` | SQLite database URL for authentication |
| `DUCKDB_PATH` | `./data/analytics/duckdb` | Path for DuckDB analytics databases |
| `JWT_SECRET_KEY` | `your-secret-key-change-in-production` | **CHANGE IN PRODUCTION** - Secret key for JWT tokens |
| `JWT_SYSTEM_SECRET_KEY` | `your-system-secret-key-change-in-production` | **CHANGE IN PRODUCTION** - System secret key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Access token expiration (8 hours) |
| `IDLE_TIMEOUT_MINUTES` | `30` | Idle session timeout |
| `ENCRYPTION_KEY` | `jT7ACJPNHdp-IwKWVDto-vohgPGxwP_95sjBlgsr9Eg=` | **CHANGE IN PRODUCTION** - Fernet encryption key |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated list of allowed CORS origins |
| `TRUEDATA_DEFAULT_AUTH_URL` | `https://auth.truedata.in/token` | TrueData authentication URL |
| `TRUEDATA_DEFAULT_WEBSOCKET_PORT` | `8086` | TrueData WebSocket port |
| `ADMIN_USERNAME` | (empty) | Admin username for initial setup (optional) |
| `ADMIN_EMAIL` | (empty) | Admin email for initial setup (optional) |
| `ADMIN_PASSWORD` | (empty) | Admin password for initial setup (optional) |

### Frontend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://backend:8000` | Backend API URL (use service name in Docker) |
| `NODE_ENV` | `production` | Node.js environment |

## First-Time Setup

### Creating Admin User

On first startup, you can create an admin user by setting environment variables:

```bash
# In docker-compose.yml or .env file
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=SecurePassword123!
```

Or create manually after startup:
```bash
docker-compose exec backend python scripts/init/init_auth_database.py \
  --username admin \
  --email admin@example.com \
  --password SecurePassword123!
```

## Data Persistence

All data is stored in the `../../data` directory, which is mounted as a volume. This includes:
- Authentication database (`auth/sqlite/auth.db`)
- Analytics databases (`analytics/duckdb/`)
- Corporate announcements (`Company Fundamentals/corporate_announcements.duckdb`)
- Symbols database (`symbols/symbols.duckdb`)
- Logs (`logs/`)
- Connection configurations (`connection/`)

**Important**: The data directory is mounted from the host, so data persists across container restarts.

## Services

### Backend (rubik-backend)
- **Port**: 8000
- **Health Check**: `http://localhost:8000/health`
- **API Docs**: `http://localhost:8000/docs`
- **Base Image**: `python:3.11-slim`

### Frontend (rubik-frontend)
- **Port**: 3000
- **Health Check**: `http://localhost:3000/`
- **Base Image**: `node:20-alpine`

## Networking

Services communicate via the `rubik-network` bridge network:
- Frontend → Backend: `http://backend:8000`
- External → Frontend: `http://localhost:3000`
- External → Backend: `http://localhost:8000`

## Troubleshooting

### Check service status
```bash
docker-compose ps
```

### View backend logs
```bash
docker-compose logs -f backend
```

### View frontend logs
```bash
docker-compose logs -f frontend
```

### Restart a service
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

### Access backend shell
```bash
docker-compose exec backend bash
```

### Access frontend shell
```bash
docker-compose exec frontend sh
```

### Check database initialization
```bash
docker-compose exec backend python scripts/init/init_auth_database.py
```

## Production Considerations

1. **Change default secrets**: Update `JWT_SECRET_KEY`, `JWT_SYSTEM_SECRET_KEY`, and `ENCRYPTION_KEY` in production
2. **Use environment variables**: Store secrets in `.env` file (not committed to git)
3. **Enable HTTPS**: Use a reverse proxy (nginx, traefik) for HTTPS
4. **Resource limits**: Already configured in docker-compose.yml:
   - Backend: 2 CPU / 2GB RAM limit, 0.5 CPU / 512MB reserved
   - Frontend: 1 CPU / 1GB RAM limit, 0.25 CPU / 256MB reserved
   - Adjust based on your infrastructure needs
5. **Log rotation**: Configured with 10MB max size and 3 file rotation
6. **Backup strategy**: Regularly backup the `data/` directory
7. **Monitoring**: Set up monitoring for health checks and resource usage

## Windows Server Compatibility

This Docker setup matches the Windows server configuration:
- Same environment variables
- Same directory structure
- Same initialization scripts
- Same port mappings

The only difference is the base paths (Windows uses `C:/Users/...` while Docker uses `/app/data`).

