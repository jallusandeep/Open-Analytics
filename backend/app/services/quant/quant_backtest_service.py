from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_backtest_tables(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_backtest_runs (
            run_id VARCHAR PRIMARY KEY,
            strategy_name VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',
            from_date DATE,
            to_date DATE,
            holding_days BIGINT DEFAULT 10,
            stop_loss_pct DOUBLE,
            target_pct DOUBLE,
            total_trades BIGINT DEFAULT 0,
            winning_trades BIGINT DEFAULT 0,
            losing_trades BIGINT DEFAULT 0,
            win_rate DOUBLE,
            average_return DOUBLE,
            median_return DOUBLE,
            best_return DOUBLE,
            worst_return DOUBLE,
            total_return DOUBLE,
            average_holding_days DOUBLE,
            max_drawdown_trade DOUBLE,
            config_json JSON,
            message VARCHAR,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            duration_seconds BIGINT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_backtest_trades (
            trade_id VARCHAR PRIMARY KEY,
            run_id VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            entry_date DATE NOT NULL,
            exit_date DATE,
            entry_price DOUBLE,
            exit_price DOUBLE,
            stop_loss_price DOUBLE,
            target_price DOUBLE,
            return_pct DOUBLE,
            holding_days BIGINT,
            exit_reason VARCHAR,
            entry_return_20d DOUBLE,
            entry_volume_ratio_20 DOUBLE,
            entry_distance_sma_20_pct DOUBLE,
            entry_distance_sma_50_pct DOUBLE,
            entry_volatility_20 DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_backtest_runs_started
        ON quant_backtest_runs (started_at);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_backtest_trades_run
        ON quant_backtest_trades (run_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_backtest_trades_symbol
        ON quant_backtest_trades (trading_symbol, entry_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_backtest_trades_entry_date
        ON quant_backtest_trades (entry_date);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def normalize_backtest_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    strategy_name = str(payload.get("strategy_name") or "momentum_volume_sma_20").strip()
    from_date = str(payload.get("from_date") or "").strip()
    to_date = str(payload.get("to_date") or "").strip()
    instrument_key = str(payload.get("instrument_key") or "").strip()
    trading_symbol = str(payload.get("trading_symbol") or "").strip()

    def to_float(value, default_value):
        try:
            if value in (None, ""):
                return default_value
            return float(value)
        except Exception:
            return default_value

    def to_int(value, default_value, minimum=1, maximum=250):
        try:
            if value in (None, ""):
                number = default_value
            else:
                number = int(value)
        except Exception:
            number = default_value

        return max(minimum, min(number, maximum))

    return {
        "strategy_name": strategy_name or "momentum_volume_sma_20",
        "from_date": from_date or None,
        "to_date": to_date or None,
        "instrument_key": instrument_key or None,
        "trading_symbol": trading_symbol or None,

        "holding_days": to_int(payload.get("holding_days"), 10, 1, 250),
        "stop_loss_pct": to_float(payload.get("stop_loss_pct"), -0.08),
        "target_pct": to_float(payload.get("target_pct"), 0.15),

        "min_return_20d": to_float(payload.get("min_return_20d"), 0.0),
        "min_volume_ratio_20": to_float(payload.get("min_volume_ratio_20"), 1.5),
        "min_distance_sma_20_pct": to_float(payload.get("min_distance_sma_20_pct"), 0.0),

        "max_trades": to_int(payload.get("max_trades"), 50000, 1, 1000000)
    }


def get_quant_backtest_source_status(conn) -> Dict[str, Any]:
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


def run_quant_backtest_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_backtest_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_backtest_tables(conn)

        source_status = get_quant_backtest_source_status(conn)

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
            "features.return_20d IS NOT NULL",
            "features.volume_ratio_20 IS NOT NULL",
            "features.distance_sma_20_pct IS NOT NULL",
            "labels.future_return_10d IS NOT NULL",
            "features.close_price IS NOT NULL",
            "features.close_price > 0",
            "features.return_20d >= ?",
            "features.volume_ratio_20 >= ?",
            "features.distance_sma_20_pct >= ?"
        ]

        params = [
            config["min_return_20d"],
            config["min_volume_ratio_20"],
            config["min_distance_sma_20_pct"]
        ]

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
        run_id = str(run_id_row[0])

        conn.execute("""
            INSERT INTO quant_backtest_runs (
                run_id,
                strategy_name,
                status,
                from_date,
                to_date,
                holding_days,
                stop_loss_pct,
                target_pct,
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
                ?,
                ?,
                TRY_CAST(? AS JSON),
                'Backtest started.',
                CURRENT_TIMESTAMP
            );
        """, [
            run_id,
            config["strategy_name"],
            config["from_date"],
            config["to_date"],
            config["holding_days"],
            config["stop_loss_pct"],
            config["target_pct"],
            str(config).replace("'", '"')
        ])

        conn.execute("BEGIN TRANSACTION")

        conn.execute(f"""
            INSERT INTO quant_backtest_trades (
                trade_id,
                run_id,
                instrument_key,
                trading_symbol,
                entry_date,
                exit_date,
                entry_price,
                exit_price,
                stop_loss_price,
                target_price,
                return_pct,
                holding_days,
                exit_reason,
                entry_return_20d,
                entry_volume_ratio_20,
                entry_distance_sma_20_pct,
                entry_distance_sma_50_pct,
                entry_volatility_20,
                created_at
            )
            WITH candidates AS (
                SELECT
                    features.instrument_key,
                    features.trading_symbol,
                    features.trading_date AS entry_date,
                    features.close_price AS entry_price,
                    features.return_20d,
                    features.volume_ratio_20,
                    features.distance_sma_20_pct,
                    features.distance_sma_50_pct,
                    features.volatility_20,
                    labels.future_return_10d,
                    labels.future_max_gain_10d,
                    labels.future_max_drawdown_10d
                FROM quant_features_daily features
                INNER JOIN quant_labels_daily labels
                    ON labels.instrument_key = features.instrument_key
                   AND labels.trading_date = features.trading_date
                WHERE {where_sql}
                ORDER BY features.trading_date, features.trading_symbol
                LIMIT ?
            ),
            future_prices AS (
                SELECT
                    candidates.instrument_key,
                    candidates.trading_symbol,
                    candidates.entry_date,
                    future.date AS future_date,
                    CAST(future.high AS DOUBLE) AS future_high,
                    CAST(future.low AS DOUBLE) AS future_low,
                    CAST(future.close AS DOUBLE) AS future_close,
                    ROW_NUMBER() OVER (
                        PARTITION BY candidates.instrument_key, candidates.entry_date
                        ORDER BY future.date
                    ) AS future_day_number
                FROM candidates
                INNER JOIN ohlcv_daily future
                    ON future.instrument_key = candidates.instrument_key
                   AND future.date > candidates.entry_date
            ),
            target_hits AS (
                SELECT
                    candidates.instrument_key,
                    candidates.entry_date,
                    MIN(future_prices.future_day_number) AS target_hit_day
                FROM candidates
                INNER JOIN future_prices
                    ON future_prices.instrument_key = candidates.instrument_key
                   AND future_prices.entry_date = candidates.entry_date
                WHERE future_prices.future_day_number <= ?
                  AND future_prices.future_high >= candidates.entry_price * (1 + ?)
                GROUP BY candidates.instrument_key, candidates.entry_date
            ),
            stop_hits AS (
                SELECT
                    candidates.instrument_key,
                    candidates.entry_date,
                    MIN(future_prices.future_day_number) AS stop_hit_day
                FROM candidates
                INNER JOIN future_prices
                    ON future_prices.instrument_key = candidates.instrument_key
                   AND future_prices.entry_date = candidates.entry_date
                WHERE future_prices.future_day_number <= ?
                  AND future_prices.future_low <= candidates.entry_price * (1 + ?)
                GROUP BY candidates.instrument_key, candidates.entry_date
            ),
            planned_exit AS (
                SELECT
                    instrument_key,
                    entry_date,
                    future_date AS planned_exit_date,
                    future_close AS planned_exit_price
                FROM future_prices
                WHERE future_day_number = ?
            ),
            exit_decision AS (
                SELECT
                    candidates.*,
                    target_hits.target_hit_day,
                    stop_hits.stop_hit_day,
                    planned_exit.planned_exit_date,
                    planned_exit.planned_exit_price,

                    CASE
                        WHEN target_hits.target_hit_day IS NOT NULL
                         AND stop_hits.stop_hit_day IS NOT NULL
                         AND target_hits.target_hit_day <= stop_hits.stop_hit_day
                        THEN target_hits.target_hit_day

                        WHEN target_hits.target_hit_day IS NOT NULL
                         AND stop_hits.stop_hit_day IS NOT NULL
                         AND stop_hits.stop_hit_day < target_hits.target_hit_day
                        THEN stop_hits.stop_hit_day

                        WHEN target_hits.target_hit_day IS NOT NULL
                        THEN target_hits.target_hit_day

                        WHEN stop_hits.stop_hit_day IS NOT NULL
                        THEN stop_hits.stop_hit_day

                        ELSE ?
                    END AS exit_day_number,

                    CASE
                        WHEN target_hits.target_hit_day IS NOT NULL
                         AND stop_hits.stop_hit_day IS NOT NULL
                         AND target_hits.target_hit_day <= stop_hits.stop_hit_day
                        THEN 'target'

                        WHEN target_hits.target_hit_day IS NOT NULL
                         AND stop_hits.stop_hit_day IS NOT NULL
                         AND stop_hits.stop_hit_day < target_hits.target_hit_day
                        THEN 'stop_loss'

                        WHEN target_hits.target_hit_day IS NOT NULL
                        THEN 'target'

                        WHEN stop_hits.stop_hit_day IS NOT NULL
                        THEN 'stop_loss'

                        ELSE 'time_exit'
                    END AS exit_reason
                FROM candidates
                LEFT JOIN target_hits
                    ON target_hits.instrument_key = candidates.instrument_key
                   AND target_hits.entry_date = candidates.entry_date
                LEFT JOIN stop_hits
                    ON stop_hits.instrument_key = candidates.instrument_key
                   AND stop_hits.entry_date = candidates.entry_date
                LEFT JOIN planned_exit
                    ON planned_exit.instrument_key = candidates.instrument_key
                   AND planned_exit.entry_date = candidates.entry_date
            ),
            final_trades AS (
                SELECT
                    exit_decision.*,
                    exit_price_row.future_date AS exit_date,

                    CASE
                        WHEN exit_decision.exit_reason = 'target'
                        THEN exit_decision.entry_price * (1 + ?)

                        WHEN exit_decision.exit_reason = 'stop_loss'
                        THEN exit_decision.entry_price * (1 + ?)

                        ELSE exit_price_row.future_close
                    END AS exit_price
                FROM exit_decision
                LEFT JOIN future_prices exit_price_row
                    ON exit_price_row.instrument_key = exit_decision.instrument_key
                   AND exit_price_row.entry_date = exit_decision.entry_date
                   AND exit_price_row.future_day_number = exit_decision.exit_day_number
                WHERE exit_price_row.future_date IS NOT NULL
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS trade_id,
                ? AS run_id,
                instrument_key,
                trading_symbol,
                entry_date,
                exit_date,
                entry_price,
                exit_price,
                entry_price * (1 + ?) AS stop_loss_price,
                entry_price * (1 + ?) AS target_price,

                CASE
                    WHEN entry_price IS NULL OR entry_price = 0 OR exit_price IS NULL THEN NULL
                    ELSE (exit_price - entry_price) / entry_price
                END AS return_pct,

                exit_day_number AS holding_days,
                exit_reason,
                return_20d AS entry_return_20d,
                volume_ratio_20 AS entry_volume_ratio_20,
                distance_sma_20_pct AS entry_distance_sma_20_pct,
                distance_sma_50_pct AS entry_distance_sma_50_pct,
                volatility_20 AS entry_volatility_20,
                CURRENT_TIMESTAMP AS created_at
            FROM final_trades;
        """, [
            *params,
            config["max_trades"],
            config["holding_days"],
            config["target_pct"],
            config["holding_days"],
            config["stop_loss_pct"],
            config["holding_days"],
            config["holding_days"],
            config["target_pct"],
            config["stop_loss_pct"],
            run_id,
            config["stop_loss_pct"],
            config["target_pct"]
        ])

        conn.execute("COMMIT")

        metrics_row = conn.execute("""
            SELECT
                COUNT(*) AS total_trades,
                SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) AS winning_trades,
                SUM(CASE WHEN return_pct <= 0 THEN 1 ELSE 0 END) AS losing_trades,
                AVG(return_pct) AS average_return,
                MEDIAN(return_pct) AS median_return,
                MAX(return_pct) AS best_return,
                MIN(return_pct) AS worst_return,
                SUM(return_pct) AS total_return,
                AVG(holding_days) AS average_holding_days,
                MIN(return_pct) AS max_drawdown_trade
            FROM quant_backtest_trades
            WHERE run_id = ?;
        """, [run_id]).fetchone()

        total_trades = int(metrics_row[0] or 0) if metrics_row else 0
        winning_trades = int(metrics_row[1] or 0) if metrics_row else 0
        losing_trades = int(metrics_row[2] or 0) if metrics_row else 0
        win_rate = (winning_trades / total_trades) if total_trades else None

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        status_text = "success" if total_trades > 0 else "empty"
        message = (
            "Backtest completed successfully."
            if total_trades > 0
            else "Backtest completed but no trades matched the strategy rules."
        )

        conn.execute("""
            UPDATE quant_backtest_runs
            SET
                status = ?,
                total_trades = ?,
                winning_trades = ?,
                losing_trades = ?,
                win_rate = ?,
                average_return = ?,
                median_return = ?,
                best_return = ?,
                worst_return = ?,
                total_return = ?,
                average_holding_days = ?,
                max_drawdown_trade = ?,
                message = ?,
                finished_at = CURRENT_TIMESTAMP,
                duration_seconds = ?
            WHERE run_id = ?;
        """, [
            status_text,
            total_trades,
            winning_trades,
            losing_trades,
            win_rate,
            metrics_row[3] if metrics_row else None,
            metrics_row[4] if metrics_row else None,
            metrics_row[5] if metrics_row else None,
            metrics_row[6] if metrics_row else None,
            metrics_row[7] if metrics_row else None,
            metrics_row[8] if metrics_row else None,
            metrics_row[9] if metrics_row else None,
            message,
            duration_seconds,
            run_id
        ])

        conn.commit()

        return {
            "status": status_text,
            "message": message,
            "run_id": run_id,
            "config": config,
            "source": source_status,
            "metrics": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "average_return": metrics_row[3] if metrics_row else None,
                "median_return": metrics_row[4] if metrics_row else None,
                "best_return": metrics_row[5] if metrics_row else None,
                "worst_return": metrics_row[6] if metrics_row else None,
                "total_return": metrics_row[7] if metrics_row else None,
                "average_holding_days": metrics_row[8] if metrics_row else None,
                "max_drawdown_trade": metrics_row[9] if metrics_row else None
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
            detail=f"Unable to run quant backtest: {error}"
        )

    finally:
        conn.close()


def get_quant_backtest_runs_service(limit: int = 50) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_backtest_tables(conn)

        try:
            safe_limit = int(limit or 50)
        except Exception:
            safe_limit = 50

        safe_limit = max(1, min(safe_limit, 500))

        rows = conn.execute("""
            SELECT
                run_id,
                strategy_name,
                status,
                from_date,
                to_date,
                holding_days,
                stop_loss_pct,
                target_pct,
                total_trades,
                winning_trades,
                losing_trades,
                win_rate,
                average_return,
                median_return,
                best_return,
                worst_return,
                total_return,
                average_holding_days,
                message,
                started_at,
                finished_at,
                duration_seconds
            FROM quant_backtest_runs
            ORDER BY started_at DESC
            LIMIT ?;
        """, [safe_limit]).fetchall()

        return {
            "status": "success",
            "runs": [
                {
                    "run_id": row[0],
                    "strategy_name": row[1],
                    "status": row[2],
                    "from_date": str(row[3]) if row[3] else None,
                    "to_date": str(row[4]) if row[4] else None,
                    "holding_days": row[5],
                    "stop_loss_pct": row[6],
                    "target_pct": row[7],
                    "total_trades": row[8],
                    "winning_trades": row[9],
                    "losing_trades": row[10],
                    "win_rate": row[11],
                    "average_return": row[12],
                    "median_return": row[13],
                    "best_return": row[14],
                    "worst_return": row[15],
                    "total_return": row[16],
                    "average_holding_days": row[17],
                    "message": row[18],
                    "started_at": str(row[19]) if row[19] else None,
                    "finished_at": str(row[20]) if row[20] else None,
                    "duration_seconds": row[21]
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant backtest runs: {error}"
        )

    finally:
        conn.close()


def get_quant_backtest_trades_service(run_id: str, limit: int = 500) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_backtest_tables(conn)

        clean_run_id = str(run_id or "").strip()

        if not clean_run_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="run_id is required."
            )

        try:
            safe_limit = int(limit or 500)
        except Exception:
            safe_limit = 500

        safe_limit = max(1, min(safe_limit, 5000))

        run_row = conn.execute("""
            SELECT
                run_id,
                strategy_name,
                status,
                total_trades,
                win_rate,
                average_return,
                best_return,
                worst_return,
                started_at,
                finished_at
            FROM quant_backtest_runs
            WHERE run_id = ?;
        """, [clean_run_id]).fetchone()

        if not run_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backtest run not found."
            )

        rows = conn.execute("""
            SELECT
                trade_id,
                instrument_key,
                trading_symbol,
                entry_date,
                exit_date,
                entry_price,
                exit_price,
                stop_loss_price,
                target_price,
                return_pct,
                holding_days,
                exit_reason,
                entry_return_20d,
                entry_volume_ratio_20,
                entry_distance_sma_20_pct,
                entry_distance_sma_50_pct,
                entry_volatility_20
            FROM quant_backtest_trades
            WHERE run_id = ?
            ORDER BY entry_date DESC, trading_symbol
            LIMIT ?;
        """, [clean_run_id, safe_limit]).fetchall()

        return {
            "status": "success",
            "run": {
                "run_id": run_row[0],
                "strategy_name": run_row[1],
                "status": run_row[2],
                "total_trades": run_row[3],
                "win_rate": run_row[4],
                "average_return": run_row[5],
                "best_return": run_row[6],
                "worst_return": run_row[7],
                "started_at": str(run_row[8]) if run_row[8] else None,
                "finished_at": str(run_row[9]) if run_row[9] else None
            },
            "trades": [
                {
                    "trade_id": row[0],
                    "instrument_key": row[1],
                    "trading_symbol": row[2],
                    "entry_date": str(row[3]) if row[3] else None,
                    "exit_date": str(row[4]) if row[4] else None,
                    "entry_price": row[5],
                    "exit_price": row[6],
                    "stop_loss_price": row[7],
                    "target_price": row[8],
                    "return_pct": row[9],
                    "holding_days": row[10],
                    "exit_reason": row[11],
                    "entry_return_20d": row[12],
                    "entry_volume_ratio_20": row[13],
                    "entry_distance_sma_20_pct": row[14],
                    "entry_distance_sma_50_pct": row[15],
                    "entry_volatility_20": row[16]
                }
                for row in rows
            ]
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant backtest trades: {error}"
        )

    finally:
        conn.close()