# backend\app\services\data_collection\company_fundamentals_service.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def json_dumps_for_db(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None

    try:
        clean_value = str(value).replace(",", "").replace("%", "").strip()
        if not clean_value:
            return None
        return float(clean_value)
    except Exception:
        return None


def ensure_upstox_company_fundamentals_tables(conn):
    global UPSTOX_COMPANY_FUNDAMENTALS_SCHEMA_READY

    if UPSTOX_COMPANY_FUNDAMENTALS_SCHEMA_READY:
        return

    def table_exists(table_name: str) -> bool:
        row = conn.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = ?;
        """, [table_name]).fetchone()

        return bool(row and row[0])

    def get_existing_columns(table_name: str) -> set:
        rows = conn.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ?;
        """, [table_name]).fetchall()

        return {row[0] for row in rows}

    def add_column_if_missing(table_name: str, column_name: str, column_definition: str):
        existing_columns = get_existing_columns(table_name)

        if column_name in existing_columns:
            return

        conn.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_definition};
        """)

    def safe_create_index(index_sql: str):
        try:
            conn.execute(index_sql)
        except Exception as error:
            try:
                conn.rollback()
            except Exception:
                pass

            print(f"Skipped Company Fundamentals index: {error}")

    if not table_exists("upstox_company_fundamentals"):
        conn.execute("""
            CREATE TABLE upstox_company_fundamentals (
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
                raw_data_json JSON,
                raw_json JSON,
                source_sync_id VARCHAR,
                source_provider_version VARCHAR,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    company_columns = [
        ("provider", "provider VARCHAR DEFAULT 'upstox'"),
        ("isin", "isin VARCHAR"),
        ("instrument_key", "instrument_key VARCHAR"),
        ("trading_symbol", "trading_symbol VARCHAR"),
        ("company_name", "company_name VARCHAR"),
        ("exchange", "exchange VARCHAR"),
        ("segment", "segment VARCHAR"),
        ("endpoint", "endpoint VARCHAR"),
        ("endpoint_label", "endpoint_label VARCHAR"),
        ("statement_type", "statement_type VARCHAR"),
        ("time_period", "time_period VARCHAR"),
        ("include_full_statement", "include_full_statement BOOLEAN DEFAULT FALSE"),
        ("api_status", "api_status VARCHAR"),
        ("data_status", "data_status VARCHAR DEFAULT 'success'"),
        ("units_in", "units_in VARCHAR"),
        ("latest_period", "latest_period VARCHAR"),
        ("period_label", "period_label VARCHAR"),
        ("report_date", "report_date DATE"),
        ("sector", "sector VARCHAR"),
        ("company_profile", "company_profile TEXT"),
        ("sector_market_cap_inr_value", "sector_market_cap_inr_value DOUBLE"),
        ("sector_market_cap_inr_unit", "sector_market_cap_inr_unit VARCHAR"),
        ("sector_market_cap_inr_formatted", "sector_market_cap_inr_formatted VARCHAR"),
        ("sector_market_cap_usd_value", "sector_market_cap_usd_value DOUBLE"),
        ("sector_market_cap_usd_unit", "sector_market_cap_usd_unit VARCHAR"),
        ("sector_market_cap_usd_formatted", "sector_market_cap_usd_formatted VARCHAR"),
        ("market_cap_inr_value", "market_cap_inr_value DOUBLE"),
        ("market_cap_inr_unit", "market_cap_inr_unit VARCHAR"),
        ("market_cap_inr_formatted", "market_cap_inr_formatted VARCHAR"),
        ("market_cap_usd_value", "market_cap_usd_value DOUBLE"),
        ("market_cap_usd_unit", "market_cap_usd_unit VARCHAR"),
        ("market_cap_usd_formatted", "market_cap_usd_formatted VARCHAR"),
        ("period_count", "period_count BIGINT DEFAULT 0"),
        ("item_count", "item_count BIGINT DEFAULT 0"),
        ("latest_revenue", "latest_revenue DOUBLE"),
        ("latest_operating_profit", "latest_operating_profit DOUBLE"),
        ("latest_net_profit", "latest_net_profit DOUBLE"),
        ("latest_total_asset", "latest_total_asset DOUBLE"),
        ("latest_total_liability", "latest_total_liability DOUBLE"),
        ("latest_operating_cash_flow", "latest_operating_cash_flow DOUBLE"),
        ("latest_investing_cash_flow", "latest_investing_cash_flow DOUBLE"),
        ("latest_financing_cash_flow", "latest_financing_cash_flow DOUBLE"),
        ("latest_promoter_holding_pct", "latest_promoter_holding_pct DOUBLE"),
        ("latest_fii_holding_pct", "latest_fii_holding_pct DOUBLE"),
        ("latest_dii_holding_pct", "latest_dii_holding_pct DOUBLE"),
        ("latest_public_holding_pct", "latest_public_holding_pct DOUBLE"),
        ("total_asset", "total_asset DOUBLE"),
        ("total_liability", "total_liability DOUBLE"),
        ("revenue", "revenue DOUBLE"),
        ("operating_profit", "operating_profit DOUBLE"),
        ("net_profit", "net_profit DOUBLE"),
        ("net_profit_growth", "net_profit_growth DOUBLE"),
        ("operating_cash_flow", "operating_cash_flow DOUBLE"),
        ("operating_cash_flow_pct_change", "operating_cash_flow_pct_change DOUBLE"),
        ("investing_cash_flow", "investing_cash_flow DOUBLE"),
        ("investing_cash_flow_pct_change", "investing_cash_flow_pct_change DOUBLE"),
        ("financing_cash_flow", "financing_cash_flow DOUBLE"),
        ("financing_cash_flow_pct_change", "financing_cash_flow_pct_change DOUBLE"),
        ("promoters_holding", "promoters_holding DOUBLE"),
        ("fii_holding", "fii_holding DOUBLE"),
        ("dii_holding", "dii_holding DOUBLE"),
        ("public_holding", "public_holding DOUBLE"),
        ("other_holding", "other_holding DOUBLE"),
        ("pe_ratio_company", "pe_ratio_company DOUBLE"),
        ("pe_ratio_sector", "pe_ratio_sector DOUBLE"),
        ("pb_ratio_company", "pb_ratio_company DOUBLE"),
        ("pb_ratio_sector", "pb_ratio_sector DOUBLE"),
        ("roa_company", "roa_company DOUBLE"),
        ("roa_sector", "roa_sector DOUBLE"),
        ("roe_company", "roe_company DOUBLE"),
        ("roe_sector", "roe_sector DOUBLE"),
        ("roce_company", "roce_company DOUBLE"),
        ("roce_sector", "roce_sector DOUBLE"),
        ("ev_ebitda_company", "ev_ebitda_company DOUBLE"),
        ("ev_ebitda_sector", "ev_ebitda_sector DOUBLE"),
        ("action_type", "action_type VARCHAR"),
        ("announcement_date", "announcement_date DATE"),
        ("ex_date", "ex_date DATE"),
        ("record_date", "record_date DATE"),
        ("action_amount", "action_amount DOUBLE"),
        ("action_ratio", "action_ratio VARCHAR"),
        ("additional_info", "additional_info TEXT"),
        ("competitor_instrument_key", "competitor_instrument_key VARCHAR"),
        ("competitor_isin", "competitor_isin VARCHAR"),
        ("competitor_company_profile", "competitor_company_profile TEXT"),
        ("competitor_sector", "competitor_sector VARCHAR"),
        ("competitor_market_cap_inr_value", "competitor_market_cap_inr_value DOUBLE"),
        ("competitor_market_cap_inr_unit", "competitor_market_cap_inr_unit VARCHAR"),
        ("competitor_market_cap_inr_formatted", "competitor_market_cap_inr_formatted VARCHAR"),
        ("competitor_market_cap_usd_value", "competitor_market_cap_usd_value DOUBLE"),
        ("competitor_market_cap_usd_unit", "competitor_market_cap_usd_unit VARCHAR"),
        ("competitor_market_cap_usd_formatted", "competitor_market_cap_usd_formatted VARCHAR"),
        ("corporate_action_count", "corporate_action_count BIGINT DEFAULT 0"),
        ("competitor_count", "competitor_count BIGINT DEFAULT 0"),
        ("summary_json", "summary_json JSON"),
        ("history_json", "history_json JSON"),
        ("full_statement_json", "full_statement_json JSON"),
        ("raw_data_json", "raw_data_json JSON"),
        ("raw_json", "raw_json JSON"),
        ("source_sync_id", "source_sync_id VARCHAR"),
        ("source_provider_version", "source_provider_version VARCHAR"),
        ("synced_at", "synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]

    for column_name, column_definition in company_columns:
        add_column_if_missing(
            "upstox_company_fundamentals",
            column_name,
            column_definition
        )

    conn.execute("""
        UPDATE upstox_company_fundamentals
        SET
            provider = COALESCE(NULLIF(TRIM(provider), ''), 'upstox'),
            include_full_statement = COALESCE(include_full_statement, FALSE),
            data_status = COALESCE(NULLIF(TRIM(data_status), ''), 'success'),
            sector_market_cap_inr_value = COALESCE(sector_market_cap_inr_value, market_cap_inr_value),
            sector_market_cap_inr_unit = COALESCE(sector_market_cap_inr_unit, market_cap_inr_unit),
            sector_market_cap_inr_formatted = COALESCE(sector_market_cap_inr_formatted, market_cap_inr_formatted),
            sector_market_cap_usd_value = COALESCE(sector_market_cap_usd_value, market_cap_usd_value),
            sector_market_cap_usd_unit = COALESCE(sector_market_cap_usd_unit, market_cap_usd_unit),
            sector_market_cap_usd_formatted = COALESCE(sector_market_cap_usd_formatted, market_cap_usd_formatted),
            latest_revenue = COALESCE(latest_revenue, revenue),
            latest_operating_profit = COALESCE(latest_operating_profit, operating_profit),
            latest_net_profit = COALESCE(latest_net_profit, net_profit),
            latest_total_asset = COALESCE(latest_total_asset, total_asset),
            latest_total_liability = COALESCE(latest_total_liability, total_liability),
            latest_operating_cash_flow = COALESCE(latest_operating_cash_flow, operating_cash_flow),
            latest_investing_cash_flow = COALESCE(latest_investing_cash_flow, investing_cash_flow),
            latest_financing_cash_flow = COALESCE(latest_financing_cash_flow, financing_cash_flow),
            latest_promoter_holding_pct = COALESCE(latest_promoter_holding_pct, promoters_holding),
            latest_fii_holding_pct = COALESCE(latest_fii_holding_pct, fii_holding),
            latest_dii_holding_pct = COALESCE(latest_dii_holding_pct, dii_holding),
            latest_public_holding_pct = COALESCE(latest_public_holding_pct, public_holding)
        WHERE provider IS NULL
           OR TRIM(provider) = ''
           OR include_full_statement IS NULL
           OR data_status IS NULL
           OR TRIM(data_status) = ''
           OR sector_market_cap_inr_value IS NULL
           OR sector_market_cap_inr_unit IS NULL
           OR sector_market_cap_inr_formatted IS NULL
           OR sector_market_cap_usd_value IS NULL
           OR sector_market_cap_usd_unit IS NULL
           OR sector_market_cap_usd_formatted IS NULL
           OR latest_revenue IS NULL
           OR latest_operating_profit IS NULL
           OR latest_net_profit IS NULL
           OR latest_total_asset IS NULL
           OR latest_total_liability IS NULL
           OR latest_operating_cash_flow IS NULL
           OR latest_investing_cash_flow IS NULL
           OR latest_financing_cash_flow IS NULL
           OR latest_promoter_holding_pct IS NULL
           OR latest_fii_holding_pct IS NULL
           OR latest_dii_holding_pct IS NULL
           OR latest_public_holding_pct IS NULL;
    """)

    if not table_exists("upstox_company_fundamentals_sync_status"):
        conn.execute("""
            CREATE TABLE upstox_company_fundamentals_sync_status (
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
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    status_columns = [
        ("provider", "provider VARCHAR DEFAULT 'upstox'"),
        ("isin", "isin VARCHAR"),
        ("instrument_key", "instrument_key VARCHAR"),
        ("trading_symbol", "trading_symbol VARCHAR"),
        ("endpoint", "endpoint VARCHAR"),
        ("statement_type", "statement_type VARCHAR"),
        ("time_period", "time_period VARCHAR"),
        ("include_full_statement", "include_full_statement BOOLEAN DEFAULT FALSE"),
        ("status", "status VARCHAR DEFAULT 'success'"),
        ("record_count", "record_count BIGINT DEFAULT 0"),
        ("last_error", "last_error VARCHAR"),
        ("source_sync_id", "source_sync_id VARCHAR"),
        ("checked_at", "checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("synced_at", "synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]

    for column_name, column_definition in status_columns:
        add_column_if_missing(
            "upstox_company_fundamentals_sync_status",
            column_name,
            column_definition
        )

    conn.execute("""
        UPDATE upstox_company_fundamentals_sync_status
        SET
            provider = COALESCE(NULLIF(TRIM(provider), ''), 'upstox'),
            include_full_statement = COALESCE(include_full_statement, FALSE),
            status = COALESCE(NULLIF(TRIM(status), ''), 'success'),
            checked_at = COALESCE(checked_at, synced_at, updated_at, CURRENT_TIMESTAMP),
            synced_at = COALESCE(synced_at, checked_at, updated_at, CURRENT_TIMESTAMP),
            updated_at = COALESCE(updated_at, checked_at, synced_at, CURRENT_TIMESTAMP)
        WHERE provider IS NULL
           OR TRIM(provider) = ''
           OR include_full_statement IS NULL
           OR status IS NULL
           OR TRIM(status) = ''
           OR checked_at IS NULL
           OR synced_at IS NULL
           OR updated_at IS NULL;
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_lookup
        ON upstox_company_fundamentals (
            provider,
            isin,
            endpoint,
            statement_type,
            time_period,
            include_full_statement
        );
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_preview
        ON upstox_company_fundamentals (
            endpoint,
            trading_symbol,
            isin,
            synced_at
        );
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_lookup
        ON upstox_company_fundamentals_sync_status (
            provider,
            isin,
            endpoint,
            statement_type,
            time_period,
            include_full_statement,
            status
        );
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_sync
        ON upstox_company_fundamentals_sync_status (
            source_sync_id
        );
    """)

    UPSTOX_COMPANY_FUNDAMENTALS_SCHEMA_READY = True

def normalize_company_fundamentals_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    endpoints = normalize_string_list(
        payload.get("endpoints") or payload.get("selected_endpoints"),
        UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_ENDPOINTS
    )
    endpoints = [
        endpoint
        for endpoint in endpoints
        if endpoint in UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS
    ]

    statement_types = normalize_string_list(
        payload.get("statement_types") or payload.get("selected_statement_types"),
        UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES
    )
    statement_types = [
        item.lower()
        for item in statement_types
        if item.lower() in UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES
    ]

    time_periods = normalize_string_list(
        payload.get("time_periods") or payload.get("selected_time_periods"),
        UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS
    )
    time_periods = [
        item.lower()
        for item in time_periods
        if item.lower() in UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS
    ]

    if not endpoints:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one Company Fundamentals endpoint."
        )

    if not statement_types:
        statement_types = UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES.copy()

    if not time_periods:
        time_periods = UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS.copy()

    return {
        "endpoints": unique_preserve_order(endpoints),
        "statement_types": unique_preserve_order(statement_types),
        "time_periods": unique_preserve_order(time_periods),
        "include_full_statement": normalize_bool(payload.get("include_full_statement"), True),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "instrument_limit": normalize_optional_positive_int(payload.get("instrument_limit"), 1, 1000000),
        "single_isin": safe_strip(payload.get("single_isin")).upper(),
        "single_instrument_key": safe_strip(payload.get("single_instrument_key")),
        "batch_size": normalize_positive_int(
            payload.get("batch_size"),
            UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_BATCH_SIZE,
            1,
            500
        ),
        "request_delay_ms": normalize_positive_int(
            payload.get("request_delay_ms"),
            UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_REQUEST_DELAY_MS,
            0,
            60000
        ),
        "retry_count": normalize_positive_int(
            payload.get("retry_count"),
            UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_RETRY_COUNT,
            1,
            10
        )
    }


def get_default_company_fundamentals_options_payload() -> dict:
    return {
        "endpoints": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_ENDPOINTS.copy(),
        "statement_types": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES.copy(),
        "time_periods": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS.copy(),
        "include_full_statement": True,
        "skip_existing": True,
        "force_refresh": False,
        "instrument_limit": None,
        "single_isin": "",
        "single_instrument_key": "",
        "batch_size": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_BATCH_SIZE,
        "request_delay_ms": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_REQUEST_DELAY_MS,
        "retry_count": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_RETRY_COUNT
    }


def get_upstox_company_fundamentals_options_service():
    return {
        "options": get_default_company_fundamentals_options_payload(),
        "endpoints": [
            {
                "value": endpoint,
                "label": definition["label"],
                "supports_statement_type": definition["supports_statement_type"],
                "supports_time_period": definition["supports_time_period"],
                "supports_full_statement": definition["supports_full_statement"]
            }
            for endpoint, definition in UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS.items()
        ],
        "statement_types": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES.copy(),
        "time_periods": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS.copy()
    }


def fetch_company_fundamental_instruments(conn, config: dict) -> List[dict]:
    filter_params = [f"{EQUITY_STOCK_ISIN_PREFIX}%"]

    where_sql = """
    WHERE isin IS NOT NULL
      AND TRIM(isin) <> ''
      AND UPPER(COALESCE(isin, '')) LIKE ?
      AND instrument_key IS NOT NULL
      AND TRIM(instrument_key) <> ''
      AND UPPER(COALESCE(segment, '')) IN ('NSE_EQ', 'BSE_EQ')
    """

    if config.get("single_isin"):
        where_sql += " AND UPPER(isin) = ?"
        filter_params.append(config["single_isin"])

    if config.get("single_instrument_key"):
        where_sql += " AND instrument_key = ?"
        filter_params.append(config["single_instrument_key"])

    limit_sql = ""
    query_params = filter_params + filter_params

    if config.get("instrument_limit"):
        limit_sql = "LIMIT ?"
        query_params.append(config["instrument_limit"])

    rows = conn.execute(f"""
        SELECT *
        FROM (
            SELECT
                instrument_key,
                trading_symbol,
                name,
                isin,
                exchange,
                segment,
                0 AS source_rank
            FROM upstox_equity_instruments
            {where_sql}

            UNION ALL

            SELECT
                instrument_key,
                trading_symbol,
                name,
                isin,
                exchange,
                segment,
                1 AS source_rank
            FROM upstox_instruments
            {where_sql}
              AND source_type = 'bod_complete'
              AND UPPER(COALESCE(instrument_type, '')) IN ('EQ', 'EQUITY')
        )
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY UPPER(isin)
            ORDER BY source_rank, trading_symbol, instrument_key
        ) = 1
        ORDER BY trading_symbol, isin
        {limit_sql};
    """, query_params).fetchall()

    instruments = [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1],
            "name": row[2],
            "isin": str(row[3] or "").upper(),
            "exchange": row[4],
            "segment": row[5]
        }
        for row in rows
        if row and safe_strip(row[3])
    ]

    print(
        "[Company Fundamentals] Equity instruments selected "
        f"for fundamentals: {len(instruments)}"
    )

    return instruments


def company_fundamentals_status_exists(
    conn,
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool
) -> bool:
    row = conn.execute("""
        SELECT 1
        FROM upstox_company_fundamentals
        WHERE provider = ?
          AND isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?
        LIMIT 1;
    """, [
        UPSTOX_PROVIDER,
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement)
    ]).fetchone()

    if row:
        return True

    status_row = conn.execute("""
        SELECT 1
        FROM upstox_company_fundamentals_sync_status
        WHERE isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?
          AND status = 'success'
        LIMIT 1;
    """, [
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement)
    ]).fetchone()

    return bool(status_row)


def get_company_fundamentals_task_key(
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool
) -> tuple:
    return (
        safe_strip(isin).upper(),
        safe_strip(endpoint),
        safe_strip(statement_type),
        safe_strip(time_period),
        bool(include_full_statement)
    )


def build_company_fundamentals_existing_status_cache(
    conn,
    instruments: List[dict],
    tasks: List[dict]
) -> set:
    isins = unique_preserve_order([
        safe_strip(instrument.get("isin")).upper()
        for instrument in instruments
        if safe_strip(instrument.get("isin"))
    ])

    if not isins or not tasks:
        return set()

    seen_task_keys = set()
    task_keys = []

    for task in tasks:
        task_key = (
            safe_strip(task.get("endpoint")),
            safe_strip(task.get("statement_type")),
            safe_strip(task.get("time_period")),
            bool(task.get("include_full_statement"))
        )

        if task_key[0] and task_key not in seen_task_keys:
            seen_task_keys.add(task_key)
            task_keys.append(task_key)

    if not task_keys:
        return set()

    task_clauses = []
    params = [UPSTOX_PROVIDER]

    for endpoint, statement_type, time_period, include_full_statement in task_keys:
        task_clauses.append("""
            (
                endpoint = ?
                AND COALESCE(statement_type, '') = ?
                AND COALESCE(time_period, '') = ?
                AND include_full_statement = ?
            )
        """)
        params.extend([
            endpoint,
            statement_type,
            time_period,
            include_full_statement
        ])

    isin_placeholders = ", ".join(["?"] * len(isins))
    params.extend(isins)

    existing_keys = set()

    rows = conn.execute(f"""
        SELECT isin, endpoint, statement_type, time_period, include_full_statement
        FROM upstox_company_fundamentals
        WHERE provider = ?
          AND ({" OR ".join(task_clauses)})
          AND UPPER(isin) IN ({isin_placeholders});
    """, params).fetchall()

    for row in rows:
        existing_keys.add(get_company_fundamentals_task_key(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4]
        ))

    status_params = []

    for endpoint, statement_type, time_period, include_full_statement in task_keys:
        status_params.extend([
            endpoint,
            statement_type,
            time_period,
            include_full_statement
        ])

    status_params.extend(isins)

    status_rows = conn.execute(f"""
        SELECT isin, endpoint, statement_type, time_period, include_full_statement
        FROM upstox_company_fundamentals_sync_status
        WHERE status = 'success'
          AND ({" OR ".join(task_clauses)})
          AND UPPER(isin) IN ({isin_placeholders});
    """, status_params).fetchall()

    for row in status_rows:
        existing_keys.add(get_company_fundamentals_task_key(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4]
        ))

    print(
        "[Company Fundamentals] Loaded saved status cache "
        f"for {len(existing_keys)} instrument/task combinations."
    )

    return existing_keys


def build_company_fundamentals_pending_jobs(
    instruments: List[dict],
    tasks: List[dict],
    existing_status_cache: set,
    skip_existing: bool,
    force_refresh: bool
) -> tuple:
    pending_jobs = []
    skipped_existing = 0
    total_jobs = 0

    for instrument_index, instrument in enumerate(instruments, start=1):
        isin = safe_strip(instrument.get("isin")).upper()

        if not isin:
            continue

        for task in tasks:
            endpoint = task["endpoint"]
            statement_type = task.get("statement_type")
            time_period = task.get("time_period")
            include_full_statement = bool(task.get("include_full_statement"))
            total_jobs += 1

            task_key = get_company_fundamentals_task_key(
                isin=isin,
                endpoint=endpoint,
                statement_type=statement_type,
                time_period=time_period,
                include_full_statement=include_full_statement
            )

            if skip_existing and not force_refresh and task_key in existing_status_cache:
                skipped_existing += 1
                continue

            pending_jobs.append({
                "instrument_index": instrument_index,
                "instrument": instrument,
                "task": task
            })

    return pending_jobs, skipped_existing, total_jobs


def record_company_fundamentals_status(
    conn,
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool,
    status_value: str,
    record_count: int,
    sync_id: str,
    error_message: Optional[str] = None
):
    conn.execute("""
        DELETE FROM upstox_company_fundamentals_sync_status
        WHERE isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?;
    """, [
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement)
    ])

    conn.execute("""
        INSERT INTO upstox_company_fundamentals_sync_status (
            isin,
            endpoint,
            statement_type,
            time_period,
            include_full_statement,
            status,
            record_count,
            last_error,
            source_sync_id,
            synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, [
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement),
        status_value,
        int(record_count or 0),
        error_message,
        sync_id
    ])


def build_company_fundamentals_tasks(config: dict) -> List[dict]:
    tasks = []

    for endpoint in config["endpoints"]:
        definition = UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS[endpoint]

        if definition["supports_statement_type"]:
            for statement_type in config["statement_types"]:
                if definition["supports_time_period"]:
                    for time_period in config["time_periods"]:
                        tasks.append({
                            "endpoint": endpoint,
                            "statement_type": statement_type,
                            "time_period": time_period,
                            "include_full_statement": bool(config["include_full_statement"])
                        })
                else:
                    tasks.append({
                        "endpoint": endpoint,
                        "statement_type": statement_type,
                        "time_period": None,
                        "include_full_statement": bool(config["include_full_statement"])
                    })
        else:
            tasks.append({
                "endpoint": endpoint,
                "statement_type": None,
                "time_period": None,
                "include_full_statement": False
            })

    return tasks


def build_company_fundamentals_url(
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool
) -> str:
    definition = UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS[endpoint]
    encoded_isin = urllib.parse.quote(isin, safe="")
    url = f"{UPSTOX_FUNDAMENTALS_BASE_URL}/{encoded_isin}/{definition['path']}"
    params = {}

    if definition["supports_statement_type"] and statement_type:
        params["type"] = statement_type

    if definition["supports_time_period"] and time_period:
        params["time_period"] = time_period

    if definition["supports_full_statement"]:
        params["fs"] = "true" if include_full_statement else "false"

    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    return url


def upstox_company_fundamentals_http_get_json(
    url: str,
    token: str,
    timeout: int = REQUEST_TIMEOUT_SECONDS
) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {normalize_upstox_token(token)}",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8")
            return json.loads(response_text or "{}")
    except urllib.error.HTTPError as error:
        error_text = error.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=error.code,
            detail=error_text or str(error),
            headers=dict(error.headers or {})
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to call Upstox Company Fundamentals API: {error}"
        )


def fetch_company_fundamentals_with_retry(
    url: str,
    token: str,
    retry_count: int,
    rate_limiter: UpstoxRollingRateLimiter,
    heartbeat_callback: Optional[Callable[[], None]] = None
) -> dict:
    attempts = max(1, int(retry_count or 1))
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            rate_limiter.wait_for_slot(heartbeat_callback)
            return upstox_company_fundamentals_http_get_json(url=url, token=token)
        except HTTPException as error:
            last_error = error
            error_text = str(error.detail).lower()
            should_retry = (
                error.status_code in (408, 429, 500, 502, 503, 504)
                or "timeout" in error_text
                or "rate" in error_text
            )

            if not should_retry or attempt >= attempts:
                raise

            sleep_seconds = get_rate_limit_retry_sleep_seconds(
                error,
                fallback_seconds=2 * attempt
            )
            print(
                "Upstox Company Fundamentals retry "
                f"{attempt}/{attempts} after {sleep_seconds}s: {error.detail}"
            )
            sleep_with_heartbeat(sleep_seconds, heartbeat_callback)

    if last_error:
        raise last_error

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to call Upstox Company Fundamentals API."
    )


def get_history_entries_from_category_rows(rows: Any, category_name: str) -> List[dict]:
    if not isinstance(rows, list):
        return []

    for row in rows:
        if not isinstance(row, dict):
            continue

        if safe_strip(row.get("category")).lower() == category_name:
            history = row.get("history")
            return history if isinstance(history, list) else []

    return []


def first_history_value(history: Any, value_key: str = "value"):
    if isinstance(history, list) and history:
        first_row = history[0]
        if isinstance(first_row, dict):
            return first_row.get(value_key)

    return None


def first_history_period(history: Any) -> Optional[str]:
    if isinstance(history, list) and history:
        first_row = history[0]
        if isinstance(first_row, dict):
            return first_row.get("period")

    return None


def get_ratio_pair(rows: Any, ratio_name: str) -> dict:
    if not isinstance(rows, list):
        return {"company": None, "sector": None}

    normalized_ratio_name = safe_strip(ratio_name).lower().replace(" ", "").replace("/", "")

    for row in rows:
        if not isinstance(row, dict):
            continue

        normalized_name = safe_strip(row.get("name")).lower().replace(" ", "").replace("/", "")

        if normalized_name == normalized_ratio_name:
            return {
                "company": safe_float(row.get("company_value")),
                "sector": safe_float(row.get("sector_value") or row.get("sector_benchmark"))
            }

    return {"company": None, "sector": None}


def normalize_company_fundamentals_record(
    response: dict,
    instrument: dict,
    task: dict,
    sync_id: str
) -> dict:
    endpoint = task["endpoint"]
    definition = UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS[endpoint]
    data = response.get("data") if isinstance(response, dict) else None
    data_dict = data if isinstance(data, dict) else {}
    data_list = data if isinstance(data, list) else []

    history_json = None
    summary_json = data
    full_statement_json = None
    latest_period = None
    period_count = 0
    item_count = len(data_list) if isinstance(data_list, list) else 0

    if isinstance(data, dict):
        full_statement_json = data.get("full_statement")

        for key in ("history", "income_statement", "cash_flow"):
            if isinstance(data.get(key), list):
                history_json = data.get(key)
                item_count = len(data.get(key))
                break

        if isinstance(history_json, list):
            if history_json and isinstance(history_json[0], dict):
                if isinstance(history_json[0].get("history"), list):
                    latest_period = first_history_period(history_json[0].get("history"))
                    period_count = len(history_json[0].get("history"))
                else:
                    latest_period = history_json[0].get("period")
                    period_count = len(history_json)

    elif isinstance(data, list):
        history_json = data
        item_count = len(data)

        if data and isinstance(data[0], dict):
            if isinstance(data[0].get("history"), list):
                latest_period = first_history_period(data[0].get("history"))
                period_count = len(data[0].get("history"))
            else:
                latest_period = data[0].get("period")
                period_count = len(data)

    sector_market_cap_inr = data_dict.get("sector_market_cap_inr") if isinstance(data_dict, dict) else {}
    sector_market_cap_usd = data_dict.get("sector_market_cap_usd") if isinstance(data_dict, dict) else {}

    income_rows = data_dict.get("income_statement") if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_INCOME_STATEMENT else []
    cash_flow_rows = data_dict.get("cash_flow") if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CASH_FLOW else []
    balance_history = data_dict.get("history") if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_BALANCE_SHEET else []

    revenue_history = get_history_entries_from_category_rows(income_rows, "revenue")
    operating_profit_history = get_history_entries_from_category_rows(income_rows, "operating_profit")
    net_profit_history = get_history_entries_from_category_rows(income_rows, "net_profit")

    operating_cash_flow_history = get_history_entries_from_category_rows(cash_flow_rows, "operating")
    investing_cash_flow_history = get_history_entries_from_category_rows(cash_flow_rows, "investing")
    financing_cash_flow_history = get_history_entries_from_category_rows(cash_flow_rows, "financing")

    latest_balance = balance_history[0] if isinstance(balance_history, list) and balance_history and isinstance(balance_history[0], dict) else {}

    shareholding_rows = data_list if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_SHARE_HOLDINGS else []
    promoter_history = get_history_entries_from_category_rows(shareholding_rows, "promoters")
    fii_history = get_history_entries_from_category_rows(shareholding_rows, "fii")
    dii_history = get_history_entries_from_category_rows(shareholding_rows, "dii") or get_history_entries_from_category_rows(shareholding_rows, "other_dii")
    public_history = get_history_entries_from_category_rows(shareholding_rows, "public")

    ratios_rows = data_list if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_KEY_RATIOS else []
    pe_ratio = get_ratio_pair(ratios_rows, "P/E")
    pb_ratio = get_ratio_pair(ratios_rows, "P/B")
    roa_ratio = get_ratio_pair(ratios_rows, "ROA")
    roe_ratio = get_ratio_pair(ratios_rows, "ROE")
    roce_ratio = get_ratio_pair(ratios_rows, "ROCE")
    ev_ebitda_ratio = get_ratio_pair(ratios_rows, "EV/EBITDA")

    return {
        "fundamental_id": str(uuid.uuid4()),
        "provider": UPSTOX_PROVIDER,
        "isin": instrument.get("isin"),
        "instrument_key": instrument.get("instrument_key"),
        "trading_symbol": instrument.get("trading_symbol"),
        "company_name": instrument.get("name"),
        "exchange": instrument.get("exchange"),
        "segment": instrument.get("segment"),
        "endpoint": endpoint,
        "endpoint_label": definition["label"],
        "statement_type": data_dict.get("type") or task.get("statement_type"),
        "time_period": data_dict.get("time_period") or task.get("time_period"),
        "include_full_statement": bool(task.get("include_full_statement")),
        "api_status": response.get("status") if isinstance(response, dict) else None,
        "units_in": data_dict.get("units_in"),
        "latest_period": latest_period,
        "sector": data_dict.get("sector"),
        "company_profile": data_dict.get("company_profile"),
        "sector_market_cap_inr_value": safe_float(sector_market_cap_inr.get("value") if isinstance(sector_market_cap_inr, dict) else None),
        "sector_market_cap_inr_unit": sector_market_cap_inr.get("unit") if isinstance(sector_market_cap_inr, dict) else None,
        "sector_market_cap_inr_formatted": sector_market_cap_inr.get("formatted") if isinstance(sector_market_cap_inr, dict) else None,
        "sector_market_cap_usd_value": safe_float(sector_market_cap_usd.get("value") if isinstance(sector_market_cap_usd, dict) else None),
        "sector_market_cap_usd_unit": sector_market_cap_usd.get("unit") if isinstance(sector_market_cap_usd, dict) else None,
        "sector_market_cap_usd_formatted": sector_market_cap_usd.get("formatted") if isinstance(sector_market_cap_usd, dict) else None,
        "period_count": int(period_count or 0),
        "item_count": int(item_count or 0),
        "latest_revenue": safe_float(first_history_value(revenue_history)),
        "latest_operating_profit": safe_float(first_history_value(operating_profit_history)),
        "latest_net_profit": safe_float(first_history_value(net_profit_history)),
        "latest_total_asset": safe_float(latest_balance.get("total_asset")),
        "latest_total_liability": safe_float(latest_balance.get("total_liability")),
        "latest_operating_cash_flow": safe_float(first_history_value(operating_cash_flow_history)),
        "latest_investing_cash_flow": safe_float(first_history_value(investing_cash_flow_history)),
        "latest_financing_cash_flow": safe_float(first_history_value(financing_cash_flow_history)),
        "latest_promoter_holding_pct": safe_float(first_history_value(promoter_history)),
        "latest_fii_holding_pct": safe_float(first_history_value(fii_history)),
        "latest_dii_holding_pct": safe_float(first_history_value(dii_history)),
        "latest_public_holding_pct": safe_float(first_history_value(public_history)),
        "pe_ratio_company": pe_ratio["company"],
        "pe_ratio_sector": pe_ratio["sector"],
        "pb_ratio_company": pb_ratio["company"],
        "pb_ratio_sector": pb_ratio["sector"],
        "roa_company": roa_ratio["company"],
        "roa_sector": roa_ratio["sector"],
        "roe_company": roe_ratio["company"],
        "roe_sector": roe_ratio["sector"],
        "roce_company": roce_ratio["company"],
        "roce_sector": roce_ratio["sector"],
        "ev_ebitda_company": ev_ebitda_ratio["company"],
        "ev_ebitda_sector": ev_ebitda_ratio["sector"],
        "corporate_action_count": len(data_list) if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CORPORATE_ACTIONS else 0,
        "competitor_count": len(data_list) if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_COMPETITORS else 0,
        "summary_json": json_dumps_for_db(summary_json),
        "history_json": json_dumps_for_db(history_json),
        "full_statement_json": json_dumps_for_db(full_statement_json),
        "raw_data_json": json_dumps_for_db(data),
        "raw_json": json_dumps_for_db(response),
        "source_sync_id": sync_id
    }


def insert_company_fundamentals_records(conn, records: List[dict]) -> int:
    if not records:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_company_fundamentals (
            fundamental_id,
            provider,
            isin,
            instrument_key,
            trading_symbol,
            company_name,
            exchange,
            segment,
            endpoint,
            endpoint_label,
            statement_type,
            time_period,
            include_full_statement,
            api_status,
            units_in,
            latest_period,
            sector,
            company_profile,
            sector_market_cap_inr_value,
            sector_market_cap_inr_unit,
            sector_market_cap_inr_formatted,
            sector_market_cap_usd_value,
            sector_market_cap_usd_unit,
            sector_market_cap_usd_formatted,
            period_count,
            item_count,
            latest_revenue,
            latest_operating_profit,
            latest_net_profit,
            latest_total_asset,
            latest_total_liability,
            latest_operating_cash_flow,
            latest_investing_cash_flow,
            latest_financing_cash_flow,
            latest_promoter_holding_pct,
            latest_fii_holding_pct,
            latest_dii_holding_pct,
            latest_public_holding_pct,
            pe_ratio_company,
            pe_ratio_sector,
            pb_ratio_company,
            pb_ratio_sector,
            roa_company,
            roa_sector,
            roe_company,
            roe_sector,
            roce_company,
            roce_sector,
            ev_ebitda_company,
            ev_ebitda_sector,
            corporate_action_count,
            competitor_count,
            summary_json,
            history_json,
            full_statement_json,
            raw_data_json,
            raw_json,
            source_sync_id,
            synced_at,
            updated_at
        )
        SELECT
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            ?,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP;
    """, [
        (
            record.get("fundamental_id"),
            record.get("provider"),
            record.get("isin"),
            record.get("instrument_key"),
            record.get("trading_symbol"),
            record.get("company_name"),
            record.get("exchange"),
            record.get("segment"),
            record.get("endpoint"),
            record.get("endpoint_label"),
            record.get("statement_type"),
            record.get("time_period"),
            bool(record.get("include_full_statement")),
            record.get("api_status"),
            record.get("units_in"),
            record.get("latest_period"),
            record.get("sector"),
            record.get("company_profile"),
            record.get("sector_market_cap_inr_value"),
            record.get("sector_market_cap_inr_unit"),
            record.get("sector_market_cap_inr_formatted"),
            record.get("sector_market_cap_usd_value"),
            record.get("sector_market_cap_usd_unit"),
            record.get("sector_market_cap_usd_formatted"),
            record.get("period_count"),
            record.get("item_count"),
            record.get("latest_revenue"),
            record.get("latest_operating_profit"),
            record.get("latest_net_profit"),
            record.get("latest_total_asset"),
            record.get("latest_total_liability"),
            record.get("latest_operating_cash_flow"),
            record.get("latest_investing_cash_flow"),
            record.get("latest_financing_cash_flow"),
            record.get("latest_promoter_holding_pct"),
            record.get("latest_fii_holding_pct"),
            record.get("latest_dii_holding_pct"),
            record.get("latest_public_holding_pct"),
            record.get("pe_ratio_company"),
            record.get("pe_ratio_sector"),
            record.get("pb_ratio_company"),
            record.get("pb_ratio_sector"),
            record.get("roa_company"),
            record.get("roa_sector"),
            record.get("roe_company"),
            record.get("roe_sector"),
            record.get("roce_company"),
            record.get("roce_sector"),
            record.get("ev_ebitda_company"),
            record.get("ev_ebitda_sector"),
            record.get("corporate_action_count"),
            record.get("competitor_count"),
            record.get("summary_json"),
            record.get("history_json"),
            record.get("full_statement_json"),
            record.get("raw_data_json"),
            record.get("raw_json"),
            record.get("source_sync_id")
        )
        for record in records
    ])

    return len(records)


def delete_existing_company_fundamentals_record(conn, record: dict):
    conn.execute("""
        DELETE FROM upstox_company_fundamentals
        WHERE provider = ?
          AND isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?;
    """, [
        record.get("provider") or UPSTOX_PROVIDER,
        record.get("isin"),
        record.get("endpoint"),
        record.get("statement_type"),
        record.get("time_period"),
        bool(record.get("include_full_statement"))
    ])


def sync_upstox_company_fundamentals_service(
    current_user: dict,
    config: Optional[dict] = None,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0
    metrics = {
        "api_calls_attempted": 0,
        "api_calls_skipped": 0,
        "records_inserted": 0,
        "failed_items": 0
    }
    failed_items = []

    try:
        service_start_perf = time.perf_counter()
        first_api_call_logged = False

        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_company_fundamentals_tables(conn)
        normalized_config = normalize_company_fundamentals_config(
            config or get_default_company_fundamentals_options_payload()
        )
        token_candidates = []

        try:
            analytical_token = get_saved_upstox_analytical_token(conn)
        except HTTPException:
            analytical_token = ""

        try:
            access_token = get_optional_upstox_access_token(conn)
        except Exception:
            access_token = ""

        if analytical_token:
            token_candidates.append(("analytical token", analytical_token))

        if access_token and access_token != analytical_token:
            token_candidates.append(("access token", access_token))

        if not token_candidates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Upstox analytical token or access token is missing. "
                    "Save token in Connections first."
                )
            )

        instruments = fetch_company_fundamental_instruments(conn, normalized_config)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No equity instruments with ISIN were found. "
                    "Run Current Instruments or Equity Instruments first."
                )
            )

        tasks = build_company_fundamentals_tasks(normalized_config)

        sync_id = create_sync_run(
            conn,
            UPSTOX_COMPANY_FUNDAMENTALS_SYNC_TYPE,
            "running",
            "Company Fundamentals sync started.",
            current_user=current_user
        )

        rate_limiter = UpstoxRollingRateLimiter()
        existing_status_cache = (
            build_company_fundamentals_existing_status_cache(conn, instruments, tasks)
            if normalized_config["skip_existing"]
            and not normalized_config["force_refresh"]
            else set()
        )
        pending_jobs, skipped_existing_jobs, total_jobs = build_company_fundamentals_pending_jobs(
            instruments=instruments,
            tasks=tasks,
            existing_status_cache=existing_status_cache,
            skip_existing=normalized_config["skip_existing"],
            force_refresh=normalized_config["force_refresh"]
        )
        metrics["api_calls_skipped"] += skipped_existing_jobs

        print(
            "[Company Fundamentals] Starting sync "
            f"instruments={len(instruments)} tasks_per_instrument={len(tasks)} "
            f"total_jobs={total_jobs} skipped_existing={skipped_existing_jobs} "
            f"pending_api_jobs={len(pending_jobs)} endpoints={normalized_config['endpoints']}"
        )

        for pending_index, pending_job in enumerate(pending_jobs, start=1):
            check_sync_cancelled(conn, sync_id)

            if pending_index > 1 and normalized_config["batch_size"]:
                if (pending_index - 1) % normalized_config["batch_size"] == 0:
                    print(
                        "[Company Fundamentals] Batch checkpoint "
                        f"after {pending_index - 1} pending API jobs."
                    )
                    check_sync_cancelled(conn, sync_id)

            instrument_index = int(pending_job.get("instrument_index") or 0)
            instrument = pending_job["instrument"]
            task = pending_job["task"]

            isin = safe_strip(instrument.get("isin")).upper()
            trading_symbol = safe_strip(instrument.get("trading_symbol")) or "--"

            if not isin:
                continue

            endpoint = task["endpoint"]
            statement_type = task.get("statement_type")
            time_period = task.get("time_period")
            include_full_statement = bool(task.get("include_full_statement"))

            url = build_company_fundamentals_url(
                isin=isin,
                endpoint=endpoint,
                statement_type=statement_type,
                time_period=time_period,
                include_full_statement=include_full_statement
            )

            try:
                if not first_api_call_logged:
                    first_api_call_logged = True
                    print(
                        "[Company Fundamentals] First API call reached after "
                        f"{time.perf_counter() - service_start_perf:.3f}s."
                    )

                print(
                    "[Company Fundamentals] API pending "
                    f"{pending_index}/{len(pending_jobs)} "
                    f"source_instrument={instrument_index}/{len(instruments)} "
                    f"{trading_symbol} {isin} {endpoint} "
                    f"{statement_type or ''} {time_period or ''}"
                )

                response = None
                last_token_error = None

                for token_index, (token_label, candidate_token) in enumerate(token_candidates):
                    try:
                        metrics["api_calls_attempted"] += 1
                        response = fetch_company_fundamentals_with_retry(
                            url=url,
                            token=candidate_token,
                            retry_count=normalized_config["retry_count"],
                            rate_limiter=rate_limiter,
                            heartbeat_callback=lambda: check_sync_cancelled(conn, sync_id)
                        )
                        break
                    except HTTPException as token_error:
                        last_token_error = token_error

                        if is_upstox_auth_token_error(token_error) and token_index + 1 < len(token_candidates):
                            print(
                                "[Company Fundamentals] "
                                f"{token_label} failed with {token_error.status_code}; "
                                "retrying with fallback token."
                            )
                            continue

                        raise

                if response is None and last_token_error:
                    raise last_token_error

                record = normalize_company_fundamentals_record(
                    response=response,
                    instrument=instrument,
                    task=task,
                    sync_id=sync_id
                )

                conn.execute("BEGIN TRANSACTION")
                delete_existing_company_fundamentals_record(conn, record)
                inserted_count = insert_company_fundamentals_records(conn, [record])
                record_company_fundamentals_status(
                    conn=conn,
                    isin=isin,
                    endpoint=endpoint,
                    statement_type=record.get("statement_type") or statement_type,
                    time_period=record.get("time_period") or time_period,
                    include_full_statement=include_full_statement,
                    status_value="success",
                    record_count=inserted_count,
                    sync_id=sync_id,
                    error_message=None
                )
                conn.execute("COMMIT")

                total_records += inserted_count
                metrics["records_inserted"] += inserted_count

                if normalized_config["request_delay_ms"]:
                    sleep_with_heartbeat(
                        normalized_config["request_delay_ms"] / 1000,
                        lambda: check_sync_cancelled(conn, sync_id)
                    )

            except SyncCancelled:
                raise
            except HTTPException as error:
                try:
                    conn.rollback()
                except Exception:
                    pass

                if is_upstox_auth_token_error(error):
                    raise

                error_text = str(error.detail)
                failed_items.append({
                    "isin": isin,
                    "trading_symbol": trading_symbol,
                    "endpoint": endpoint,
                    "statement_type": statement_type,
                    "time_period": time_period,
                    "include_full_statement": include_full_statement,
                    "error": error_text
                })
                metrics["failed_items"] += 1

                try:
                    record_company_fundamentals_status(
                        conn=conn,
                        isin=isin,
                        endpoint=endpoint,
                        statement_type=statement_type,
                        time_period=time_period,
                        include_full_statement=include_full_statement,
                        status_value="failed",
                        record_count=0,
                        sync_id=sync_id,
                        error_message=error_text
                    )
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                print(
                    "[Company Fundamentals] API failed "
                    f"{trading_symbol} {isin} {endpoint}: {error_text}"
                )
                continue
            except Exception as error:
                try:
                    conn.rollback()
                except Exception:
                    pass

                error_text = str(error)
                failed_items.append({
                    "isin": isin,
                    "trading_symbol": trading_symbol,
                    "endpoint": endpoint,
                    "statement_type": statement_type,
                    "time_period": time_period,
                    "include_full_statement": include_full_statement,
                    "error": error_text
                })
                metrics["failed_items"] += 1

                print(
                    "[Company Fundamentals] Save/API failed "
                    f"{trading_symbol} {isin} {endpoint}: {error_text}"
                )
                continue

        all_api_calls_failed = (
            bool(failed_items)
            and metrics["api_calls_attempted"] > 0
            and metrics["records_inserted"] == 0
        )
        status_text = (
            "failed"
            if all_api_calls_failed
            else "success" if not failed_items else "partial_success"
        )
        message = "Company Fundamentals synced successfully."

        if failed_items:
            failed_file = DATA_DIR / "upstox_company_fundamentals_failed_items.json"

            with open(failed_file, "w", encoding="utf-8") as output_file:
                json.dump(failed_items, output_file, ensure_ascii=False, indent=2, default=str)

            first_error = safe_strip(failed_items[0].get("error"))
            message = (
                "Company Fundamentals sync failed. "
                f"First error: {first_error}"
                if all_api_calls_failed
                else (
                    "Company Fundamentals synced with some failed items. "
                    f"Failed items saved to {failed_file}."
                )
            )

        finish_sync_run(
            conn,
            sync_id,
            status_text,
            message,
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": status_text,
            "message": message,
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "metrics": metrics,
            "failed_items": len(failed_items)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            saved_records = safe_table_count(conn, "upstox_company_fundamentals")
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Company Fundamentals sync cancelled. Completed rows were saved.",
                total_records,
                started_at
            )
        else:
            saved_records = 0

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Company Fundamentals sync cancelled. Completed rows were saved.",
            "total_records": total_records,
            "saved_records": saved_records,
            "duration_seconds": duration_seconds(started_at),
            "metrics": metrics
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Company Fundamentals sync failed: {error.detail}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Company Fundamentals sync failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to sync Company Fundamentals: {error}"
        )

    finally:
        conn.close()


def build_company_fundamentals_preview_filters(
    search: str,
    endpoint: str,
    statement_type: str,
    time_period: str,
    segment: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_endpoint = endpoint.strip() if endpoint else "all"
    clean_statement_type = statement_type.strip() if statement_type else "all"
    clean_time_period = time_period.strip() if time_period else "all"
    clean_segment = segment.strip() if segment else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(isin, '')) LIKE ?
                OR LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(company_name, '')) LIKE ?
                OR LOWER(COALESCE(endpoint_label, '')) LIKE ?
                OR LOWER(COALESCE(sector, '')) LIKE ?
                OR LOWER(COALESCE(company_profile, '')) LIKE ?
            )
        """)
        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if clean_endpoint != "all":
        where_clauses.append("endpoint = ?")
        params.append(clean_endpoint)

    if clean_statement_type != "all":
        where_clauses.append("statement_type = ?")
        params.append(clean_statement_type)

    if clean_time_period != "all":
        where_clauses.append("time_period = ?")
        params.append(clean_time_period)

    if clean_segment != "all":
        where_clauses.append("segment = ?")
        params.append(clean_segment)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_company_fundamentals_preview(row):
    return {
        "fundamental_id": row[0],
        "isin": row[1],
        "instrument_key": row[2],
        "trading_symbol": row[3],
        "company_name": row[4],
        "exchange": row[5],
        "segment": row[6],
        "endpoint": row[7],
        "endpoint_label": row[8],
        "statement_type": row[9],
        "time_period": row[10],
        "include_full_statement": bool(row[11]),
        "api_status": row[12],
        "units_in": row[13],
        "latest_period": row[14],
        "sector": row[15],
        "company_profile": row[16],
        "sector_market_cap_inr_formatted": row[17],
        "sector_market_cap_usd_formatted": row[18],
        "period_count": row[19],
        "item_count": row[20],
        "latest_revenue": row[21],
        "latest_operating_profit": row[22],
        "latest_net_profit": row[23],
        "latest_total_asset": row[24],
        "latest_total_liability": row[25],
        "latest_operating_cash_flow": row[26],
        "latest_investing_cash_flow": row[27],
        "latest_financing_cash_flow": row[28],
        "latest_promoter_holding_pct": row[29],
        "latest_fii_holding_pct": row[30],
        "latest_dii_holding_pct": row[31],
        "latest_public_holding_pct": row[32],
        "pe_ratio_company": row[33],
        "pe_ratio_sector": row[34],
        "pb_ratio_company": row[35],
        "pb_ratio_sector": row[36],
        "roa_company": row[37],
        "roa_sector": row[38],
        "roe_company": row[39],
        "roe_sector": row[40],
        "roce_company": row[41],
        "roce_sector": row[42],
        "ev_ebitda_company": row[43],
        "ev_ebitda_sector": row[44],
        "corporate_action_count": row[45],
        "competitor_count": row[46],
        "summary_json": row[47],
        "history_json": row[48],
        "full_statement_json": row[49],
        "raw_data_json": row[50],
        "raw_json": row[51],
        "source_sync_id": row[52],
        "synced_at": str(row[53]) if row[53] else None,
        "updated_at": str(row[54]) if row[54] else None
    }


def get_upstox_company_fundamentals_preview_service(
    search: str = "",
    endpoint: str = "all",
    statement_type: str = "all",
    time_period: str = "all",
    segment: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        ensure_upstox_company_fundamentals_tables(conn)

        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_company_fundamentals_preview_filters(
            search=search,
            endpoint=endpoint,
            statement_type=statement_type,
            time_period=time_period,
            segment=segment
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_company_fundamentals
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                fundamental_id,
                isin,
                instrument_key,
                trading_symbol,
                company_name,
                exchange,
                segment,
                endpoint,
                endpoint_label,
                statement_type,
                time_period,
                include_full_statement,
                api_status,
                units_in,
                latest_period,
                sector,
                company_profile,
                sector_market_cap_inr_formatted,
                sector_market_cap_usd_formatted,
                period_count,
                item_count,
                latest_revenue,
                latest_operating_profit,
                latest_net_profit,
                latest_total_asset,
                latest_total_liability,
                latest_operating_cash_flow,
                latest_investing_cash_flow,
                latest_financing_cash_flow,
                latest_promoter_holding_pct,
                latest_fii_holding_pct,
                latest_dii_holding_pct,
                latest_public_holding_pct,
                pe_ratio_company,
                pe_ratio_sector,
                pb_ratio_company,
                pb_ratio_sector,
                roa_company,
                roa_sector,
                roe_company,
                roe_sector,
                roce_company,
                roce_sector,
                ev_ebitda_company,
                ev_ebitda_sector,
                corporate_action_count,
                competitor_count,
                CAST(COALESCE(summary_json, '{{}}') AS VARCHAR),
                CAST(COALESCE(history_json, '[]') AS VARCHAR),
                CAST(COALESCE(full_statement_json, '[]') AS VARCHAR),
                CAST(COALESCE(raw_data_json, '{{}}') AS VARCHAR),
                CAST(COALESCE(raw_json, '{{}}') AS VARCHAR),
                source_sync_id,
                synced_at,
                updated_at
            FROM upstox_company_fundamentals
            {where_sql}
            ORDER BY synced_at DESC, trading_symbol, endpoint, statement_type, time_period
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_company_fundamentals_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()
