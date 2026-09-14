"""Upstox IPO calendar collection and preview."""

from .common import *
from .news_ipo_service import ensure_upstox_news_ipo_tables, fetch_upstox_json_with_retry


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



