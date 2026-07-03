from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def table_exists(conn, table_name: str) -> bool:
    row = conn.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?;
    """, [table_name]).fetchone()

    return bool(row and int(row[0] or 0) > 0)


def get_table_basic_status(conn, table_name: str, date_column: Optional[str] = None) -> Dict[str, Any]:
    if not table_exists(conn, table_name):
        return {
            "table_name": table_name,
            "exists": False,
            "row_count": 0,
            "min_date": None,
            "max_date": None
        }

    if date_column:
        row = conn.execute(f"""
            SELECT
                COUNT(*) AS row_count,
                MIN({date_column}) AS min_date,
                MAX({date_column}) AS max_date
            FROM {table_name};
        """).fetchone()

        return {
            "table_name": table_name,
            "exists": True,
            "row_count": int(row[0] or 0) if row else 0,
            "min_date": str(row[1]) if row and row[1] else None,
            "max_date": str(row[2]) if row and row[2] else None
        }

    row = conn.execute(f"""
        SELECT COUNT(*)
        FROM {table_name};
    """).fetchone()

    return {
        "table_name": table_name,
        "exists": True,
        "row_count": int(row[0] or 0) if row else 0,
        "min_date": None,
        "max_date": None
    }


def get_ohlcv_daily_quality(conn) -> Dict[str, Any]:
    if not table_exists(conn, "ohlcv_daily"):
        return {
            "status": "missing",
            "message": "ohlcv_daily table does not exist.",
            "row_count": 0,
            "instrument_count": 0,
            "min_date": None,
            "max_date": None,
            "missing_price_rows": 0,
            "zero_close_rows": 0,
            "duplicate_rows": 0,
            "latest_date_rows": 0
        }

    summary_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(date) AS min_date,
            MAX(date) AS max_date,
            SUM(
                CASE
                    WHEN open IS NULL
                      OR high IS NULL
                      OR low IS NULL
                      OR close IS NULL
                    THEN 1 ELSE 0
                END
            ) AS missing_price_rows,
            SUM(
                CASE
                    WHEN close IS NULL OR close = 0
                    THEN 1 ELSE 0
                END
            ) AS zero_close_rows
        FROM ohlcv_daily;
    """).fetchone()

    duplicate_row = conn.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT instrument_key, date, COUNT(*) AS row_count
            FROM ohlcv_daily
            GROUP BY instrument_key, date
            HAVING COUNT(*) > 1
        ) duplicates;
    """).fetchone()

    latest_row = conn.execute("""
        SELECT COUNT(*)
        FROM ohlcv_daily
        WHERE date = (
            SELECT MAX(date)
            FROM ohlcv_daily
        );
    """).fetchone()

    row_count = int(summary_row[0] or 0) if summary_row else 0

    return {
        "status": "ready" if row_count > 0 else "empty",
        "message": "OHLCV daily data is available." if row_count > 0 else "OHLCV daily table is empty.",
        "row_count": row_count,
        "instrument_count": int(summary_row[1] or 0) if summary_row else 0,
        "min_date": str(summary_row[2]) if summary_row and summary_row[2] else None,
        "max_date": str(summary_row[3]) if summary_row and summary_row[3] else None,
        "missing_price_rows": int(summary_row[4] or 0) if summary_row else 0,
        "zero_close_rows": int(summary_row[5] or 0) if summary_row else 0,
        "duplicate_rows": int(duplicate_row[0] or 0) if duplicate_row else 0,
        "latest_date_rows": int(latest_row[0] or 0) if latest_row else 0
    }


def get_quant_feature_quality(conn) -> Dict[str, Any]:
    if not table_exists(conn, "quant_features_daily"):
        return {
            "status": "missing",
            "message": "quant_features_daily table does not exist.",
            "row_count": 0,
            "instrument_count": 0,
            "min_date": None,
            "max_date": None,
            "usable_rows": 0,
            "latest_date_rows": 0
        }

    summary_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date,
            SUM(
                CASE
                    WHEN return_20d IS NOT NULL
                     AND volume_ratio_20 IS NOT NULL
                     AND sma_20 IS NOT NULL
                     AND sma_50 IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS usable_rows
        FROM quant_features_daily;
    """).fetchone()

    latest_row = conn.execute("""
        SELECT COUNT(*)
        FROM quant_features_daily
        WHERE trading_date = (
            SELECT MAX(trading_date)
            FROM quant_features_daily
        );
    """).fetchone()

    row_count = int(summary_row[0] or 0) if summary_row else 0

    return {
        "status": "ready" if row_count > 0 else "empty",
        "message": "Quant features are available." if row_count > 0 else "Quant features table is empty.",
        "row_count": row_count,
        "instrument_count": int(summary_row[1] or 0) if summary_row else 0,
        "min_date": str(summary_row[2]) if summary_row and summary_row[2] else None,
        "max_date": str(summary_row[3]) if summary_row and summary_row[3] else None,
        "usable_rows": int(summary_row[4] or 0) if summary_row else 0,
        "latest_date_rows": int(latest_row[0] or 0) if latest_row else 0
    }


def get_quant_label_quality(conn) -> Dict[str, Any]:
    if not table_exists(conn, "quant_labels_daily"):
        return {
            "status": "missing",
            "message": "quant_labels_daily table does not exist.",
            "row_count": 0,
            "instrument_count": 0,
            "min_date": None,
            "max_date": None,
            "usable_10d_rows": 0,
            "usable_20d_rows": 0
        }

    row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date,
            SUM(CASE WHEN future_return_10d IS NOT NULL THEN 1 ELSE 0 END) AS usable_10d_rows,
            SUM(CASE WHEN future_return_20d IS NOT NULL THEN 1 ELSE 0 END) AS usable_20d_rows
        FROM quant_labels_daily;
    """).fetchone()

    row_count = int(row[0] or 0) if row else 0

    return {
        "status": "ready" if row_count > 0 else "empty",
        "message": "Quant labels are available." if row_count > 0 else "Quant labels table is empty.",
        "row_count": row_count,
        "instrument_count": int(row[1] or 0) if row else 0,
        "min_date": str(row[2]) if row and row[2] else None,
        "max_date": str(row[3]) if row and row[3] else None,
        "usable_10d_rows": int(row[4] or 0) if row else 0,
        "usable_20d_rows": int(row[5] or 0) if row else 0
    }


def get_quant_data_readiness_service() -> Dict[str, Any]:
    conn = get_connection()

    try:
        ohlcv_quality = get_ohlcv_daily_quality(conn)
        feature_quality = get_quant_feature_quality(conn)
        label_quality = get_quant_label_quality(conn)

        supporting_tables = {
            "upstox_ohlcv_candles": get_table_basic_status(conn, "upstox_ohlcv_candles", "candle_date"),
            "upstox_instruments": get_table_basic_status(conn, "upstox_instruments", "synced_at"),
            "upstox_equity_instruments": get_table_basic_status(conn, "upstox_equity_instruments", "downloaded_at"),
            "corporate_actions": get_table_basic_status(conn, "corporate_actions", "ex_date"),
            "fundamentals": get_table_basic_status(conn, "fundamentals", "report_date"),
            "equity_news": get_table_basic_status(conn, "equity_news", "published_at"),
            "fii_dii_activity": get_table_basic_status(conn, "fii_dii_activity", "date")
        }

        blockers = []
        warnings = []

        if ohlcv_quality["row_count"] <= 0:
            blockers.append("Run OHLCV daily collection first.")

        if ohlcv_quality["missing_price_rows"] > 0:
            warnings.append("Some OHLCV rows have missing open/high/low/close values.")

        if ohlcv_quality["zero_close_rows"] > 0:
            warnings.append("Some OHLCV rows have zero or missing close price.")

        if feature_quality["row_count"] <= 0:
            warnings.append("Quant features are not built yet.")

        if label_quality["row_count"] <= 0:
            warnings.append("Quant labels are not built yet.")

        readiness_status = "ready"

        if blockers:
            readiness_status = "blocked"
        elif warnings:
            readiness_status = "partial"

        return {
            "status": "success",
            "readiness_status": readiness_status,
            "blockers": blockers,
            "warnings": warnings,
            "ohlcv_daily": ohlcv_quality,
            "quant_features": feature_quality,
            "quant_labels": label_quality,
            "supporting_tables": supporting_tables
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant data readiness: {error}"
        )

    finally:
        conn.close()


def get_quant_pipeline_status_service() -> Dict[str, Any]:
    conn = get_connection()

    try:
        tables = {
            "quant_features_daily": get_table_basic_status(conn, "quant_features_daily", "trading_date"),
            "quant_labels_daily": get_table_basic_status(conn, "quant_labels_daily", "trading_date"),
            "quant_rankings_daily": get_table_basic_status(conn, "quant_rankings_daily", "trading_date"),
            "quant_trade_plans": get_table_basic_status(conn, "quant_trade_plans", "trading_date"),
            "quant_signal_explanations": get_table_basic_status(conn, "quant_signal_explanations", "trading_date"),
            "quant_backtest_runs": get_table_basic_status(conn, "quant_backtest_runs", "started_at"),
            "quant_backtest_trades": get_table_basic_status(conn, "quant_backtest_trades", "entry_date")
        }

        recommended_next_step = "Run OHLCV daily collection."

        if tables["quant_features_daily"]["row_count"] <= 0:
            recommended_next_step = "Build quant features."
        elif tables["quant_labels_daily"]["row_count"] <= 0:
            recommended_next_step = "Build quant labels."
        elif tables["quant_backtest_runs"]["row_count"] <= 0:
            recommended_next_step = "Run first backtest."
        elif tables["quant_rankings_daily"]["row_count"] <= 0:
            recommended_next_step = "Build daily rankings."
        elif tables["quant_trade_plans"]["row_count"] <= 0:
            recommended_next_step = "Build trade plans."
        elif tables["quant_signal_explanations"]["row_count"] <= 0:
            recommended_next_step = "Build signal explanations."
        else:
            recommended_next_step = "Pipeline is ready for UI preview and ML dataset build."

        return {
            "status": "success",
            "tables": tables,
            "recommended_next_step": recommended_next_step
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant pipeline status: {error}"
        )

    finally:
        conn.close()