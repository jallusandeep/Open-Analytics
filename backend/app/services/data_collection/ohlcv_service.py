# backend\app\services\data_collection\ohlcv_service.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def parse_iso_date(value: Any, field_name: str, default_value: Optional[date] = None) -> date:
    if value in (None, ""):
        if default_value is not None:
            return default_value

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required."
        )

    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a valid date in YYYY-MM-DD format."
        )


def normalize_string_list(value: Any, default_values: List[str]) -> List[str]:
    if value in (None, ""):
        return default_values.copy()

    if isinstance(value, str):
        values = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        values = [str(item).strip() for item in value]
    else:
        values = []

    return unique_preserve_order([value for value in values if value]) or default_values.copy()


def normalize_bool(value: Any, default_value: bool = False) -> bool:
    if value is None:
        return default_value

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    clean_value = str(value).strip().lower()

    if clean_value in ("1", "true", "yes", "y", "on"):
        return True

    if clean_value in ("0", "false", "no", "n", "off"):
        return False

    return default_value


def normalize_positive_int(value: Any, default_value: int, minimum: int = 1, maximum: Optional[int] = None) -> int:
    try:
        number = int(value)
    except Exception:
        number = default_value

    number = max(minimum, number)

    if maximum is not None:
        number = min(maximum, number)

    return number


def normalize_optional_positive_int(value: Any, minimum: int = 1, maximum: Optional[int] = None) -> Optional[int]:
    if value in (None, "", 0, "0", "all"):
        return None

    try:
        number = int(value)
    except Exception:
        return None

    number = max(minimum, number)

    if maximum is not None:
        number = min(maximum, number)

    return number


def normalize_ohlcv_interval_key(value: Any) -> str:
    clean_value = str(value or "").strip().lower().replace(" ", "")

    aliases = {
        "1m": "1minute",
        "1min": "1minute",
        "1minute": "1minute",
        "3m": "3minute",
        "3min": "3minute",
        "3minute": "3minute",
        "5m": "5minute",
        "5min": "5minute",
        "5minute": "5minute",
        "15m": "15minute",
        "15min": "15minute",
        "15minute": "15minute",
        "30m": "30minute",
        "30min": "30minute",
        "30minute": "30minute",
        "1h": "1hour",
        "1hour": "1hour",
        "hour": "1hour",
        "day": "day",
        "daily": "day",
        "1day": "day",
        "week": "week",
        "weekly": "week",
        "1week": "week",
        "month": "month",
        "monthly": "month",
        "1month": "month"
    }

    return aliases.get(clean_value, clean_value)


def normalize_ohlcv_config(payload: Optional[dict]) -> dict:
    payload = payload or {}
    today = datetime.now().date()

    selected_sources = normalize_string_list(
        payload.get("sources") or payload.get("selected_sources"),
        OHLCV_DEFAULT_SOURCES
    )
    selected_sources = [value for value in selected_sources if value in OHLCV_ALLOWED_SOURCES]

    selected_modes = normalize_string_list(
        payload.get("candle_modes") or payload.get("selected_candle_modes"),
        OHLCV_DEFAULT_MODES
    )
    selected_modes = [value for value in selected_modes if value in OHLCV_ALLOWED_MODES]

    raw_intervals = normalize_string_list(
        payload.get("intervals") or payload.get("selected_intervals"),
        OHLCV_DEFAULT_INTERVALS
    )
    selected_intervals = []

    for interval in raw_intervals:
        interval_key = normalize_ohlcv_interval_key(interval)

        if interval_key in OHLCV_INTERVAL_OPTIONS:
            selected_intervals.append(interval_key)

    selected_intervals = unique_preserve_order(selected_intervals)

    if not selected_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one OHLCV instrument source."
        )

    if not selected_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one OHLCV candle mode."
        )

    if not selected_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one OHLCV interval."
        )

    raw_from_date = payload.get("from_date")
    raw_to_date = payload.get("to_date")

    from_date_was_provided = raw_from_date not in (None, "")
    to_date_was_provided = raw_to_date not in (None, "")

    use_current_day = normalize_bool(
        payload.get("use_current_day") if "use_current_day" in payload else payload.get("to_current_day"),
        not to_date_was_provided
    )
    auto_date_range = normalize_bool(
        payload.get("auto_date_range"),
        not from_date_was_provided
    )

    from_date = parse_iso_date(
        raw_from_date,
        "from_date",
        OHLCV_CURRENT_HISTORY_START_DATE
    )
    to_date = today if use_current_day else parse_iso_date(raw_to_date, "to_date", today)

    if to_date > today:
        to_date = today

    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_date must be greater than or equal to from_date."
        )

    if OHLCV_INTRADAY_MODE in selected_modes:
        to_date = today if use_current_day else min(to_date, today)

    instrument_limit = normalize_optional_positive_int(payload.get("instrument_limit"), 1, 1000000)
    single_instrument_key = safe_strip(payload.get("single_instrument_key"))

    batch_size = normalize_positive_int(
        payload.get("batch_size"),
        OHLCV_DEFAULT_BATCH_SIZE,
        1,
        500
    )
    request_delay_ms = normalize_positive_int(
        payload.get("request_delay_ms"),
        OHLCV_DEFAULT_REQUEST_DELAY_MS,
        0,
        60000
    )
    batch_delay_seconds = normalize_positive_int(
        payload.get("batch_delay_seconds"),
        OHLCV_DEFAULT_BATCH_DELAY_SECONDS,
        0,
        3600
    )
    retry_count = normalize_positive_int(
        payload.get("retry_count"),
        OHLCV_DEFAULT_RETRY_COUNT,
        1,
        10
    )

    return {
        "sources": selected_sources,
        "candle_modes": selected_modes,
        "intervals": selected_intervals,
        "from_date": from_date,
        "to_date": to_date,
        "from_date_was_provided": from_date_was_provided,
        "to_date_was_provided": to_date_was_provided,
        "use_current_day": use_current_day,
        "auto_date_range": auto_date_range,
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "respect_api_limits": normalize_bool(payload.get("respect_api_limits"), True),
        "retry_failed": normalize_bool(payload.get("retry_failed"), True),
        "instrument_limit": instrument_limit,
        "single_instrument_key": single_instrument_key,
        "batch_size": batch_size,
        "request_delay_ms": request_delay_ms,
        "batch_delay_seconds": batch_delay_seconds,
        "retry_count": retry_count
    }


def ohlcv_config_to_jsonable(config: dict) -> dict:
    return {
        **config,
        "from_date": config["from_date"].isoformat(),
        "to_date": config["to_date"].isoformat(),
        "from_date_was_provided": bool(config.get("from_date_was_provided")),
        "to_date_was_provided": bool(config.get("to_date_was_provided")),
        "use_current_day": bool(config.get("use_current_day")),
        "auto_date_range": bool(config.get("auto_date_range"))
    }

def get_default_ohlcv_options_payload() -> dict:
    today = datetime.now().date()

    return {
        "sources": OHLCV_DEFAULT_SOURCES.copy(),
        "candle_modes": OHLCV_DEFAULT_MODES.copy(),
        "intervals": OHLCV_DEFAULT_INTERVALS.copy(),
        "from_date": OHLCV_CURRENT_HISTORY_START_DATE.isoformat(),
        "to_date": today.isoformat(),
        "from_date_was_provided": False,
        "to_date_was_provided": False,
        "use_current_day": True,
        "auto_date_range": True,
        "skip_existing": True,
        "respect_api_limits": True,
        "retry_failed": True,
        "instrument_limit": None,
        "single_instrument_key": "",
        "batch_size": OHLCV_DEFAULT_BATCH_SIZE,
        "request_delay_ms": OHLCV_DEFAULT_REQUEST_DELAY_MS,
        "batch_delay_seconds": OHLCV_DEFAULT_BATCH_DELAY_SECONDS,
        "retry_count": OHLCV_DEFAULT_RETRY_COUNT
    }


def get_upstox_ohlcv_options_service():
    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT request_options, updated_at, updated_by
            FROM upstox_ohlcv_collection_settings
            WHERE setting_name = 'default'
              AND is_active = TRUE
            LIMIT 1;
        """).fetchone()

        if not row or not row[0]:
            return {
                "options": get_default_ohlcv_options_payload(),
                "updated_at": None,
                "updated_by": None
            }

        try:
            request_options = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception:
            request_options = get_default_ohlcv_options_payload()

        return {
            "options": request_options or get_default_ohlcv_options_payload(),
            "updated_at": str(row[1]) if row[1] else None,
            "updated_by": row[2]
        }

    finally:
        conn.close()


def save_upstox_ohlcv_options_service(payload: dict, current_user: dict):
    normalized_config = normalize_ohlcv_config(payload)
    request_options = ohlcv_config_to_jsonable(normalized_config)
    trigger_metadata = get_sync_trigger_metadata(current_user)
    user_id = trigger_metadata["triggered_by_id"] or "system"

    conn = get_connection()

    try:
        existing = conn.execute("""
            SELECT setting_id
            FROM upstox_ohlcv_collection_settings
            WHERE setting_name = 'default'
            LIMIT 1;
        """).fetchone()

        if existing:
            conn.execute("""
                UPDATE upstox_ohlcv_collection_settings
                SET
                    request_options = TRY_CAST(? AS JSON),
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE setting_name = 'default';
            """, [
                json.dumps(request_options, ensure_ascii=False, default=str),
                user_id
            ])
        else:
            conn.execute("""
                INSERT INTO upstox_ohlcv_collection_settings (
                    setting_id,
                    setting_name,
                    request_options,
                    is_active,
                    created_by,
                    updated_by
                )
                VALUES (?, 'default', TRY_CAST(? AS JSON), TRUE, ?, ?);
            """, [
                str(uuid.uuid4()),
                json.dumps(request_options, ensure_ascii=False, default=str),
                user_id,
                user_id
            ])

        conn.commit()

        return {
            "status": "success",
            "message": "OHLCV options saved successfully.",
            "data": {
                "options": request_options
            }
        }

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    finally:
        conn.close()


def get_saved_ohlcv_options_for_run(conn) -> dict:
    row = conn.execute("""
        SELECT request_options
        FROM upstox_ohlcv_collection_settings
        WHERE setting_name = 'default'
          AND is_active = TRUE
        LIMIT 1;
    """).fetchone()

    if not row or not row[0]:
        return get_default_ohlcv_options_payload()

    try:
        return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except Exception:
        return get_default_ohlcv_options_payload()

def update_ohlcv_sync_run_options(conn, sync_id: str, config: dict):
    jsonable_config = ohlcv_config_to_jsonable(config)

    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            request_options = TRY_CAST(? AS JSON),
            selected_sources = TRY_CAST(? AS JSON),
            selected_candle_modes = TRY_CAST(? AS JSON),
            selected_intervals = TRY_CAST(? AS JSON),
            from_date = TRY_CAST(? AS DATE),
            to_date = TRY_CAST(? AS DATE),
            skip_existing = ?,
            respect_api_limits = ?,
            retry_failed = ?,
            instrument_limit = ?,
            single_instrument_key = ?,
            batch_size = ?,
            request_delay_ms = ?,
            batch_delay_seconds = ?
        WHERE sync_id = ?;
    """, [
        json.dumps(jsonable_config, ensure_ascii=False, default=str),
        json.dumps(config["sources"], ensure_ascii=False),
        json.dumps(config["candle_modes"], ensure_ascii=False),
        json.dumps(config["intervals"], ensure_ascii=False),
        config["from_date"].isoformat(),
        config["to_date"].isoformat(),
        bool(config["skip_existing"]),
        bool(config["respect_api_limits"]),
        bool(config["retry_failed"]),
        config["instrument_limit"],
        config["single_instrument_key"],
        config["batch_size"],
        config["request_delay_ms"],
        config["batch_delay_seconds"],
        sync_id
    ])

    conn.commit()


def finish_ohlcv_sync_run_metrics(conn, sync_id: str, metrics: dict):
    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            api_calls_attempted = ?,
            api_calls_skipped = ?,
            candles_inserted = ?,
            candles_skipped = ?,
            failed_instruments = ?,
            last_heartbeat_at = CURRENT_TIMESTAMP
        WHERE sync_id = ?;
    """, [
        int(metrics.get("api_calls_attempted") or 0),
        int(metrics.get("api_calls_skipped") or 0),
        int(metrics.get("candles_inserted") or 0),
        int(metrics.get("candles_skipped") or 0),
        int(metrics.get("failed_instruments") or 0),
        sync_id
    ])

    conn.commit()


def get_ohlcv_interval_definition(interval_key: str) -> dict:
    interval = OHLCV_INTERVAL_OPTIONS.get(interval_key)

    if not interval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OHLCV interval: {interval_key}"
        )

    return interval


def get_ohlcv_chunk_days(unit: str, interval_value: int, source: str) -> Optional[int]:
    if source == OHLCV_EXPIRED_SOURCE:
        return OHLCV_CURRENT_INTRADAY_SMALL_MAX_DAYS if unit == "minutes" else OHLCV_EXPIRED_MAX_DAYS

    if unit == "minutes" and interval_value <= 15:
        return OHLCV_CURRENT_INTRADAY_SMALL_MAX_DAYS

    if unit == "minutes" and interval_value > 15:
        return OHLCV_CURRENT_INTRADAY_LARGE_MAX_DAYS

    if unit == "hours":
        return OHLCV_CURRENT_INTRADAY_LARGE_MAX_DAYS

    if unit == "days":
        return OHLCV_CURRENT_DAILY_MAX_DAYS

    return None


def split_ohlcv_date_range(from_date: date, to_date: date, unit: str, interval_value: int, source: str) -> List[dict]:
    max_days = get_ohlcv_chunk_days(unit, interval_value, source)

    if not max_days:
        return [{"from_date": from_date, "to_date": to_date}]

    chunks = []
    current_from = from_date

    while current_from <= to_date:
        current_to = min(to_date, current_from + timedelta(days=max_days - 1))
        chunks.append({"from_date": current_from, "to_date": current_to})
        current_from = current_to + timedelta(days=1)

    return chunks


def get_ohlcv_available_start_date(source: str, mode: str, unit: str) -> date:
    if source == OHLCV_CURRENT_SOURCE and mode == OHLCV_HISTORICAL_MODE:
        if unit in ("minutes", "hours"):
            return OHLCV_INTRADAY_HISTORY_START_DATE

        return OHLCV_CURRENT_HISTORY_START_DATE

    if source == OHLCV_CURRENT_SOURCE and mode == OHLCV_INTRADAY_MODE:
        return OHLCV_INTRADAY_HISTORY_START_DATE

    return OHLCV_CURRENT_HISTORY_START_DATE




# --- Open Analytics OHLCV chunk history helpers ---
def ensure_ohlcv_chunk_sync_status_table(conn):
    global OHLCV_CHUNK_STATUS_SCHEMA_READY

    # Always verify/migrate this small table. Older DBs may have this table without
    # record_count, and a process-level flag can otherwise skip the migration.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ohlcv_chunk_sync_status (
            provider VARCHAR DEFAULT 'upstox',
            instrument_key VARCHAR NOT NULL,
            instrument_source VARCHAR NOT NULL,
            candle_mode VARCHAR NOT NULL,
            unit VARCHAR NOT NULL,
            interval_value BIGINT NOT NULL,
            from_date DATE NOT NULL,
            to_date DATE NOT NULL,
            status VARCHAR DEFAULT 'success',
            record_count BIGINT DEFAULT 0,
            returned_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            source_sync_id VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    def get_existing_columns(table_name: str) -> set:
        try:
            rows = conn.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = ?;
            """, [table_name]).fetchall()
            return {row[0] for row in rows}
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return set()

    def add_column_if_missing(column_name: str, column_definition: str):
        existing_columns = get_existing_columns("upstox_ohlcv_chunk_sync_status")

        if column_name in existing_columns:
            return

        try:
            conn.execute(f"""
                ALTER TABLE upstox_ohlcv_chunk_sync_status
                ADD COLUMN {column_definition};
            """)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    add_column_if_missing("provider", "provider VARCHAR DEFAULT 'upstox'")
    add_column_if_missing("record_count", "record_count BIGINT DEFAULT 0")
    add_column_if_missing("returned_count", "returned_count BIGINT DEFAULT 0")
    add_column_if_missing("last_error", "last_error VARCHAR")
    add_column_if_missing("source_sync_id", "source_sync_id VARCHAR")
    add_column_if_missing("checked_at", "checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    add_column_if_missing("updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    existing_columns = get_existing_columns("upstox_ohlcv_chunk_sync_status")

    if "record_count" in existing_columns and "returned_count" in existing_columns:
        try:
            conn.execute("""
                UPDATE upstox_ohlcv_chunk_sync_status
                SET record_count = COALESCE(record_count, returned_count, 0),
                    returned_count = COALESCE(returned_count, record_count, 0)
                WHERE record_count IS NULL
                   OR returned_count IS NULL;
            """)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    for index_sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_upstox_ohlcv_chunk_status_lookup
        ON upstox_ohlcv_chunk_sync_status (
            provider,
            instrument_key,
            instrument_source,
            candle_mode,
            unit,
            interval_value,
            from_date,
            to_date,
            status
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_upstox_ohlcv_chunk_status_sync
        ON upstox_ohlcv_chunk_sync_status (source_sync_id);
        """
    ]:
        try:
            conn.execute(index_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    try:
        conn.commit()
    except Exception:
        pass

    OHLCV_CHUNK_STATUS_SCHEMA_READY = True


def normalize_ohlcv_key_date(value):
    if value in (None, ""):
        return None

    if hasattr(value, "date") and not isinstance(value, date):
        value = value.date()

    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]

    return str(value)[:10]


def get_ohlcv_chunk_status_key(
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    from_date,
    to_date
) -> tuple:
    return (
        safe_strip(source),
        safe_strip(mode),
        safe_strip(instrument_key),
        safe_strip(unit),
        int(interval_value or 1),
        normalize_ohlcv_key_date(from_date),
        normalize_ohlcv_key_date(to_date)
    )


def build_ohlcv_chunk_history_index(
    conn,
    source: str,
    config: dict,
    instruments: List[dict]
) -> set:
    if not config.get("skip_existing") or config.get("force_refresh"):
        return set()

    ensure_ohlcv_chunk_sync_status_table(conn)

    instrument_keys = unique_preserve_order([
        safe_strip(instrument.get("instrument_key"))
        for instrument in instruments
        if safe_strip(instrument.get("instrument_key"))
    ])

    if not instrument_keys:
        return set()

    interval_rows = []

    for mode in config["candle_modes"]:
        if source == OHLCV_EXPIRED_SOURCE and mode == OHLCV_INTRADAY_MODE:
            continue

        for interval_key in config["intervals"]:
            interval = OHLCV_INTERVAL_OPTIONS.get(interval_key)

            if not interval:
                continue

            if source == OHLCV_EXPIRED_SOURCE and not interval.get("expired_interval"):
                continue

            if mode == OHLCV_INTRADAY_MODE and interval["unit"] in ("weeks", "months"):
                continue

            interval_rows.append((
                mode,
                interval["unit"],
                int(interval["interval_value"] or 1)
            ))

    if not interval_rows:
        return set()

    instrument_placeholders = ", ".join(["?"] * len(instrument_keys))
    history_index = set()

    for mode, unit, interval_value in interval_rows:
        rows = conn.execute(f"""
            SELECT
                instrument_source,
                candle_mode,
                instrument_key,
                unit,
                interval_value,
                from_date,
                to_date
            FROM upstox_ohlcv_chunk_sync_status
            WHERE provider = ?
              AND instrument_source = ?
              AND candle_mode = ?
              AND unit = ?
              AND interval_value = ?
              AND to_date >= TRY_CAST(? AS DATE)
              AND from_date <= TRY_CAST(? AS DATE)
              AND instrument_key IN ({instrument_placeholders})
              AND status = 'success';
        """, [
            UPSTOX_PROVIDER,
            source,
            mode,
            unit,
            interval_value,
            config["from_date"],
            config["to_date"],
            *instrument_keys
        ]).fetchall()

        for row in rows:
            if not row:
                continue

            history_index.add(get_ohlcv_chunk_status_key(
                source=row[0],
                mode=row[1],
                instrument_key=row[2],
                unit=row[3],
                interval_value=row[4],
                from_date=row[5],
                to_date=row[6]
            ))

    log_ohlcv_message(
        "Bulk indexed DB history check loaded "
        f"{len(history_index)} checked chunks for source={source}."
    )

    return history_index


def record_ohlcv_chunk_status(
    conn,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    from_date,
    to_date,
    status_value: str,
    record_count: int,
    sync_id: str,
    error_message: str = None
):
    ensure_ohlcv_chunk_sync_status_table(conn)

    conn.execute("""
        DELETE FROM upstox_ohlcv_chunk_sync_status
        WHERE provider = ?
          AND instrument_key = ?
          AND instrument_source = ?
          AND candle_mode = ?
          AND unit = ?
          AND interval_value = ?
          AND from_date = TRY_CAST(? AS DATE)
          AND to_date = TRY_CAST(? AS DATE);
    """, [
        UPSTOX_PROVIDER,
        instrument_key,
        source,
        mode,
        unit,
        int(interval_value or 1),
        from_date,
        to_date
    ])

    conn.execute("""
        INSERT INTO upstox_ohlcv_chunk_sync_status (
            provider,
            instrument_key,
            instrument_source,
            candle_mode,
            unit,
            interval_value,
            from_date,
            to_date,
            status,
            record_count,
            returned_count,
            last_error,
            source_sync_id,
            checked_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, TRY_CAST(? AS DATE), TRY_CAST(? AS DATE), ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """, [
        UPSTOX_PROVIDER,
        instrument_key,
        source,
        mode,
        unit,
        int(interval_value or 1),
        from_date,
        to_date,
        status_value,
        int(record_count or 0),
        int(record_count or 0),
        error_message,
        sync_id
    ])
# --- End Open Analytics OHLCV chunk history helpers ---


def build_ohlcv_saved_bounds_cache(
    conn,
    source: str,
    config: dict,
    instruments: List[dict]
) -> dict:
    instrument_keys = unique_preserve_order([
        safe_strip(instrument.get("instrument_key"))
        for instrument in instruments
        if safe_strip(instrument.get("instrument_key"))
    ])

    if not instrument_keys:
        return {}

    interval_rows = []

    for mode in config["candle_modes"]:
        for interval_key in config["intervals"]:
            interval = OHLCV_INTERVAL_OPTIONS.get(interval_key)

            if not interval:
                continue

            interval_rows.append((
                mode,
                interval["unit"],
                int(interval["interval_value"])
            ))

    if not interval_rows:
        return {}

    instrument_placeholders = ", ".join(["?"] * len(instrument_keys))
    cache = {}

    for mode, unit, interval_value in interval_rows:
        rows = conn.execute(f"""
            SELECT
                candles.candle_mode,
                candles.instrument_key,
                candles.unit,
                candles.interval_value,
                MIN(candles.candle_date) AS min_date,
                MAX(candles.candle_date) AS max_date,
                COUNT(1) AS row_count
            FROM upstox_ohlcv_candles candles
            WHERE candles.provider = ?
              AND candles.instrument_source = ?
              AND candles.candle_mode = ?
              AND candles.unit = ?
              AND candles.interval_value = ?
              AND candles.instrument_key IN ({instrument_placeholders})
            GROUP BY
                candles.candle_mode,
                candles.instrument_key,
                candles.unit,
                candles.interval_value;
        """, [
            UPSTOX_PROVIDER,
            source,
            mode,
            unit,
            int(interval_value or 0),
            *instrument_keys
        ]).fetchall()

        for row in rows:
            cache[(
                row[0],
                row[1],
                row[2],
                int(row[3] or 0)
            )] = {
                "min_date": row[4],
                "max_date": row[5],
                "count": int(row[6] or 0)
            }

    log_ohlcv_message(
        f"Bulk indexed DB check loaded saved OHLCV bounds for source={source}: "
        f"{len(cache)} instrument/mode/interval groups."
    )

    return cache

def get_saved_ohlcv_date_bounds(
    conn,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    saved_bounds_cache: Optional[dict] = None
) -> dict:
    cache_key = (
        mode,
        instrument_key,
        unit,
        int(interval_value or 0)
    )

    if saved_bounds_cache is not None:
        return saved_bounds_cache.get(cache_key, {
            "min_date": None,
            "max_date": None,
            "count": 0
        })

    return {
        "min_date": None,
        "max_date": None,
        "count": 0
    }


def should_skip_ohlcv_chunk_by_saved_bounds(
    conn,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    from_date: date,
    to_date: date,
    saved_bounds_cache: Optional[dict] = None
) -> bool:
    # Do not skip API calls using only MIN/MAX candle dates.
    # MIN/MAX can say a range is covered even when dates inside the range are missing.
    # Exact chunk history is still used for fast skipping, and duplicate candles are
    # removed before insert, so API calls can safely backfill missing candles.
    return False


def get_effective_ohlcv_date_range_for_instrument(
    conn,
    config: dict,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    saved_bounds_cache: Optional[dict] = None
) -> Optional[dict]:
    available_start_date = get_ohlcv_available_start_date(
        source=source,
        mode=mode,
        unit=unit
    )
    effective_from_date = max(config["from_date"], available_start_date)
    effective_to_date = config["to_date"]

    if effective_to_date < effective_from_date:
        return None

    if (
        config.get("skip_existing")
        and config.get("auto_date_range")
        and not config.get("from_date_was_provided")
    ):
        bounds = get_saved_ohlcv_date_bounds(
            conn=conn,
            source=source,
            mode=mode,
            instrument_key=instrument_key,
            unit=unit,
            interval_value=interval_value,
            saved_bounds_cache=saved_bounds_cache
        )
        saved_max_date = bounds.get("max_date")

        if saved_max_date:
            effective_from_date = max(
                effective_from_date,
                saved_max_date + timedelta(days=1)
            )

            if effective_from_date > effective_to_date:
                return None

    return {
        "from_date": effective_from_date,
        "to_date": effective_to_date
    }



def fetch_ohlcv_instruments(conn, source: str, config: dict) -> List[dict]:
    params = []

    if source == OHLCV_CURRENT_SOURCE:
        nse_type_placeholders = ", ".join(["?"] * len(OHLCV_CURRENT_NSE_EQUITY_TYPES))
        bse_type_placeholders = ", ".join(["?"] * len(OHLCV_CURRENT_BSE_EQUITY_TYPES))
        params.extend([
            f"{EQUITY_STOCK_ISIN_PREFIX}%",
            *OHLCV_CURRENT_NSE_EQUITY_TYPES,
            *OHLCV_CURRENT_BSE_EQUITY_TYPES
        ])

        where_sql = """
        WHERE instrument_key IS NOT NULL
          AND TRIM(instrument_key) <> ''
          AND UPPER(COALESCE(isin, '')) LIKE ?
          AND source_type = 'bod_complete'
          AND (
              (
                  UPPER(COALESCE(segment, '')) = 'NSE_EQ'
                  AND UPPER(COALESCE(instrument_type, '')) IN ({nse_type_placeholders})
              )
              OR
              (
                  UPPER(COALESCE(segment, '')) = 'BSE_EQ'
                  AND UPPER(COALESCE(instrument_type, '')) IN ({bse_type_placeholders})
              )
          )
        """.format(
            nse_type_placeholders=nse_type_placeholders,
            bse_type_placeholders=bse_type_placeholders
        )

        if config["single_instrument_key"]:
            where_sql += " AND instrument_key = ?"
            params.append(config["single_instrument_key"])

        limit_sql = ""

        if config["instrument_limit"]:
            limit_sql = "LIMIT ?"
            params.append(config["instrument_limit"])

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                isin,
                NULL AS expiry,
                instrument_type
            FROM upstox_instruments
            {where_sql}
            ORDER BY trading_symbol, instrument_key
            {limit_sql};
        """, params).fetchall()

        return [
            {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "name": row[2],
                "exchange": row[3],
                "segment": row[4],
                "isin": row[5],
                "expiry": row[6],
                "instrument_type": row[7]
            }
            for row in rows
        ]

    if source == OHLCV_EXPIRED_SOURCE:
        where_sql = "WHERE instrument_key IS NOT NULL AND TRIM(instrument_key) <> ''"

        if config["single_instrument_key"]:
            where_sql += " AND instrument_key = ?"
            params.append(config["single_instrument_key"])

        limit_sql = ""

        if config["instrument_limit"]:
            limit_sql = "LIMIT ?"
            params.append(config["instrument_limit"])

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                NULL AS isin,
                expiry,
                instrument_type
            FROM upstox_expired_instruments
            {where_sql}
            ORDER BY expiry DESC, trading_symbol, instrument_key
            {limit_sql};
        """, params).fetchall()

        return [
            {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "name": row[2],
                "exchange": row[3],
                "segment": row[4],
                "isin": row[5],
                "expiry": row[6],
                "instrument_type": row[7]
            }
            for row in rows
        ]

    return []

    if source == OHLCV_EXPIRED_SOURCE:
        where_sql = "WHERE instrument_key IS NOT NULL AND TRIM(instrument_key) <> ''"

        if config["single_instrument_key"]:
            where_sql += " AND instrument_key = ?"
            params.append(config["single_instrument_key"])

        limit_sql = ""

        if config["instrument_limit"]:
            limit_sql = "LIMIT ?"
            params.append(config["instrument_limit"])

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                NULL AS isin,
                expiry,
                instrument_type
            FROM upstox_expired_instruments
            {where_sql}
            ORDER BY expiry DESC, trading_symbol, instrument_key
            {limit_sql};
        """, params).fetchall()

        return [
            {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "name": row[2],
                "exchange": row[3],
                "segment": row[4],
                "isin": row[5],
                "expiry": row[6],
                "instrument_type": row[7]
            }
            for row in rows
        ]

    return []


def build_ohlcv_url(source: str, mode: str, instrument_key: str, interval: dict, from_date: date, to_date: date) -> str:
    encoded_instrument_key = urllib.parse.quote(instrument_key, safe="")

    if source == OHLCV_EXPIRED_SOURCE:
        expired_interval = interval.get("expired_interval")

        if not expired_interval:
            raise ValueError("Interval is not supported for expired OHLCV candles.")

        return (
            f"{UPSTOX_EXPIRED_HISTORICAL_URL}/"
            f"{encoded_instrument_key}/{expired_interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        )

    if mode == OHLCV_INTRADAY_MODE:
        return (
            f"{UPSTOX_CURRENT_INTRADAY_V3_URL}/"
            f"{encoded_instrument_key}/{interval['unit']}/{interval['interval_value']}"
        )

    return (
        f"{UPSTOX_CURRENT_HISTORICAL_V3_URL}/"
        f"{encoded_instrument_key}/{interval['unit']}/{interval['interval_value']}/"
        f"{to_date.isoformat()}/{from_date.isoformat()}"
    )


def upstox_http_get_json(url: str, token: str, timeout: int = OHLCV_REQUEST_TIMEOUT_SECONDS) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
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
            detail=f"Unable to call Upstox OHLCV API: {error}"
        )


def fetch_ohlcv_candles_with_retry(
    url: str,
    token: str,
    retry_count: int,
    retry_failed: bool,
    rate_limiter: UpstoxRollingRateLimiter,
    heartbeat_callback: Optional[Callable[[], None]] = None
) -> dict:
    attempts = retry_count if retry_failed else 1
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            rate_limiter.wait_for_slot(heartbeat_callback)
            return upstox_http_get_json(url=url, token=token)
        except HTTPException as error:
            last_error = error
            error_text = str(error.detail).lower()
            should_retry = (
                error.status_code in (408, 429, 500, 502, 503, 504)
                or "timeout" in error_text
                or "rate" in error_text
            )

            if not retry_failed or not should_retry or attempt >= attempts:
                raise

            sleep_seconds = get_rate_limit_retry_sleep_seconds(
                error,
                fallback_seconds=2 * attempt
            )
            print(f"Upstox OHLCV retry {attempt}/{attempts} after {sleep_seconds}s: {error.detail}")
            sleep_with_heartbeat(sleep_seconds, heartbeat_callback)

    if last_error:
        raise last_error

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to call Upstox OHLCV API."
    )


def extract_ohlcv_candles(response: dict) -> List[list]:
    if not isinstance(response, dict):
        return []

    data = response.get("data")

    if isinstance(data, dict) and isinstance(data.get("candles"), list):
        return data.get("candles")

    if isinstance(response.get("candles"), list):
        return response.get("candles")

    return []


def parse_ohlcv_timestamp(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None

    clean_value = str(value).strip()

    try:
        parsed = datetime.fromisoformat(clean_value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except Exception:
        pass

    try:
        return datetime.strptime(clean_value[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def normalize_ohlcv_candle_record(
    candle: list,
    source: str,
    mode: str,
    interval: dict,
    instrument: dict,
    sync_id: str
) -> Optional[dict]:
    if not isinstance(candle, list) or len(candle) < 6:
        return None

    candle_timestamp = parse_ohlcv_timestamp(candle[0])

    if not candle_timestamp:
        return None

    return {
        "provider": UPSTOX_PROVIDER,
        "instrument_source": source,
        "candle_mode": mode,
        "instrument_key": instrument.get("instrument_key"),
        "trading_symbol": instrument.get("trading_symbol"),
        "name": instrument.get("name"),
        "exchange": instrument.get("exchange"),
        "segment": instrument.get("segment"),
        "isin": instrument.get("isin"),
        "expiry": normalize_expiry_value(instrument.get("expiry")),
        "instrument_type": instrument.get("instrument_type"),
        "unit": interval["unit"],
        "interval_value": interval["interval_value"],
        "interval_label": interval["label"],
        "candle_timestamp": candle_timestamp,
        "candle_date": candle_timestamp.date(),
        "open_price": candle[1] if len(candle) > 1 else None,
        "high_price": candle[2] if len(candle) > 2 else None,
        "low_price": candle[3] if len(candle) > 3 else None,
        "close_price": candle[4] if len(candle) > 4 else None,
        "volume": candle[5] if len(candle) > 5 else 0,
        "open_interest": candle[6] if len(candle) > 6 else 0,
        "source_sync_id": sync_id,
        "raw_json": json.dumps(candle, ensure_ascii=False, default=str)
    }


def insert_ohlcv_candles(conn, records: List[dict]) -> int:
    if not records:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_ohlcv_candles (
            provider,
            instrument_source,
            candle_mode,
            instrument_key,
            trading_symbol,
            name,
            exchange,
            segment,
            isin,
            expiry,
            instrument_type,
            unit,
            interval_value,
            interval_label,
            candle_timestamp,
            candle_date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            open_interest,
            source_sync_id,
            raw_json,
            ingested_at,
            updated_at
        )
        SELECT
            ?, ?, ?, ?, ?, ?, ?, ?, ?, TRY_CAST(? AS DATE), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            TRY_CAST(? AS JSON), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            record.get("provider"),
            record.get("instrument_source"),
            record.get("candle_mode"),
            record.get("instrument_key"),
            record.get("trading_symbol"),
            record.get("name"),
            record.get("exchange"),
            record.get("segment"),
            record.get("isin"),
            record.get("expiry"),
            record.get("instrument_type"),
            record.get("unit"),
            record.get("interval_value"),
            record.get("interval_label"),
            record.get("candle_timestamp"),
            record.get("candle_date"),
            record.get("open_price"),
            record.get("high_price"),
            record.get("low_price"),
            record.get("close_price"),
            record.get("volume"),
            record.get("open_interest"),
            record.get("source_sync_id"),
            record.get("raw_json")
        )
        for record in records
    ])

    return len(records)


def insert_ohlcv_daily_compatibility_rows(conn, records: List[dict]) -> int:
    daily_records = [
        record
        for record in records
        if record.get("instrument_source") == OHLCV_CURRENT_SOURCE
        and record.get("candle_mode") == OHLCV_HISTORICAL_MODE
        and record.get("unit") == "days"
        and int(record.get("interval_value") or 0) == 1
    ]

    if not daily_records:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO ohlcv_daily (
            instrument_key,
            trading_symbol,
            date,
            open,
            high,
            low,
            close,
            volume,
            oi,
            ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, [
        (
            record.get("instrument_key"),
            record.get("trading_symbol") or "--",
            record.get("candle_date"),
            record.get("open_price"),
            record.get("high_price"),
            record.get("low_price"),
            record.get("close_price"),
            record.get("volume") or 0,
            record.get("open_interest") or 0
        )
        for record in daily_records
    ])

    return len(daily_records)



def log_ohlcv_message(message: str):
    print(f"[OHLCV] {message}", flush=True)


def count_ohlcv_records_for_sync(
    conn,
    sync_id: Optional[str],
    started_at: Optional[datetime] = None
) -> int:
    if not sync_id:
        return 0

    try:
        row = conn.execute("""
            SELECT COUNT(*)
            FROM upstox_ohlcv_candles
            WHERE source_sync_id = ?;
        """, [sync_id]).fetchone()

        return int(row[0] or 0) if row else 0

    except Exception as error:
        log_ohlcv_message(f"Unable to count saved records for sync {sync_id}: {error}")
        return 0

def filter_new_ohlcv_records(conn, records: List[dict]) -> List[dict]:
    if not records:
        return []

    try:
        conn.execute("DROP TABLE IF EXISTS temp_ohlcv_incoming_records")

        conn.execute("""
            CREATE TEMP TABLE temp_ohlcv_incoming_records (
                provider VARCHAR,
                instrument_source VARCHAR,
                candle_mode VARCHAR,
                instrument_key VARCHAR,
                trading_symbol VARCHAR,
                name VARCHAR,
                exchange VARCHAR,
                segment VARCHAR,
                isin VARCHAR,
                expiry VARCHAR,
                instrument_type VARCHAR,
                unit VARCHAR,
                interval_value INTEGER,
                interval_label VARCHAR,
                candle_timestamp TIMESTAMP,
                candle_date DATE,
                open_price DOUBLE,
                high_price DOUBLE,
                low_price DOUBLE,
                close_price DOUBLE,
                volume DOUBLE,
                open_interest DOUBLE,
                source_sync_id VARCHAR,
                raw_json VARCHAR
            );
        """)

        conn.executemany("""
            INSERT INTO temp_ohlcv_incoming_records (
                provider,
                instrument_source,
                candle_mode,
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                isin,
                expiry,
                instrument_type,
                unit,
                interval_value,
                interval_label,
                candle_timestamp,
                candle_date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                open_interest,
                source_sync_id,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, [
            (
                record.get("provider"),
                record.get("instrument_source"),
                record.get("candle_mode"),
                record.get("instrument_key"),
                record.get("trading_symbol"),
                record.get("name"),
                record.get("exchange"),
                record.get("segment"),
                record.get("isin"),
                record.get("expiry"),
                record.get("instrument_type"),
                record.get("unit"),
                int(record.get("interval_value") or 0),
                record.get("interval_label"),
                record.get("candle_timestamp"),
                record.get("candle_date"),
                record.get("open_price"),
                record.get("high_price"),
                record.get("low_price"),
                record.get("close_price"),
                record.get("volume"),
                record.get("open_interest"),
                record.get("source_sync_id"),
                record.get("raw_json")
            )
            for record in records
        ])

        rows = conn.execute("""
            SELECT
                incoming.provider,
                incoming.instrument_source,
                incoming.candle_mode,
                incoming.instrument_key,
                incoming.trading_symbol,
                incoming.name,
                incoming.exchange,
                incoming.segment,
                incoming.isin,
                incoming.expiry,
                incoming.instrument_type,
                incoming.unit,
                incoming.interval_value,
                incoming.interval_label,
                incoming.candle_timestamp,
                incoming.candle_date,
                incoming.open_price,
                incoming.high_price,
                incoming.low_price,
                incoming.close_price,
                incoming.volume,
                incoming.open_interest,
                incoming.source_sync_id,
                incoming.raw_json
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            provider,
                            instrument_source,
                            candle_mode,
                            instrument_key,
                            unit,
                            interval_value,
                            candle_timestamp
                        ORDER BY candle_timestamp
                    ) AS duplicate_rank
                FROM temp_ohlcv_incoming_records
            ) incoming
            LEFT JOIN upstox_ohlcv_candles existing
                ON existing.provider = incoming.provider
               AND existing.instrument_source = incoming.instrument_source
               AND existing.candle_mode = incoming.candle_mode
               AND existing.instrument_key = incoming.instrument_key
               AND existing.unit = incoming.unit
               AND existing.interval_value = incoming.interval_value
               AND existing.candle_timestamp = incoming.candle_timestamp
            WHERE incoming.duplicate_rank = 1
              AND existing.instrument_key IS NULL;
        """).fetchall()

        return [
            {
                "provider": row[0],
                "instrument_source": row[1],
                "candle_mode": row[2],
                "instrument_key": row[3],
                "trading_symbol": row[4],
                "name": row[5],
                "exchange": row[6],
                "segment": row[7],
                "isin": row[8],
                "expiry": row[9],
                "instrument_type": row[10],
                "unit": row[11],
                "interval_value": row[12],
                "interval_label": row[13],
                "candle_timestamp": row[14],
                "candle_date": row[15],
                "open_price": row[16],
                "high_price": row[17],
                "low_price": row[18],
                "close_price": row[19],
                "volume": row[20],
                "open_interest": row[21],
                "source_sync_id": row[22],
                "raw_json": row[23]
            }
            for row in rows
        ]

    finally:
        try:
            conn.execute("DROP TABLE IF EXISTS temp_ohlcv_incoming_records")
        except Exception:
            pass

def persist_ohlcv_records(conn, records: List[dict]) -> int:
    if not records:
        return 0

    new_records = filter_new_ohlcv_records(conn, records)

    if not new_records:
        log_ohlcv_message(
            "OHLCV batch skipped because all returned candles already exist in DuckDB."
        )
        return 0

    try:
        conn.execute("BEGIN TRANSACTION")
        insert_ohlcv_candles(conn, new_records)
        insert_ohlcv_daily_compatibility_rows(conn, new_records)
        conn.execute("COMMIT")
        return len(new_records)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def update_ohlcv_metrics_progress(conn, sync_id: str, metrics: dict):
    try:
        finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
    except Exception as error:
        print(f"Unable to update OHLCV progress metrics: {error}")


def sync_upstox_ohlcv_daily_service(
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
        "candles_inserted": 0,
        "candles_skipped": 0,
        "failed_instruments": 0
    }
    failed_items = []
    service_start_perf = time.perf_counter()
    first_api_call_logged = False

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        run_config = config or get_saved_ohlcv_options_for_run(conn)
        normalized_config = normalize_ohlcv_config(run_config)

        log_ohlcv_message(
            "Starting collection "
            f"sources={normalized_config['sources']} "
            f"modes={normalized_config['candle_modes']} "
            f"intervals={normalized_config['intervals']} "
            f"from={normalized_config['from_date']} "
            f"to={normalized_config['to_date']} "
            f"use_current_day={normalized_config['use_current_day']} "
            f"auto_date_range={normalized_config['auto_date_range']} "
            f"limit={normalized_config['instrument_limit'] or 'all'} "
            f"single={normalized_config['single_instrument_key'] or '--'}"
        )

        analytical_token = None
        access_token = None

        if OHLCV_CURRENT_SOURCE in normalized_config["sources"]:
            analytical_token = get_saved_upstox_analytical_token(conn)
            log_ohlcv_message("Analytical token loaded for current OHLCV.")

        if OHLCV_EXPIRED_SOURCE in normalized_config["sources"]:
            access_token = get_saved_upstox_access_token(conn)
            log_ohlcv_message("Access token loaded for expired OHLCV.")

        sync_id = create_sync_run(
            conn,
            OHLCV_SYNC_TYPE,
            "running",
            "OHLCV download started.",
            current_user=current_user
        )
        update_ohlcv_sync_run_options(conn, sync_id, normalized_config)

        log_ohlcv_message(f"Sync run created: {sync_id}")

        ensure_ohlcv_chunk_sync_status_table(conn)

        rate_limiter = UpstoxRollingRateLimiter()

        for source in normalized_config["sources"]:
            check_sync_cancelled(conn, sync_id)

            source_start_perf = time.perf_counter()
            instruments = fetch_ohlcv_instruments(conn, source, normalized_config)

            if not instruments:
                log_ohlcv_message(f"No instruments found for source={source}.")
                continue

            token = analytical_token if source == OHLCV_CURRENT_SOURCE else access_token

            if not safe_strip(token):
                token_name = "analytical token" if source == OHLCV_CURRENT_SOURCE else "access token"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Upstox {token_name} is missing. Save/refresh the Upstox connection token before running OHLCV."
                )

            log_ohlcv_message(
                f"Source {source}: {len(instruments)} instruments loaded "
                f"in {time.perf_counter() - source_start_perf:.3f}s."
            )

            source_api_calls_before = int(metrics.get("api_calls_attempted") or 0)
            source_skips_before = int(metrics.get("api_calls_skipped") or 0)

            bounds_start_perf = time.perf_counter()
            saved_bounds_cache = build_ohlcv_saved_bounds_cache(
                conn=conn,
                source=source,
                config=normalized_config,
                instruments=instruments
            )
            log_ohlcv_message(
                f"Saved bounds indexed DB check completed in "
                f"{time.perf_counter() - bounds_start_perf:.3f}s."
            )

            history_start_perf = time.perf_counter()
            chunk_history_index = build_ohlcv_chunk_history_index(
                conn=conn,
                source=source,
                config=normalized_config,
                instruments=instruments
            )
            log_ohlcv_message(
                f"Chunk history indexed DB check completed in "
                f"{time.perf_counter() - history_start_perf:.3f}s."
            )

            for instrument_index, instrument in enumerate(instruments, start=1):
                check_sync_cancelled(conn, sync_id)

                if instrument_index > 1 and normalized_config["batch_size"]:
                    if (instrument_index - 1) % normalized_config["batch_size"] == 0:
                        log_ohlcv_message(
                            "Batch pause "
                            f"after {instrument_index - 1} instruments "
                            f"for {normalized_config['batch_delay_seconds']}s."
                        )
                        sleep_with_heartbeat(
                            normalized_config["batch_delay_seconds"],
                            lambda: check_sync_cancelled(conn, sync_id)
                        )
                        check_sync_cancelled(conn, sync_id)

                instrument_key = safe_strip(instrument.get("instrument_key"))
                trading_symbol = safe_strip(instrument.get("trading_symbol")) or "--"

                if not instrument_key:
                    continue

                log_ohlcv_message(
                    f"Instrument {instrument_index}/{len(instruments)} "
                    f"{trading_symbol} ({instrument_key})"
                )

                for mode in normalized_config["candle_modes"]:
                    check_sync_cancelled(conn, sync_id)

                    if source == OHLCV_EXPIRED_SOURCE and mode == OHLCV_INTRADAY_MODE:
                        metrics["api_calls_skipped"] += 1
                        log_ohlcv_message(
                            f"Skipped {instrument_key}: expired intraday is not supported."
                        )
                        update_ohlcv_metrics_progress(conn, sync_id, metrics)
                        continue

                    for interval_key in normalized_config["intervals"]:
                        check_sync_cancelled(conn, sync_id)

                        interval = get_ohlcv_interval_definition(interval_key)

                        if source == OHLCV_EXPIRED_SOURCE and not interval.get("expired_interval"):
                            metrics["api_calls_skipped"] += 1
                            log_ohlcv_message(
                                f"Skipped {instrument_key}: expired interval {interval_key} is not supported."
                            )
                            update_ohlcv_metrics_progress(conn, sync_id, metrics)
                            continue

                        if mode == OHLCV_INTRADAY_MODE and interval["unit"] in ("weeks", "months"):
                            metrics["api_calls_skipped"] += 1
                            log_ohlcv_message(
                                f"Skipped {instrument_key}: intraday interval {interval_key} is not supported."
                            )
                            update_ohlcv_metrics_progress(conn, sync_id, metrics)
                            continue

                        effective_range = get_effective_ohlcv_date_range_for_instrument(
                            conn=conn,
                            config=normalized_config,
                            source=source,
                            mode=mode,
                            instrument_key=instrument_key,
                            unit=interval["unit"],
                            interval_value=interval["interval_value"],
                            saved_bounds_cache=saved_bounds_cache
                        )

                        if not effective_range:
                            metrics["api_calls_skipped"] += 1
                            log_ohlcv_message(
                                f"Skipped {instrument_key}: saved data already reaches "
                                f"{normalized_config['to_date']} for {source} {mode} {interval_key}."
                            )
                            update_ohlcv_metrics_progress(conn, sync_id, metrics)
                            continue

                        chunks = split_ohlcv_date_range(
                            from_date=effective_range["from_date"],
                            to_date=effective_range["to_date"],
                            unit=interval["unit"],
                            interval_value=interval["interval_value"],
                            source=source
                        )

                        if mode == OHLCV_INTRADAY_MODE:
                            chunks = [
                                {
                                    "from_date": effective_range["to_date"],
                                    "to_date": effective_range["to_date"]
                                }
                            ]

                        for chunk_index, chunk in enumerate(chunks, start=1):
                            check_sync_cancelled(conn, sync_id)

                            chunk_from = chunk["from_date"]
                            chunk_to = chunk["to_date"]
                            chunk_status_key = get_ohlcv_chunk_status_key(
                                source=source,
                                mode=mode,
                                instrument_key=instrument_key,
                                unit=interval["unit"],
                                interval_value=interval["interval_value"],
                                from_date=chunk_from,
                                to_date=chunk_to
                            )

                            if normalized_config["skip_existing"] and chunk_status_key in chunk_history_index:
                                skipped_days = (chunk_to - chunk_from).days + 1
                                metrics["api_calls_skipped"] += 1
                                metrics["candles_skipped"] += skipped_days
                                log_ohlcv_message(
                                    f"Skipped API call {instrument_key} {source} {mode} "
                                    f"{interval_key} {chunk_from} to {chunk_to}: chunk history already checked."
                                )
                                update_ohlcv_metrics_progress(conn, sync_id, metrics)
                                continue

                            if normalized_config["skip_existing"] and should_skip_ohlcv_chunk_by_saved_bounds(
                                conn=conn,
                                source=source,
                                mode=mode,
                                instrument_key=instrument_key,
                                unit=interval["unit"],
                                interval_value=interval["interval_value"],
                                from_date=chunk_from,
                                to_date=chunk_to,
                                saved_bounds_cache=saved_bounds_cache
                            ):
                                skipped_days = (chunk_to - chunk_from).days + 1
                                metrics["api_calls_skipped"] += 1
                                metrics["candles_skipped"] += skipped_days
                                log_ohlcv_message(
                                    f"Skipped API call {instrument_key} {source} {mode} "
                                    f"{interval_key} {chunk_from} to {chunk_to}: saved date range already covers it."
                                )
                                update_ohlcv_metrics_progress(conn, sync_id, metrics)
                                continue

                            url = build_ohlcv_url(
                                source=source,
                                mode=mode,
                                instrument_key=instrument_key,
                                interval=interval,
                                from_date=chunk_from,
                                to_date=chunk_to
                            )

                            try:
                                if not first_api_call_logged:
                                    first_api_call_logged = True
                                    log_ohlcv_message(
                                        "First OHLCV API call reached after "
                                        f"{time.perf_counter() - service_start_perf:.3f}s."
                                    )

                                log_ohlcv_message(
                                    f"API {source} {mode} {interval_key} "
                                    f"chunk {chunk_index}/{len(chunks)} "
                                    f"{instrument_key} {chunk_from} to {chunk_to}"
                                )

                                response = fetch_ohlcv_candles_with_retry(
                                    url=url,
                                    token=token,
                                    retry_count=normalized_config["retry_count"],
                                    retry_failed=normalized_config["retry_failed"],
                                    rate_limiter=rate_limiter,
                                    heartbeat_callback=lambda: check_sync_cancelled(conn, sync_id)
                                )
                                metrics["api_calls_attempted"] += 1

                                candles = extract_ohlcv_candles(response)

                                if not candles:
                                    log_ohlcv_message(
                                        f"API returned 0 candles for {instrument_key} {source} {mode} "
                                        f"{interval_key} {chunk_from} to {chunk_to}."
                                    )

                                records = []

                                for candle in candles:
                                    normalized_record = normalize_ohlcv_candle_record(
                                        candle=candle,
                                        source=source,
                                        mode=mode,
                                        interval=interval,
                                        instrument=instrument,
                                        sync_id=sync_id
                                    )

                                    if normalized_record:
                                        records.append(normalized_record)

                                inserted_records = persist_ohlcv_records(conn, records)

                                record_ohlcv_chunk_status(
                                    conn=conn,
                                    source=source,
                                    mode=mode,
                                    instrument_key=instrument_key,
                                    unit=interval["unit"],
                                    interval_value=interval["interval_value"],
                                    from_date=chunk_from,
                                    to_date=chunk_to,
                                    status_value="success",
                                    record_count=inserted_records,
                                    sync_id=sync_id,
                                    error_message=None
                                )
                                chunk_history_index.add(chunk_status_key)

                                if inserted_records:
                                    total_records += inserted_records
                                    metrics["candles_inserted"] += inserted_records

                                log_ohlcv_message(
                                    f"Saved {inserted_records} OHLCV rows for "
                                    f"{instrument_key} {source} {mode} {interval_key} "
                                    f"{chunk_from} to {chunk_to}. "
                                    f"Total saved={total_records}."
                                )

                                update_ohlcv_metrics_progress(conn, sync_id, metrics)

                                if normalized_config["request_delay_ms"]:
                                    sleep_with_heartbeat(
                                        normalized_config["request_delay_ms"] / 1000,
                                        lambda: check_sync_cancelled(conn, sync_id)
                                    )
                                    check_sync_cancelled(conn, sync_id)

                            except SyncCancelled:
                                raise
                            except HTTPException as error:
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass

                                metrics["failed_instruments"] += 1
                                failed_items.append({
                                    "instrument_key": instrument_key,
                                    "source": source,
                                    "mode": mode,
                                    "interval": interval_key,
                                    "from_date": chunk_from.isoformat(),
                                    "to_date": chunk_to.isoformat(),
                                    "error": error.detail
                                })
                                try:
                                    record_ohlcv_chunk_status(
                                        conn=conn,
                                        source=source,
                                        mode=mode,
                                        instrument_key=instrument_key,
                                        unit=interval["unit"],
                                        interval_value=interval["interval_value"],
                                        from_date=chunk_from,
                                        to_date=chunk_to,
                                        status_value="failed",
                                        record_count=0,
                                        sync_id=sync_id,
                                        error_message=str(error.detail)
                                    )
                                    conn.commit()
                                except Exception:
                                    try:
                                        conn.rollback()
                                    except Exception:
                                        pass
                                log_ohlcv_message(
                                    "API failed "
                                    f"{instrument_key} {source} {mode} {interval_key} "
                                    f"{chunk_from} to {chunk_to}: {error.detail}"
                                )
                                update_ohlcv_metrics_progress(conn, sync_id, metrics)
                                continue
                            except Exception as error:
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass

                                metrics["failed_instruments"] += 1
                                failed_items.append({
                                    "instrument_key": instrument_key,
                                    "source": source,
                                    "mode": mode,
                                    "interval": interval_key,
                                    "from_date": chunk_from.isoformat(),
                                    "to_date": chunk_to.isoformat(),
                                    "error": str(error)
                                })
                                log_ohlcv_message(
                                    "Save/API failed "
                                    f"{instrument_key} {source} {mode} {interval_key} "
                                    f"{chunk_from} to {chunk_to}: {error}"
                                )
                                update_ohlcv_metrics_progress(conn, sync_id, metrics)
                                continue

            source_api_calls_after = int(metrics.get("api_calls_attempted") or 0)
            source_skips_after = int(metrics.get("api_calls_skipped") or 0)
            log_ohlcv_message(
                f"Source {source} completed in {time.perf_counter() - source_start_perf:.3f}s: "
                f"api_calls={source_api_calls_after - source_api_calls_before}, "
                f"skipped={source_skips_after - source_skips_before}."
            )

        total_records = count_ohlcv_records_for_sync(conn, sync_id) or total_records
        metrics["candles_inserted"] = max(
            int(metrics.get("candles_inserted") or 0),
            int(total_records or 0)
        )

        status_text = "success" if not failed_items else "partial_success"
        message = "OHLCV downloaded successfully."

        if failed_items:
            failed_file = DATA_DIR / "upstox_ohlcv_failed_items.json"

            with open(failed_file, "w", encoding="utf-8") as output_file:
                json.dump(failed_items, output_file, ensure_ascii=False, indent=2, default=str)

            message = (
                "OHLCV downloaded with some failed instruments. "
                f"Failed items saved to {failed_file}."
            )

        finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
        finish_sync_run(
            conn,
            sync_id,
            status_text,
            message,
            total_records,
            started_at
        )

        log_ohlcv_message(
            f"Finished sync {sync_id}: status={status_text}, saved={total_records}, "
            f"api_calls={metrics['api_calls_attempted']}, skipped={metrics['api_calls_skipped']}, "
            f"failed={metrics['failed_instruments']}."
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

        saved_records = count_ohlcv_records_for_sync(conn, sync_id, started_at)
        total_records = max(total_records, saved_records)
        metrics["candles_inserted"] = max(
            int(metrics.get("candles_inserted") or 0),
            int(total_records or 0)
        )

        log_ohlcv_message(
            f"Cancellation received for sync {sync_id}. "
            f"Committed OHLCV rows preserved={total_records}."
        )

        if sync_id:
            finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "OHLCV download cancelled. Completed rows were saved.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "OHLCV download cancelled. Completed rows were saved.",
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
            saved_records = count_ohlcv_records_for_sync(conn, sync_id)
            total_records = max(total_records, saved_records)
            finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"OHLCV download failed: {error.detail}",
                total_records,
                started_at
            )

        log_ohlcv_message(f"Failed sync {sync_id}: {error.detail}")

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            saved_records = count_ohlcv_records_for_sync(conn, sync_id)
            total_records = max(total_records, saved_records)
            finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"OHLCV download failed: {error}",
                total_records,
                started_at
            )

        log_ohlcv_message(f"Failed sync {sync_id}: {error}")

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to download OHLCV: {error}"
        )

    finally:
        conn.close()
