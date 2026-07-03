from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_pattern_tables(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_pattern_runs (
            pattern_run_id VARCHAR PRIMARY KEY,
            pattern_name VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',
            from_date DATE,
            to_date DATE,
            min_sample_size BIGINT DEFAULT 30,
            total_patterns BIGINT DEFAULT 0,
            best_pattern VARCHAR,
            best_avg_forward_return DOUBLE,
            config_json JSON,
            message VARCHAR,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            duration_seconds BIGINT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_pattern_matches (
            match_id VARCHAR PRIMARY KEY,
            pattern_run_id VARCHAR NOT NULL,
            pattern_name VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            close_price DOUBLE,
            return_20d DOUBLE,
            volume_ratio_20 DOUBLE,
            distance_sma_20_pct DOUBLE,
            volatility_20 DOUBLE,
            momentum_20 DOUBLE,

            future_return_5d DOUBLE,
            future_return_10d DOUBLE,
            future_return_20d DOUBLE,
            future_max_gain_10d DOUBLE,
            future_max_drawdown_10d DOUBLE,
            future_positive_10d BOOLEAN,

            pattern_bucket VARCHAR,
            pattern_score DOUBLE,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_pattern_summary (
            summary_id VARCHAR PRIMARY KEY,
            pattern_run_id VARCHAR NOT NULL,
            pattern_name VARCHAR NOT NULL,
            pattern_bucket VARCHAR NOT NULL,

            sample_size BIGINT DEFAULT 0,
            positive_10d_count BIGINT DEFAULT 0,
            positive_10d_rate DOUBLE,

            avg_future_return_5d DOUBLE,
            avg_future_return_10d DOUBLE,
            avg_future_return_20d DOUBLE,

            median_future_return_10d DOUBLE,
            best_future_return_10d DOUBLE,
            worst_future_return_10d DOUBLE,

            avg_max_gain_10d DOUBLE,
            avg_max_drawdown_10d DOUBLE,

            avg_pattern_score DOUBLE,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_pattern_runs_started
        ON quant_pattern_runs (started_at);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_pattern_matches_run
        ON quant_pattern_matches (pattern_run_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_pattern_matches_symbol_date
        ON quant_pattern_matches (trading_symbol, trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_pattern_summary_run
        ON quant_pattern_summary (pattern_run_id);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def normalize_pattern_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    pattern_name = str(payload.get("pattern_name") or "momentum_volume_trend_buckets").strip()
    from_date = str(payload.get("from_date") or "").strip()
    to_date = str(payload.get("to_date") or "").strip()
    instrument_key = str(payload.get("instrument_key") or "").strip()
    trading_symbol = str(payload.get("trading_symbol") or "").strip()

    def to_int(value, default_value, minimum=1, maximum=1000000):
        try:
            if value in (None, ""):
                number = default_value
            else:
                number = int(value)
        except Exception:
            number = default_value

        return max(minimum, min(number, maximum))

    return {
        "pattern_name": pattern_name or "momentum_volume_trend_buckets",
        "from_date": from_date or None,
        "to_date": to_date or None,
        "instrument_key": instrument_key or None,
        "trading_symbol": trading_symbol or None,
        "min_sample_size": to_int(payload.get("min_sample_size"), 30, 5, 1000000),
        "limit": to_int(payload.get("limit"), 100000, 1, 1000000)
    }


def get_quant_pattern_source_status(conn) -> Dict[str, Any]:
    feature_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_features_daily;
    """).fetchone()

    label_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_labels_daily;
    """).fetchone()

    return {
        "features": {
            "row_count": int(feature_row[0] or 0) if feature_row else 0,
            "instrument_count": int(feature_row[1] or 0) if feature_row else 0,
            "min_date": str(feature_row[2]) if feature_row and feature_row[2] else None,
            "max_date": str(feature_row[3]) if feature_row and feature_row[3] else None
        },
        "labels": {
            "row_count": int(label_row[0] or 0) if label_row else 0,
            "instrument_count": int(label_row[1] or 0) if label_row else 0,
            "min_date": str(label_row[2]) if label_row and label_row[2] else None,
            "max_date": str(label_row[3]) if label_row and label_row[3] else None
        }
    }


def run_quant_pattern_discovery_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_pattern_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_pattern_tables(conn)

        source_status = get_quant_pattern_source_status(conn)

        if source_status["features"]["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in quant_features_daily. Build quant features first.",
                "source": source_status
            }

        if source_status["labels"]["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in quant_labels_daily. Build quant labels first.",
                "source": source_status
            }

        where_parts = [
            "features.close_price IS NOT NULL",
            "features.close_price > 0",
            "features.return_20d IS NOT NULL",
            "features.volume_ratio_20 IS NOT NULL",
            "features.distance_sma_20_pct IS NOT NULL",
            "features.volatility_20 IS NOT NULL",
            "labels.future_return_10d IS NOT NULL"
        ]
        params = []

        if config["from_date"]:
            where_parts.append("features.trading_date >= TRY_CAST(? AS DATE)")
            params.append(config["from_date"])

        if config["to_date"]:
            where_parts.append("features.trading_date <= TRY_CAST(? AS DATE)")
            params.append(config["to_date"])

        if config["instrument_key"]:
            where_parts.append("features.instrument_key = ?")
            params.append(config["instrument_key"])

        if config["trading_symbol"]:
            where_parts.append("UPPER(features.trading_symbol) = UPPER(?)")
            params.append(config["trading_symbol"])

        where_sql = " AND ".join(where_parts)

        run_id_row = conn.execute("SELECT uuid();").fetchone()
        pattern_run_id = str(run_id_row[0])

        conn.execute("""
            INSERT INTO quant_pattern_runs (
                pattern_run_id,
                pattern_name,
                status,
                from_date,
                to_date,
                min_sample_size,
                config_json,
                message,
                started_at
            )
            VALUES (
                ?,
                ?,
                'running',
                TRY_CAST(? AS DATE),
                TRY_CAST(? AS DATE),
                ?,
                TRY_CAST(? AS JSON),
                'Pattern discovery started.',
                CURRENT_TIMESTAMP
            );
        """, [
            pattern_run_id,
            config["pattern_name"],
            config["from_date"],
            config["to_date"],
            config["min_sample_size"],
            str(config).replace("'", '"')
        ])

        conn.execute("BEGIN TRANSACTION")

        conn.execute(f"""
            INSERT INTO quant_pattern_matches (
                match_id,
                pattern_run_id,
                pattern_name,
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,
                return_20d,
                volume_ratio_20,
                distance_sma_20_pct,
                volatility_20,
                momentum_20,

                future_return_5d,
                future_return_10d,
                future_return_20d,
                future_max_gain_10d,
                future_max_drawdown_10d,
                future_positive_10d,

                pattern_bucket,
                pattern_score,

                created_at
            )
            WITH joined AS (
                SELECT
                    features.instrument_key,
                    features.trading_symbol,
                    features.trading_date,

                    features.close_price,
                    features.return_20d,
                    features.volume_ratio_20,
                    features.distance_sma_20_pct,
                    features.volatility_20,
                    features.momentum_20,

                    labels.future_return_5d,
                    labels.future_return_10d,
                    labels.future_return_20d,
                    labels.future_max_gain_10d,
                    labels.future_max_drawdown_10d,
                    labels.future_positive_10d
                FROM quant_features_daily features
                INNER JOIN quant_labels_daily labels
                    ON labels.instrument_key = features.instrument_key
                   AND labels.trading_date = features.trading_date
                WHERE {where_sql}
                ORDER BY features.trading_date, features.trading_symbol
                LIMIT ?
            ),
            bucketed AS (
                SELECT
                    *,
                    CONCAT(
                        CASE
                            WHEN return_20d >= 0.20 THEN 'strong_momentum'
                            WHEN return_20d >= 0.05 THEN 'positive_momentum'
                            WHEN return_20d >= -0.05 THEN 'flat_momentum'
                            ELSE 'weak_momentum'
                        END,
                        '|',
                        CASE
                            WHEN volume_ratio_20 >= 2.0 THEN 'high_volume'
                            WHEN volume_ratio_20 >= 1.2 THEN 'above_avg_volume'
                            ELSE 'normal_low_volume'
                        END,
                        '|',
                        CASE
                            WHEN distance_sma_20_pct >= 0.05 THEN 'above_sma20'
                            WHEN distance_sma_20_pct >= 0 THEN 'near_above_sma20'
                            ELSE 'below_sma20'
                        END,
                        '|',
                        CASE
                            WHEN volatility_20 >= 0.06 THEN 'high_volatility'
                            WHEN volatility_20 >= 0.03 THEN 'medium_volatility'
                            ELSE 'low_volatility'
                        END
                    ) AS pattern_bucket,

                    (
                        CASE
                            WHEN return_20d >= 0.20 THEN 35
                            WHEN return_20d >= 0.05 THEN 25
                            WHEN return_20d >= -0.05 THEN 10
                            ELSE 0
                        END
                        +
                        CASE
                            WHEN volume_ratio_20 >= 2.0 THEN 25
                            WHEN volume_ratio_20 >= 1.2 THEN 15
                            ELSE 5
                        END
                        +
                        CASE
                            WHEN distance_sma_20_pct >= 0.05 THEN 25
                            WHEN distance_sma_20_pct >= 0 THEN 15
                            ELSE 0
                        END
                        +
                        CASE
                            WHEN volatility_20 <= 0.03 THEN 15
                            WHEN volatility_20 <= 0.06 THEN 8
                            ELSE 0
                        END
                    ) AS pattern_score
                FROM joined
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS match_id,
                ? AS pattern_run_id,
                ? AS pattern_name,
                instrument_key,
                trading_symbol,
                trading_date,

                close_price,
                return_20d,
                volume_ratio_20,
                distance_sma_20_pct,
                volatility_20,
                momentum_20,

                future_return_5d,
                future_return_10d,
                future_return_20d,
                future_max_gain_10d,
                future_max_drawdown_10d,
                future_positive_10d,

                pattern_bucket,
                pattern_score,

                CURRENT_TIMESTAMP AS created_at
            FROM bucketed;
        """, [
            *params,
            config["limit"],
            pattern_run_id,
            config["pattern_name"]
        ])

        conn.execute("""
            INSERT INTO quant_pattern_summary (
                summary_id,
                pattern_run_id,
                pattern_name,
                pattern_bucket,

                sample_size,
                positive_10d_count,
                positive_10d_rate,

                avg_future_return_5d,
                avg_future_return_10d,
                avg_future_return_20d,

                median_future_return_10d,
                best_future_return_10d,
                worst_future_return_10d,

                avg_max_gain_10d,
                avg_max_drawdown_10d,

                avg_pattern_score,

                created_at
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS summary_id,
                pattern_run_id,
                pattern_name,
                pattern_bucket,

                COUNT(*) AS sample_size,
                SUM(CASE WHEN future_positive_10d THEN 1 ELSE 0 END) AS positive_10d_count,
                CASE
                    WHEN COUNT(*) = 0 THEN NULL
                    ELSE SUM(CASE WHEN future_positive_10d THEN 1 ELSE 0 END) / CAST(COUNT(*) AS DOUBLE)
                END AS positive_10d_rate,

                AVG(future_return_5d) AS avg_future_return_5d,
                AVG(future_return_10d) AS avg_future_return_10d,
                AVG(future_return_20d) AS avg_future_return_20d,

                MEDIAN(future_return_10d) AS median_future_return_10d,
                MAX(future_return_10d) AS best_future_return_10d,
                MIN(future_return_10d) AS worst_future_return_10d,

                AVG(future_max_gain_10d) AS avg_max_gain_10d,
                AVG(future_max_drawdown_10d) AS avg_max_drawdown_10d,

                AVG(pattern_score) AS avg_pattern_score,

                CURRENT_TIMESTAMP AS created_at
            FROM quant_pattern_matches
            WHERE pattern_run_id = ?
            GROUP BY
                pattern_run_id,
                pattern_name,
                pattern_bucket
            HAVING COUNT(*) >= ?
            ORDER BY avg_future_return_10d DESC;
        """, [
            pattern_run_id,
            config["min_sample_size"]
        ])

        conn.execute("COMMIT")

        metrics_row = conn.execute("""
            SELECT
                COUNT(*) AS total_patterns,
                MAX(avg_future_return_10d) AS best_avg_forward_return
            FROM quant_pattern_summary
            WHERE pattern_run_id = ?;
        """, [pattern_run_id]).fetchone()

        best_row = conn.execute("""
            SELECT pattern_bucket
            FROM quant_pattern_summary
            WHERE pattern_run_id = ?
            ORDER BY avg_future_return_10d DESC
            LIMIT 1;
        """, [pattern_run_id]).fetchone()

        match_row = conn.execute("""
            SELECT COUNT(*)
            FROM quant_pattern_matches
            WHERE pattern_run_id = ?;
        """, [pattern_run_id]).fetchone()

        total_patterns = int(metrics_row[0] or 0) if metrics_row else 0
        best_avg_forward_return = metrics_row[1] if metrics_row else None
        best_pattern = best_row[0] if best_row else None
        total_matches = int(match_row[0] or 0) if match_row else 0

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        status_text = "success" if total_patterns > 0 else "empty"
        message = (
            "Pattern discovery completed successfully."
            if total_patterns > 0
            else "Pattern discovery completed but no pattern bucket met the minimum sample size."
        )

        conn.execute("""
            UPDATE quant_pattern_runs
            SET
                status = ?,
                total_patterns = ?,
                best_pattern = ?,
                best_avg_forward_return = ?,
                message = ?,
                finished_at = CURRENT_TIMESTAMP,
                duration_seconds = ?
            WHERE pattern_run_id = ?;
        """, [
            status_text,
            total_patterns,
            best_pattern,
            best_avg_forward_return,
            message,
            duration_seconds,
            pattern_run_id
        ])

        conn.commit()

        return {
            "status": status_text,
            "message": message,
            "pattern_run_id": pattern_run_id,
            "config": config,
            "source": source_status,
            "metrics": {
                "total_matches": total_matches,
                "total_patterns": total_patterns,
                "best_pattern": best_pattern,
                "best_avg_forward_return": best_avg_forward_return
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
            detail=f"Unable to run quant pattern discovery: {error}"
        )

    finally:
        conn.close()


def get_quant_pattern_runs_service(limit: int = 50) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_pattern_tables(conn)

        try:
            safe_limit = int(limit or 50)
        except Exception:
            safe_limit = 50

        safe_limit = max(1, min(safe_limit, 500))

        rows = conn.execute("""
            SELECT
                pattern_run_id,
                pattern_name,
                status,
                from_date,
                to_date,
                min_sample_size,
                total_patterns,
                best_pattern,
                best_avg_forward_return,
                message,
                started_at,
                finished_at,
                duration_seconds
            FROM quant_pattern_runs
            ORDER BY started_at DESC
            LIMIT ?;
        """, [safe_limit]).fetchall()

        return {
            "status": "success",
            "runs": [
                {
                    "pattern_run_id": row[0],
                    "pattern_name": row[1],
                    "status": row[2],
                    "from_date": str(row[3]) if row[3] else None,
                    "to_date": str(row[4]) if row[4] else None,
                    "min_sample_size": row[5],
                    "total_patterns": row[6],
                    "best_pattern": row[7],
                    "best_avg_forward_return": row[8],
                    "message": row[9],
                    "started_at": str(row[10]) if row[10] else None,
                    "finished_at": str(row[11]) if row[11] else None,
                    "duration_seconds": row[12]
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant pattern runs: {error}"
        )

    finally:
        conn.close()


def get_quant_pattern_summary_service(
    pattern_run_id: str,
    limit: int = 100
) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_pattern_tables(conn)

        clean_run_id = str(pattern_run_id or "").strip()

        if not clean_run_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pattern_run_id is required."
            )

        try:
            safe_limit = int(limit or 100)
        except Exception:
            safe_limit = 100

        safe_limit = max(1, min(safe_limit, 1000))

        run_row = conn.execute("""
            SELECT
                pattern_run_id,
                pattern_name,
                status,
                total_patterns,
                best_pattern,
                best_avg_forward_return,
                started_at,
                finished_at
            FROM quant_pattern_runs
            WHERE pattern_run_id = ?;
        """, [clean_run_id]).fetchone()

        if not run_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pattern run not found."
            )

        rows = conn.execute("""
            SELECT
                summary_id,
                pattern_bucket,
                sample_size,
                positive_10d_count,
                positive_10d_rate,
                avg_future_return_5d,
                avg_future_return_10d,
                avg_future_return_20d,
                median_future_return_10d,
                best_future_return_10d,
                worst_future_return_10d,
                avg_max_gain_10d,
                avg_max_drawdown_10d,
                avg_pattern_score
            FROM quant_pattern_summary
            WHERE pattern_run_id = ?
            ORDER BY avg_future_return_10d DESC
            LIMIT ?;
        """, [clean_run_id, safe_limit]).fetchall()

        return {
            "status": "success",
            "run": {
                "pattern_run_id": run_row[0],
                "pattern_name": run_row[1],
                "status": run_row[2],
                "total_patterns": run_row[3],
                "best_pattern": run_row[4],
                "best_avg_forward_return": run_row[5],
                "started_at": str(run_row[6]) if run_row[6] else None,
                "finished_at": str(run_row[7]) if run_row[7] else None
            },
            "summary": [
                {
                    "summary_id": row[0],
                    "pattern_bucket": row[1],
                    "sample_size": row[2],
                    "positive_10d_count": row[3],
                    "positive_10d_rate": row[4],
                    "avg_future_return_5d": row[5],
                    "avg_future_return_10d": row[6],
                    "avg_future_return_20d": row[7],
                    "median_future_return_10d": row[8],
                    "best_future_return_10d": row[9],
                    "worst_future_return_10d": row[10],
                    "avg_max_gain_10d": row[11],
                    "avg_max_drawdown_10d": row[12],
                    "avg_pattern_score": row[13]
                }
                for row in rows
            ]
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant pattern summary: {error}"
        )

    finally:
        conn.close()