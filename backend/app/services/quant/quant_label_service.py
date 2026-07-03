from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_labels_daily_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_labels_daily (
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            close_price DOUBLE,

            future_close_1d DOUBLE,
            future_close_5d DOUBLE,
            future_close_10d DOUBLE,
            future_close_20d DOUBLE,

            future_return_1d DOUBLE,
            future_return_5d DOUBLE,
            future_return_10d DOUBLE,
            future_return_20d DOUBLE,

            future_max_high_10d DOUBLE,
            future_min_low_10d DOUBLE,
            future_max_gain_10d DOUBLE,
            future_max_drawdown_10d DOUBLE,

            future_positive_1d BOOLEAN,
            future_positive_5d BOOLEAN,
            future_positive_10d BOOLEAN,
            future_positive_20d BOOLEAN,

            label_source VARCHAR DEFAULT 'ohlcv_daily',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (instrument_key, trading_date)
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_labels_daily_symbol_date
        ON quant_labels_daily (trading_symbol, trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_labels_daily_date
        ON quant_labels_daily (trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_labels_daily_instrument
        ON quant_labels_daily (instrument_key);
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


def get_quant_labels_status(conn) -> Dict[str, Any]:
    ensure_quant_labels_daily_table(conn)

    row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_labels_daily;
    """).fetchone()

    usable_row = conn.execute("""
        SELECT COUNT(*)
        FROM quant_labels_daily
        WHERE future_return_10d IS NOT NULL;
    """).fetchone()

    return {
        "row_count": int(row[0] or 0) if row else 0,
        "instrument_count": int(row[1] or 0) if row else 0,
        "min_date": str(row[2]) if row and row[2] else None,
        "max_date": str(row[3]) if row and row[3] else None,
        "usable_10d_label_count": int(usable_row[0] or 0) if usable_row else 0
    }


def normalize_label_build_payload(payload: Optional[dict]) -> Dict[str, Any]:
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


def build_quant_labels_daily_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_label_build_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_labels_daily_table(conn)

        source_status = get_ohlcv_daily_status(conn)

        if source_status["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in ohlcv_daily. Run OHLCV daily collection first.",
                "source": source_status,
                "labels": get_quant_labels_status(conn),
                "duration_seconds": 0
            }

        where_parts = [
            "instrument_key IS NOT NULL",
            "TRIM(instrument_key) <> ''",
            "date IS NOT NULL",
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
                    f"DELETE FROM quant_labels_daily WHERE {' AND '.join(delete_where)};",
                    delete_params
                )
            else:
                conn.execute("DELETE FROM quant_labels_daily;")

        conn.execute("BEGIN TRANSACTION")

        conn.execute(f"""
            INSERT INTO quant_labels_daily (
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,

                future_close_1d,
                future_close_5d,
                future_close_10d,
                future_close_20d,

                future_return_1d,
                future_return_5d,
                future_return_10d,
                future_return_20d,

                future_max_high_10d,
                future_min_low_10d,
                future_max_gain_10d,
                future_max_drawdown_10d,

                future_positive_1d,
                future_positive_5d,
                future_positive_10d,
                future_positive_20d,

                label_source,
                created_at,
                updated_at
            )
            WITH base AS (
                SELECT
                    instrument_key,
                    trading_symbol,
                    date AS trading_date,
                    CAST(high AS DOUBLE) AS high_price,
                    CAST(low AS DOUBLE) AS low_price,
                    CAST(close AS DOUBLE) AS close_price
                FROM ohlcv_daily
                WHERE {where_sql}
                ORDER BY instrument_key, date
                {limit_sql}
            ),
            enriched AS (
                SELECT
                    *,
                    LEAD(close_price, 1) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS future_close_1d,

                    LEAD(close_price, 5) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS future_close_5d,

                    LEAD(close_price, 10) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS future_close_10d,

                    LEAD(close_price, 20) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS future_close_20d,

                    MAX(high_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 1 FOLLOWING AND 10 FOLLOWING
                    ) AS future_max_high_10d,

                    MIN(low_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 1 FOLLOWING AND 10 FOLLOWING
                    ) AS future_min_low_10d
                FROM base
            )
            SELECT
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,

                future_close_1d,
                future_close_5d,
                future_close_10d,
                future_close_20d,

                CASE
                    WHEN close_price IS NULL OR close_price = 0 OR future_close_1d IS NULL THEN NULL
                    ELSE (future_close_1d - close_price) / close_price
                END AS future_return_1d,

                CASE
                    WHEN close_price IS NULL OR close_price = 0 OR future_close_5d IS NULL THEN NULL
                    ELSE (future_close_5d - close_price) / close_price
                END AS future_return_5d,

                CASE
                    WHEN close_price IS NULL OR close_price = 0 OR future_close_10d IS NULL THEN NULL
                    ELSE (future_close_10d - close_price) / close_price
                END AS future_return_10d,

                CASE
                    WHEN close_price IS NULL OR close_price = 0 OR future_close_20d IS NULL THEN NULL
                    ELSE (future_close_20d - close_price) / close_price
                END AS future_return_20d,

                future_max_high_10d,
                future_min_low_10d,

                CASE
                    WHEN close_price IS NULL OR close_price = 0 OR future_max_high_10d IS NULL THEN NULL
                    ELSE (future_max_high_10d - close_price) / close_price
                END AS future_max_gain_10d,

                CASE
                    WHEN close_price IS NULL OR close_price = 0 OR future_min_low_10d IS NULL THEN NULL
                    ELSE (future_min_low_10d - close_price) / close_price
                END AS future_max_drawdown_10d,

                CASE
                    WHEN future_close_1d IS NULL OR close_price IS NULL THEN NULL
                    ELSE future_close_1d > close_price
                END AS future_positive_1d,

                CASE
                    WHEN future_close_5d IS NULL OR close_price IS NULL THEN NULL
                    ELSE future_close_5d > close_price
                END AS future_positive_5d,

                CASE
                    WHEN future_close_10d IS NULL OR close_price IS NULL THEN NULL
                    ELSE future_close_10d > close_price
                END AS future_positive_10d,

                CASE
                    WHEN future_close_20d IS NULL OR close_price IS NULL THEN NULL
                    ELSE future_close_20d > close_price
                END AS future_positive_20d,

                'ohlcv_daily' AS label_source,
                CURRENT_TIMESTAMP AS created_at,
                CURRENT_TIMESTAMP AS updated_at
            FROM enriched;
        """, params)

        conn.execute("COMMIT")

        label_status = get_quant_labels_status(conn)
        duration_seconds = int((datetime.now() - started_at).total_seconds())

        return {
            "status": "success",
            "message": "Quant daily labels built successfully.",
            "source": source_status,
            "labels": label_status,
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
            detail=f"Unable to build quant daily labels: {error}"
        )

    finally:
        conn.close()


def get_quant_labels_summary_service() -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_labels_daily_table(conn)

        latest_rows = conn.execute("""
            SELECT
                instrument_key,
                trading_symbol,
                trading_date,
                close_price,
                future_return_1d,
                future_return_5d,
                future_return_10d,
                future_return_20d,
                future_max_gain_10d,
                future_max_drawdown_10d,
                future_positive_10d
            FROM quant_labels_daily
            WHERE trading_date = (
                SELECT MAX(trading_date)
                FROM quant_labels_daily
                WHERE future_return_10d IS NOT NULL
            )
            ORDER BY trading_symbol
            LIMIT 100;
        """).fetchall()

        return {
            "status": "success",
            "source": get_ohlcv_daily_status(conn),
            "labels": get_quant_labels_status(conn),
            "latest": [
                {
                    "instrument_key": row[0],
                    "trading_symbol": row[1],
                    "trading_date": str(row[2]) if row[2] else None,
                    "close_price": row[3],
                    "future_return_1d": row[4],
                    "future_return_5d": row[5],
                    "future_return_10d": row[6],
                    "future_return_20d": row[7],
                    "future_max_gain_10d": row[8],
                    "future_max_drawdown_10d": row[9],
                    "future_positive_10d": row[10]
                }
                for row in latest_rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant labels summary: {error}"
        )

    finally:
        conn.close()
