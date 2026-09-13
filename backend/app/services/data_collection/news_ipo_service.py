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
