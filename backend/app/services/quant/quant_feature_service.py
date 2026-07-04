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

            rsi_14 DOUBLE,
            macd_line DOUBLE,
            macd_signal DOUBLE,
            macd_histogram DOUBLE,
            bollinger_position DOUBLE,
            bollinger_width DOUBLE,
            atr_14_pct DOUBLE,
            stochastic_k_14 DOUBLE,
            stochastic_d_3 DOUBLE,
            adx_14 DOUBLE,
            roc_12 DOUBLE,
            williams_r_14 DOUBLE,
            mfi_14 DOUBLE,
            chaikin_money_flow_20 DOUBLE,
            vwap_distance_20 DOUBLE,
            donchian_position_20 DOUBLE,
            obv_slope_20 DOUBLE,
            pvt_slope_20 DOUBLE,

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



    for column_sql in [
        "ALTER TABLE quant_features_daily ADD COLUMN rsi_14 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN macd_line DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN macd_signal DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN macd_histogram DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN bollinger_position DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN bollinger_width DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN atr_14_pct DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN stochastic_k_14 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN stochastic_d_3 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN adx_14 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN roc_12 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN williams_r_14 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN mfi_14 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN chaikin_money_flow_20 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN vwap_distance_20 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN donchian_position_20 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN obv_slope_20 DOUBLE;",
        "ALTER TABLE quant_features_daily ADD COLUMN pvt_slope_20 DOUBLE;"
    ]:
        try:
            conn.execute(column_sql)
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

                rsi_14,
                macd_line,
                macd_signal,
                macd_histogram,
                bollinger_position,
                bollinger_width,
                atr_14_pct,
                stochastic_k_14,
                stochastic_d_3,
                adx_14,
                roc_12,
                williams_r_14,
                mfi_14,
                chaikin_money_flow_20,
                vwap_distance_20,
                donchian_position_20,
                obv_slope_20,
                pvt_slope_20,

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

                    LAG(close_price, 12) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS close_12d_ago,

                    LAG(close_price, 20) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS close_20d_ago,

                    LAG(close_price, 1) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS previous_close,

                    LAG(high_price, 1) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS previous_high,

                    LAG(low_price, 1) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS previous_low
                FROM base
            ),
            returns AS (
                SELECT
                    *,
                    CASE
                        WHEN close_1d_ago IS NULL OR close_1d_ago = 0 THEN NULL
                        ELSE (close_price - close_1d_ago) / close_1d_ago
                    END AS return_1d_for_vol,

                    CASE
                        WHEN previous_close IS NULL THEN NULL
                        ELSE close_price - previous_close
                    END AS price_change,

                    CASE
                        WHEN previous_close IS NULL THEN NULL
                        ELSE GREATEST(close_price - previous_close, 0)
                    END AS gain_1d,

                    CASE
                        WHEN previous_close IS NULL THEN NULL
                        ELSE GREATEST(previous_close - close_price, 0)
                    END AS loss_1d,

                    GREATEST(
                        high_price - low_price,
                        ABS(high_price - COALESCE(previous_close, close_price)),
                        ABS(low_price - COALESCE(previous_close, close_price))
                    ) AS true_range,

                    CASE
                        WHEN previous_high IS NULL OR previous_low IS NULL THEN NULL
                        WHEN high_price - previous_high > previous_low - low_price
                         AND high_price - previous_high > 0
                        THEN high_price - previous_high
                        ELSE 0
                    END AS plus_dm,

                    CASE
                        WHEN previous_high IS NULL OR previous_low IS NULL THEN NULL
                        WHEN previous_low - low_price > high_price - previous_high
                         AND previous_low - low_price > 0
                        THEN previous_low - low_price
                        ELSE 0
                    END AS minus_dm,

                    CASE
                        WHEN previous_close IS NULL THEN 0
                        WHEN close_price > previous_close THEN CAST(volume AS DOUBLE)
                        WHEN close_price < previous_close THEN -CAST(volume AS DOUBLE)
                        ELSE 0
                    END AS signed_volume,

                    CASE
                        WHEN previous_close IS NULL OR previous_close = 0 THEN 0
                        ELSE ((close_price - previous_close) / previous_close) * CAST(volume AS DOUBLE)
                    END AS pvt_increment,

                    CASE
                        WHEN high_price IS NULL OR low_price IS NULL OR high_price = low_price THEN 0
                        ELSE (((close_price - low_price) - (high_price - close_price)) / (high_price - low_price)) * CAST(volume AS DOUBLE)
                    END AS money_flow_volume,

                    CASE
                        WHEN previous_close IS NULL THEN 0
                        WHEN close_price > previous_close THEN ((high_price + low_price + close_price) / 3.0) * CAST(volume AS DOUBLE)
                        ELSE 0
                    END AS positive_money_flow,

                    CASE
                        WHEN previous_close IS NULL THEN 0
                        WHEN close_price < previous_close THEN ((high_price + low_price + close_price) / 3.0) * CAST(volume AS DOUBLE)
                        ELSE 0
                    END AS negative_money_flow
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

                    AVG(close_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
                    ) AS sma_12,

                    AVG(close_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 25 PRECEDING AND CURRENT ROW
                    ) AS sma_26,

                    STDDEV_SAMP(close_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS close_stddev_20,

                    AVG(gain_1d) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS avg_gain_14,

                    AVG(loss_1d) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS avg_loss_14,

                    AVG(true_range) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS atr_14,

                    MIN(low_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS lowest_low_14,

                    MAX(high_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS highest_high_14,

                    AVG(plus_dm) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS plus_dm_14,

                    AVG(minus_dm) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS minus_dm_14,

                    MAX(high_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS highest_high_20,

                    MIN(low_price) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS lowest_low_20,

                    SUM(CAST(volume AS DOUBLE) * ((high_price + low_price + close_price) / 3.0)) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS vwap_numerator_20,

                    SUM(CAST(volume AS DOUBLE)) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS vwap_denominator_20,

                    SUM(money_flow_volume) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS cmf_numerator_20,

                    SUM(CAST(volume AS DOUBLE)) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS cmf_denominator_20,

                    SUM(positive_money_flow) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS positive_money_flow_14,

                    SUM(negative_money_flow) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS negative_money_flow_14,

                    SUM(signed_volume) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS obv,

                    SUM(pvt_increment) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS pvt,

                    STDDEV_SAMP(return_1d_for_vol) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS volatility_20
                FROM returns
            ),
            indicator_seed AS (
                SELECT
                    *,
                    LAG(obv, 20) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS obv_20d_ago,
                    LAG(pvt, 20) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                    ) AS pvt_20d_ago
                FROM enriched
            ),
            indicator_base AS (
                SELECT
                    *,
                    (sma_12 - sma_26) AS macd_line,
                    CASE
                        WHEN avg_loss_14 IS NULL OR avg_loss_14 = 0 THEN 100
                        WHEN avg_gain_14 IS NULL THEN 0
                        ELSE 100 - (100 / (1 + (avg_gain_14 / avg_loss_14)))
                    END AS rsi_14,
                    CASE
                        WHEN sma_20 IS NULL OR close_stddev_20 IS NULL OR close_stddev_20 = 0 THEN NULL
                        ELSE (close_price - (sma_20 - (2 * close_stddev_20))) / (4 * close_stddev_20)
                    END AS bollinger_position,
                    CASE
                        WHEN sma_20 IS NULL OR sma_20 = 0 OR close_stddev_20 IS NULL THEN NULL
                        ELSE (4 * close_stddev_20) / sma_20
                    END AS bollinger_width,
                    CASE
                        WHEN close_price IS NULL OR close_price = 0 THEN NULL
                        ELSE atr_14 / close_price
                    END AS atr_14_pct,
                    CASE
                        WHEN highest_high_14 IS NULL
                          OR lowest_low_14 IS NULL
                          OR highest_high_14 = lowest_low_14
                        THEN NULL
                        ELSE (close_price - lowest_low_14) / (highest_high_14 - lowest_low_14) * 100
                    END AS stochastic_k_14,
                    CASE
                        WHEN atr_14 IS NULL OR atr_14 = 0 THEN NULL
                        ELSE 100 * plus_dm_14 / atr_14
                    END AS plus_di_14,
                    CASE
                        WHEN atr_14 IS NULL OR atr_14 = 0 THEN NULL
                        ELSE 100 * minus_dm_14 / atr_14
                    END AS minus_di_14
                FROM indicator_seed
            ),
            final_indicators AS (
                SELECT
                    *,
                    AVG(macd_line) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 8 PRECEDING AND CURRENT ROW
                    ) AS macd_signal,
                    AVG(stochastic_k_14) OVER (
                        PARTITION BY instrument_key
                        ORDER BY trading_date
                        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                    ) AS stochastic_d_3,
                    CASE
                        WHEN plus_di_14 IS NULL OR minus_di_14 IS NULL OR plus_di_14 + minus_di_14 = 0 THEN NULL
                        ELSE 100 * ABS(plus_di_14 - minus_di_14) / (plus_di_14 + minus_di_14)
                    END AS adx_14,
                    CASE
                        WHEN close_12d_ago IS NULL OR close_12d_ago = 0 THEN NULL
                        ELSE (close_price - close_12d_ago) / close_12d_ago
                    END AS roc_12,
                    CASE
                        WHEN highest_high_14 IS NULL OR lowest_low_14 IS NULL OR highest_high_14 = lowest_low_14 THEN NULL
                        ELSE -100 * (highest_high_14 - close_price) / (highest_high_14 - lowest_low_14)
                    END AS williams_r_14,
                    CASE
                        WHEN negative_money_flow_14 IS NULL OR negative_money_flow_14 = 0 THEN 100
                        WHEN positive_money_flow_14 IS NULL THEN 0
                        ELSE 100 - (100 / (1 + (positive_money_flow_14 / negative_money_flow_14)))
                    END AS mfi_14,
                    CASE
                        WHEN cmf_denominator_20 IS NULL OR cmf_denominator_20 = 0 THEN NULL
                        ELSE cmf_numerator_20 / cmf_denominator_20
                    END AS chaikin_money_flow_20,
                    CASE
                        WHEN vwap_denominator_20 IS NULL OR vwap_denominator_20 = 0 THEN NULL
                        WHEN vwap_numerator_20 / vwap_denominator_20 = 0 THEN NULL
                        ELSE (close_price - (vwap_numerator_20 / vwap_denominator_20)) / (vwap_numerator_20 / vwap_denominator_20)
                    END AS vwap_distance_20,
                    CASE
                        WHEN highest_high_20 IS NULL OR lowest_low_20 IS NULL OR highest_high_20 = lowest_low_20 THEN NULL
                        ELSE (close_price - lowest_low_20) / (highest_high_20 - lowest_low_20) * 100
                    END AS donchian_position_20,
                    CASE
                        WHEN obv_20d_ago IS NULL OR obv_20d_ago = 0 THEN NULL
                        ELSE (obv - obv_20d_ago) / ABS(obv_20d_ago)
                    END AS obv_slope_20,
                    CASE
                        WHEN pvt_20d_ago IS NULL OR pvt_20d_ago = 0 THEN NULL
                        ELSE (pvt - pvt_20d_ago) / ABS(pvt_20d_ago)
                    END AS pvt_slope_20
                FROM indicator_base
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

                rsi_14,
                macd_line,
                macd_signal,
                macd_line - macd_signal AS macd_histogram,
                bollinger_position,
                bollinger_width,
                atr_14_pct,
                stochastic_k_14,
                stochastic_d_3,
                adx_14,
                roc_12,
                williams_r_14,
                mfi_14,
                chaikin_money_flow_20,
                vwap_distance_20,
                donchian_position_20,
                obv_slope_20,
                pvt_slope_20,

                'ohlcv_daily' AS source_table,
                CURRENT_TIMESTAMP AS created_at,
                CURRENT_TIMESTAMP AS updated_at
            FROM final_indicators;
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









