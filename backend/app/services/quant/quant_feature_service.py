from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_features_daily_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_features_daily (
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume BIGINT,
            oi BIGINT,

            return_1d DOUBLE,
            return_5d DOUBLE,
            return_10d DOUBLE,
            return_20d DOUBLE,

            range_pct DOUBLE,
            close_position DOUBLE,
            gap_pct DOUBLE,

            volume_avg_20 DOUBLE,
            volume_ratio_20 DOUBLE,

            sma_20 DOUBLE,
            sma_50 DOUBLE,
            distance_sma_20_pct DOUBLE,
            distance_sma_50_pct DOUBLE,

            volatility_20 DOUBLE,
            momentum_20 DOUBLE,

            source_table VARCHAR DEFAULT 'ohlcv_daily',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (instrument_key, trading_date)
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_features_daily_symbol_date
        ON quant_features_daily (trading_symbol, trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_features_daily_date
        ON quant_features_daily (trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_features_daily_instrument
        ON quant_features_daily (instrument_key);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def get_ohlcv_daily_status(conn) -> Dict[str, Any]:
    row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(date) AS min_date,
            MAX(date) AS max_date
        FROM ohlcv_daily;
    """).fetchone()

    return {
        "row_count": int(row[0] or 0) if row else 0,
        "instrument_count": int(row[1] or 0) if row else 0,
        "min_date": str(row[2]) if row and row[2] else None,
        "max_date": str(row[3]) if row and row[3] else None
    }


def get_quant_features_status(conn) -> Dict[str, Any]:
    ensure_quant_features_daily_table(conn)

    row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_features_daily;
    """).fetchone()

    return {
        "row_count": int(row[0] or 0) if row else 0,
        "instrument_count": int(row[1] or 0) if row else 0,
        "min_date": str(row[2]) if row and row[2] else None,
        "max_date": str(row[3]) if row and row[3] else None
    }


def normalize_feature_build_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    instrument_key = str(payload.get("instrument_key") or "").strip()
    trading_symbol = str(payload.get("trading_symbol") or "").strip()
    from_date = str(payload.get("from_date") or "").strip()
    to_date = str(payload.get("to_date") or "").strip()

    limit = payload.get("limit")

    try:
        limit = int(limit) if limit not in (None, "", "all") else None
    except Exception:
        limit = None

    if limit is not None:
        limit = max(1, min(limit, 1000000))

    return {
        "instrument_key": instrument_key or None,
        "trading_symbol": trading_symbol or None,
        "from_date": from_date or None,
        "to_date": to_date or None,
        "limit": limit,
        "rebuild": bool(payload.get("rebuild", True))
    }


def build_quant_features_daily_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_feature_build_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_features_daily_table(conn)

        source_status = get_ohlcv_daily_status(conn)

        if source_status["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in ohlcv_daily. Run OHLCV daily collection first.",
                "source": source_status,
                "features": get_quant_features_status(conn),
                "duration_seconds": 0
            }

        where_parts = [
            "instrument_key IS NOT NULL",
            "TRIM(instrument_key) <> ''",
            "date IS NOT NULL",
            "open IS NOT NULL",
            "high IS NOT NULL",
            "low IS NOT NULL",
            "close IS NOT NULL"
        ]
        params = []

        if config["instrument_key"]:
            where_parts.append("instrument_key = ?")
            params.append(config["instrument_key"])

        if config["trading_symbol"]:
            where_parts.append("UPPER(trading_symbol) = UPPER(?)")
            params.append(config["trading_symbol"])

        if config["from_date"]:
            where_parts.append("date >= TRY_CAST(? AS DATE)")
            params.append(config["from_date"])

        if config["to_date"]:
            where_parts.append("date <= TRY_CAST(? AS DATE)")
            params.append(config["to_date"])

        where_sql = " AND ".join(where_parts)

        limit_sql = ""
        if config["limit"]:
            limit_sql = "LIMIT ?"
            params.append(config["limit"])

        if config["rebuild"]:
            delete_where = []
            delete_params = []

            if config["instrument_key"]:
                delete_where.append("instrument_key = ?")
                delete_params.append(config["instrument_key"])

            if config["trading_symbol"]:
                delete_where.append("UPPER(trading_symbol) = UPPER(?)")
                delete_params.append(config["trading_symbol"])

            if config["from_date"]:
                delete_where.append("trading_date >= TRY_CAST(? AS DATE)")
                delete_params.append(config["from_date"])

            if config["to_date"]:
                delete_where.append("trading_date <= TRY_CAST(? AS DATE)")
                delete_params.append(config["to_date"])

            if delete_where:
                conn.execute(
                    f"DELETE FROM quant_features_daily WHERE {' AND '.join(delete_where)};",
                    delete_params
                )
            else:
                conn.execute("DELETE FROM quant_features_daily;")

        conn.execute("BEGIN TRANSACTION")

        conn.execute(f"""
            INSERT INTO quant_features_daily (
                instrument_key,
                trading_symbol,
                trading_date,

                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                oi,

                return_1d,
                return_5d,
                return_10d,
                return_20d,

                range_pct,
                close_position,
                gap_pct,

                volume_avg_20,
                volume_ratio_20,

                sma_20,
                sma_50,
                distance_sma_20_pct,
                distance_sma_50_pct,

                volatility_20,
                momentum_20,

                source_table,
                created_at,
                updated_at
            )
            WITH base AS (
                SELECT
                    instrument_key,
                    trading_symbol,
                    date AS trading_date,
                    CAST(open AS DOUBLE) AS open_price,
                    CAST(high AS DOUBLE) AS high_price,
                    CAST(low AS DOUBLE) AS low_price,
                    CAST(close AS DOUBLE) AS close_price,
                    CAST(COALESCE(volume, 0) AS BIGINT) AS volume,
                    CAST(COALESCE(oi, 0) AS BIGINT) AS oi
                FROM ohlcv_daily
                WHERE {where_sql}
                ORDER BY instrument_key, date
                {limit_sql}
            ),
            lagged AS (
                SELECT
                    *,
                    LAG(close_price, 1) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS close_1d_ago,

                    LAG(close_price, 5) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS close_5d_ago,

                    LAG(close_price, 10) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS close_10d_ago,

                    LAG(close_price, 20) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS close_20d_ago,

                    LAG(close_price, 1) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS previous_close
                FROM base
            ),
            returns AS (
                SELECT
                    *,
                    CASE
                        WHEN close_1d_ago IS NULL OR close_1d_ago = 0 THEN NULL
                        ELSE (close_price - close_1d_ago) / close_1d_ago
                    END AS return_1d_for_vol
                FROM lagged
            ),
            enriched AS (
                SELECT
                    *,
                    AVG(CAST(volume AS DOUBLE)) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS volume_avg_20,

                    AVG(close_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS sma_20,

                    AVG(close_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
                    ) AS sma_50,

                    STDDEV_SAMP(return_1d_for_vol) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS volatility_20
                FROM returns
            )
            SELECT
                instrument_key,
                trading_symbol,
                trading_date,

                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                oi,

                CASE
                    WHEN close_1d_ago IS NULL OR close_1d_ago = 0 THEN NULL
                    ELSE (close_price - close_1d_ago) / close_1d_ago
                END AS return_1d,

                CASE
                    WHEN close_5d_ago IS NULL OR close_5d_ago = 0 THEN NULL
                    ELSE (close_price - close_5d_ago) / close_5d_ago
                END AS return_5d,

                CASE
                    WHEN close_10d_ago IS NULL OR close_10d_ago = 0 THEN NULL
                    ELSE (close_price - close_10d_ago) / close_10d_ago
                END AS return_10d,

                CASE
                    WHEN close_20d_ago IS NULL OR close_20d_ago = 0 THEN NULL
                    ELSE (close_price - close_20d_ago) / close_20d_ago
                END AS return_20d,

                CASE
                    WHEN close_price IS NULL OR close_price = 0 THEN NULL
                    ELSE (high_price - low_price) / close_price
                END AS range_pct,

                CASE
                    WHEN high_price IS NULL
                      OR low_price IS NULL
                      OR high_price = low_price
                    THEN NULL
                    ELSE (close_price - low_price) / (high_price - low_price)
                END AS close_position,

                CASE
                    WHEN previous_close IS NULL OR previous_close = 0 THEN NULL
                    ELSE (open_price - previous_close) / previous_close
                END AS gap_pct,

                volume_avg_20,

                CASE
                    WHEN volume_avg_20 IS NULL OR volume_avg_20 = 0 THEN NULL
                    ELSE CAST(volume AS DOUBLE) / volume_avg_20
                END AS volume_ratio_20,

                sma_20,
                sma_50,

                CASE
                    WHEN sma_20 IS NULL OR sma_20 = 0 THEN NULL
                    ELSE (close_price - sma_20) / sma_20
                END AS distance_sma_20_pct,

                CASE
                    WHEN sma_50 IS NULL OR sma_50 = 0 THEN NULL
                    ELSE (close_price - sma_50) / sma_50
                END AS distance_sma_50_pct,

                volatility_20,

                CASE
                    WHEN close_20d_ago IS NULL OR close_20d_ago = 0 THEN NULL
                    ELSE (close_price - close_20d_ago) / close_20d_ago
                END AS momentum_20,

                'ohlcv_daily' AS source_table,
                CURRENT_TIMESTAMP AS created_at,
                CURRENT_TIMESTAMP AS updated_at
            FROM enriched;
        """, params)

        conn.execute("COMMIT")

        feature_status = get_quant_features_status(conn)

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        return {
            "status": "success",
            "message": "Quant daily features built successfully.",
            "source": source_status,
            "features": feature_status,
            "config": config,
            "duration_seconds": duration_seconds
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to build quant daily features: {error}"
        )

    finally:
        conn.close()


def get_quant_features_summary_service() -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_features_daily_table(conn)

        latest_rows = conn.execute("""
            SELECT
                instrument_key,
                trading_symbol,
                trading_date,
                close_price,
                return_1d,
                return_5d,
                return_20d,
                volume_ratio_20,
                distance_sma_20_pct,
                distance_sma_50_pct,
                volatility_20,
                momentum_20
            FROM quant_features_daily
            WHERE trading_date = (
                SELECT MAX(trading_date)
                FROM quant_features_daily
            )
            ORDER BY trading_symbol
            LIMIT 100;
        """).fetchall()

        feature_status = get_quant_features_status(conn)
        source_status = get_ohlcv_daily_status(conn)

        return {
            "status": "success",
            "source": source_status,
            "features": feature_status,
            "latest": [
                {
                    "instrument_key": row[0],
                    "trading_symbol": row[1],
                    "trading_date": str(row[2]) if row[2] else None,
                    "close_price": row[3],
                    "return_1d": row[4],
                    "return_5d": row[5],
                    "return_20d": row[6],
                    "volume_ratio_20": row[7],
                    "distance_sma_20_pct": row[8],
                    "distance_sma_50_pct": row[9],
                    "volatility_20": row[10],
                    "momentum_20": row[11]
                }
                for row in latest_rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant features summary: {error}"
        )

    finally:
        conn.close()

