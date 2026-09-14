FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Explicit copies exclude .env, real databases, and developer environments.
COPY app ./app
COPY tests/container_app.py ./container_app.py
ENV APP_ENV=test DUCKDB_PATH=/tmp/test.duckdb JWT_SECRET_KEY=container-test-secret-not-for-production QUANT_REFRESH_ON_STARTUP=false
CMD ["uvicorn", "container_app:app", "--host", "0.0.0.0", "--port", "8000"]
