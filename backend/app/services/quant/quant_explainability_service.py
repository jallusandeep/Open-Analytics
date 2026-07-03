from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_trade_plans_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_trade_plans (
            plan_id VARCHAR PRIMARY KEY,
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            rank_number BIGINT,
            final_score DOUBLE,
            signal_label VARCHAR,

            close_price DOUBLE,
            entry_price DOUBLE,
            entry_zone_low DOUBLE,
            entry_zone_high DOUBLE,
            stop_loss_price DOUBLE,
            target_1_price DOUBLE,
            target_2_price DOUBLE,

            risk_pct DOUBLE,
            target_1_pct DOUBLE,
            target_2_pct DOUBLE,
            reward_risk_1 DOUBLE,
            reward_risk_2 DOUBLE,

            suggested_holding_days BIGINT,
            position_note VARCHAR,
            plan_reason TEXT,

            momentum_score DOUBLE,
            volume_score DOUBLE,
            trend_score DOUBLE,
            risk_score DOUBLE,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (instrument_key, trading_date)
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_trade_plans_date_rank
        ON quant_trade_plans (trading_date, rank_number);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_trade_plans_symbol_date
        ON quant_trade_plans (trading_symbol, trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_trade_plans_score
        ON quant_trade_plans (trading_date, final_score);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def normalize_trade_plan_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    trading_date = str(payload.get("trading_date") or "").strip()
    limit = payload.get("limit")

    try:
        limit = int(limit) if limit not in (None, "", "all") else 50
    except Exception:
        limit = 50

    limit = max(1, min(limit, 500))

    return {
        "trading_date": trading_date or None,
        "limit": limit,
        "rebuild": bool(payload.get("rebuild", True))
    }


def get_quant_trade_plan_source_status(conn) -> Dict[str, Any]:
    ranking_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_rankings_daily;
    """).fetchone()

    feature_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_features_daily;
    """).fetchone()

    return {
        "rankings": {
            "row_count": int(ranking_row[0] or 0) if ranking_row else 0,
            "instrument_count": int(ranking_row[1] or 0) if ranking_row else 0,
            "min_date": str(ranking_row[2]) if ranking_row and ranking_row[2] else None,
            "max_date": str(ranking_row[3]) if ranking_row and ranking_row[3] else None
        },
        "features": {
            "row_count": int(feature_row[0] or 0) if feature_row else 0,
            "instrument_count": int(feature_row[1] or 0) if feature_row else 0,
            "min_date": str(feature_row[2]) if feature_row and feature_row[2] else None,
            "max_date": str(feature_row[3]) if feature_row and feature_row[3] else None
        }
    }


def build_quant_trade_plans_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_trade_plan_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_trade_plans_table(conn)

        source_status = get_quant_trade_plan_source_status(conn)

        if source_status["rankings"]["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in quant_rankings_daily. Build rankings first.",
                "source": source_status,
                "plans": {
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
                FROM quant_rankings_daily;
            """).fetchone()

        target_date = date_row[0] if date_row else None

        if not target_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to resolve trade plan trading_date."
            )

        if config["rebuild"]:
            conn.execute("""
                DELETE FROM quant_trade_plans
                WHERE trading_date = ?;
            """, [target_date])

        conn.execute("BEGIN TRANSACTION")

        conn.execute("""
            INSERT INTO quant_trade_plans (
                plan_id,
                instrument_key,
                trading_symbol,
                trading_date,

                rank_number,
                final_score,
                signal_label,

                close_price,
                entry_price,
                entry_zone_low,
                entry_zone_high,
                stop_loss_price,
                target_1_price,
                target_2_price,

                risk_pct,
                target_1_pct,
                target_2_pct,
                reward_risk_1,
                reward_risk_2,

                suggested_holding_days,
                position_note,
                plan_reason,

                momentum_score,
                volume_score,
                trend_score,
                risk_score,

                created_at,
                updated_at
            )
            WITH ranked AS (
                SELECT
                    ranking.instrument_key,
                    ranking.trading_symbol,
                    ranking.trading_date,
                    ranking.rank_number,
                    ranking.final_score,
                    ranking.signal_label,
                    ranking.close_price,
                    ranking.return_20d,
                    ranking.volume_ratio_20,
                    ranking.distance_sma_20_pct,
                    ranking.distance_sma_50_pct,
                    ranking.volatility_20,
                    ranking.momentum_20,
                    ranking.momentum_score,
                    ranking.volume_score,
                    ranking.trend_score,
                    ranking.risk_score
                FROM quant_rankings_daily ranking
                WHERE ranking.trading_date = ?
                  AND ranking.rank_number <= ?
                  AND ranking.signal_label IN ('Strong Watch', 'Watch', 'Neutral')
                  AND ranking.close_price IS NOT NULL
                  AND ranking.close_price > 0
                ORDER BY ranking.rank_number
            ),
            planned AS (
                SELECT
                    *,
                    close_price AS entry_price,

                    close_price * 0.985 AS entry_zone_low,
                    close_price * 1.015 AS entry_zone_high,

                    CASE
                        WHEN COALESCE(volatility_20, 0.03) >= 0.06 THEN close_price * 0.88
                        WHEN COALESCE(volatility_20, 0.03) >= 0.04 THEN close_price * 0.90
                        ELSE close_price * 0.92
                    END AS stop_loss_price,

                    CASE
                        WHEN final_score >= 80 THEN close_price * 1.12
                        WHEN final_score >= 65 THEN close_price * 1.09
                        ELSE close_price * 1.06
                    END AS target_1_price,

                    CASE
                        WHEN final_score >= 80 THEN close_price * 1.22
                        WHEN final_score >= 65 THEN close_price * 1.16
                        ELSE close_price * 1.10
                    END AS target_2_price,

                    CASE
                        WHEN final_score >= 80 THEN 20
                        WHEN final_score >= 65 THEN 15
                        ELSE 10
                    END AS suggested_holding_days
                FROM ranked
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS plan_id,
                instrument_key,
                trading_symbol,
                trading_date,

                rank_number,
                final_score,
                signal_label,

                close_price,
                entry_price,
                entry_zone_low,
                entry_zone_high,
                stop_loss_price,
                target_1_price,
                target_2_price,

                CASE
                    WHEN entry_price IS NULL OR entry_price = 0 THEN NULL
                    ELSE (stop_loss_price - entry_price) / entry_price
                END AS risk_pct,

                CASE
                    WHEN entry_price IS NULL OR entry_price = 0 THEN NULL
                    ELSE (target_1_price - entry_price) / entry_price
                END AS target_1_pct,

                CASE
                    WHEN entry_price IS NULL OR entry_price = 0 THEN NULL
                    ELSE (target_2_price - entry_price) / entry_price
                END AS target_2_pct,

                CASE
                    WHEN entry_price IS NULL
                      OR entry_price = 0
                      OR stop_loss_price IS NULL
                      OR target_1_price IS NULL
                      OR entry_price = stop_loss_price
                    THEN NULL
                    ELSE ABS((target_1_price - entry_price) / (entry_price - stop_loss_price))
                END AS reward_risk_1,

                CASE
                    WHEN entry_price IS NULL
                      OR entry_price = 0
                      OR stop_loss_price IS NULL
                      OR target_2_price IS NULL
                      OR entry_price = stop_loss_price
                    THEN NULL
                    ELSE ABS((target_2_price - entry_price) / (entry_price - stop_loss_price))
                END AS reward_risk_2,

                suggested_holding_days,

                CASE
                    WHEN final_score >= 80 THEN 'High priority watchlist. Use risk control before entry.'
                    WHEN final_score >= 65 THEN 'Good setup watchlist. Confirm market direction before entry.'
                    ELSE 'Neutral setup. Wait for stronger confirmation.'
                END AS position_note,

                CONCAT(
                    'Rank ', rank_number,
                    ' with final score ', ROUND(final_score, 2),
                    '. Momentum=', ROUND(COALESCE(momentum_score, 0), 2),
                    ', Volume=', ROUND(COALESCE(volume_score, 0), 2),
                    ', Trend=', ROUND(COALESCE(trend_score, 0), 2),
                    ', Risk=', ROUND(COALESCE(risk_score, 0), 2),
                    '. Entry zone is around current close with stop below volatility-adjusted support.'
                ) AS plan_reason,

                momentum_score,
                volume_score,
                trend_score,
                risk_score,

                CURRENT_TIMESTAMP AS created_at,
                CURRENT_TIMESTAMP AS updated_at
            FROM planned;
        """, [target_date, config["limit"]])

        conn.execute("COMMIT")

        count_row = conn.execute("""
            SELECT COUNT(*)
            FROM quant_trade_plans
            WHERE trading_date = ?;
        """, [target_date]).fetchone()

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        return {
            "status": "success",
            "message": "Quant trade plans built successfully.",
            "source": source_status,
            "plans": {
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
            detail=f"Unable to build quant trade plans: {error}"
        )

    finally:
        conn.close()


def get_quant_trade_plans_service(
    trading_date: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_trade_plans_table(conn)

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
                FROM quant_trade_plans;
            """).fetchone()

        target_date = date_row[0] if date_row else None

        if not target_date:
            return {
                "status": "empty",
                "message": "No trade plans found. Build trade plans first.",
                "trading_date": None,
                "plans": []
            }

        rows = conn.execute("""
            SELECT
                plan_id,
                instrument_key,
                trading_symbol,
                trading_date,

                rank_number,
                final_score,
                signal_label,

                close_price,
                entry_price,
                entry_zone_low,
                entry_zone_high,
                stop_loss_price,
                target_1_price,
                target_2_price,

                risk_pct,
                target_1_pct,
                target_2_pct,
                reward_risk_1,
                reward_risk_2,

                suggested_holding_days,
                position_note,
                plan_reason,

                momentum_score,
                volume_score,
                trend_score,
                risk_score
            FROM quant_trade_plans
            WHERE trading_date = ?
            ORDER BY rank_number
            LIMIT ?;
        """, [target_date, safe_limit]).fetchall()

        return {
            "status": "success",
            "trading_date": str(target_date),
            "plans": [
                {
                    "plan_id": row[0],
                    "instrument_key": row[1],
                    "trading_symbol": row[2],
                    "trading_date": str(row[3]) if row[3] else None,

                    "rank_number": row[4],
                    "final_score": row[5],
                    "signal_label": row[6],

                    "close_price": row[7],
                    "entry_price": row[8],
                    "entry_zone_low": row[9],
                    "entry_zone_high": row[10],
                    "stop_loss_price": row[11],
                    "target_1_price": row[12],
                    "target_2_price": row[13],

                    "risk_pct": row[14],
                    "target_1_pct": row[15],
                    "target_2_pct": row[16],
                    "reward_risk_1": row[17],
                    "reward_risk_2": row[18],

                    "suggested_holding_days": row[19],
                    "position_note": row[20],
                    "plan_reason": row[21],

                    "momentum_score": row[22],
                    "volume_score": row[23],
                    "trend_score": row[24],
                    "risk_score": row[25]
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant trade plans: {error}"
        )

    finally:
        conn.close()
