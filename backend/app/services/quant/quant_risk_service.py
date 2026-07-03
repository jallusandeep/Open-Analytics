from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_risk_tables(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_risk_daily (
            risk_id VARCHAR PRIMARY KEY,
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            close_price DOUBLE,
            volatility_20 DOUBLE,
            range_pct DOUBLE,
            volume_ratio_20 DOUBLE,
            return_1d DOUBLE,
            return_5d DOUBLE,
            return_20d DOUBLE,

            risk_level VARCHAR,
            risk_score DOUBLE,

            suggested_stop_loss_pct DOUBLE,
            suggested_position_size_pct DOUBLE,
            max_capital_at_risk_pct DOUBLE,

            risk_reason TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (instrument_key, trading_date)
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_risk_daily_date
        ON quant_risk_daily (trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_risk_daily_symbol_date
        ON quant_risk_daily (trading_symbol, trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_risk_daily_level
        ON quant_risk_daily (trading_date, risk_level);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def normalize_risk_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    trading_date = str(payload.get("trading_date") or "").strip()
    instrument_key = str(payload.get("instrument_key") or "").strip()
    trading_symbol = str(payload.get("trading_symbol") or "").strip()

    limit = payload.get("limit")

    try:
        limit = int(limit) if limit not in (None, "", "all") else 100000
    except Exception:
        limit = 100000

    limit = max(1, min(limit, 1000000))

    return {
        "trading_date": trading_date or None,
        "instrument_key": instrument_key or None,
        "trading_symbol": trading_symbol or None,
        "limit": limit,
        "rebuild": bool(payload.get("rebuild", True))
    }


def get_quant_risk_source_status(conn) -> Dict[str, Any]:
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


def build_quant_risk_daily_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_risk_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_risk_tables(conn)

        source_status = get_quant_risk_source_status(conn)

        if source_status["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in quant_features_daily. Build quant features first.",
                "source": source_status,
                "risk": {
                    "row_count": 0,
                    "trading_date": config["trading_date"]
                }
            }

        if config["trading_date"]:
            date_row = conn.execute("""
                SELECT TRY_CAST(? AS DATE);
            """, [config["trading_date"]]).fetchone()
        else:
            date_row = conn.execute("""
                SELECT MAX(trading_date)
                FROM quant_features_daily;
            """).fetchone()

        target_date = date_row[0] if date_row else None

        if not target_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to resolve risk trading_date."
            )

        delete_where = ["trading_date = ?"]
        delete_params = [target_date]

        source_where = ["trading_date = ?"]
        source_params = [target_date]

        if config["instrument_key"]:
            delete_where.append("instrument_key = ?")
            delete_params.append(config["instrument_key"])
            source_where.append("instrument_key = ?")
            source_params.append(config["instrument_key"])

        if config["trading_symbol"]:
            delete_where.append("UPPER(trading_symbol) = UPPER(?)")
            delete_params.append(config["trading_symbol"])
            source_where.append("UPPER(trading_symbol) = UPPER(?)")
            source_params.append(config["trading_symbol"])

        if config["rebuild"]:
            conn.execute(
                f"DELETE FROM quant_risk_daily WHERE {' AND '.join(delete_where)};",
                delete_params
            )

        source_where_sql = " AND ".join(source_where)

        conn.execute("BEGIN TRANSACTION")

        conn.execute(f"""
            INSERT INTO quant_risk_daily (
                risk_id,
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,
                volatility_20,
                range_pct,
                volume_ratio_20,
                return_1d,
                return_5d,
                return_20d,

                risk_level,
                risk_score,

                suggested_stop_loss_pct,
                suggested_position_size_pct,
                max_capital_at_risk_pct,

                risk_reason,

                created_at,
                updated_at
            )
            WITH base AS (
                SELECT
                    instrument_key,
                    trading_symbol,
                    trading_date,
                    close_price,
                    volatility_20,
                    range_pct,
                    volume_ratio_20,
                    return_1d,
                    return_5d,
                    return_20d,

                    (
                        CASE
                            WHEN volatility_20 IS NULL THEN 30
                            WHEN volatility_20 >= 0.08 THEN 100
                            WHEN volatility_20 >= 0.06 THEN 80
                            WHEN volatility_20 >= 0.04 THEN 60
                            WHEN volatility_20 >= 0.02 THEN 35
                            ELSE 20
                        END
                        +
                        CASE
                            WHEN range_pct IS NULL THEN 10
                            WHEN range_pct >= 0.08 THEN 40
                            WHEN range_pct >= 0.05 THEN 25
                            WHEN range_pct >= 0.03 THEN 15
                            ELSE 5
                        END
                        +
                        CASE
                            WHEN ABS(COALESCE(return_1d, 0)) >= 0.08 THEN 35
                            WHEN ABS(COALESCE(return_1d, 0)) >= 0.05 THEN 25
                            WHEN ABS(COALESCE(return_1d, 0)) >= 0.03 THEN 15
                            ELSE 5
                        END
                        +
                        CASE
                            WHEN volume_ratio_20 IS NULL THEN 10
                            WHEN volume_ratio_20 >= 5 THEN 30
                            WHEN volume_ratio_20 >= 3 THEN 20
                            WHEN volume_ratio_20 >= 2 THEN 10
                            ELSE 5
                        END
                    ) / 2.05 AS risk_score
                FROM quant_features_daily
                WHERE {source_where_sql}
                  AND close_price IS NOT NULL
                  AND close_price > 0
                ORDER BY trading_symbol
                LIMIT ?
            ),
            classified AS (
                SELECT
                    *,
                    CASE
                        WHEN risk_score >= 75 THEN 'Very High'
                        WHEN risk_score >= 55 THEN 'High'
                        WHEN risk_score >= 35 THEN 'Medium'
                        ELSE 'Low'
                    END AS risk_level,

                    CASE
                        WHEN risk_score >= 75 THEN -0.12
                        WHEN risk_score >= 55 THEN -0.10
                        WHEN risk_score >= 35 THEN -0.08
                        ELSE -0.06
                    END AS suggested_stop_loss_pct,

                    CASE
                        WHEN risk_score >= 75 THEN 0.02
                        WHEN risk_score >= 55 THEN 0.04
                        WHEN risk_score >= 35 THEN 0.06
                        ELSE 0.08
                    END AS suggested_position_size_pct,

                    CASE
                        WHEN risk_score >= 75 THEN 0.0024
                        WHEN risk_score >= 55 THEN 0.0040
                        WHEN risk_score >= 35 THEN 0.0048
                        ELSE 0.0048
                    END AS max_capital_at_risk_pct
                FROM base
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS risk_id,
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,
                volatility_20,
                range_pct,
                volume_ratio_20,
                return_1d,
                return_5d,
                return_20d,

                risk_level,
                risk_score,

                suggested_stop_loss_pct,
                suggested_position_size_pct,
                max_capital_at_risk_pct,

                CONCAT(
                    'Risk level is ', risk_level,
                    '. Volatility 20=', ROUND(COALESCE(volatility_20, 0) * 100, 2),
                    '%, daily range=', ROUND(COALESCE(range_pct, 0) * 100, 2),
                    '%, 1D return=', ROUND(COALESCE(return_1d, 0) * 100, 2),
                    '%, volume ratio=', ROUND(COALESCE(volume_ratio_20, 0), 2),
                    '. Suggested position size is ',
                    ROUND(suggested_position_size_pct * 100, 2),
                    '% of capital with stop loss at ',
                    ROUND(suggested_stop_loss_pct * 100, 2),
                    '%.'
                ) AS risk_reason,

                CURRENT_TIMESTAMP AS created_at,
                CURRENT_TIMESTAMP AS updated_at
            FROM classified;
        """, [*source_params, config["limit"]])

        conn.execute("COMMIT")

        count_row = conn.execute("""
            SELECT COUNT(*)
            FROM quant_risk_daily
            WHERE trading_date = ?;
        """, [target_date]).fetchone()

        level_rows = conn.execute("""
            SELECT risk_level, COUNT(*)
            FROM quant_risk_daily
            WHERE trading_date = ?
            GROUP BY risk_level
            ORDER BY risk_level;
        """, [target_date]).fetchall()

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        return {
            "status": "success",
            "message": "Quant risk daily rows built successfully.",
            "source": source_status,
            "risk": {
                "row_count": int(count_row[0] or 0) if count_row else 0,
                "trading_date": str(target_date),
                "risk_levels": {
                    row[0]: int(row[1] or 0)
                    for row in level_rows
                }
            },
            "config": {
                **config,
                "trading_date": str(target_date)
            },
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
            detail=f"Unable to build quant risk rows: {error}"
        )

    finally:
        conn.close()


def get_quant_risk_daily_service(
    trading_date: Optional[str] = None,
    instrument_key: Optional[str] = None,
    trading_symbol: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_risk_tables(conn)

        try:
            safe_limit = int(limit or 100)
        except Exception:
            safe_limit = 100

        safe_limit = max(1, min(safe_limit, 1000))

        if trading_date:
            date_row = conn.execute("""
                SELECT TRY_CAST(? AS DATE);
            """, [trading_date]).fetchone()
        else:
            date_row = conn.execute("""
                SELECT MAX(trading_date)
                FROM quant_risk_daily;
            """).fetchone()

        target_date = date_row[0] if date_row else None

        if not target_date:
            return {
                "status": "empty",
                "message": "No risk rows found. Build risk first.",
                "trading_date": None,
                "risk": []
            }

        where_parts = ["trading_date = ?"]
        params = [target_date]

        clean_instrument_key = str(instrument_key or "").strip()
        clean_trading_symbol = str(trading_symbol or "").strip()
        clean_risk_level = str(risk_level or "").strip()

        if clean_instrument_key:
            where_parts.append("instrument_key = ?")
            params.append(clean_instrument_key)

        if clean_trading_symbol:
            where_parts.append("UPPER(trading_symbol) = UPPER(?)")
            params.append(clean_trading_symbol)

        if clean_risk_level:
            where_parts.append("UPPER(risk_level) = UPPER(?)")
            params.append(clean_risk_level)

        params.append(safe_limit)

        rows = conn.execute(f"""
            SELECT
                risk_id,
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,
                volatility_20,
                range_pct,
                volume_ratio_20,
                return_1d,
                return_5d,
                return_20d,

                risk_level,
                risk_score,

                suggested_stop_loss_pct,
                suggested_position_size_pct,
                max_capital_at_risk_pct,

                risk_reason
            FROM quant_risk_daily
            WHERE {' AND '.join(where_parts)}
            ORDER BY risk_score DESC, trading_symbol
            LIMIT ?;
        """, params).fetchall()

        return {
            "status": "success",
            "trading_date": str(target_date),
            "risk": [
                {
                    "risk_id": row[0],
                    "instrument_key": row[1],
                    "trading_symbol": row[2],
                    "trading_date": str(row[3]) if row[3] else None,

                    "close_price": row[4],
                    "volatility_20": row[5],
                    "range_pct": row[6],
                    "volume_ratio_20": row[7],
                    "return_1d": row[8],
                    "return_5d": row[9],
                    "return_20d": row[10],

                    "risk_level": row[11],
                    "risk_score": row[12],

                    "suggested_stop_loss_pct": row[13],
                    "suggested_position_size_pct": row[14],
                    "max_capital_at_risk_pct": row[15],

                    "risk_reason": row[16]
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant risk rows: {error}"
        )

    finally:
        conn.close()
