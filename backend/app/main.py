from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_database, get_connection
from app.version import APP_VERSION, SCHEMA_VERSION
from app.services.data_collection_scheduler_service import (
    start_data_collection_scheduler,
    stop_data_collection_scheduler
)

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.user_routes import router as user_router
from app.api.v1.admin_routes import router as admin_router
from app.api.v1.connection_routes import router as connection_router
from app.api.v1.data_collection_routes import router as data_collection_router


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=APP_VERSION
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_origin_regex=(
        r"^http://("
        r"localhost|127\.0\.0\.1|0\.0\.0\.0|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r"):\d+$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_database()
    start_data_collection_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_data_collection_scheduler()


app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(connection_router, prefix="/api/v1")
app.include_router(data_collection_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "message": "Open Analytics Backend Running",
        "status": "success",
        "app_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION
    }


@app.get("/health")
def health_check():
    return {
        "app": settings.APP_NAME,
        "status": "healthy",
        "database": "duckdb",
        "app_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION
    }


@app.get("/version")
def get_version():
    return {
        "app": settings.APP_NAME,
        "app_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION
    }


@app.get("/db-version")
def get_db_version():
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT key, value, updated_at
            FROM app_metadata
            ORDER BY key;
        """).fetchall()

        return {
            "metadata": [
                {
                    "key": row[0],
                    "value": row[1],
                    "updated_at": str(row[2])
                }
                for row in rows
            ]
        }

    finally:
        conn.close()
