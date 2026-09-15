"""Schema creation for one part of the existing DuckDB database."""


def ensure_instrument_schema(conn, safe_execute):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reference_equity_details (
            isin VARCHAR NOT NULL,
            trading_symbol VARCHAR NOT NULL,
            name VARCHAR,
            exchange VARCHAR NOT NULL,
            segment VARCHAR NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (isin, exchange, segment)
        );
    """)
    conn.execute("""
        INSERT INTO reference_equity_details (isin, trading_symbol, name, exchange, segment)
        SELECT old.isin, old.trading_symbol, old.name, old.exchange, old.segment
        FROM reference_equities AS old
        WHERE NOT EXISTS (
            SELECT 1 FROM reference_equity_details AS newer
            WHERE newer.isin = old.isin AND newer.exchange = old.exchange AND newer.segment = old.segment
        )
    """) if conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'reference_equities'").fetchone()[0] else None
    # -----------------------------
    # Upstox instruments
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_instruments (
            instrument_key VARCHAR,
            source_type VARCHAR,
            segment VARCHAR,
            name VARCHAR,
            exchange VARCHAR,
            isin VARCHAR,
            instrument_type VARCHAR,
            trading_symbol VARCHAR,
            short_name VARCHAR,
            exchange_token VARCHAR,
            expiry DATE,
            strike_price DOUBLE,
            lot_size BIGINT,
            minimum_lot BIGINT,
            freeze_quantity DOUBLE,
            tick_size DOUBLE,
            weekly BOOLEAN,
            underlying_key VARCHAR,
            underlying_symbol VARCHAR,
            underlying_type VARCHAR,
            security_type VARCHAR,
            raw_json JSON,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN source_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN segment VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN exchange VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN instrument_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN short_name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN exchange_token VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN expiry DATE;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN strike_price DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN lot_size BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN minimum_lot BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN freeze_quantity DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN tick_size DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN weekly BOOLEAN;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN underlying_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN underlying_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN underlying_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN security_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Upstox expired instruments
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_expired_instruments (
            instrument_key VARCHAR,
            segment VARCHAR,
            name VARCHAR,
            exchange VARCHAR,
            instrument_type VARCHAR,
            trading_symbol VARCHAR,
            exchange_token VARCHAR,
            expiry DATE,
            strike_price DOUBLE,
            lot_size BIGINT,
            minimum_lot BIGINT,
            freeze_quantity DOUBLE,
            tick_size DOUBLE,
            weekly BOOLEAN,
            underlying_key VARCHAR,
            underlying_symbol VARCHAR,
            underlying_type VARCHAR,
            source_type VARCHAR,
            raw_json JSON,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN segment VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN exchange VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN instrument_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN exchange_token VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN expiry DATE;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN strike_price DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN lot_size BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN minimum_lot BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN freeze_quantity DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN tick_size DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN weekly BOOLEAN;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN underlying_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN underlying_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN underlying_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN source_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_expired_contract_sync_status (
            underlying_key VARCHAR,
            expiry DATE,
            source_type VARCHAR,
            status VARCHAR DEFAULT 'success',
            record_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN underlying_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN expiry DATE;")
    safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN source_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN status VARCHAR DEFAULT 'success';")
    safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN record_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN last_error VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_expired_underlying_sync_status (
            underlying_key VARCHAR,
            status VARCHAR DEFAULT 'success',
            expiry_count BIGINT DEFAULT 0,
            record_count BIGINT DEFAULT 0,
            include_options BOOLEAN DEFAULT TRUE,
            include_futures BOOLEAN DEFAULT TRUE,
            last_error VARCHAR,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN underlying_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN status VARCHAR DEFAULT 'success';")
    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN expiry_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN record_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN include_options BOOLEAN DEFAULT TRUE;")
    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN include_futures BOOLEAN DEFAULT TRUE;")
    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN last_error VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Upstox equity instruments
    # Daily NSE_EQ equity collection table.
    # instrument_key is the Upstox API key used for all future API calls.
    # downloaded_at is refreshed only when the daily equity dump runs.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_equity_instruments (
            instrument_key VARCHAR PRIMARY KEY,
            trading_symbol VARCHAR,
            name VARCHAR,
            isin VARCHAR,
            exchange VARCHAR DEFAULT 'NSE',
            segment VARCHAR DEFAULT 'NSE_EQ',
            exchange_token VARCHAR,
            tick_size DOUBLE,
            lot_size BIGINT,
            freeze_quantity DOUBLE,
            short_name VARCHAR,
            security_type VARCHAR,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN exchange VARCHAR DEFAULT 'NSE';")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN segment VARCHAR DEFAULT 'NSE_EQ';")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN exchange_token VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN tick_size DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN lot_size BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN freeze_quantity DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN short_name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN security_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Upstox sync runs
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_sync_runs (
            sync_id VARCHAR PRIMARY KEY,
            sync_type VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'running',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            duration_seconds BIGINT,
            message VARCHAR,
            total_records BIGINT DEFAULT 0,
            trigger_source VARCHAR DEFAULT 'manual',
            triggered_by_id VARCHAR,
            triggered_by_name VARCHAR,
            triggered_by_role VARCHAR
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN sync_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN status VARCHAR DEFAULT 'running';")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN finished_at TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN duration_seconds BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN message VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN total_records BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN trigger_source VARCHAR DEFAULT 'manual';")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN triggered_by_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN triggered_by_name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN triggered_by_role VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN request_options JSON;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN selected_sources JSON;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN selected_candle_modes JSON;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN selected_intervals JSON;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN from_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN to_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN skip_existing BOOLEAN DEFAULT TRUE;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN respect_api_limits BOOLEAN DEFAULT TRUE;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN retry_failed BOOLEAN DEFAULT TRUE;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN instrument_limit BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN single_instrument_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN batch_size BIGINT DEFAULT 25;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN request_delay_ms BIGINT DEFAULT 500;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN batch_delay_seconds BIGINT DEFAULT 2;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN api_calls_attempted BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN api_calls_skipped BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN candles_inserted BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN candles_skipped BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN failed_instruments BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN last_heartbeat_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        UPDATE upstox_sync_runs
        SET last_heartbeat_at = COALESCE(last_heartbeat_at, finished_at, started_at, CURRENT_TIMESTAMP)
        WHERE last_heartbeat_at IS NULL;
    """)

    conn.execute("""
        UPDATE upstox_sync_runs
        SET trigger_source = 'manual'
        WHERE trigger_source IS NULL OR TRIM(trigger_source) = '';
    """)

    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            status = 'failed',
            finished_at = CURRENT_TIMESTAMP,
            duration_seconds = date_diff('second', started_at, CURRENT_TIMESTAMP),
            message = 'Sync run was interrupted before completion.'
        WHERE status IN ('running', 'cancel_requested');
    """)

    # -----------------------------
    # Upstox market holidays / calendar
    # Stores Upstox market holiday calendar for past and future dates.
    # Used by OHLCV sync to avoid unnecessary calls on non-trading days.
    # Upstox API:
    #   GET /v2/market/holidays
    #   GET /v2/market/holidays/{date}
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_market_holidays (
            holiday_date DATE PRIMARY KEY,
            description VARCHAR,
            holiday_type VARCHAR,
            closed_exchanges JSON,
            open_exchanges JSON,
            is_trading_day BOOLEAN DEFAULT FALSE,
            source_provider VARCHAR DEFAULT 'upstox',
            raw_json JSON,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN description VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN holiday_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN closed_exchanges JSON;")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN open_exchanges JSON;")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN is_trading_day BOOLEAN DEFAULT FALSE;")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN source_provider VARCHAR DEFAULT 'upstox';")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        UPDATE upstox_market_holidays
        SET source_provider = 'upstox'
        WHERE source_provider IS NULL OR TRIM(source_provider) = '';
    """)

    conn.execute("""
        UPDATE upstox_market_holidays
        SET is_trading_day = FALSE
        WHERE is_trading_day IS NULL;
    """)

    # -----------------------------
    # Upstox data collection schedules
    # Multiple IST schedules for current, expired, and equity instruments.
    # schedule_time is stored in 24-hour HH:MM format.
    # schedule_label is used for 12-hour display like 09:30 AM.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_data_collection_schedules (
            schedule_id VARCHAR PRIMARY KEY,
            job_type VARCHAR NOT NULL,
            schedule_time VARCHAR NOT NULL,
            schedule_label VARCHAR,
            time_format VARCHAR DEFAULT '24',
            schedule_frequency VARCHAR DEFAULT 'daily',
            timezone VARCHAR DEFAULT 'Asia/Kolkata',
            is_active BOOLEAN DEFAULT TRUE,
            last_run_date VARCHAR,
            last_run_at TIMESTAMP,
            next_run_at TIMESTAMP,
            record_status VARCHAR DEFAULT 'S',
            version_no INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN job_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN schedule_time VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN schedule_label VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN time_format VARCHAR DEFAULT '24';")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN schedule_frequency VARCHAR DEFAULT 'daily';")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN timezone VARCHAR DEFAULT 'Asia/Kolkata';")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN last_run_date VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN last_run_at TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN next_run_at TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN record_status VARCHAR DEFAULT 'S';")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN version_no INTEGER DEFAULT 1;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN created_by VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN updated_by VARCHAR;")

    conn.execute("""
        UPDATE upstox_data_collection_schedules
        SET timezone = 'Asia/Kolkata'
        WHERE timezone IS NULL OR TRIM(timezone) = '';
    """)

    conn.execute("""
        UPDATE upstox_data_collection_schedules
        SET time_format = '24'
        WHERE time_format IS NULL OR TRIM(time_format) = '';
    """)

    conn.execute("""
        UPDATE upstox_data_collection_schedules
        SET schedule_frequency = 'daily'
        WHERE schedule_frequency IS NULL OR TRIM(schedule_frequency) = '';
    """)

    conn.execute("""
        UPDATE upstox_data_collection_schedules
        SET record_status = 'S'
        WHERE record_status IS NULL;
    """)

    conn.execute("""
        UPDATE upstox_data_collection_schedules
        SET version_no = 1
        WHERE version_no IS NULL;
    """)

    # -----------------------------
    # Upstox OHLCV saved collection settings
    # Stores saved checkbox/options config for OHLCV Options, Run Saved Options, and Scheduler.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ohlcv_collection_settings (
            setting_id VARCHAR PRIMARY KEY,
            setting_name VARCHAR UNIQUE NOT NULL DEFAULT 'default',
            request_options JSON,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN setting_name VARCHAR DEFAULT 'default';")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN request_options JSON;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN created_by VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN updated_by VARCHAR;")

    conn.execute("""
        UPDATE upstox_ohlcv_collection_settings
        SET is_active = TRUE
        WHERE is_active IS NULL;
    """)

    # -----------------------------
    # Upstox OHLCV collection status
    # Tracks completed OHLCV API chunks so skip-existing can avoid repeat calls,
    # including empty successful holiday/non-trading ranges.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ohlcv_collection_status (
            provider VARCHAR DEFAULT 'upstox',
            instrument_source VARCHAR NOT NULL,
            candle_mode VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            unit VARCHAR NOT NULL,
            interval_value BIGINT NOT NULL,
            from_date DATE NOT NULL,
            to_date DATE NOT NULL,
            status VARCHAR DEFAULT 'success',
            candle_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            source_sync_id VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN instrument_source VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN candle_mode VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN instrument_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN interval_value BIGINT;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN from_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN to_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN status VARCHAR DEFAULT 'success';")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN candle_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN last_error VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN source_sync_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        UPDATE upstox_ohlcv_collection_status
        SET provider = 'upstox'
        WHERE provider IS NULL OR TRIM(provider) = '';
    """)

    # -----------------------------
    # Stocks
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            stock_id VARCHAR PRIMARY KEY,
            symbol VARCHAR UNIQUE NOT NULL,
            company_name VARCHAR,
            exchange VARCHAR,
            sector VARCHAR,
            record_status VARCHAR DEFAULT 'S',
            version_no INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE stocks ADD COLUMN record_status VARCHAR DEFAULT 'S';")
    safe_execute(conn, "ALTER TABLE stocks ADD COLUMN version_no INTEGER DEFAULT 1;")
    safe_execute(conn, "ALTER TABLE stocks ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Stock prices
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            price_id VARCHAR PRIMARY KEY,
            stock_id VARCHAR NOT NULL,
            trade_date DATE NOT NULL,
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume BIGINT,
            record_status VARCHAR DEFAULT 'S',
            version_no INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE stock_prices ADD COLUMN record_status VARCHAR DEFAULT 'S';")
    safe_execute(conn, "ALTER TABLE stock_prices ADD COLUMN version_no INTEGER DEFAULT 1;")
    safe_execute(conn, "ALTER TABLE stock_prices ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

