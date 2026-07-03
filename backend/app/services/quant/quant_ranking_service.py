from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_rankings_daily_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_rankings_daily (
            ranking_id VARCHAR PRIMARY KEY,
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            close_price DOUBLE,

            return_1d DOUBLE,
            return_5d DOUBLE,
            return_10d DOUBLE,
            return_20d DOUBLE,

            volume_ratio_20 DOUBLE,
            distance_sma_20_pct DOUBLE,
            distance_sma_50_pct DOUBLE,
            volatility_20 DOUBLE,
            momentum_20 DOUBLE,

            momentum_score DOUBLE,
            volume_score DOUBLE,
            trend_score DOUBLE,
            risk_score DOUBLE,
            final_score DOUBLE,

            rank_number BIGINT,
            signal_label VARCHAR,
            signal_reason VARCHAR,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (instrument_key, trading_date)
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_rankings_daily_date_rank
        ON quant_rankings_daily (trading_date, rank_number);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_rankings_daily_symbol_date
        ON quant_rankings_daily (trading_symbol, trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_rankings_daily_score
        ON quant_rankings_daily (trading_date, final_score);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def normalize_ranking_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    trading_date = str(payload.get("trading_date") or "").strip()
    limit = payload.get("limit")

    try:
        limit = int(limit) if limit not in (None, "", "all") else 100
    except Exception:
        limit = 100

    limit = max(1, min(limit, 1000))

    return {
        "trading_date": trading_date or None,
        "limit": limit,
        "rebuild": bool(payload.get("rebuild", True))
    }


def get_quant_ranking_source_status(conn) -> Dict[str, Any]:
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


def build_quant_rankings_daily_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_ranking_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_rankings_daily_table(conn)

        source_status = get_quant_ranking_source_status(conn)

        if source_status["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in quant_features_daily. Build quant features first.",
                "source": source_status,
                "rankings": {
                    "row_count": 0,
                    "trading_date": config["trading_date"]
                }
            }

        date_row = None

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
                detail="Unable to resolve ranking trading_date."
            )

        if config["rebuild"]:
            conn.execute("""
                DELETE FROM quant_rankings_daily
                WHERE trading_date = ?;
            """, [target_date])

        conn.execute("BEGIN TRANSACTION")

        conn.execute("""
            INSERT INTO quant_rankings_daily (
                ranking_id,
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,

                return_1d,
                return_5d,
                return_10d,
                return_20d,

                volume_ratio_20,
                distance_sma_20_pct,
                distance_sma_50_pct,
                volatility_20,
                momentum_20,

                momentum_score,
                volume_score,
                trend_score,
                risk_score,
                final_score,

                rank_number,
                signal_label,
                signal_reason,

                created_at,
                updated_at
            )
            WITH latest_features AS (
                SELECT
                    instrument_key,
                    trading_symbol,
                    trading_date,
                    close_price,
                    return_1d,
                    return_5d,
                    return_10d,
                    return_20d,
                    volume_ratio_20,
                    distance_sma_20_pct,
                    distance_sma_50_pct,
                    volatility_20,
                    momentum_20
                FROM quant_features_daily
                WHERE trading_date = ?
                  AND close_price IS NOT NULL
                  AND close_price > 0
            ),
            scored AS (
                SELECT
                    *,
                    CASE
                        WHEN momentum_20 IS NULL THEN 0
                        WHEN momentum_20 >= 0.25 THEN 100
                        WHEN momentum_20 <= -0.25 THEN 0
                        ELSE (momentum_20 + 0.25) / 0.50 * 100
                    END AS momentum_score,

                    CASE
                        WHEN volume_ratio_20 IS NULL THEN 0
                        WHEN volume_ratio_20 >= 3 THEN 100
                        WHEN volume_ratio_20 <= 0.5 THEN 0
                        ELSE (volume_ratio_20 - 0.5) / 2.5 * 100
                    END AS volume_score,

                    CASE
                        WHEN distance_sma_20_pct IS NULL THEN 0
                        WHEN distance_sma_20_pct >= 0.20 THEN 100
                        WHEN distance_sma_20_pct <= -0.20 THEN 0
                        ELSE (distance_sma_20_pct + 0.20) / 0.40 * 100
                    END AS trend_score,

                    CASE
                        WHEN volatility_20 IS NULL THEN 50
                        WHEN volatility_20 <= 0.01 THEN 100
                        WHEN volatility_20 >= 0.08 THEN 0
                        ELSE (0.08 - volatility_20) / 0.07 * 100
                    END AS risk_score
                FROM latest_features
            ),
            final_scored AS (
                SELECT
                    *,
                    (
                        COALESCE(momentum_score, 0) * 0.35
                        + COALESCE(volume_score, 0) * 0.25
                        + COALESCE(trend_score, 0) * 0.25
                        + COALESCE(risk_score, 0) * 0.15
                    ) AS final_score
                FROM scored
            ),
            ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        ORDER BY final_score DESC, trading_symbol
                    ) AS rank_number
                FROM final_scored
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS ranking_id,
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,

                return_1d,
                return_5d,
                return_10d,
                return_20d,

                volume_ratio_20,
                distance_sma_20_pct,
                distance_sma_50_pct,
                volatility_20,
                momentum_20,

                momentum_score,
                volume_score,
                trend_score,
                risk_score,
                final_score,

                rank_number,

                CASE
                    WHEN final_score >= 80 THEN 'Strong Watch'
                    WHEN final_score >= 65 THEN 'Watch'
                    WHEN final_score >= 50 THEN 'Neutral'
                    WHEN final_score >= 35 THEN 'Weak'
                    ELSE 'Avoid'
                END AS signal_label,

                CONCAT(
                    'Momentum score=', ROUND(momentum_score, 2),
                    ', Volume score=', ROUND(volume_score, 2),
                    ', Trend score=', ROUND(trend_score, 2),
                    ', Risk score=', ROUND(risk_score, 2)
                ) AS signal_reason,

                CURRENT_TIMESTAMP AS created_at,
                CURRENT_TIMESTAMP AS updated_at
            FROM ranked
            WHERE rank_number <= ?;
        """, [target_date, config["limit"]])

        conn.execute("COMMIT")

        count_row = conn.execute("""
            SELECT COUNT(*)
            FROM quant_rankings_daily
            WHERE trading_date = ?;
        """, [target_date]).fetchone()

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        return {
            "status": "success",
            "message": "Quant daily rankings built successfully.",
            "source": source_status,
            "rankings": {
                "row_count": int(count_row[0] or 0) if count_row else 0,
                "trading_date": str(target_date),
                "limit": config["limit"]
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
            detail=f"Unable to build quant rankings: {error}"
        )

    finally:
        conn.close()


def get_quant_rankings_service(
    trading_date: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_rankings_daily_table(conn)

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
                FROM quant_rankings_daily;
            """).fetchone()

        target_date = date_row[0] if date_row else None

        if not target_date:
            return {
                "status": "empty",
                "message": "No rankings found. Build rankings first.",
                "trading_date": None,
                "rankings": []
            }

        rows = conn.execute("""
            SELECT
                rank_number,
                instrument_key,
                trading_symbol,
                trading_date,
                close_price,

                return_1d,
                return_5d,
                return_10d,
                return_20d,

                volume_ratio_20,
                distance_sma_20_pct,
                distance_sma_50_pct,
                volatility_20,
                momentum_20,

                momentum_score,
                volume_score,
                trend_score,
                risk_score,
                final_score,

                signal_label,
                signal_reason
            FROM quant_rankings_daily
            WHERE trading_date = ?
            ORDER BY rank_number
            LIMIT ?;
        """, [target_date, safe_limit]).fetchall()

        return {
            "status": "success",
            "trading_date": str(target_date),
            "rankings": [
                {
                    "rank_number": row[0],
                    "instrument_key": row[1],
                    "trading_symbol": row[2],
                    "trading_date": str(row[3]) if row[3] else None,
                    "close_price": row[4],
                    "return_1d": row[5],
                    "return_5d": row[6],
                    "return_10d": row[7],
                    "return_20d": row[8],
                    "volume_ratio_20": row[9],
                    "distance_sma_20_pct": row[10],
                    "distance_sma_50_pct": row[11],
                    "volatility_20": row[12],
                    "momentum_20": row[13],
                    "momentum_score": row[14],
                    "volume_score": row[15],
                    "trend_score": row[16],
                    "risk_score": row[17],
                    "final_score": row[18],
                    "signal_label": row[19],
                    "signal_reason": row[20]
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant rankings: {error}"
        )

    finally:
        conn.close()
