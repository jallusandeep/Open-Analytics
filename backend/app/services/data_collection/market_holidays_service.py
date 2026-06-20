# backend\app\services\data_collection\market_holidays_service.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def get_optional_upstox_access_token(conn) -> str:
    row = conn.execute("""
        SELECT access_token, connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row:
        return ""

    connection_status = row[1] or "saved"

    if connection_status == "disconnected":
        return ""

    return normalize_upstox_token(row[0])


def upstox_market_holidays_http_get_json(
    url: str,
    token: str = "",
    timeout: int = REQUEST_TIMEOUT_SECONDS
) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "OpenAnalytics/1.0"
    }

    clean_token = normalize_upstox_token(token)

    if clean_token:
        headers["Authorization"] = f"Bearer {clean_token}"

    request = urllib.request.Request(url, headers=headers)

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
            detail=f"Unable to call Upstox Market Holidays API: {error}"
        )


def fetch_market_holidays_with_retry(
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
            return upstox_market_holidays_http_get_json(url=url, token=token)
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
                "Upstox Market Holidays retry "
                f"{attempt}/{attempts} after {sleep_seconds}s: {error.detail}"
            )
            sleep_with_heartbeat(sleep_seconds, heartbeat_callback)

    if last_error:
        raise last_error

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to call Upstox Market Holidays API."
    )


def extract_market_holiday_rows(response: dict) -> List[dict]:
    if not isinstance(response, dict):
        return []

    data = response.get("data")

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return [data]

    return []


def normalize_market_holiday_record(record: dict) -> Optional[dict]:
    plain_record = model_to_dict(record)

    if not isinstance(plain_record, dict):
        return None

    holiday_date = normalize_expiry_value(plain_record.get("date"))

    if not holiday_date:
        return None

    closed_exchanges = plain_record.get("closed_exchanges")
    open_exchanges = plain_record.get("open_exchanges")

    if not isinstance(closed_exchanges, list):
        closed_exchanges = []

    if not isinstance(open_exchanges, list):
        open_exchanges = []

    return {
        "holiday_date": holiday_date,
        "description": plain_record.get("description"),
        "holiday_type": plain_record.get("holiday_type"),
        "closed_exchanges": json.dumps(closed_exchanges, ensure_ascii=False, default=str),
        "open_exchanges": json.dumps(open_exchanges, ensure_ascii=False, default=str),
        "is_trading_day": bool(open_exchanges),
        "raw_json": json.dumps(plain_record, ensure_ascii=False, default=str)
    }


def insert_market_holiday_records(conn, records: List[dict]) -> int:
    if not records:
        return 0

    unique_records = {}

    for record in records:
        normalized = normalize_market_holiday_record(record)

        if normalized and normalized.get("holiday_date"):
            unique_records[normalized["holiday_date"]] = normalized

    rows = list(unique_records.values())

    if not rows:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_market_holidays (
            holiday_date,
            description,
            holiday_type,
            closed_exchanges,
            open_exchanges,
            is_trading_day,
            source_provider,
            raw_json,
            synced_at,
            updated_at
        )
        SELECT
            TRY_CAST(? AS DATE),
            ?,
            ?,
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            ?,
            'upstox',
            TRY_CAST(? AS JSON),
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP;
    """, [
        (
            row.get("holiday_date"),
            row.get("description"),
            row.get("holiday_type"),
            row.get("closed_exchanges"),
            row.get("open_exchanges"),
            bool(row.get("is_trading_day")),
            row.get("raw_json")
        )
        for row in rows
    ])

    return len(rows)


def sync_upstox_market_holidays_service(
    current_user: dict,
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

        access_token = get_optional_upstox_access_token(conn)

        sync_id = create_sync_run(
            conn,
            UPSTOX_MARKET_HOLIDAYS_SYNC_TYPE,
            "running",
            "Upstox market holidays sync started.",
            current_user=current_user
        )

        check_sync_cancelled(conn, sync_id)

        rate_limiter = UpstoxRollingRateLimiter()
        heartbeat_callback = lambda: check_sync_cancelled(conn, sync_id)

        try:
            response = fetch_market_holidays_with_retry(
                url=UPSTOX_MARKET_HOLIDAYS_URL,
                token=access_token,
                retry_count=UPSTOX_NEWS_DEFAULT_RETRY_COUNT,
                rate_limiter=rate_limiter,
                heartbeat_callback=heartbeat_callback
            )
        except HTTPException as error:
            if access_token and error.status_code in (400, 401, 403):
                response = fetch_market_holidays_with_retry(
                    url=UPSTOX_MARKET_HOLIDAYS_URL,
                    token="",
                    retry_count=UPSTOX_NEWS_DEFAULT_RETRY_COUNT,
                    rate_limiter=rate_limiter,
                    heartbeat_callback=heartbeat_callback
                )
            else:
                raise

        check_sync_cancelled(conn, sync_id)

        records = extract_market_holiday_rows(response)

        conn.execute("BEGIN TRANSACTION")
        total_records = insert_market_holiday_records(conn, records)
        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Upstox market holidays synced successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Upstox market holidays synced successfully.",
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
                "Upstox market holidays sync cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Upstox market holidays sync cancelled.",
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
                f"Upstox market holidays sync failed: {error.detail}",
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
                f"Upstox market holidays sync failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to sync Upstox market holidays: {error}"
        )

    finally:
        conn.close()
