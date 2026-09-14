"""Schema creation for one part of the existing DuckDB database."""


def ensure_legacy_data_schema(conn, safe_execute):
    # -----------------------------
    # Prediction requests
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_requests (
            request_id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            model_name VARCHAR,
            request_status VARCHAR DEFAULT 'pending',
            record_status VARCHAR DEFAULT 'S',
            version_no INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE prediction_requests ADD COLUMN record_status VARCHAR DEFAULT 'S';")
    safe_execute(conn, "ALTER TABLE prediction_requests ADD COLUMN version_no INTEGER DEFAULT 1;")
    safe_execute(conn, "ALTER TABLE prediction_requests ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Prediction results
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_results (
            result_id VARCHAR PRIMARY KEY,
            request_id VARCHAR NOT NULL,
            predicted_price DOUBLE,
            confidence_score DOUBLE,
            prediction_for_date DATE,
            record_status VARCHAR DEFAULT 'S',
            version_no INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE prediction_results ADD COLUMN record_status VARCHAR DEFAULT 'S';")
    safe_execute(conn, "ALTER TABLE prediction_results ADD COLUMN version_no INTEGER DEFAULT 1;")
    safe_execute(conn, "ALTER TABLE prediction_results ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Sync log table
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            sync_id VARCHAR PRIMARY KEY,
            table_name VARCHAR NOT NULL,
            record_id VARCHAR NOT NULL,
            action_type VARCHAR NOT NULL,
            version_no INTEGER,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            changed_by VARCHAR,
            device_id VARCHAR
        );
    """)

    # -----------------------------
    # OHLCV Candles
    # Stores Upstox candle data for current/equity and expired instruments.
    # Supports historical/intraday, multiple intervals, skip-existing checks, and duplicate-safe inserts.
    # Upstox candle fields: timestamp, open, high, low, close, volume, open_interest.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ohlcv_candles (
            provider VARCHAR DEFAULT 'upstox',
            instrument_source VARCHAR NOT NULL,
            candle_mode VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            name VARCHAR,
            exchange VARCHAR,
            segment VARCHAR,
            isin VARCHAR,
            expiry DATE,
            instrument_type VARCHAR,
            unit VARCHAR NOT NULL,
            interval_value INTEGER NOT NULL,
            interval_label VARCHAR NOT NULL,
            candle_timestamp TIMESTAMP NOT NULL,
            candle_date DATE,
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume BIGINT,
            open_interest BIGINT DEFAULT 0,
            source_sync_id VARCHAR,
            raw_json JSON,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (
                provider,
                instrument_source,
                candle_mode,
                instrument_key,
                unit,
                interval_value,
                candle_timestamp
            )
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN instrument_source VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN candle_mode VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN instrument_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN exchange VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN segment VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN expiry DATE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN instrument_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN interval_value INTEGER;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN interval_label VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN candle_timestamp TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN candle_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN open_price DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN high_price DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN low_price DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN close_price DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN volume BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN open_interest BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN source_sync_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_ohlcv_candles_bounds
        ON upstox_ohlcv_candles (
            provider,
            instrument_source,
            candle_mode,
            instrument_key,
            unit,
            interval_value,
            candle_date
        );
    """)
    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_ohlcv_candles_identity
        ON upstox_ohlcv_candles (
            provider,
            instrument_source,
            candle_mode,
            instrument_key,
            unit,
            interval_value,
            candle_timestamp
        );
    """)

    # -----------------------------
    # OHLCV Daily compatibility table
    # Kept for existing code/screens that still read ohlcv_daily.
    # New OHLCV logic writes to upstox_ohlcv_candles and can also mirror daily candles here.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_daily (
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR NOT NULL,
            date DATE NOT NULL,
            open DOUBLE NOT NULL,
            high DOUBLE NOT NULL,
            low DOUBLE NOT NULL,
            close DOUBLE NOT NULL,
            volume BIGINT NOT NULL,
            oi BIGINT DEFAULT 0,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (instrument_key, date)
        );
    """)

    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN date DATE;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN open DOUBLE;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN high DOUBLE;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN low DOUBLE;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN close DOUBLE;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN volume BIGINT;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN oi BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Equity news
    # Stock-level news articles.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS equity_news (
            news_id VARCHAR PRIMARY KEY,
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR NOT NULL,
            title VARCHAR,
            summary TEXT,
            source VARCHAR,
            url VARCHAR,
            published_at TIMESTAMP,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN instrument_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN title VARCHAR;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN summary TEXT;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN source VARCHAR;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN url VARCHAR;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN thumbnail VARCHAR;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN published_at TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

