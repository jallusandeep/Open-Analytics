# backend\app\services\data_collection\expired_instruments.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def import_upstox_client():
    try:
        import upstox_client
        return upstox_client
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Upstox Python SDK is not installed. "
                "Run: pip install -r backend/requirements.txt"
            )
        )


def create_expired_instrument_api(access_token: str):
    upstox_client = import_upstox_client()

    configuration = upstox_client.Configuration()
    configuration.access_token = normalize_upstox_token(access_token)

    return upstox_client.ExpiredInstrumentApi(
        upstox_client.ApiClient(configuration)
    )


def model_to_dict(value: Any):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [model_to_dict(item) for item in value]

    if isinstance(value, tuple):
        return [model_to_dict(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): model_to_dict(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }

    if hasattr(value, "to_dict"):
        try:
            return model_to_dict(value.to_dict())
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        return {
            str(key): model_to_dict(item)
            for key, item in value.__dict__.items()
            if not str(key).startswith("_")
        }

    return str(value)


def extract_api_data(response: Any):
    payload = model_to_dict(response)

    if isinstance(payload, dict):
        data = payload.get("data")

        if data is not None:
            return data

        if "expiries" in payload:
            return payload.get("expiries")

        if "expiry_dates" in payload:
            return payload.get("expiry_dates")

    return payload


def normalize_expiry_value(value: Any) -> Optional[str]:
    if value is None:
        return None

    clean_value = str(value).strip()

    if not clean_value:
        return None

    return clean_value[:10]


def first_available(data: dict, keys: List[str], default=None):
    for key in keys:
        value = data.get(key)

        if value is not None:
            return value

    return default


def normalize_expired_contract_record(
    record: dict,
    source_type: str,
    underlying_key: str,
    expiry_date: str
) -> dict:
    plain_record = model_to_dict(record)

    if not isinstance(plain_record, dict):
        plain_record = {
            "value": plain_record
        }

    expiry = first_available(
        plain_record,
        ["expiry", "expiry_date", "expiration_date"],
        expiry_date
    )

    instrument_type = first_available(
        plain_record,
        ["instrument_type", "type"],
        "OPT" if source_type == EXPIRED_SOURCE_OPTION else "FUT"
    )

    return {
        "instrument_key": first_available(plain_record, ["instrument_key", "instrumentKey"]),
        "segment": first_available(plain_record, ["segment"]),
        "name": first_available(plain_record, ["name"]),
        "exchange": first_available(plain_record, ["exchange"]),
        "instrument_type": instrument_type,
        "trading_symbol": first_available(
            plain_record,
            ["trading_symbol", "tradingSymbol", "symbol"]
        ),
        "exchange_token": first_available(
            plain_record,
            ["exchange_token", "exchangeToken"]
        ),
        "expiry": normalize_expiry_value(expiry),
        "strike_price": first_available(
            plain_record,
            ["strike_price", "strikePrice", "strike"]
        ),
        "lot_size": first_available(
            plain_record,
            ["lot_size", "lotSize"]
        ),
        "minimum_lot": first_available(
            plain_record,
            ["minimum_lot", "minimumLot"]
        ),
        "freeze_quantity": first_available(
            plain_record,
            ["freeze_quantity", "freezeQuantity"]
        ),
        "tick_size": first_available(
            plain_record,
            ["tick_size", "tickSize"]
        ),
        "weekly": first_available(plain_record, ["weekly"]),
        "underlying_key": first_available(
            plain_record,
            ["underlying_key", "underlyingKey"],
            underlying_key
        ),
        "underlying_symbol": first_available(
            plain_record,
            ["underlying_symbol", "underlyingSymbol"]
        ),
        "underlying_type": first_available(
            plain_record,
            ["underlying_type", "underlyingType"]
        ),
        "source_type": source_type,
        "raw_json": json.dumps(plain_record, ensure_ascii=False, default=str)
    }


def normalize_expiry_list(response: Any) -> List[str]:
    data = extract_api_data(response)

    values = []

    if isinstance(data, list):
        values = data
    elif isinstance(data, dict):
        for key in ("expiries", "expiry_dates", "expiryDates", "data"):
            if isinstance(data.get(key), list):
                values = data.get(key)
                break

    normalized = []

    for item in values:
        if isinstance(item, dict):
            expiry = first_available(
                item,
                ["expiry", "expiry_date", "expiryDate", "date"]
            )
        else:
            expiry = item

        expiry_value = normalize_expiry_value(expiry)

        if expiry_value:
            normalized.append(expiry_value)

    return sorted(set(normalized))


def normalize_contract_list(
    response: Any,
    source_type: str,
    underlying_key: str,
    expiry_date: str
) -> List[dict]:
    data = extract_api_data(response)

    if isinstance(data, dict):
        possible_rows = None

        for key in ("contracts", "instruments", "data"):
            if isinstance(data.get(key), list):
                possible_rows = data.get(key)
                break

        if possible_rows is None:
            possible_rows = [data]

        data = possible_rows

    if not isinstance(data, list):
        return []

    rows = []

    for item in data:
        normalized = normalize_expired_contract_record(
            record=item,
            source_type=source_type,
            underlying_key=underlying_key,
            expiry_date=expiry_date
        )

        if normalized.get("instrument_key"):
            rows.append(normalized)

    return rows


def unique_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    unique_values = []

    for value in values:
        clean_value = safe_strip(value)

        if clean_value and clean_value not in seen:
            seen.add(clean_value)
            unique_values.append(clean_value)

    return unique_values


def get_configured_expired_underlying_keys(
    conn,
    segment: str = DEFAULT_EXPIRED_UNDERLYING_SEGMENT,
    underlying_types: Optional[List[str]] = None
) -> List[str]:
    clean_segment = safe_strip(segment) or DEFAULT_EXPIRED_UNDERLYING_SEGMENT
    clean_underlying_types = unique_preserve_order(
        underlying_types or DEFAULT_EXPIRED_UNDERLYING_TYPES
    )

    if not clean_underlying_types:
        clean_underlying_types = DEFAULT_EXPIRED_UNDERLYING_TYPES.copy()

    type_placeholders = ", ".join(["?"] * len(clean_underlying_types))

    try:
        rows = conn.execute(f"""
            SELECT
                underlying_key,
                MIN(COALESCE(underlying_symbol, '')) AS symbol,
                MIN(COALESCE(underlying_type, '')) AS type,
                COUNT(1) AS contract_count
            FROM upstox_instruments
            WHERE segment = ?
              AND underlying_key IS NOT NULL
              AND TRIM(underlying_key) <> ''
              AND UPPER(COALESCE(underlying_type, '')) IN ({type_placeholders})
            GROUP BY underlying_key
            ORDER BY
                CASE
                    WHEN MIN(UPPER(COALESCE(underlying_type, ''))) = 'INDEX' THEN 0
                    ELSE 1
                END,
                MIN(COALESCE(underlying_symbol, '')),
                underlying_key;
        """, [clean_segment] + clean_underlying_types).fetchall()
    except Exception as error:
        print(f"Unable to discover expired underlying keys: {error}")
        rows = []

    discovered_keys = [row[0] for row in rows if row and safe_strip(row[0])]

    if discovered_keys:
        print(
            "Discovered expired underlying keys from current instruments: "
            f"{len(discovered_keys)}"
        )
        return unique_preserve_order(discovered_keys)

    print("Using fallback expired index underlying keys.")
    return DEFAULT_EXPIRED_UNDERLYING_KEYS.copy()


def normalize_sync_expired_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    raw_underlying_keys = payload.get("underlying_keys")

    if isinstance(raw_underlying_keys, str):
        underlying_keys = [
            value.strip()
            for value in raw_underlying_keys.split(",")
            if value.strip()
        ]
    elif isinstance(raw_underlying_keys, list):
        underlying_keys = [
            str(value).strip()
            for value in raw_underlying_keys
            if str(value).strip()
        ]
    else:
        underlying_keys = []

    raw_underlying_types = payload.get("underlying_types")

    if isinstance(raw_underlying_types, str):
        underlying_types = [
            value.strip().upper()
            for value in raw_underlying_types.split(",")
            if value.strip()
        ]
    elif isinstance(raw_underlying_types, list):
        underlying_types = [
            str(value).strip().upper()
            for value in raw_underlying_types
            if str(value).strip()
        ]
    else:
        underlying_types = DEFAULT_EXPIRED_UNDERLYING_TYPES.copy()

    underlying_types = unique_preserve_order(underlying_types)
    underlying_segment = safe_strip(
        payload.get("underlying_segment")
    ) or DEFAULT_EXPIRED_UNDERLYING_SEGMENT

    include_options = bool(payload.get("include_options", True))
    include_futures = bool(payload.get("include_futures", True))

    try:
        max_expiries = payload.get("max_expiries_per_underlying")

        if max_expiries in (None, "", 0, "0"):
            max_expiries = None
        else:
            max_expiries = max(1, int(max_expiries))
    except Exception:
        max_expiries = None

    try:
        request_pause_seconds = float(payload.get("request_pause_seconds", 0.15))
    except Exception:
        request_pause_seconds = 0.05

    if request_pause_seconds < 0:
        request_pause_seconds = 0

    force_refresh = bool(payload.get("force_refresh", False))

    return {
        "underlying_keys": underlying_keys,
        "underlying_segment": underlying_segment,
        "underlying_types": underlying_types,
        "include_options": include_options,
        "include_futures": include_futures,
        "max_expiries_per_underlying": max_expiries,
        "request_pause_seconds": request_pause_seconds,
        "force_refresh": force_refresh
    }


def write_expired_records_to_local_json(records: List[dict]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_file = EXPIRED_INSTRUMENT_FILE.with_suffix(".json.download")

    with open(temp_file, "w", encoding="utf-8") as output_file:
        json.dump(records, output_file, ensure_ascii=False, default=str)

    temp_file.replace(EXPIRED_INSTRUMENT_FILE)

    return EXPIRED_INSTRUMENT_FILE


def ensure_expired_contract_sync_status_table(conn):
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

    for index_sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_expired_contract_status_lookup
        ON upstox_expired_contract_sync_status (
            underlying_key,
            expiry,
            source_type,
            status
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_expired_contract_status_synced
        ON upstox_expired_contract_sync_status (synced_at);
        """
    ]:
        try:
            conn.execute(index_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def ensure_expired_underlying_sync_status_table(conn):
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

    for index_sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_expired_underlying_status_lookup
        ON upstox_expired_underlying_sync_status (
            underlying_key,
            status,
            include_options,
            include_futures
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_expired_underlying_status_synced
        ON upstox_expired_underlying_sync_status (synced_at);
        """
    ]:
        try:
            conn.execute(index_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def has_expired_underlying_been_fully_checked(
    conn,
    underlying_key: str,
    include_options: bool,
    include_futures: bool,
    max_expiries: Optional[int] = None,
    force_refresh: bool = False
) -> bool:
    if force_refresh or max_expiries:
        return False

    ensure_expired_underlying_sync_status_table(conn)

    row = conn.execute("""
        SELECT status
        FROM upstox_expired_underlying_sync_status
        WHERE underlying_key = ?
          AND status = 'success'
          AND (? = FALSE OR include_options = TRUE)
          AND (? = FALSE OR include_futures = TRUE)
        LIMIT 1;
    """, [underlying_key, include_options, include_futures]).fetchone()

    return bool(row)


def build_expired_underlying_status_index(
    conn,
    underlying_keys: List[str],
    include_options: bool,
    include_futures: bool,
    max_expiries: Optional[int] = None,
    force_refresh: bool = False
) -> set:
    if force_refresh or max_expiries:
        return set()

    clean_keys = unique_preserve_order([
        safe_strip(underlying_key)
        for underlying_key in underlying_keys
        if safe_strip(underlying_key)
    ])

    if not clean_keys:
        return set()

    ensure_expired_underlying_sync_status_table(conn)
    placeholders = ", ".join(["?"] * len(clean_keys))

    rows = conn.execute(f"""
        SELECT underlying_key
        FROM upstox_expired_underlying_sync_status
        WHERE underlying_key IN ({placeholders})
          AND status = 'success'
          AND (? = FALSE OR include_options = TRUE)
          AND (? = FALSE OR include_futures = TRUE);
    """, [
        *clean_keys,
        include_options,
        include_futures
    ]).fetchall()

    status_index = {
        safe_strip(row[0])
        for row in rows
        if row and safe_strip(row[0])
    }

    print(
        "Expired underlyings bulk indexed DB check loaded "
        f"{len(status_index)} fully checked underlyings."
    )

    return status_index


def record_expired_underlying_status(
    conn,
    underlying_key: str,
    status_value: str,
    expiry_count: int = 0,
    record_count: int = 0,
    include_options: bool = True,
    include_futures: bool = True,
    error_message: Optional[str] = None
):
    ensure_expired_underlying_sync_status_table(conn)

    conn.execute("""
        DELETE FROM upstox_expired_underlying_sync_status
        WHERE underlying_key = ?
          AND include_options = ?
          AND include_futures = ?;
    """, [underlying_key, include_options, include_futures])

    conn.execute("""
        INSERT INTO upstox_expired_underlying_sync_status (
            underlying_key,
            status,
            expiry_count,
            record_count,
            include_options,
            include_futures,
            last_error,
            synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, [
        underlying_key,
        status_value,
        int(expiry_count or 0),
        int(record_count or 0),
        bool(include_options),
        bool(include_futures),
        error_message
    ])


def has_expired_contract_group_been_checked(
    conn,
    underlying_key: str,
    expiry_date: str,
    source_type: str,
    force_refresh: bool = False
) -> bool:
    if force_refresh:
        return False

    existing_records = conn.execute("""
        SELECT COUNT(1)
        FROM upstox_expired_instruments
        WHERE underlying_key = ?
          AND expiry = TRY_CAST(? AS DATE)
          AND source_type = ?;
    """, [underlying_key, expiry_date, source_type]).fetchone()[0]

    if existing_records:
        return True

    ensure_expired_contract_sync_status_table(conn)

    status_row = conn.execute("""
        SELECT status
        FROM upstox_expired_contract_sync_status
        WHERE underlying_key = ?
          AND expiry = TRY_CAST(? AS DATE)
          AND source_type = ?
          AND status = 'success'
        LIMIT 1;
    """, [underlying_key, expiry_date, source_type]).fetchone()

    return bool(status_row)


def get_expired_contract_group_key(
    underlying_key: str,
    expiry_date: Any,
    source_type: str
) -> tuple:
    return (
        safe_strip(underlying_key),
        normalize_expiry_value(expiry_date),
        safe_strip(source_type)
    )


def build_expired_contract_group_status_index(
    conn,
    underlying_key: str,
    expiry_dates: List[Any],
    source_types: List[str],
    force_refresh: bool = False
) -> set:
    if force_refresh:
        return set()

    clean_underlying_key = safe_strip(underlying_key)
    clean_expiries = unique_preserve_order([
        normalize_expiry_value(expiry_date)
        for expiry_date in expiry_dates
        if normalize_expiry_value(expiry_date)
    ])
    clean_source_types = unique_preserve_order([
        safe_strip(source_type)
        for source_type in source_types
        if safe_strip(source_type)
    ])

    if not clean_underlying_key or not clean_expiries or not clean_source_types:
        return set()

    ensure_expired_contract_sync_status_table(conn)
    expiry_placeholders = ", ".join(["TRY_CAST(? AS DATE)"] * len(clean_expiries))
    source_type_placeholders = ", ".join(["?"] * len(clean_source_types))
    status_index = set()

    rows = conn.execute(f"""
        SELECT underlying_key, expiry, source_type
        FROM upstox_expired_instruments
        WHERE underlying_key = ?
          AND expiry IN ({expiry_placeholders})
          AND source_type IN ({source_type_placeholders})
        GROUP BY underlying_key, expiry, source_type;
    """, [
        clean_underlying_key,
        *clean_expiries,
        *clean_source_types
    ]).fetchall()

    for row in rows:
        status_index.add(get_expired_contract_group_key(row[0], row[1], row[2]))

    status_rows = conn.execute(f"""
        SELECT underlying_key, expiry, source_type
        FROM upstox_expired_contract_sync_status
        WHERE underlying_key = ?
          AND expiry IN ({expiry_placeholders})
          AND source_type IN ({source_type_placeholders})
          AND status = 'success';
    """, [
        clean_underlying_key,
        *clean_expiries,
        *clean_source_types
    ]).fetchall()

    for row in status_rows:
        status_index.add(get_expired_contract_group_key(row[0], row[1], row[2]))

    print(
        "Expired contracts bulk indexed DB check loaded "
        f"{len(status_index)} checked groups for {clean_underlying_key}."
    )

    return status_index


def record_expired_contract_group_status(
    conn,
    underlying_key: str,
    expiry_date: str,
    source_type: str,
    status_value: str,
    record_count: int = 0,
    error_message: Optional[str] = None
):
    ensure_expired_contract_sync_status_table(conn)

    conn.execute("""
        DELETE FROM upstox_expired_contract_sync_status
        WHERE underlying_key = ?
          AND expiry = TRY_CAST(? AS DATE)
          AND source_type = ?;
    """, [underlying_key, expiry_date, source_type])

    conn.execute("""
        INSERT INTO upstox_expired_contract_sync_status (
            underlying_key,
            expiry,
            source_type,
            status,
            record_count,
            last_error,
            synced_at
        )
        VALUES (?, TRY_CAST(? AS DATE), ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, [
        underlying_key,
        expiry_date,
        source_type,
        status_value,
        int(record_count or 0),
        error_message
    ])


def download_expired_instruments_with_sdk(
    conn,
    sync_id: str,
    access_token: str,
    config: Optional[dict] = None,
    heartbeat_callback: Optional[Callable[[], None]] = None
) -> dict:
    config = normalize_sync_expired_config(config)

    expired_api = create_expired_instrument_api(access_token)
    rate_limiter = UpstoxRollingRateLimiter()

    underlying_keys = config["underlying_keys"]

    if not underlying_keys:
        underlying_keys = get_configured_expired_underlying_keys(
            conn,
            segment=config["underlying_segment"],
            underlying_types=config["underlying_types"]
        )

    include_options = config["include_options"]
    include_futures = config["include_futures"]
    max_expiries = config["max_expiries_per_underlying"]
    request_pause_seconds = config["request_pause_seconds"]
    force_refresh = config["force_refresh"]

    if not include_options and not include_futures:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one expired instrument type: options or futures."
        )

    records = []
    failed_items = []
    group_statuses = []
    skipped_groups = 0
    underlying_statuses = []
    skipped_underlyings = 0
    persisted_records = 0
    was_cancelled = False

    underlying_status_index = build_expired_underlying_status_index(
        conn=conn,
        underlying_keys=underlying_keys,
        include_options=include_options,
        include_futures=include_futures,
        max_expiries=max_expiries,
        force_refresh=force_refresh
    )

    def persist_completed_expired_batch():
        nonlocal records
        nonlocal group_statuses
        nonlocal underlying_statuses
        nonlocal persisted_records

        if not records and not group_statuses and not underlying_statuses:
            return

        try:
            conn.execute("BEGIN TRANSACTION")
            saved_records = import_expired_instruments_records(
                conn=conn,
                sync_id=sync_id,
                records=records,
                group_statuses=group_statuses,
                underlying_statuses=underlying_statuses
            )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

        persisted_records += saved_records
        records = []
        group_statuses = []
        underlying_statuses = []

    print("Downloading Upstox expired instruments using Python SDK.")
    print(f"Underlying keys: {len(underlying_keys)}")

    try:
        for underlying_index, underlying_key in enumerate(underlying_keys, start=1):
            check_sync_cancelled(conn, sync_id)

            if safe_strip(underlying_key) in underlying_status_index:
                skipped_underlyings += 1
                print(
                    "Skipping expired instruments for "
                    f"{underlying_key}: full underlying already checked."
                )
                continue

            print(
                "Fetching expired expiries "
                f"{underlying_index}/{len(underlying_keys)}: {underlying_key}"
            )

            try:
                rate_limiter.wait_for_slot(heartbeat_callback)
                expiries_response = expired_api.get_expiries(underlying_key)
                expiries = normalize_expiry_list(expiries_response)
            except Exception as error:
                error_text = str(error)

                if is_upstox_expired_permission_error(error_text):
                    failed_items.append({
                        "underlying_key": underlying_key,
                        "expiry": None,
                        "type": "expiries",
                        "error": (
                            "Expired Instruments API access is not permitted "
                            f"for this underlying: {error_text}"
                        )
                    })
                    print(
                        "Skipping expired instruments for "
                        f"{underlying_key}: permission denied by Upstox."
                    )
                    continue

                if "401" in error_text or "UDAPI100050" in error_text or "Invalid token" in error_text:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Upstox token is invalid or expired. "
                            "Please save a fresh analytics token in Connections, "
                            "restart the backend, then run Expired Instruments again."
                        )
                    )

                failed_items.append({
                    "underlying_key": underlying_key,
                    "expiry": None,
                    "type": "expiries",
                    "error": error_text
                })
                print(f"Unable to fetch expiries for {underlying_key}: {error}")
                continue

            if max_expiries:
                expiries = expiries[:max_expiries]

            print(f"Expired expiries found for {underlying_key}: {len(expiries)}")
            underlying_failed = False
            underlying_record_count = 0
            source_types_to_check = []

            if include_options:
                source_types_to_check.append(EXPIRED_SOURCE_OPTION)

            if include_futures:
                source_types_to_check.append(EXPIRED_SOURCE_FUTURE)

            contract_group_status_index = build_expired_contract_group_status_index(
                conn=conn,
                underlying_key=underlying_key,
                expiry_dates=expiries,
                source_types=source_types_to_check,
                force_refresh=force_refresh
            )

            for expiry_index, expiry_date in enumerate(expiries, start=1):
                check_sync_cancelled(conn, sync_id)

                if include_options:
                    option_group_key = get_expired_contract_group_key(
                        underlying_key,
                        expiry_date,
                        EXPIRED_SOURCE_OPTION
                    )

                    if option_group_key in contract_group_status_index:
                        skipped_groups += 1
                        print(
                            f"Options {underlying_key} {expiry_date}: "
                            "already available, skipping API call."
                        )
                    else:
                        try:
                            rate_limiter.wait_for_slot(heartbeat_callback)
                            options_response = expired_api.get_expired_option_contracts(
                                underlying_key,
                                expiry_date
                            )

                            option_rows = normalize_contract_list(
                                response=options_response,
                                source_type=EXPIRED_SOURCE_OPTION,
                                underlying_key=underlying_key,
                                expiry_date=expiry_date
                            )

                            records.extend(option_rows)
                            underlying_record_count += len(option_rows)
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_OPTION,
                                "status": "success",
                                "record_count": len(option_rows),
                                "error": None
                            })
                            contract_group_status_index.add(option_group_key)

                            print(
                                f"Options {underlying_key} {expiry_date} "
                                f"({expiry_index}/{len(expiries)}): {len(option_rows)}"
                            )

                        except Exception as error:
                            error_text = str(error)
                            underlying_failed = True
                            failed_items.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "type": "options",
                                "error": error_text
                            })
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_OPTION,
                                "status": "failed",
                                "record_count": 0,
                                "error": error_text
                            })
                            print(
                                f"Unable to fetch expired option contracts for "
                                f"{underlying_key} {expiry_date}: {error}"
                            )

                    if request_pause_seconds:
                        sleep_with_heartbeat(request_pause_seconds, heartbeat_callback)

                check_sync_cancelled(conn, sync_id)

                if include_futures:
                    future_group_key = get_expired_contract_group_key(
                        underlying_key,
                        expiry_date,
                        EXPIRED_SOURCE_FUTURE
                    )

                    if future_group_key in contract_group_status_index:
                        skipped_groups += 1
                        print(
                            f"Futures {underlying_key} {expiry_date}: "
                            "already available, skipping API call."
                        )
                    else:
                        try:
                            rate_limiter.wait_for_slot(heartbeat_callback)
                            futures_response = expired_api.get_expired_future_contracts(
                                underlying_key,
                                expiry_date
                            )

                            future_rows = normalize_contract_list(
                                response=futures_response,
                                source_type=EXPIRED_SOURCE_FUTURE,
                                underlying_key=underlying_key,
                                expiry_date=expiry_date
                            )

                            records.extend(future_rows)
                            underlying_record_count += len(future_rows)
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_FUTURE,
                                "status": "success",
                                "record_count": len(future_rows),
                                "error": None
                            })
                            contract_group_status_index.add(future_group_key)

                            print(
                                f"Futures {underlying_key} {expiry_date} "
                                f"({expiry_index}/{len(expiries)}): {len(future_rows)}"
                            )

                        except Exception as error:
                            error_text = str(error)
                            underlying_failed = True
                            failed_items.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "type": "futures",
                                "error": error_text
                            })
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_FUTURE,
                                "status": "failed",
                                "record_count": 0,
                                "error": error_text
                            })
                            print(
                                f"Unable to fetch expired future contracts for "
                                f"{underlying_key} {expiry_date}: {error}"
                            )

                    if request_pause_seconds:
                        sleep_with_heartbeat(request_pause_seconds, heartbeat_callback)

            if not max_expiries:
                underlying_statuses.append({
                    "underlying_key": underlying_key,
                    "status": "failed" if underlying_failed else "success",
                    "expiry_count": len(expiries),
                    "record_count": underlying_record_count,
                    "include_options": include_options,
                    "include_futures": include_futures,
                    "error": "One or more contract groups failed." if underlying_failed else None
                })
                if not underlying_failed:
                    underlying_status_index.add(safe_strip(underlying_key))

            persist_completed_expired_batch()
    except SyncCancelled:
        was_cancelled = True
        print("Expired instrument download cancelled; saving completed downloaded records.")

    if failed_items:
        failed_file = DATA_DIR / "upstox_expired_instruments_failed_items.json"

        with open(failed_file, "w", encoding="utf-8") as output_file:
            json.dump(failed_items, output_file, ensure_ascii=False, indent=2, default=str)

        print(f"Expired instruments failed items saved: {failed_file}")

    unique_records = {}

    for record in records:
        instrument_key = record.get("instrument_key")
        source_type = record.get("source_type")
        expiry = record.get("expiry")
        unique_key = f"{source_type}|{expiry}|{instrument_key}"

        if instrument_key:
            unique_records[unique_key] = record

    final_records = list(unique_records.values())

    print(f"Expired instruments downloaded: {len(final_records)}")
    print(f"Expired contract API groups skipped as already available: {skipped_groups}")
    print(f"Expired underlyings skipped as fully checked: {skipped_underlyings}")

    if not final_records and failed_items:
        first_failure = failed_items[0]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "No expired instruments were downloaded. First failure: "
                f"{first_failure.get('underlying_key')} "
                f"{first_failure.get('type')}: {first_failure.get('error')}"
            )
        )

    return {
        "records": final_records,
        "group_statuses": group_statuses,
        "underlying_statuses": underlying_statuses,
        "persisted_records": persisted_records,
        "skipped_groups": skipped_groups,
        "skipped_underlyings": skipped_underlyings,
        "cancelled": was_cancelled
    }


def import_expired_instruments_records(
    conn,
    sync_id: str,
    records: List[dict],
    group_statuses: Optional[List[dict]] = None,
    underlying_statuses: Optional[List[dict]] = None,
    allow_cancelled_import: bool = False
) -> int:
    if not allow_cancelled_import:
        check_sync_cancelled(conn, sync_id)

    insert_started_at = time.time()
    unique_records = {}

    for record in records:
        instrument_key = safe_strip(record.get("instrument_key"))
        source_type = safe_strip(record.get("source_type"))
        expiry = normalize_expiry_value(record.get("expiry"))

        if not instrument_key or source_type not in (EXPIRED_SOURCE_OPTION, EXPIRED_SOURCE_FUTURE):
            continue

        if not expiry:
            continue

        unique_records[f"{source_type}|{expiry}|{instrument_key}"] = {
            **record,
            "instrument_key": instrument_key,
            "source_type": source_type,
            "expiry": expiry
        }

    deduped_records = list(unique_records.values())
    groups_to_replace = unique_preserve_order([
        f"{record.get('underlying_key')}|{record.get('expiry')}|{record.get('source_type')}"
        for record in deduped_records
    ])

    print(f"Expired rows valid for direct insert after Python de-dupe: {len(deduped_records)}")

    for group_key in groups_to_replace:
        underlying_key, expiry_date, source_type = group_key.rsplit("|", 2)

        conn.execute("""
            DELETE FROM upstox_expired_instruments
            WHERE underlying_key = ?
              AND expiry = TRY_CAST(? AS DATE)
              AND source_type = ?;
        """, [underlying_key, expiry_date, source_type])

    if not allow_cancelled_import:
        check_sync_cancelled(conn, sync_id)

    if deduped_records:
        conn.executemany("""
            INSERT INTO upstox_expired_instruments (
                instrument_key,
                segment,
                name,
                exchange,
                instrument_type,
                trading_symbol,
                exchange_token,
                expiry,
                strike_price,
                lot_size,
                minimum_lot,
                freeze_quantity,
                tick_size,
                weekly,
                underlying_key,
                underlying_symbol,
                underlying_type,
                source_type,
                raw_json,
                synced_at
            )
            SELECT
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                TRY_CAST(? AS DATE),
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
                CURRENT_TIMESTAMP;
        """, [
            (
                record.get("instrument_key"),
                record.get("segment"),
                record.get("name"),
                record.get("exchange"),
                record.get("instrument_type"),
                record.get("trading_symbol"),
                record.get("exchange_token"),
                record.get("expiry"),
                record.get("strike_price"),
                record.get("lot_size"),
                record.get("minimum_lot"),
                record.get("freeze_quantity"),
                record.get("tick_size"),
                record.get("weekly"),
                record.get("underlying_key"),
                record.get("underlying_symbol"),
                record.get("underlying_type"),
                record.get("source_type"),
                record.get("raw_json")
            )
            for record in deduped_records
        ])

    for group_status in group_statuses or []:
        record_expired_contract_group_status(
            conn,
            underlying_key=group_status.get("underlying_key"),
            expiry_date=group_status.get("expiry"),
            source_type=group_status.get("source_type"),
            status_value=group_status.get("status") or "failed",
            record_count=group_status.get("record_count") or 0,
            error_message=group_status.get("error")
        )

    for underlying_status in underlying_statuses or []:
        record_expired_underlying_status(
            conn,
            underlying_key=underlying_status.get("underlying_key"),
            status_value=underlying_status.get("status") or "failed",
            expiry_count=underlying_status.get("expiry_count") or 0,
            record_count=underlying_status.get("record_count") or 0,
            include_options=bool(underlying_status.get("include_options", True)),
            include_futures=bool(underlying_status.get("include_futures", True)),
            error_message=underlying_status.get("error")
        )

    print(f"DuckDB expired direct insert time: {round(time.time() - insert_started_at, 2)} seconds")

    return len(deduped_records)


def import_expired_instruments_from_local_file(conn, sync_id: str, local_file: Path) -> int:
    check_sync_cancelled(conn, sync_id)

    duckdb_path = normalize_duckdb_file_path(local_file)

    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired")

    read_started_at = time.time()

    print("Reading expired instrument JSON directly with DuckDB...")

    conn.execute(
        """
        CREATE TEMP TABLE temp_upstox_expired AS
        SELECT *
        FROM read_json(
            ?,
            format = 'array',
            maximum_object_size = 16777216,
            columns = {
                instrument_key: 'VARCHAR',
                segment: 'VARCHAR',
                name: 'VARCHAR',
                exchange: 'VARCHAR',
                instrument_type: 'VARCHAR',
                trading_symbol: 'VARCHAR',
                exchange_token: 'VARCHAR',
                expiry: 'VARCHAR',
                strike_price: 'DOUBLE',
                lot_size: 'BIGINT',
                minimum_lot: 'BIGINT',
                freeze_quantity: 'DOUBLE',
                tick_size: 'DOUBLE',
                weekly: 'BOOLEAN',
                underlying_key: 'VARCHAR',
                underlying_symbol: 'VARCHAR',
                underlying_type: 'VARCHAR',
                source_type: 'VARCHAR',
                raw_json: 'VARCHAR'
            }
        );
        """,
        [duckdb_path]
    )

    print(f"DuckDB expired JSON read time: {round(time.time() - read_started_at, 2)} seconds")

    check_sync_cancelled(conn, sync_id)

    total_rows = conn.execute("""
        SELECT COUNT(*)
        FROM temp_upstox_expired;
    """).fetchone()[0]

    print(f"Expired rows loaded into temp table: {total_rows}")

    insert_started_at = time.time()

    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired_valid")

    conn.execute("""
        CREATE TEMP TABLE temp_upstox_expired_valid AS
        SELECT *
        FROM (
            SELECT
                instrument_key,
                segment,
                name,
                exchange,
                instrument_type,
                trading_symbol,
                exchange_token,
                TRY_CAST(expiry AS DATE) AS expiry_date,
                strike_price,
                lot_size,
                minimum_lot,
                freeze_quantity,
                tick_size,
                weekly,
                underlying_key,
                underlying_symbol,
                underlying_type,
                source_type,
                TRY_CAST(raw_json AS JSON) AS raw_json,
                ROW_NUMBER() OVER (
                    PARTITION BY source_type, TRY_CAST(expiry AS DATE), instrument_key
                    ORDER BY trading_symbol
                ) AS duplicate_rank
            FROM temp_upstox_expired
            WHERE instrument_key IS NOT NULL
              AND TRIM(instrument_key) <> ''
              AND source_type IN (?, ?)
              AND TRY_CAST(expiry AS DATE) IS NOT NULL
        )
        WHERE duplicate_rank = 1;
    """, [EXPIRED_SOURCE_OPTION, EXPIRED_SOURCE_FUTURE])

    valid_rows = conn.execute("""
        SELECT COUNT(*)
        FROM temp_upstox_expired_valid;
    """).fetchone()[0]

    print(f"Expired rows valid for insert after de-dupe: {valid_rows}")

    conn.execute("""
        DELETE FROM upstox_expired_instruments
        WHERE EXISTS (
            SELECT 1
            FROM (
                SELECT DISTINCT
                    source_type,
                    underlying_key,
                    expiry_date
                FROM temp_upstox_expired_valid
            ) AS downloaded_groups
            WHERE downloaded_groups.source_type = upstox_expired_instruments.source_type
              AND COALESCE(downloaded_groups.underlying_key, '') = COALESCE(upstox_expired_instruments.underlying_key, '')
              AND downloaded_groups.expiry_date = upstox_expired_instruments.expiry
        );
    """)

    check_sync_cancelled(conn, sync_id)

    conn.execute("""
        INSERT INTO upstox_expired_instruments (
            instrument_key,
            segment,
            name,
            exchange,
            instrument_type,
            trading_symbol,
            exchange_token,
            expiry,
            strike_price,
            lot_size,
            minimum_lot,
            freeze_quantity,
            tick_size,
            weekly,
            underlying_key,
            underlying_symbol,
            underlying_type,
            source_type,
            raw_json,
            synced_at
        )
        SELECT
            instrument_key,
            segment,
            name,
            exchange,
            instrument_type,
            trading_symbol,
            exchange_token,
            expiry_date AS expiry,
            strike_price,
            lot_size,
            minimum_lot,
            freeze_quantity,
            tick_size,
            weekly,
            underlying_key,
            underlying_symbol,
            underlying_type,
            source_type,
            raw_json,
            CURRENT_TIMESTAMP AS synced_at
        FROM temp_upstox_expired_valid;
    """)

    print(f"DuckDB expired insert time: {round(time.time() - insert_started_at, 2)} seconds")

    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired_valid")
    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired")

    return int(valid_rows or 0)
