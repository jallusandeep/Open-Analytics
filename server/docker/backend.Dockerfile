FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    dos2unix \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone early to avoid rebuilds
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy and install Python dependencies first for better layer caching
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install \
    --no-cache-dir \
    --default-timeout=120 \
    --retries=5 \
    -r requirements.txt

COPY backend/ ./backend/

# Create data directory structure
# RUN mkdir -p /app/data/auth/sqlite \
#     && mkdir -p /app/data/auth/postgres/migrations \
#     && mkdir -p /app/data/analytics/duckdb \
#     && mkdir -p /app/data/analytics/postgres/analytics_schema \
#     && mkdir -p /app/data/Company\ Fundamentals \
#     && mkdir -p /app/data/symbols \
#     && mkdir -p /app/data/connection/truedata \
#     && mkdir -p /app/data/logs/app \
#     && mkdir -p /app/data/logs/db_logs \
#     && mkdir -p /app/data/logs/jobs \
#     && mkdir -p /app/data/temp \
#     && mkdir -p /app/data/backups \
#     && chmod -R 755 /app/data

# Fix line endings for Python files (skip if dos2unix fails on binary files)
RUN find ./backend -type f -name "*.py" -exec dos2unix {} + || true

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxshmfence1 \
    libxss1 \
    libxext6 \
    libxfixes3 \
    libglib2.0-0 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN which chromium && chromium --version
RUN which chromedriver && chromedriver --version

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy entrypoint script
COPY server/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && dos2unix /app/entrypoint.sh || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

WORKDIR /app/backend
CMD ["/app/entrypoint.sh"]