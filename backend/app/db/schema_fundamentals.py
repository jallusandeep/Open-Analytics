"""Schema creation for one part of the existing DuckDB database."""


def ensure_fundamentals_schema(conn, safe_execute, migrate_fii_dii_activity_table):
    # -----------------------------
    # Upstox company fundamentals
    # Complete Upstox Company Fundamentals API storage.
    # Stores every endpoint response as raw_json so no field is lost.
    # Preview/search columns are duplicated separately for fast UI tables.
    #
    # endpoint values:
    #   company_profile
    #   balance_sheet
    #   income_statement
    #   cash_flow
    #   share_holdings
    #   key_ratios
    #   corporate_actions
    #   competitors
    #
    # statement_type/time_period/include_full_statement are used for:
    #   balance_sheet, income_statement, cash_flow
    # Other endpoints keep these as NULL/false.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_company_fundamentals (
            fundamental_id VARCHAR PRIMARY KEY,
            provider VARCHAR DEFAULT 'upstox',
            isin VARCHAR NOT NULL,
            instrument_key VARCHAR,
            trading_symbol VARCHAR,
            company_name VARCHAR,
            exchange VARCHAR,
            segment VARCHAR,
            endpoint VARCHAR NOT NULL,
            endpoint_label VARCHAR,
            statement_type VARCHAR,
            time_period VARCHAR,
            include_full_statement BOOLEAN DEFAULT FALSE,
            api_status VARCHAR,
            data_status VARCHAR DEFAULT 'success',
            units_in VARCHAR,
            latest_period VARCHAR,
            period_label VARCHAR,
            report_date DATE,
            sector VARCHAR,
            company_profile TEXT,
            sector_market_cap_inr_value DOUBLE,
            sector_market_cap_inr_unit VARCHAR,
            sector_market_cap_inr_formatted VARCHAR,
            sector_market_cap_usd_value DOUBLE,
            sector_market_cap_usd_unit VARCHAR,
            sector_market_cap_usd_formatted VARCHAR,
            market_cap_inr_value DOUBLE,
            market_cap_inr_unit VARCHAR,
            market_cap_inr_formatted VARCHAR,
            market_cap_usd_value DOUBLE,
            market_cap_usd_unit VARCHAR,
            market_cap_usd_formatted VARCHAR,
            period_count BIGINT DEFAULT 0,
            item_count BIGINT DEFAULT 0,
            latest_revenue DOUBLE,
            latest_operating_profit DOUBLE,
            latest_net_profit DOUBLE,
            latest_total_asset DOUBLE,
            latest_total_liability DOUBLE,
            latest_operating_cash_flow DOUBLE,
            latest_investing_cash_flow DOUBLE,
            latest_financing_cash_flow DOUBLE,
            latest_promoter_holding_pct DOUBLE,
            latest_fii_holding_pct DOUBLE,
            latest_dii_holding_pct DOUBLE,
            latest_public_holding_pct DOUBLE,
            total_asset DOUBLE,
            total_liability DOUBLE,
            revenue DOUBLE,
            operating_profit DOUBLE,
            net_profit DOUBLE,
            net_profit_growth DOUBLE,
            operating_cash_flow DOUBLE,
            operating_cash_flow_pct_change DOUBLE,
            investing_cash_flow DOUBLE,
            investing_cash_flow_pct_change DOUBLE,
            financing_cash_flow DOUBLE,
            financing_cash_flow_pct_change DOUBLE,
            promoters_holding DOUBLE,
            fii_holding DOUBLE,
            dii_holding DOUBLE,
            public_holding DOUBLE,
            other_holding DOUBLE,
            pe_ratio_company DOUBLE,
            pe_ratio_sector DOUBLE,
            pb_ratio_company DOUBLE,
            pb_ratio_sector DOUBLE,
            roa_company DOUBLE,
            roa_sector DOUBLE,
            roe_company DOUBLE,
            roe_sector DOUBLE,
            roce_company DOUBLE,
            roce_sector DOUBLE,
            ev_ebitda_company DOUBLE,
            ev_ebitda_sector DOUBLE,
            action_type VARCHAR,
            announcement_date DATE,
            ex_date DATE,
            record_date DATE,
            action_amount DOUBLE,
            action_ratio VARCHAR,
            additional_info TEXT,
            competitor_instrument_key VARCHAR,
            competitor_isin VARCHAR,
            competitor_company_profile TEXT,
            competitor_sector VARCHAR,
            competitor_market_cap_inr_value DOUBLE,
            competitor_market_cap_inr_unit VARCHAR,
            competitor_market_cap_inr_formatted VARCHAR,
            competitor_market_cap_usd_value DOUBLE,
            competitor_market_cap_usd_unit VARCHAR,
            competitor_market_cap_usd_formatted VARCHAR,
            corporate_action_count BIGINT DEFAULT 0,
            competitor_count BIGINT DEFAULT 0,
            summary_json JSON,
            history_json JSON,
            full_statement_json JSON,
            raw_json JSON,
            raw_data_json JSON,
            source_sync_id VARCHAR,
            source_provider_version VARCHAR,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN instrument_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN company_name VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN exchange VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN segment VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN endpoint VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN endpoint_label VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN statement_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN time_period VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN include_full_statement BOOLEAN DEFAULT FALSE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN api_status VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN data_status VARCHAR DEFAULT 'success';")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN units_in VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_period VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN period_label VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN report_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN company_profile TEXT;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector_market_cap_inr_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector_market_cap_inr_unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector_market_cap_inr_formatted VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector_market_cap_usd_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector_market_cap_usd_unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector_market_cap_usd_formatted VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_inr_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_inr_unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_inr_formatted VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_usd_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_usd_unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_usd_formatted VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN period_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN item_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_revenue DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_operating_profit DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_net_profit DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_total_asset DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_total_liability DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_operating_cash_flow DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_investing_cash_flow DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_financing_cash_flow DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_promoter_holding_pct DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_fii_holding_pct DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_dii_holding_pct DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN latest_public_holding_pct DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN total_asset DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN total_liability DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN revenue DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN operating_profit DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN net_profit DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN net_profit_growth DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN operating_cash_flow DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN operating_cash_flow_pct_change DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN investing_cash_flow DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN investing_cash_flow_pct_change DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN financing_cash_flow DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN financing_cash_flow_pct_change DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN promoters_holding DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN fii_holding DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN dii_holding DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN public_holding DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN other_holding DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pe_ratio_company DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pe_ratio_sector DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pb_ratio_company DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pb_ratio_sector DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roa_company DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roa_sector DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roe_company DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roe_sector DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roce_company DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roce_sector DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN ev_ebitda_company DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN ev_ebitda_sector DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN action_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN announcement_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN ex_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN record_date DATE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN action_amount DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN action_ratio VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN additional_info TEXT;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_instrument_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_company_profile TEXT;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_sector VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_inr_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_inr_unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_inr_formatted VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_usd_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_usd_unit VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_usd_formatted VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN corporate_action_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN summary_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN history_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN full_statement_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN raw_data_json JSON;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN source_sync_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN source_provider_version VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        UPDATE upstox_company_fundamentals
        SET provider = 'upstox'
        WHERE provider IS NULL OR TRIM(provider) = '';
    """)

    conn.execute("""
        UPDATE upstox_company_fundamentals
        SET include_full_statement = FALSE
        WHERE include_full_statement IS NULL;
    """)

    conn.execute("""
        UPDATE upstox_company_fundamentals
        SET data_status = 'success'
        WHERE data_status IS NULL OR TRIM(data_status) = '';
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_isin_endpoint
        ON upstox_company_fundamentals (isin, endpoint);
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_endpoint_synced
        ON upstox_company_fundamentals (endpoint, synced_at);
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_symbol
        ON upstox_company_fundamentals (trading_symbol);
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_sync
        ON upstox_company_fundamentals (source_sync_id);
    """)

    # -----------------------------
    # Upstox company fundamentals collection status
    # Tracks checked API request groups, including empty success responses.
    # This lets the sync skip API calls that were already completed.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_company_fundamentals_sync_status (
            provider VARCHAR DEFAULT 'upstox',
            isin VARCHAR NOT NULL,
            instrument_key VARCHAR,
            trading_symbol VARCHAR,
            endpoint VARCHAR NOT NULL,
            statement_type VARCHAR,
            time_period VARCHAR,
            include_full_statement BOOLEAN DEFAULT FALSE,
            status VARCHAR DEFAULT 'success',
            record_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            source_sync_id VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN instrument_key VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN endpoint VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN statement_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN time_period VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN include_full_statement BOOLEAN DEFAULT FALSE;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN status VARCHAR DEFAULT 'success';")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN record_count BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN last_error VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN source_sync_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        UPDATE upstox_company_fundamentals_sync_status
        SET provider = 'upstox'
        WHERE provider IS NULL OR TRIM(provider) = '';
    """)

    conn.execute("""
        UPDATE upstox_company_fundamentals_sync_status
        SET include_full_statement = FALSE
        WHERE include_full_statement IS NULL;
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_isin_endpoint
        ON upstox_company_fundamentals_sync_status (isin, endpoint, status);
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_sync
        ON upstox_company_fundamentals_sync_status (source_sync_id);
    """)

    # -----------------------------
    # Fundamentals
    # Company financial data.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            instrument_key VARCHAR NOT NULL,
            isin VARCHAR NOT NULL,
            trading_symbol VARCHAR NOT NULL,
            report_date DATE NOT NULL,
            period_type VARCHAR NOT NULL,
            revenue DOUBLE,
            net_profit DOUBLE,
            eps DOUBLE,
            pe_ratio DOUBLE,
            debt_to_equity DOUBLE,
            roe DOUBLE,
            cash_from_operations DOUBLE,
            promoter_holding_pct DOUBLE,
            fii_holding_pct DOUBLE,
            dii_holding_pct DOUBLE,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (instrument_key, report_date, period_type)
        );
    """)

    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN report_date DATE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN period_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN revenue DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN net_profit DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN eps DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN pe_ratio DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN debt_to_equity DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN roe DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN cash_from_operations DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN promoter_holding_pct DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN fii_holding_pct DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN dii_holding_pct DOUBLE;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # Corporate actions
    # Dividends, splits, bonuses, and similar company actions.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS corporate_actions (
            instrument_key VARCHAR NOT NULL,
            isin VARCHAR NOT NULL,
            trading_symbol VARCHAR NOT NULL,
            action_type VARCHAR NOT NULL,
            ex_date DATE NOT NULL,
            record_date DATE,
            amount DOUBLE,
            remarks VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (instrument_key, action_type, ex_date)
        );
    """)

    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN isin VARCHAR;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN trading_symbol VARCHAR;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN action_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN ex_date DATE;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN record_date DATE;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN amount DOUBLE;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN ratio VARCHAR;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN remarks VARCHAR;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    # -----------------------------
    # FII / DII activity
    # Market-level institutional flow data.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fii_dii_activity (
            date DATE NOT NULL,
            category VARCHAR NOT NULL,
            data_type VARCHAR NOT NULL DEFAULT 'NSE_EQ|CASH',
            buy_value DOUBLE,
            sell_value DOUBLE,
            net_value DOUBLE,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, category, data_type)
        );
    """)

    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN category VARCHAR;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN data_type VARCHAR DEFAULT 'NSE_EQ|CASH';")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN buy_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN sell_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN net_value DOUBLE;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN buy_contracts BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN sell_contracts BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN oi_contracts BIGINT DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN oi_amount DOUBLE DEFAULT 0;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    migrate_fii_dii_activity_table(conn)

