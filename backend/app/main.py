from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_database, get_connection
from app.version import APP_VERSION, SCHEMA_VERSION
from app.services.connection_scheduler_service import (
    start_connection_scheduler,
    stop_connection_scheduler
)
from app.services.data_collection_scheduler_service import (
    start_data_collection_scheduler,
    stop_data_collection_scheduler
)

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.user_routes import router as user_router
from app.api.v1.admin_routes import router as admin_router
from app.api.v1.connection_routes import router as connection_router
from app.api.v1.ai_connection_routes import router as ai_connection_router
from app.api.v1.data_collection_routes import router as data_collection_router
from app.engines.data_quality.data_quality_routes import router as data_quality_router
from app.engines.returns.returns_routes import router as returns_router
from app.engines.risk.risk_routes import router as risk_router
from app.engines.liquidity.liquidity_routes import router as liquidity_router
from app.engines.cross_sectional_ranking.ranking_routes import router as cross_sectional_ranking_router
from app.engines.fundamental.fundamental_routes import router as fundamental_router
from app.engines.valuation.valuation_routes import router as valuation_router
from app.engines.factor.factor_routes import router as factor_router
from app.engines.news_event.news_event_routes import router as news_event_router
from app.engines.institutional_flow.institutional_flow_routes import router as institutional_flow_router
from app.engines.derivatives.derivatives_routes import router as derivatives_router
from app.engines.market_breadth.market_breadth_routes import router as market_breadth_router
from app.engines.market_regime.market_regime_routes import router as market_regime_router
from app.api.v1.reference_data_routes import router as reference_data_router
from app.api.v1.security_reference_routes import router as security_reference_router
from app.api.v1.table_view_routes import router as table_view_router
app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=APP_VERSION
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://openanalytics.co.in"
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
    start_connection_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_connection_scheduler()
    stop_data_collection_scheduler()


app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(connection_router, prefix="/api/v1")
app.include_router(ai_connection_router, prefix="/api/v1")
app.include_router(data_collection_router, prefix="/api/v1")
app.include_router(data_quality_router, prefix="/api/v1")
app.include_router(returns_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(liquidity_router, prefix="/api/v1")
app.include_router(cross_sectional_ranking_router, prefix="/api/v1")
app.include_router(fundamental_router, prefix="/api/v1")
app.include_router(valuation_router, prefix="/api/v1")
app.include_router(factor_router, prefix="/api/v1")
app.include_router(news_event_router, prefix="/api/v1")
app.include_router(institutional_flow_router, prefix="/api/v1")
app.include_router(derivatives_router, prefix="/api/v1")
app.include_router(market_breadth_router, prefix="/api/v1")
app.include_router(market_regime_router, prefix="/api/v1")
app.include_router(reference_data_router, prefix="/api/v1")
app.include_router(security_reference_router, prefix="/api/v1")
app.include_router(table_view_router, prefix="/api/v1")
from app.api.v1.data_export_routes import router as data_export_router
app.include_router(data_export_router, prefix="/api/v1")


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
