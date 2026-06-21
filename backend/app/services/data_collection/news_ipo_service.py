# backend\app\services\data_collection\news_ipo_service.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def ensure_upstox_news_ipo_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS equity_news (
            news_id VARCHAR PRIMARY KEY,
            provider VARCHAR DEFAULT 'upstox',
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            company_name VARCHAR,
            isin VARCHAR,
            heading VARCHAR,
            title VARCHAR,
            summary TEXT,
            thumbnail VARCHAR,
            article_link VARCHAR,
            url VARCHAR,
            source VARCHAR,
            published_time_ms BIGINT,
            published_at TIMESTAMP,
            raw_json JSON,
            source_sync_id VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for column_sql in [
        "ALTER TABLE equity_news ADD COLUMN provider VARCHAR DEFAULT 'upstox';",
        "ALTER TABLE equity_news ADD COLUMN company_name VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN isin VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN heading VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN thumbnail VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN article_link VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN published_time_ms BIGINT;",
        "ALTER TABLE equity_news ADD COLUMN raw_json JSON;",
        "ALTER TABLE equity_news ADD COLUMN source_sync_id VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
    ]:
        try:
            conn.execute(column_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_equity_news_sync_status (
            provider VARCHAR DEFAULT 'upstox',
            instrument_key VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',
            record_count BIGINT DEFAULT 0,
            page_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            source_sync_id VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ipo_list (
            ipo_id VARCHAR PRIMARY KEY,
            provider VARCHAR DEFAULT 'upstox',
            symbol VARCHAR,
            name VARCHAR,
            status VARCHAR,
            isin VARCHAR,
            issue_type VARCHAR,
            issue_size DOUBLE,
            industry VARCHAR,
            minimum_price DOUBLE,
            maximum_price DOUBLE,
            bidding_start_date DATE,
            bidding_end_date DATE,
            total_subscription DOUBLE,
            raw_json JSON,
            source_sync_id VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ipo_details (
            ipo_id VARCHAR PRIMARY KEY,
            provider VARCHAR DEFAULT 'upstox',
            symbol VARCHAR,
            name VARCHAR,
            status VARCHAR,
            isin VARCHAR,
            issue_type VARCHAR,
            issue_size DOUBLE,
            industry VARCHAR,
            minimum_price DOUBLE,
            maximum_price DOUBLE,
            lot_size BIGINT,
            minimum_quantity BIGINT,
            face_value DOUBLE,
            tick_size DOUBLE,
            cut_off_price DOUBLE,
            listing_price DOUBLE,
            listing_exchange VARCHAR,
            bidding_start_date DATE,
            bidding_end_date DATE,
            daily_start_time VARCHAR,
            daily_end_time VARCHAR,
            allotment_date DATE,
            refund_date DATE,
            listing_date DATE,
            rhp_url VARCHAR,
            drhp_url VARCHAR,
            registrar_name VARCHAR,
            registrar_email VARCHAR,
            registrar_phone VARCHAR,
            total_subscription DOUBLE,
            timeline_json JSON,
            registrar_info_json JSON,
            raw_json JSON,
            source_sync_id VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ipo_sync_status (
            provider VARCHAR DEFAULT 'upstox',
            status_filter VARCHAR NOT NULL,
            issue_type_filter VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',
            record_count BIGINT DEFAULT 0,
            page_count BIGINT DEFAULT 0,
            detail_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            source_sync_id VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipo_gmp_scraper (
            ipo_name VARCHAR PRIMARY KEY,
            ipo_gmp VARCHAR,
            price_band VARCHAR,
            ipo_date VARCHAR,
            ipo_type VARCHAR,
            ipo_status VARCHAR,
            last_updated VARCHAR,
            source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/',
            raw_json JSON,
            source_sync_id VARCHAR,
            data_hash VARCHAR,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for column_sql in [
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_gmp VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN price_band VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_date VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_type VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_status VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN last_updated VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN raw_json JSON;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_sync_id VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN data_hash VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
    ]:
        try:
            conn.execute(column_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipo_gmp_scraper_snapshots (
            snapshot_id VARCHAR PRIMARY KEY,
            source_sync_id VARCHAR NOT NULL,
            ipo_name VARCHAR NOT NULL,
            ipo_gmp VARCHAR,
            price_band VARCHAR,
            ipo_date VARCHAR,
            ipo_type VARCHAR,
            ipo_status VARCHAR,
            last_updated VARCHAR,
            source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/',
            raw_json JSON,
            data_hash VARCHAR,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for column_sql in [
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN snapshot_id VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_sync_id VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_name VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_gmp VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN price_band VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_date VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_type VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_status VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN last_updated VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN raw_json JSON;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN data_hash VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
    ]:
        try:
            conn.execute(column_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    for index_sql in [
        "CREATE INDEX IF NOT EXISTS idx_equity_news_status_lookup ON upstox_equity_news_sync_status (instrument_key, status, checked_at);",
        "CREATE INDEX IF NOT EXISTS idx_equity_news_status_sync ON upstox_equity_news_sync_status (source_sync_id);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_sync_status_lookup ON upstox_ipo_sync_status (status_filter, issue_type_filter, status);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_sync_status_sync ON upstox_ipo_sync_status (source_sync_id);",
        "CREATE INDEX IF NOT EXISTS idx_upstox_ipo_list_status ON upstox_ipo_list (derived_status);",
        "CREATE INDEX IF NOT EXISTS idx_upstox_ipo_list_updated ON upstox_ipo_list (updated_at);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_status ON ipo_gmp_scraper (ipo_status);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_updated ON ipo_gmp_scraper (updated_at);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_ipo_name ON ipo_gmp_scraper_snapshots (ipo_name);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_sync ON ipo_gmp_scraper_snapshots (source_sync_id);"
    ]:
        try:
            conn.execute(index_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def get_saved_upstox_market_data_token(conn) -> str:
    row = conn.execute("""
        SELECT analytical_token, access_token, connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upstox connection is not configured.")

    if (row[2] or "saved") == "disconnected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upstox connection is disconnected.")

    analytical_token = normalize_upstox_token(row[0])
    access_token = normalize_upstox_token(row[1])

    if analytical_token:
        return analytical_token

    if access_token:
        return access_token

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upstox analytical token is missing.")


def upstox_news_ipo_http_get_json(url: str, token: str, purpose: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict:
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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to call Upstox {purpose} API: {error}")


def fetch_upstox_json_with_retry(
    url: str,
    token: str,
    retry_count: int,
    rate_limiter: UpstoxRollingRateLimiter,
    purpose: str,
    heartbeat_callback: Optional[Callable[[], None]] = None
) -> dict:
    attempts = max(1, int(retry_count or 1))
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            rate_limiter.wait_for_slot(heartbeat_callback)
            return upstox_news_ipo_http_get_json(url=url, token=token, purpose=purpose)
        except HTTPException as error:
            last_error = error
            error_text = str(error.detail).lower()
            should_retry = error.status_code in (408, 429, 500, 502, 503, 504) or "timeout" in error_text or "rate" in error_text

            if not should_retry or attempt >= attempts:
                raise

            sleep_seconds = get_rate_limit_retry_sleep_seconds(
                error,
                fallback_seconds=2 * attempt
            )
            print(
                f"Upstox {purpose} retry {attempt}/{attempts} "
                f"after {sleep_seconds}s: {error.detail}"
            )
            sleep_with_heartbeat(sleep_seconds, heartbeat_callback)

    if last_error:
        raise last_error

    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to call Upstox {purpose} API.")


def chunk_records(values: List[Any], chunk_size: int) -> List[List[Any]]:
    return [values[index:index + chunk_size] for index in range(0, len(values), chunk_size)]


def parse_upstox_epoch_ms(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None

    try:
        return datetime.fromtimestamp(int(float(value)) / 1000)
    except Exception:
        return None


def normalize_news_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    return {
        "instrument_limit": normalize_optional_positive_int(payload.get("instrument_limit"), 1, 1000000),
        "single_instrument_key": safe_strip(payload.get("single_instrument_key")),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "retry_count": normalize_positive_int(payload.get("retry_count"), UPSTOX_NEWS_DEFAULT_RETRY_COUNT, 1, 10)
    }

def normalize_equity_news_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    return {
        "batch_size": normalize_positive_int(
            payload.get("batch_size"),
            UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL,
            1,
            UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL
        ),
        "page_size": normalize_positive_int(
            payload.get("page_size"),
            UPSTOX_NEWS_MAX_PAGE_SIZE,
            1,
            UPSTOX_NEWS_MAX_PAGE_SIZE
        ),
        "retry_count": normalize_positive_int(
            payload.get("retry_count"),
            UPSTOX_NEWS_DEFAULT_RETRY_COUNT,
            1,
            10
        ),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "instrument_limit": normalize_optional_positive_int(
            payload.get("instrument_limit"),
            1,
            1000000
        ),
        "single_instrument_key": safe_strip(payload.get("single_instrument_key"))
    }

def fetch_equity_news_instruments(conn, config: dict) -> List[dict]:
    params = []
    where_sql = """
    WHERE instrument_key IS NOT NULL
      AND TRIM(instrument_key) <> ''
    """

    if config.get("single_instrument_key"):
        where_sql += " AND instrument_key = ?"
        params.append(config["single_instrument_key"])

    limit_sql = ""

    if config.get("instrument_limit"):
        limit_sql = "LIMIT ?"
        params.append(config["instrument_limit"])

    rows = conn.execute(f"""
        SELECT instrument_key, trading_symbol, name, isin, exchange, segment
        FROM upstox_equity_instruments
        {where_sql}
        ORDER BY trading_symbol, instrument_key
        {limit_sql};
    """, params).fetchall()

    return [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1],
            "name": row[2],
            "isin": row[3],
            "exchange": row[4],
            "segment": row[5]
        }
        for row in rows
        if row and safe_strip(row[0])
    ]


def build_equity_news_url(
    instrument_keys: List[str],
    page_number: int,
    page_size: int = UPSTOX_NEWS_MAX_PAGE_SIZE
) -> str:
    params = {
        "category": "instrument_keys",
        "instrument_keys": ",".join(instrument_keys),
        "page_number": int(page_number),
        "page_size": min(
            max(1, int(page_size or UPSTOX_NEWS_MAX_PAGE_SIZE)),
            UPSTOX_NEWS_MAX_PAGE_SIZE
        )
    }
    return f"{UPSTOX_EQUITY_NEWS_URL}?{urllib.parse.urlencode(params)}"


def build_upstox_equity_news_url(
    instrument_keys: List[str],
    page_number: int,
    page_size: int = UPSTOX_NEWS_MAX_PAGE_SIZE
) -> str:
    return build_equity_news_url(
        instrument_keys=instrument_keys,
        page_number=page_number,
        page_size=page_size
    )


def extract_news_response_items(response: dict) -> List[dict]:
    data = response.get("data") if isinstance(response, dict) else None

    if not isinstance(data, dict):
        return []

    rows = []

    for instrument_key, articles in data.items():
        if isinstance(articles, list):
            for article in articles:
                if isinstance(article, dict):
                    rows.append({"instrument_key": instrument_key, "article": article})

    return rows


def extract_equity_news_rows(response: dict) -> List[dict]:
    return extract_news_response_items(response)


def fetch_equity_news_with_retry(
    url: str,
    token: str,
    retry_count: int,
    rate_limiter: UpstoxRollingRateLimiter,
    heartbeat_callback: Optional[Callable[[], None]] = None
) -> dict:
    return fetch_upstox_json_with_retry(
        url=url,
        token=token,
        retry_count=retry_count,
        rate_limiter=rate_limiter,
        purpose="Equity News",
        heartbeat_callback=heartbeat_callback
    )


def should_continue_news_pagination(response: dict, page_number: int, item_count: int, page_size: int = UPSTOX_NEWS_MAX_PAGE_SIZE) -> bool:
    if item_count <= 0:
        return False

    metadata = response.get("metadata") if isinstance(response, dict) else None

    if isinstance(metadata, dict):
        page = metadata.get("page")

        if isinstance(page, dict):
            total_pages = page.get("total_pages") or page.get("totalPages")

            if total_pages is not None:
                try:
                    return page_number < int(total_pages)
                except Exception:
                    pass

    for container in (
        response.get("data") if isinstance(response, dict) else None,
        metadata,
        response
    ):
        if not isinstance(container, dict):
            continue

        total_pages = container.get("total_pages") or container.get("totalPages")

        if total_pages is not None:
            try:
                return page_number < int(total_pages)
            except Exception:
                pass

    return item_count >= min(max(1, int(page_size or UPSTOX_NEWS_MAX_PAGE_SIZE)), UPSTOX_NEWS_MAX_PAGE_SIZE)


def normalize_equity_news_record(instrument_lookup: dict, response_item: dict, sync_id: str) -> Optional[dict]:
    instrument_key = safe_strip(response_item.get("instrument_key"))
    article = response_item.get("article")

    if not instrument_key or not isinstance(article, dict):
        return None

    instrument = instrument_lookup.get(instrument_key, {})
    heading = article.get("heading") or article.get("title")
    article_link = article.get("article_link") or article.get("link") or article.get("url")
    published_time_ms = article.get("published_time") or article.get("published_at")
    published_at = parse_upstox_epoch_ms(published_time_ms)
    unique_text = f"{instrument_key}|{article_link or ''}|{published_time_ms or ''}|{heading or ''}"

    return {
        "news_id": str(uuid.uuid5(uuid.NAMESPACE_URL, unique_text)),
        "provider": UPSTOX_PROVIDER,
        "instrument_key": instrument_key,
        "trading_symbol": instrument.get("trading_symbol"),
        "company_name": instrument.get("name"),
        "isin": instrument.get("isin"),
        "heading": heading,
        "title": heading,
        "summary": article.get("summary"),
        "thumbnail": article.get("thumbnail"),
        "article_link": article_link,
        "url": article_link,
        "source": article.get("source") or article.get("publisher"),
        "published_time_ms": int(published_time_ms) if str(published_time_ms or "").isdigit() else None,
        "published_at": published_at,
        "raw_json": json_dumps_for_db(article),
        "source_sync_id": sync_id
    }


def normalize_equity_news_records(response: dict, instruments: List[dict], sync_id: str) -> List[dict]:
    instrument_lookup = {
        safe_strip(instrument.get("instrument_key")): instrument
        for instrument in instruments
        if safe_strip(instrument.get("instrument_key"))
    }

    records = []

    for response_item in extract_news_response_items(response):
        record = normalize_equity_news_record(
            instrument_lookup=instrument_lookup,
            response_item=response_item,
            sync_id=sync_id
        )

        if record:
            records.append(record)

    return records


def insert_equity_news_records(conn, records: List[dict]) -> int:
    rows_by_id = {record.get("news_id"): record for record in records if record.get("news_id")}
    rows = list(rows_by_id.values())

    if not rows:
        return 0

    conn.executemany("DELETE FROM equity_news WHERE news_id = ?;", [(row.get("news_id"),) for row in rows])

    conn.executemany("""
        INSERT INTO equity_news (
            news_id, provider, instrument_key, trading_symbol, company_name, isin,
            heading, title, summary, thumbnail, article_link, url, source,
            published_time_ms, published_at, raw_json, source_sync_id, ingested_at, updated_at
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRY_CAST(? AS JSON), ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            row.get("news_id"), row.get("provider"), row.get("instrument_key"),
            row.get("trading_symbol"), row.get("company_name"), row.get("isin"),
            row.get("heading"), row.get("title"), row.get("summary"), row.get("thumbnail"),
            row.get("article_link"), row.get("url"), row.get("source"),
            row.get("published_time_ms"), row.get("published_at"), row.get("raw_json"),
            row.get("source_sync_id")
        )
        for row in rows
    ])

    return len(rows)


def record_equity_news_status(conn, instrument_key: str, status_value: str, record_count: int, page_count: int, sync_id: str, error_message: Optional[str] = None):
    conn.execute("DELETE FROM upstox_equity_news_sync_status WHERE instrument_key = ?;", [instrument_key])
    conn.execute("""
        INSERT INTO upstox_equity_news_sync_status (
            provider, instrument_key, status, record_count, page_count, last_error,
            source_sync_id, checked_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """, [UPSTOX_PROVIDER, instrument_key, status_value, int(record_count or 0), int(page_count or 0), error_message, sync_id])


def record_equity_news_sync_status(
    conn,
    instrument_keys: List[str],
    status_value: str,
    record_count: int,
    sync_id: str,
    error_message: Optional[str] = None,
    page_count: int = 1
):
    clean_keys = [
        safe_strip(instrument_key)
        for instrument_key in instrument_keys
        if safe_strip(instrument_key)
    ]

    if not clean_keys:
        return

    per_instrument_count = int(record_count or 0)

    for instrument_key in clean_keys:
        record_equity_news_status(
            conn=conn,
            instrument_key=instrument_key,
            status_value=status_value,
            record_count=per_instrument_count,
            page_count=page_count,
            sync_id=sync_id,
            error_message=error_message
        )


def equity_news_batch_recently_checked(conn, instrument_keys: List[str]) -> bool:
    clean_keys = [
        safe_strip(instrument_key)
        for instrument_key in instrument_keys
        if safe_strip(instrument_key)
    ]

    if not clean_keys:
        return False

    placeholders = ", ".join(["?"] * len(clean_keys))

    try:
        row = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_equity_news_sync_status
            WHERE instrument_key IN ({placeholders})
              AND status = 'success'
              AND checked_at >= CURRENT_TIMESTAMP - INTERVAL '1 day';
        """, clean_keys).fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

    return bool(row and int(row[0] or 0) >= len(clean_keys))


def build_equity_news_recent_status_cache(conn, instruments: List[dict]) -> set:
    instrument_keys = unique_preserve_order([
        safe_strip(instrument.get("instrument_key"))
        for instrument in instruments
        if safe_strip(instrument.get("instrument_key"))
    ])

    if not instrument_keys:
        return set()

    placeholders = ", ".join(["?"] * len(instrument_keys))

    try:
        rows = conn.execute(f"""
            SELECT instrument_key
            FROM upstox_equity_news_sync_status
            WHERE instrument_key IN ({placeholders})
              AND status = 'success'
              AND checked_at >= CURRENT_TIMESTAMP - INTERVAL '1 day';
        """, instrument_keys).fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return set()

    return {
        safe_strip(row[0])
        for row in rows
        if row and safe_strip(row[0])
    }


def fetch_equity_news_instruments(conn, config: Optional[dict] = None) -> List[dict]:
    config = config or {}

    instrument_limit = normalize_optional_positive_int(
        config.get("instrument_limit"),
        1,
        1000000
    )
    single_instrument_key = safe_strip(config.get("single_instrument_key"))

    params = []
    limit_sql = ""

    if single_instrument_key:
        single_filter_sql = " AND instrument_key = ?"
        params.append(single_instrument_key)
    else:
        single_filter_sql = ""

    if instrument_limit:
        limit_sql = "LIMIT ?"

    final_params = params + params

    if instrument_limit:
        final_params.append(instrument_limit)

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
            WHERE instrument_key IS NOT NULL
              AND TRIM(instrument_key) <> ''
              AND UPPER(COALESCE(isin, '')) LIKE '{EQUITY_STOCK_ISIN_PREFIX}%'
              {single_filter_sql}

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
            WHERE instrument_key IS NOT NULL
              AND TRIM(instrument_key) <> ''
              AND UPPER(COALESCE(isin, '')) LIKE '{EQUITY_STOCK_ISIN_PREFIX}%'
              AND source_type = 'bod_complete'
              AND UPPER(COALESCE(segment, '')) IN ('NSE_EQ', 'BSE_EQ')
              AND UPPER(COALESCE(instrument_type, '')) IN ('EQ', 'EQUITY')
              {single_filter_sql}
        )
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY instrument_key
            ORDER BY source_rank, trading_symbol, instrument_key
        ) = 1
        ORDER BY trading_symbol, instrument_key
        {limit_sql};
    """, final_params).fetchall()

    return [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1],
            "name": row[2],
            "isin": row[3],
            "exchange": row[4],
            "segment": row[5]
        }
        for row in rows
        if row and safe_strip(row[0])
    ]

def sync_upstox_equity_news_service(
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
    service_start_perf = time.perf_counter()
    first_api_call_logged = False

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_news_ipo_tables(conn)

        normalized_config = normalize_equity_news_config(config or {})

        analytical_token = ""
        access_token = ""

        try:
            analytical_token = get_saved_upstox_analytical_token(conn)
        except HTTPException:
            analytical_token = ""

        try:
            access_token = get_optional_upstox_access_token(conn)
        except Exception:
            access_token = ""

        token_candidates = []

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

        instruments = fetch_equity_news_instruments(conn, normalized_config)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No equity instruments found. Run Current Instruments first, "
                    "then run Equity News again."
                )
            )

        sync_id = create_sync_run(
            conn,
            "upstox_equity_news",
            "running",
            "Equity News sync started.",
            current_user=current_user
        )

        rate_limiter = UpstoxRollingRateLimiter()

        batch_size = min(
            int(
                normalized_config.get("batch_size")
                or UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL
            ),
            UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL
        )
        page_size = min(
            int(
                normalized_config.get("page_size")
                or UPSTOX_NEWS_MAX_PAGE_SIZE
            ),
            UPSTOX_NEWS_MAX_PAGE_SIZE
        )
        retry_count = int(normalized_config.get("retry_count") or 3)
        force_refresh = bool(normalized_config.get("force_refresh", False))
        skip_existing = bool(normalized_config.get("skip_existing", True))
        recent_status_cache = (
            build_equity_news_recent_status_cache(conn, instruments)
            if skip_existing and not force_refresh
            else set()
        )

        print(
            "[Equity News] Starting sync "
            f"instruments={len(instruments)} "
            f"batch_size={batch_size} "
            f"page_size={page_size}"
        )

        for batch_start in range(0, len(instruments), batch_size):
            check_sync_cancelled(conn, sync_id)

            batch = instruments[batch_start:batch_start + batch_size]
            instrument_keys = [
                safe_strip(instrument.get("instrument_key"))
                for instrument in batch
                if safe_strip(instrument.get("instrument_key"))
            ]

            if not instrument_keys:
                continue

            if (
                skip_existing
                and not force_refresh
                and instrument_keys
                and all(instrument_key in recent_status_cache for instrument_key in instrument_keys)
            ):
                metrics["api_calls_skipped"] += 1
                print(
                    "[Equity News] Skipped batch because all instruments were "
                    "recently checked."
                )
                continue

            page_number = 1

            while page_number <= UPSTOX_NEWS_MAX_PAGE_NUMBER:
                check_sync_cancelled(conn, sync_id)

                url = build_upstox_equity_news_url(
                    instrument_keys=instrument_keys,
                    page_number=page_number,
                    page_size=page_size
                )

                try:
                    if not first_api_call_logged:
                        first_api_call_logged = True
                        print(
                            "[Equity News] First API call reached after "
                            f"{time.perf_counter() - service_start_perf:.3f}s."
                        )

                    print(
                        "[Equity News] API batch "
                        f"{batch_start + 1}-{batch_start + len(batch)} "
                        f"of {len(instruments)}, page={page_number}"
                    )

                    response = None
                    last_token_error = None

                    for token_index, (token_label, candidate_token) in enumerate(token_candidates):
                        try:
                            metrics["api_calls_attempted"] += 1
                            response = fetch_equity_news_with_retry(
                                url=url,
                                token=candidate_token,
                                retry_count=retry_count,
                                rate_limiter=rate_limiter,
                                heartbeat_callback=lambda: check_sync_cancelled(conn, sync_id)
                            )
                            break
                        except HTTPException as token_error:
                            last_token_error = token_error

                            if token_error.status_code in (401, 403) and token_index + 1 < len(token_candidates):
                                print(
                                    "[Equity News] "
                                    f"{token_label} failed with {token_error.status_code}; "
                                    "retrying with fallback token."
                                )
                                continue

                            raise

                    if response is None and last_token_error:
                        raise last_token_error

                    records = normalize_equity_news_records(
                        response=response,
                        instruments=batch,
                        sync_id=sync_id
                    )

                    conn.execute("BEGIN TRANSACTION")

                    inserted_count = insert_equity_news_records(conn, records)

                    record_equity_news_sync_status(
                        conn=conn,
                        instrument_keys=instrument_keys,
                        status_value="success",
                        record_count=inserted_count,
                        sync_id=sync_id,
                        error_message=None
                    )

                    conn.execute("COMMIT")

                    total_records += inserted_count
                    metrics["records_inserted"] += inserted_count

                    print(
                        "[Equity News] Saved "
                        f"{inserted_count} rows for page={page_number}. "
                        f"Total saved={total_records}."
                    )

                    extracted_rows = extract_equity_news_rows(response)
                    has_more_pages = should_continue_news_pagination(
                        response=response,
                        page_number=page_number,
                        item_count=len(extracted_rows),
                        page_size=page_size
                    )

                    if not has_more_pages:
                        break

                    page_number += 1

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
                        "instrument_keys": instrument_keys,
                        "page_number": page_number,
                        "error": error_text
                    })
                    metrics["failed_items"] += 1

                    try:
                        record_equity_news_sync_status(
                            conn=conn,
                            instrument_keys=instrument_keys,
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
                        "[Equity News] API failed "
                        f"batch={batch_start + 1}-{batch_start + len(batch)} "
                        f"page={page_number}: {error_text}"
                    )
                    break

                except Exception as error:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                    error_text = str(error)
                    failed_items.append({
                        "instrument_keys": instrument_keys,
                        "page_number": page_number,
                        "error": error_text
                    })
                    metrics["failed_items"] += 1

                    print(
                        "[Equity News] Save/API failed "
                        f"batch={batch_start + 1}-{batch_start + len(batch)} "
                        f"page={page_number}: {error_text}"
                    )
                    break

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
        message = "Equity News synced successfully."

        if failed_items:
            failed_file = DATA_DIR / "upstox_equity_news_failed_items.json"

            with open(failed_file, "w", encoding="utf-8") as output_file:
                json.dump(
                    failed_items,
                    output_file,
                    ensure_ascii=False,
                    indent=2,
                    default=str
                )

            first_error = safe_strip(failed_items[0].get("error"))
            message = (
                "Equity News sync failed. "
                f"First error: {first_error}"
                if all_api_calls_failed
                else (
                    "Equity News synced with some failed batches. "
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
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Equity News sync cancelled. Completed rows were saved.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Equity News sync cancelled. Completed rows were saved.",
            "total_records": total_records,
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
                f"Equity News sync failed: {error.detail}",
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
                f"Equity News sync failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to sync Equity News: {error}"
        )

    finally:
        conn.close()


def normalize_ipo_config(payload: Optional[dict]) -> dict:
    payload = payload or {}
    statuses = normalize_string_list(payload.get("statuses") or payload.get("selected_statuses"), UPSTOX_IPO_DEFAULT_STATUSES)
    issue_types = normalize_string_list(payload.get("issue_types") or payload.get("selected_issue_types"), UPSTOX_IPO_DEFAULT_ISSUE_TYPES)

    return {
        "statuses": unique_preserve_order([item.lower() for item in statuses if item.lower() in UPSTOX_IPO_DEFAULT_STATUSES]) or UPSTOX_IPO_DEFAULT_STATUSES.copy(),
        "issue_types": unique_preserve_order([item.lower() for item in issue_types if item.lower() in UPSTOX_IPO_DEFAULT_ISSUE_TYPES]) or UPSTOX_IPO_DEFAULT_ISSUE_TYPES.copy(),
        "include_details": normalize_bool(payload.get("include_details"), True),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "retry_count": normalize_positive_int(payload.get("retry_count"), UPSTOX_IPO_DEFAULT_RETRY_COUNT, 1, 10)
    }


def build_ipo_list_url(status_filter: str, issue_type_filter: str, page_number: int) -> str:
    params = {"status": status_filter, "issue_type": issue_type_filter, "page_number": int(page_number), "records": UPSTOX_IPO_MAX_RECORDS_PER_CALL}
    return f"{UPSTOX_IPO_LIST_URL}?{urllib.parse.urlencode(params)}"


def build_ipo_detail_url(ipo_id: str) -> str:
    return UPSTOX_IPO_DETAIL_URL.format(ipo_id=urllib.parse.quote(str(ipo_id), safe=""))


def build_ipo_completed_status_index(conn, config: dict) -> set:
    if not config.get("skip_existing") or config.get("force_refresh"):
        return set()

    statuses = [
        safe_strip(status_filter).lower()
        for status_filter in config.get("statuses", [])
        if safe_strip(status_filter).lower() in ("closed", "listed")
    ]
    issue_types = [
        safe_strip(issue_type_filter).lower()
        for issue_type_filter in config.get("issue_types", [])
        if safe_strip(issue_type_filter)
    ]

    statuses = unique_preserve_order(statuses)
    issue_types = unique_preserve_order(issue_types)

    if not statuses or not issue_types:
        return set()

    status_placeholders = ", ".join(["?"] * len(statuses))
    issue_type_placeholders = ", ".join(["?"] * len(issue_types))

    rows = conn.execute(f"""
        SELECT status_filter, issue_type_filter
        FROM upstox_ipo_sync_status
        WHERE status = 'success'
          AND LOWER(status_filter) IN ({status_placeholders})
          AND LOWER(issue_type_filter) IN ({issue_type_placeholders});
    """, [
        *statuses,
        *issue_types
    ]).fetchall()

    status_index = {
        (
            safe_strip(row[0]).lower(),
            safe_strip(row[1]).lower()
        )
        for row in rows
        if row and safe_strip(row[0]) and safe_strip(row[1])
    }

    print(
        "[IPO Calendar] Bulk indexed DB check loaded "
        f"{len(status_index)} completed status/issue groups."
    )

    return status_index


def extract_ipo_list_rows(response: dict) -> List[dict]:
    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, dict):
        for key in ("ipos", "ipo", "data"):
            if isinstance(data.get(key), list):
                return data.get(key)
    if isinstance(data, list):
        return data
    return response.get("ipos") if isinstance(response, dict) and isinstance(response.get("ipos"), list) else []


def should_continue_ipo_pagination(response: dict, page_number: int, item_count: int) -> bool:
    if item_count <= 0:
        return False

    data = response.get("data") if isinstance(response, dict) else {}
    meta_data = response.get("meta_data") if isinstance(response, dict) else {}
    metadata = response.get("metadata") if isinstance(response, dict) else {}

    page_containers = []

    for metadata_container in (meta_data, metadata):
        if isinstance(metadata_container, dict) and isinstance(metadata_container.get("page"), dict):
            page_containers.append(metadata_container.get("page"))

    for container in page_containers + [data, meta_data, metadata, response]:
        if not isinstance(container, dict):
            continue
        total_pages = container.get("total_pages") or container.get("totalPages")
        if total_pages is not None:
            try:
                return page_number < int(total_pages)
            except Exception:
                pass
        total = container.get("total")
        if total is not None:
            try:
                return page_number * UPSTOX_IPO_MAX_RECORDS_PER_CALL < int(total)
            except Exception:
                pass

    return item_count >= UPSTOX_IPO_MAX_RECORDS_PER_CALL


def extract_ipo_detail_record(response: dict) -> Optional[dict]:
    data = response.get("data") if isinstance(response, dict) else None

    if isinstance(data, dict):
        return data

    return response if isinstance(response, dict) else None


def normalize_ipo_date(value: Any) -> Optional[str]:
    return normalize_expiry_value(value)


def normalize_ipo_list_record(record: dict, sync_id: str) -> Optional[dict]:
    if not isinstance(record, dict):
        return None

    ipo_id = safe_strip(record.get("id") or record.get("ipo_id"))
    if not ipo_id:
        return None

    return {
        "ipo_id": ipo_id,
        "provider": UPSTOX_PROVIDER,
        "symbol": record.get("symbol"),
        "name": record.get("name"),
        "status": record.get("status"),
        "isin": record.get("isin"),
        "issue_type": record.get("issue_type"),
        "issue_size": safe_float(record.get("issue_size")),
        "industry": record.get("industry") or record.get("company_sector"),
        "minimum_price": safe_float(record.get("minimum_price") or record.get("price_band_min")),
        "maximum_price": safe_float(record.get("maximum_price") or record.get("price_band_max")),
        "bidding_start_date": normalize_ipo_date(record.get("bidding_start_date") or record.get("open_date")),
        "bidding_end_date": normalize_ipo_date(record.get("bidding_end_date") or record.get("close_date")),
        "total_subscription": safe_float(record.get("total_subscription")),
        "raw_json": json_dumps_for_db(record),
        "source_sync_id": sync_id
    }


def normalize_ipo_detail_record(record: dict, sync_id: str) -> Optional[dict]:
    if not isinstance(record, dict):
        return None

    ipo_id = safe_strip(record.get("id") or record.get("ipo_id"))
    if not ipo_id:
        return None

    timeline = record.get("timeline") if isinstance(record.get("timeline"), dict) else {}
    registrar_info = record.get("registrar_info") if isinstance(record.get("registrar_info"), dict) else {}

    return {
        "ipo_id": ipo_id,
        "provider": UPSTOX_PROVIDER,
        "symbol": record.get("symbol"),
        "name": record.get("name"),
        "status": record.get("status"),
        "isin": record.get("isin"),
        "issue_type": record.get("issue_type"),
        "issue_size": safe_float(record.get("issue_size")),
        "industry": record.get("industry") or record.get("company_sector"),
        "minimum_price": safe_float(record.get("minimum_price") or record.get("price_band_min")),
        "maximum_price": safe_float(record.get("maximum_price") or record.get("price_band_max")),
        "lot_size": normalize_optional_positive_int(record.get("lot_size"), 1, 1000000000),
        "minimum_quantity": normalize_optional_positive_int(record.get("minimum_quantity"), 1, 1000000000),
        "face_value": safe_float(record.get("face_value")),
        "tick_size": safe_float(record.get("tick_size")),
        "cut_off_price": safe_float(record.get("cut_off_price")),
        "listing_price": safe_float(record.get("listing_price")),
        "listing_exchange": record.get("listing_exchange"),
        "bidding_start_date": normalize_ipo_date(record.get("bidding_start_date") or timeline.get("application_start_date")),
        "bidding_end_date": normalize_ipo_date(record.get("bidding_end_date") or timeline.get("application_end_date")),
        "daily_start_time": record.get("daily_start_time"),
        "daily_end_time": record.get("daily_end_time"),
        "allotment_date": normalize_ipo_date(timeline.get("allotment_date") or record.get("allotment_date")),
        "refund_date": normalize_ipo_date(timeline.get("refund_initiation_date") or record.get("refund_date")),
        "listing_date": normalize_ipo_date(timeline.get("listing_date") or record.get("listing_date")),
        "rhp_url": record.get("rhp_url"),
        "drhp_url": record.get("drhp_url"),
        "registrar_name": registrar_info.get("name") or registrar_info.get("registrar"),
        "registrar_email": registrar_info.get("email"),
        "registrar_phone": registrar_info.get("contact_number") or registrar_info.get("phone"),
        "total_subscription": safe_float(record.get("total_subscription")),
        "timeline_json": json_dumps_for_db(timeline),
        "registrar_info_json": json_dumps_for_db(registrar_info),
        "raw_json": json_dumps_for_db(record),
        "source_sync_id": sync_id
    }


def insert_ipo_list_records(conn, records: List[dict]) -> int:
    rows = list({record.get("ipo_id"): record for record in records if record.get("ipo_id")}.values())
    if not rows:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_ipo_list (
            ipo_id, provider, symbol, name, status, isin, issue_type, issue_size,
            industry, minimum_price, maximum_price, bidding_start_date, bidding_end_date,
            total_subscription, raw_json, source_sync_id, ingested_at, updated_at
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRY_CAST(? AS DATE), TRY_CAST(? AS DATE), ?, TRY_CAST(? AS JSON), ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            row.get("ipo_id"), row.get("provider"), row.get("symbol"), row.get("name"),
            row.get("status"), row.get("isin"), row.get("issue_type"), row.get("issue_size"),
            row.get("industry"), row.get("minimum_price"), row.get("maximum_price"),
            row.get("bidding_start_date"), row.get("bidding_end_date"), row.get("total_subscription"),
            row.get("raw_json"), row.get("source_sync_id")
        )
        for row in rows
    ])
    return len(rows)


def insert_ipo_detail_records(conn, records: List[dict]) -> int:
    rows = list({record.get("ipo_id"): record for record in records if record.get("ipo_id")}.values())
    if not rows:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_ipo_details (
            ipo_id, provider, symbol, name, status, isin, issue_type, issue_size,
            industry, minimum_price, maximum_price, lot_size, minimum_quantity,
            face_value, tick_size, cut_off_price, listing_price, listing_exchange,
            bidding_start_date, bidding_end_date, daily_start_time, daily_end_time,
            allotment_date, refund_date, listing_date, rhp_url, drhp_url,
            registrar_name, registrar_email, registrar_phone, total_subscription,
            timeline_json, registrar_info_json, raw_json, source_sync_id,
            ingested_at, updated_at
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
               TRY_CAST(? AS DATE), TRY_CAST(? AS DATE), ?, ?,
               TRY_CAST(? AS DATE), TRY_CAST(? AS DATE), TRY_CAST(? AS DATE),
               ?, ?, ?, ?, ?, ?, TRY_CAST(? AS JSON), TRY_CAST(? AS JSON),
               TRY_CAST(? AS JSON), ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            row.get("ipo_id"), row.get("provider"), row.get("symbol"), row.get("name"),
            row.get("status"), row.get("isin"), row.get("issue_type"), row.get("issue_size"),
            row.get("industry"), row.get("minimum_price"), row.get("maximum_price"),
            row.get("lot_size"), row.get("minimum_quantity"), row.get("face_value"),
            row.get("tick_size"), row.get("cut_off_price"), row.get("listing_price"),
            row.get("listing_exchange"), row.get("bidding_start_date"), row.get("bidding_end_date"),
            row.get("daily_start_time"), row.get("daily_end_time"), row.get("allotment_date"),
            row.get("refund_date"), row.get("listing_date"), row.get("rhp_url"), row.get("drhp_url"),
            row.get("registrar_name"), row.get("registrar_email"), row.get("registrar_phone"),
            row.get("total_subscription"), row.get("timeline_json"), row.get("registrar_info_json"),
            row.get("raw_json"), row.get("source_sync_id")
        )
        for row in rows
    ])

    return len(rows)


def refresh_ipo_calendar_statuses(conn):
    conn.execute("""
        UPDATE upstox_ipo_details
        SET status = derived.next_status,
            updated_at = CURRENT_TIMESTAMP
        FROM (
            SELECT
                ipo_id,
                CASE
                    WHEN LOWER(COALESCE(status, '')) = 'listed'
                         OR listing_date <= CURRENT_DATE THEN 'listed'
                    WHEN bidding_start_date IS NOT NULL
                         AND CURRENT_DATE < bidding_start_date THEN 'upcoming'
                    WHEN bidding_start_date IS NOT NULL
                         AND bidding_end_date IS NOT NULL
                         AND CURRENT_DATE BETWEEN bidding_start_date AND bidding_end_date THEN 'open'
                    WHEN bidding_end_date IS NOT NULL
                         AND CURRENT_DATE > bidding_end_date THEN 'closed'
                    ELSE LOWER(COALESCE(status, 'upcoming'))
                END AS next_status
            FROM upstox_ipo_details
        ) derived
        WHERE upstox_ipo_details.ipo_id = derived.ipo_id
          AND COALESCE(LOWER(upstox_ipo_details.status), '') <> derived.next_status;
    """)

    conn.execute("""
        UPDATE upstox_ipo_list
        SET status = derived.next_status,
            updated_at = CURRENT_TIMESTAMP
        FROM (
            SELECT
                ipo_id,
                CASE
                    WHEN LOWER(COALESCE(status, '')) = 'listed' THEN 'listed'
                    WHEN bidding_start_date IS NOT NULL
                         AND CURRENT_DATE < bidding_start_date THEN 'upcoming'
                    WHEN bidding_start_date IS NOT NULL
                         AND bidding_end_date IS NOT NULL
                         AND CURRENT_DATE BETWEEN bidding_start_date AND bidding_end_date THEN 'open'
                    WHEN bidding_end_date IS NOT NULL
                         AND CURRENT_DATE > bidding_end_date THEN 'closed'
                    ELSE LOWER(COALESCE(status, 'upcoming'))
                END AS next_status
            FROM upstox_ipo_list
        ) derived
        WHERE upstox_ipo_list.ipo_id = derived.ipo_id
          AND COALESCE(LOWER(upstox_ipo_list.status), '') <> derived.next_status;
    """)


def sync_upstox_ipo_calendar_service(current_user: dict, config: Optional[dict] = None, clear_cancel_at_start: bool = True):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0
    metrics = {
        "api_calls_attempted": 0,
        "api_calls_skipped": 0,
        "list_records_saved": 0,
        "detail_records_saved": 0,
        "failed_groups": 0
    }

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_news_ipo_tables(conn)
        normalized_config = normalize_ipo_config(config)
        token = get_saved_upstox_access_token(conn)
        sync_id = create_sync_run(conn, UPSTOX_IPO_SYNC_TYPE, "running", "IPO Calendar sync started.", current_user=current_user)
        rate_limiter = UpstoxRollingRateLimiter()
        completed_status_index = build_ipo_completed_status_index(conn, normalized_config)

        for status_filter in normalized_config["statuses"]:
            for issue_type_filter in normalized_config["issue_types"]:
                check_sync_cancelled(conn, sync_id)

                if (
                    normalized_config["skip_existing"]
                    and not normalized_config["force_refresh"]
                    and status_filter in ("closed", "listed")
                    and (status_filter.lower(), issue_type_filter.lower()) in completed_status_index
                ):
                    metrics["api_calls_skipped"] += 1
                    continue

                page_number = 1
                page_count = 0
                group_count = 0
                detail_count = 0

                try:
                    while True:
                        check_sync_cancelled(conn, sync_id)
                        response = fetch_upstox_json_with_retry(
                            url=build_ipo_list_url(status_filter, issue_type_filter, page_number),
                            token=token,
                            retry_count=normalized_config["retry_count"],
                            rate_limiter=rate_limiter,
                            purpose="IPO",
                            heartbeat_callback=lambda: check_sync_cancelled(conn, sync_id)
                        )
                        metrics["api_calls_attempted"] += 1
                        page_count += 1
                        response_rows = extract_ipo_list_rows(response)
                        records = [record for record in (normalize_ipo_list_record(item, sync_id) for item in response_rows) if record]

                        conn.execute("BEGIN TRANSACTION")
                        saved_count = insert_ipo_list_records(conn, records)
                        conn.execute("COMMIT")

                        total_records += saved_count
                        group_count += saved_count
                        metrics["list_records_saved"] += saved_count

                        if normalized_config["include_details"] and records:
                            detail_records = []

                            for record in records:
                                check_sync_cancelled(conn, sync_id)
                                ipo_id = record.get("ipo_id")

                                if not ipo_id:
                                    continue

                                detail_response = fetch_upstox_json_with_retry(
                                    url=build_ipo_detail_url(ipo_id),
                                    token=token,
                                    retry_count=normalized_config["retry_count"],
                                    rate_limiter=rate_limiter,
                                    purpose="IPO Detail",
                                    heartbeat_callback=lambda: check_sync_cancelled(conn, sync_id)
                                )
                                metrics["api_calls_attempted"] += 1

                                detail_record = normalize_ipo_detail_record(
                                    extract_ipo_detail_record(detail_response),
                                    sync_id
                                )

                                if detail_record:
                                    detail_records.append(detail_record)

                            if detail_records:
                                conn.execute("BEGIN TRANSACTION")
                                saved_detail_count = insert_ipo_detail_records(conn, detail_records)
                                conn.execute("COMMIT")
                                detail_count += saved_detail_count
                                metrics["detail_records_saved"] += saved_detail_count

                        if not should_continue_ipo_pagination(response, page_number, len(response_rows)):
                            break
                        page_number += 1

                    conn.execute("BEGIN TRANSACTION")
                    record_ipo_status(conn, status_filter, issue_type_filter, "success", group_count, page_count, detail_count, sync_id)
                    conn.execute("COMMIT")

                except SyncCancelled:
                    raise
                except Exception as error:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    metrics["failed_groups"] += 1
                    error_text = str(error.detail) if isinstance(error, HTTPException) else str(error)
                    try:
                        conn.execute("BEGIN TRANSACTION")
                        record_ipo_status(conn, status_filter, issue_type_filter, "failed", 0, page_count, 0, sync_id, error_text)
                        conn.execute("COMMIT")
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    print(f"[IPO Calendar] Group failed {status_filter}/{issue_type_filter}: {error_text}")
                    continue

        refresh_ipo_calendar_statuses(conn)
        status_text = "success" if metrics["failed_groups"] == 0 else "partial_success"
        message = "IPO Calendar synced successfully." if status_text == "success" else "IPO Calendar synced with some failed groups."
        finish_sync_run(conn, sync_id, status_text, message, total_records, started_at)

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {"status": status_text, "message": message, "total_records": total_records, "duration_seconds": duration_seconds(started_at), "metrics": metrics}

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass
        if sync_id:
            finish_sync_run(conn, sync_id, "cancelled", "IPO Calendar sync cancelled. Completed rows were saved.", total_records, started_at)
        if clear_cancel_at_start:
            clear_cancel_signal()
        return {"status": "cancelled", "message": "IPO Calendar sync cancelled. Completed rows were saved.", "total_records": total_records, "duration_seconds": duration_seconds(started_at), "metrics": metrics}
    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass
        if sync_id:
            finish_sync_run(conn, sync_id, "failed", f"IPO Calendar sync failed: {error.detail}", total_records, started_at)
        if clear_cancel_at_start:
            clear_cancel_signal()
        raise
    finally:
        conn.close()


def record_ipo_status(conn, status_filter: str, issue_type_filter: str, status_value: str, record_count: int, page_count: int, detail_count: int, sync_id: str, error_message: Optional[str] = None):
    conn.execute("DELETE FROM upstox_ipo_sync_status WHERE status_filter = ? AND issue_type_filter = ?;", [status_filter, issue_type_filter])
    conn.execute("""
        INSERT INTO upstox_ipo_sync_status (
            provider, status_filter, issue_type_filter, status, record_count, page_count,
            detail_count, last_error, source_sync_id, checked_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """, [UPSTOX_PROVIDER, status_filter, issue_type_filter, status_value, int(record_count or 0), int(page_count or 0), int(detail_count or 0), error_message, sync_id])


def get_upstox_equity_news_preview_service(search: str = "", segment: str = "all", source: str = "all", page: int = 1, page_size: int = 50):
    conn = get_connection()
    try:
        ensure_upstox_news_ipo_tables(conn)
        refresh_ipo_calendar_statuses(conn)
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size
        where_clauses = []
        params = []

        if search:
            search_value = f"%{search.strip().lower()}%"
            where_clauses.append("""
                (
                    LOWER(COALESCE(instrument_key, '')) LIKE ?
                    OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                    OR LOWER(COALESCE(company_name, '')) LIKE ?
                    OR LOWER(COALESCE(isin, '')) LIKE ?
                    OR LOWER(COALESCE(heading, title, '')) LIKE ?
                    OR LOWER(COALESCE(summary, '')) LIKE ?
                    OR LOWER(COALESCE(source, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 7)

        if source != "all":
            where_clauses.append("source = ?")
            params.append(source)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        total_records = conn.execute(f"SELECT COUNT(*) FROM equity_news {where_sql};", params).fetchone()[0]
        rows = conn.execute(f"""
            SELECT news_id, instrument_key, trading_symbol, company_name, isin,
                   COALESCE(heading, title) AS heading, title, summary, thumbnail,
                   article_link, COALESCE(url, article_link) AS url, source,
                   published_time_ms, published_at, source_sync_id, ingested_at, updated_at
            FROM equity_news
            {where_sql}
            ORDER BY published_at DESC NULLS LAST, ingested_at DESC, trading_symbol
            LIMIT ? OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()
        total_pages = max(1, int((total_records + current_page_size - 1) / current_page_size))
        return {
            "rows": [
                {
                    "news_id": row[0], "instrument_key": row[1], "trading_symbol": row[2],
                    "company_name": row[3], "isin": row[4], "heading": row[5],
                    "title": row[6], "summary": row[7], "thumbnail": row[8],
                    "article_link": row[9], "url": row[10], "source": row[11],
                    "published_time_ms": row[12], "published_at": str(row[13]) if row[13] else None,
                    "source_sync_id": row[14], "ingested_at": str(row[15]) if row[15] else None,
                    "updated_at": str(row[16]) if row[16] else None
                }
                for row in rows
            ],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }
    finally:
        conn.close()


def get_upstox_ipo_calendar_preview_service(search: str = "", ipo_status: str = "all", issue_type: str = "all", page: int = 1, page_size: int = 50):
    conn = get_connection()
    try:
        ensure_upstox_news_ipo_tables(conn)
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size
        status_sql = """
            CASE
                WHEN LOWER(COALESCE(detail.status, ipo.status, '')) = 'listed'
                     OR detail.listing_date <= CURRENT_DATE THEN 'listed'
                WHEN COALESCE(detail.bidding_start_date, ipo.bidding_start_date) IS NOT NULL
                     AND CURRENT_DATE < COALESCE(detail.bidding_start_date, ipo.bidding_start_date) THEN 'upcoming'
                WHEN COALESCE(detail.bidding_start_date, ipo.bidding_start_date) IS NOT NULL
                     AND COALESCE(detail.bidding_end_date, ipo.bidding_end_date) IS NOT NULL
                     AND CURRENT_DATE BETWEEN COALESCE(detail.bidding_start_date, ipo.bidding_start_date)
                                         AND COALESCE(detail.bidding_end_date, ipo.bidding_end_date) THEN 'open'
                WHEN COALESCE(detail.bidding_end_date, ipo.bidding_end_date) IS NOT NULL
                     AND CURRENT_DATE > COALESCE(detail.bidding_end_date, ipo.bidding_end_date) THEN 'closed'
                ELSE LOWER(COALESCE(detail.status, ipo.status, 'upcoming'))
            END
        """
        where_clauses = []
        params = []

        if search:
            search_value = f"%{search.strip().lower()}%"
            where_clauses.append("""
                (
                    LOWER(COALESCE(ipo.ipo_id, '')) LIKE ?
                    OR LOWER(COALESCE(detail.symbol, ipo.symbol, '')) LIKE ?
                    OR LOWER(COALESCE(detail.name, ipo.name, '')) LIKE ?
                    OR LOWER(COALESCE(detail.isin, ipo.isin, '')) LIKE ?
                    OR LOWER(COALESCE(detail.industry, ipo.industry, '')) LIKE ?
                    OR LOWER(COALESCE(ipo.derived_status, '')) LIKE ?
                    OR LOWER(COALESCE(detail.issue_type, ipo.issue_type, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 7)

        if ipo_status != "all":
            where_clauses.append("ipo.derived_status = ?")
            params.append(ipo_status.lower())

        if issue_type != "all":
            where_clauses.append("LOWER(COALESCE(detail.issue_type, ipo.issue_type, '')) = ?")
            params.append(issue_type.lower())

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        from_sql = f"""
            FROM (
                SELECT
                    ipo.*,
                    {status_sql} AS derived_status
                FROM upstox_ipo_list ipo
                LEFT JOIN upstox_ipo_details detail
                    ON detail.ipo_id = ipo.ipo_id
            ) ipo
            LEFT JOIN upstox_ipo_details detail
                ON detail.ipo_id = ipo.ipo_id
        """
        total_records = conn.execute(f"SELECT COUNT(*) {from_sql} {where_sql};", params).fetchone()[0]
        rows = conn.execute(f"""
            SELECT
                ipo.ipo_id,
                COALESCE(detail.symbol, ipo.symbol),
                COALESCE(detail.name, ipo.name),
                ipo.derived_status,
                COALESCE(detail.isin, ipo.isin),
                COALESCE(detail.issue_type, ipo.issue_type),
                COALESCE(detail.issue_size, ipo.issue_size),
                COALESCE(detail.industry, ipo.industry),
                COALESCE(detail.minimum_price, ipo.minimum_price),
                COALESCE(detail.maximum_price, ipo.maximum_price),
                COALESCE(detail.bidding_start_date, ipo.bidding_start_date),
                COALESCE(detail.bidding_end_date, ipo.bidding_end_date),
                COALESCE(detail.total_subscription, ipo.total_subscription),
                COALESCE(detail.source_sync_id, ipo.source_sync_id),
                ipo.ingested_at,
                COALESCE(detail.updated_at, ipo.updated_at)
            {from_sql}
            {where_sql}
            ORDER BY COALESCE(detail.bidding_start_date, ipo.bidding_start_date) DESC NULLS LAST,
                     COALESCE(detail.name, ipo.name)
            LIMIT ? OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()
        total_pages = max(1, int((total_records + current_page_size - 1) / current_page_size))
        return {
            "rows": [
                {
                    "ipo_id": row[0], "symbol": row[1], "name": row[2], "status": row[3],
                    "isin": row[4], "issue_type": row[5], "issue_size": row[6], "industry": row[7],
                    "minimum_price": row[8], "maximum_price": row[9],
                    "bidding_start_date": str(row[10]) if row[10] else None,
                    "bidding_end_date": str(row[11]) if row[11] else None,
                    "total_subscription": row[12], "source_sync_id": row[13],
                    "ingested_at": str(row[14]) if row[14] else None,
                    "updated_at": str(row[15]) if row[15] else None
                }
                for row in rows
            ],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }
    finally:
        conn.close()



def normalize_ipo_gmp_value(value: Any) -> str:
    if value is None:
        return ""

    clean_value = str(value).strip()

    if clean_value.lower() in ("nan", "none", "null"):
        return ""

    return clean_value


def parse_ipo_gmp_date_range(value: Any) -> Optional[dict]:
    clean_value = normalize_ipo_gmp_value(value)

    if not clean_value:
        return None

    normalized = re.sub(r"\s+", " ", clean_value.replace("–", "-").replace("—", "-")).strip()
    current_year = date.today().year

    match = re.search(
        r"(?P<start_day>\d{1,2})\s*-\s*(?P<end_day>\d{1,2})\s+"
        r"(?P<month>[A-Za-z]{3,9})(?:\s+(?P<year>\d{4}))?",
        normalized
    )

    if match:
        try:
            month = datetime.strptime(match.group("month")[:3], "%b").month
            year = int(match.group("year") or current_year)
            return {
                "start_date": date(year, month, int(match.group("start_day"))),
                "end_date": date(year, month, int(match.group("end_day")))
            }
        except Exception:
            return None

    match = re.search(
        r"(?P<start_day>\d{1,2})\s+"
        r"(?P<start_month>[A-Za-z]{3,9})\s*-\s*"
        r"(?P<end_day>\d{1,2})\s+"
        r"(?P<end_month>[A-Za-z]{3,9})(?:\s+(?P<year>\d{4}))?",
        normalized
    )

    if match:
        try:
            start_month = datetime.strptime(match.group("start_month")[:3], "%b").month
            end_month = datetime.strptime(match.group("end_month")[:3], "%b").month
            start_year = int(match.group("year") or current_year)
            end_year = start_year + 1 if end_month < start_month else start_year
            return {
                "start_date": date(start_year, start_month, int(match.group("start_day"))),
                "end_date": date(end_year, end_month, int(match.group("end_day")))
            }
        except Exception:
            return None

    match = re.search(
        r"(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]{3,9})(?:\s+(?P<year>\d{4}))?",
        normalized
    )

    if match:
        try:
            month = datetime.strptime(match.group("month")[:3], "%b").month
            year = int(match.group("year") or current_year)
            parsed_date = date(year, month, int(match.group("day")))
            return {
                "start_date": parsed_date,
                "end_date": parsed_date
            }
        except Exception:
            return None

    return None


def derive_ipo_gmp_status(ipo_date: Any, current_status: Any = None) -> str:
    status_value = normalize_ipo_gmp_value(current_status)
    parsed_range = parse_ipo_gmp_date_range(ipo_date)

    if not parsed_range:
        return status_value

    today = date.today()

    if today < parsed_range["start_date"]:
        return "Upcoming"

    if parsed_range["start_date"] <= today <= parsed_range["end_date"]:
        return "Open"

    if today > parsed_range["end_date"]:
        return "Closed"

    return status_value


def parse_ipo_gmp_number(value: Any) -> Optional[float]:
    clean_value = normalize_ipo_gmp_value(value)

    if not clean_value:
        return None

    normalized_value = (
        clean_value
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace("INR", "")
        .strip()
    )
    matches = re.findall(r"-?\d+(?:\.\d+)?", normalized_value)

    if not matches:
        return None

    try:
        values = [float(match) for match in matches]
    except ValueError:
        return None

    return max(values) if values else None


def format_ipo_gmp_money(value: float) -> str:
    if value == int(value):
        return f"₹{int(value)}"

    return f"₹{value:.2f}"


def calculate_ipo_gmp_gain(ipo_gmp: Any, price_band: Any) -> Optional[str]:
    gmp_value = parse_ipo_gmp_number(ipo_gmp)
    price_band_value = parse_ipo_gmp_number(price_band)

    if gmp_value is None or price_band_value in (None, 0):
        return None

    estimated_listing = price_band_value + gmp_value
    gain_percent = (gmp_value / price_band_value) * 100

    return f"{format_ipo_gmp_money(estimated_listing)} ({gain_percent:.2f}%)"


def find_ipo_gmp_table_from_html(url: str):
    tables = pd.read_html(url)

    for df in tables:
        cols = [str(column).strip() for column in df.columns]

        if "IPO Name" in cols and "IPO GMP" in cols:
            df = df.copy()
            df.columns = cols
            return df

    raise ValueError("Target IPO GMP table was not found with pandas.read_html.")


def first_existing_path(paths: List[str]) -> Optional[str]:
    for path in paths:
        clean_path = safe_strip(path)

        if clean_path and Path(clean_path).exists():
            return clean_path

    return None


def find_ipo_gmp_table_with_selenium(url: str):
    import os
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "pandas.read_html failed and Selenium is not installed. "
                "Install selenium and ChromeDriver support, or fix read_html dependencies."
            )
        )

    options = webdriver.ChromeOptions()

    chrome_binary = first_existing_path(
        [
            os.environ.get("CHROME_BIN"),
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
    )

    if chrome_binary:
        options.binary_location = chrome_binary

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--window-size=1920,1080")

    chromedriver_path = first_existing_path(
        [
            os.environ.get("CHROMEDRIVER_PATH"),
            "/usr/bin/chromedriver"
        ]
    )
    service = Service(executable_path=chromedriver_path) if chromedriver_path else Service()

    driver = None

    try:
        driver = webdriver.Chrome(
            service=service,
            options=options,
        )

        wait = WebDriverWait(driver, 25)

        driver.get(url)

        wait.until(
            EC.presence_of_all_elements_located(
                (By.TAG_NAME, "table")
            )
        )

        time.sleep(2)

        tables = driver.find_elements(By.TAG_NAME, "table")

        html_table = None

        for table in tables:
            table_text = table.text.strip()

            if (
                "IPO Name" in table_text
                and "IPO GMP" in table_text
                and "Price Band" in table_text
                and "Last Updated" in table_text
            ):
                html_table = table.get_attribute("outerHTML")
                break

        if html_table is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Target IPO GMP table was not found with Selenium.",
            )

        df = pd.read_html(StringIO(html_table))[0]
        df.columns = [str(column).strip() for column in df.columns]

        return df

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Selenium failed using "
                f"Chrome='{chrome_binary or 'auto'}', "
                f"ChromeDriver='{chromedriver_path or 'Selenium Manager'}'. "
                f"Error: {exc}"
            ),
        )

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def get_ipo_gmp_dataframe(url: str = IPO_GMP_SCRAPER_URL):
    try:
        return find_ipo_gmp_table_from_html(url)
    except Exception as error:
        print("IPO GMP read_html failed, trying Selenium fallback.")
        print(f"Reason: {error}")

    return find_ipo_gmp_table_with_selenium(url)


def normalize_ipo_gmp_dataframe(df):
    normalized_df = df.copy()
    normalized_df.columns = [str(column).strip() for column in normalized_df.columns]

    if (
        not set(IPO_GMP_SCRAPER_REQUIRED_COLUMNS).issubset(set(normalized_df.columns))
        and not normalized_df.empty
    ):
        first_row_values = [
            normalize_ipo_gmp_value(value)
            for value in normalized_df.iloc[0].tolist()
        ]

        if "IPO Name" in first_row_values and "IPO GMP" in first_row_values:
            normalized_df = normalized_df.iloc[1:].copy()
            normalized_df.columns = first_row_values

    normalized_df.columns = [str(column).strip() for column in normalized_df.columns]
    return normalized_df.reset_index(drop=True)


def normalize_ipo_gmp_record(row: dict, source_url: str) -> Optional[dict]:
    ipo_name = normalize_ipo_gmp_value(row.get("IPO Name"))

    if not ipo_name:
        return None

    raw_record = {
        key: normalize_ipo_gmp_value(value)
        for key, value in row.items()
    }

    return {
        "ipo_name": ipo_name,
        "ipo_gmp": normalize_ipo_gmp_value(row.get("IPO GMP")),
        "price_band": normalize_ipo_gmp_value(row.get("Price Band")),
        "ipo_date": normalize_ipo_gmp_value(row.get("Date")),
        "ipo_type": normalize_ipo_gmp_value(row.get("Type")),
        "ipo_status": derive_ipo_gmp_status(row.get("Date"), row.get("Status")),
        "last_updated": normalize_ipo_gmp_value(row.get("Last Updated")),
        "source_url": source_url,
        "raw_json": json_dumps_for_db(raw_record)
    }


def get_ipo_gmp_record_hash(record: dict) -> str:
    comparable_record = {
        key: record.get(key) or ""
        for key in (
            "ipo_name",
            "ipo_gmp",
            "price_band",
            "ipo_date",
            "ipo_type",
            "ipo_status",
            "last_updated"
        )
    }

    payload = json.dumps(
        comparable_record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scrape_ipo_gmp_records(source_url: str = IPO_GMP_SCRAPER_URL) -> List[dict]:
    df = normalize_ipo_gmp_dataframe(get_ipo_gmp_dataframe(source_url))

    missing_columns = [
        column
        for column in IPO_GMP_SCRAPER_REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "IPO GMP scraper table is missing required columns: "
                + ", ".join(missing_columns)
            )
        )

    records = []

    for row in df.to_dict(orient="records"):
        record = normalize_ipo_gmp_record(row, source_url)

        if record:
            records.append(record)

    return list({
        record["ipo_name"].lower(): record
        for record in records
        if record.get("ipo_name")
    }.values())


def insert_ipo_gmp_scraper_records(
    conn,
    records: List[dict],
    source_sync_id: str
) -> int:
    rows = list({
        safe_strip(record.get("ipo_name")).lower(): record
        for record in records
        if safe_strip(record.get("ipo_name"))
    }.values())

    if not rows:
        return 0

    for row in rows:
        row["data_hash"] = get_ipo_gmp_record_hash(row)

    conn.executemany("""
        INSERT OR REPLACE INTO ipo_gmp_scraper (
            ipo_name,
            ipo_gmp,
            price_band,
            ipo_date,
            ipo_type,
            ipo_status,
            last_updated,
            source_url,
            raw_json,
            source_sync_id,
            data_hash,
            scraped_at,
            updated_at
        )
        SELECT
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            TRY_CAST(? AS JSON),
            ?,
            ?,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP;
    """, [
        (
            row.get("ipo_name"),
            row.get("ipo_gmp"),
            row.get("price_band"),
            row.get("ipo_date"),
            row.get("ipo_type"),
            row.get("ipo_status"),
            row.get("last_updated"),
            row.get("source_url"),
            row.get("raw_json"),
            source_sync_id,
            row.get("data_hash")
        )
        for row in rows
    ])

    conn.executemany("""
        INSERT INTO ipo_gmp_scraper_snapshots (
            snapshot_id,
            source_sync_id,
            ipo_name,
            ipo_gmp,
            price_band,
            ipo_date,
            ipo_type,
            ipo_status,
            last_updated,
            source_url,
            raw_json,
            data_hash,
            scraped_at
        )
        SELECT
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            TRY_CAST(? AS JSON),
            ?,
            CURRENT_TIMESTAMP;
    """, [
        (
            str(uuid.uuid4()),
            source_sync_id,
            row.get("ipo_name"),
            row.get("ipo_gmp"),
            row.get("price_band"),
            row.get("ipo_date"),
            row.get("ipo_type"),
            row.get("ipo_status"),
            row.get("last_updated"),
            row.get("source_url"),
            row.get("raw_json"),
            row.get("data_hash")
        )
        for row in rows
    ])

    return len(rows)


def refresh_ipo_gmp_statuses(conn):
    rows = conn.execute("""
        SELECT ipo_name, ipo_date, ipo_status
        FROM ipo_gmp_scraper;
    """).fetchall()

    updates = []

    for row in rows:
        next_status = derive_ipo_gmp_status(row[1], row[2])

        if next_status and next_status.lower() != normalize_ipo_gmp_value(row[2]).lower():
            updates.append((next_status, row[0]))

    if not updates:
        return 0

    conn.executemany("""
        UPDATE ipo_gmp_scraper
        SET ipo_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE ipo_name = ?;
    """, updates)

    return len(updates)


def sync_ipo_gmp_scraper_service(
    current_user: dict,
    config: Optional[dict] = None,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_news_ipo_tables(conn)

        payload = config or {}
        source_url = safe_strip(payload.get("source_url")) or IPO_GMP_SCRAPER_URL

        sync_id = create_sync_run(
            conn,
            IPO_GMP_SCRAPER_SYNC_TYPE,
            "running",
            "IPO GMP scraper started.",
            current_user=current_user
        )

        check_sync_cancelled(conn, sync_id)

        records = scrape_ipo_gmp_records(source_url=source_url)

        check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")
        total_records = insert_ipo_gmp_scraper_records(
            conn,
            records,
            sync_id
        )
        refresh_ipo_gmp_statuses(conn)
        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "IPO GMP scraper completed successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "IPO GMP scraper completed successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "IPO GMP scraper cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "IPO GMP scraper cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
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
                f"IPO GMP scraper failed: {error.detail}",
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
                f"IPO GMP scraper failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run IPO GMP scraper: {error}"
        )

    finally:
        conn.close()



def get_ipo_gmp_scraper_preview_service(
    search: str = "",
    ipo_status: str = "all",
    ipo_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        ensure_upstox_news_ipo_tables(conn)
        refresh_ipo_gmp_statuses(conn)

        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size
        where_clauses = []
        params = []

        if search:
            search_value = f"%{search.strip().lower()}%"
            where_clauses.append("""
                (
                    LOWER(COALESCE(ipo_name, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_gmp, '')) LIKE ?
                    OR LOWER(COALESCE(price_band, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_date, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_type, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_status, '')) LIKE ?
                    OR LOWER(COALESCE(last_updated, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 7)

        if ipo_status != "all":
            where_clauses.append("LOWER(COALESCE(ipo_status, '')) = ?")
            params.append(ipo_status.lower())

        if ipo_type != "all":
            where_clauses.append("LOWER(COALESCE(ipo_type, '')) = ?")
            params.append(ipo_type.lower())

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM ipo_gmp_scraper
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                ipo_name,
                ipo_gmp,
                price_band,
                ipo_date,
                ipo_type,
                ipo_status,
                last_updated,
                source_url,
                scraped_at,
                updated_at
            FROM ipo_gmp_scraper
            {where_sql}
            ORDER BY updated_at DESC, ipo_name
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [
                {
                    "ipo_name": row[0],
                    "ipo_gmp": row[1],
                    "price_band": row[2],
                    "gain": calculate_ipo_gmp_gain(row[1], row[2]),
                    "ipo_date": row[3],
                    "ipo_type": row[4],
                    "ipo_status": row[5],
                    "last_updated": row[6],
                    "source_url": row[7],
                    "scraped_at": str(row[8]) if row[8] else None,
                    "updated_at": str(row[9]) if row[9] else None
                }
                for row in rows
            ],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()
