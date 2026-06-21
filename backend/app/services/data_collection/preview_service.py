# backend\app\services\data_collection\preview_service.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def build_market_holidays_preview_filters(
    search: str,
    holiday_type: str,
    exchange: str,
    trading_status: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_holiday_type = holiday_type.strip() if holiday_type else "all"
    clean_exchange = exchange.strip() if exchange else "all"
    clean_trading_status = trading_status.strip() if trading_status else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(description, '')) LIKE ?
                OR LOWER(COALESCE(holiday_type, '')) LIKE ?
                OR LOWER(CAST(COALESCE(closed_exchanges, '[]') AS VARCHAR)) LIKE ?
                OR LOWER(CAST(COALESCE(open_exchanges, '[]') AS VARCHAR)) LIKE ?
                OR CAST(holiday_date AS VARCHAR) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            f"%{clean_search}%"
        ])

    if clean_holiday_type != "all":
        where_clauses.append("holiday_type = ?")
        params.append(clean_holiday_type)

    if clean_exchange != "all":
        exchange_value = f"%{clean_exchange}%"
        where_clauses.append("""
            (
                CAST(COALESCE(closed_exchanges, '[]') AS VARCHAR) LIKE ?
                OR CAST(COALESCE(open_exchanges, '[]') AS VARCHAR) LIKE ?
            )
        """)
        params.extend([exchange_value, exchange_value])

    if clean_trading_status == "open":
        where_clauses.append("is_trading_day = TRUE")

    if clean_trading_status == "closed":
        where_clauses.append("is_trading_day = FALSE")

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_market_holidays_preview(row):
    return {
        "holiday_date": str(row[0]) if row[0] else None,
        "description": row[1],
        "holiday_type": row[2],
        "closed_exchanges": row[3],
        "open_exchanges": row[4],
        "is_trading_day": bool(row[5]),
        "source_provider": row[6],
        "synced_at": str(row[7]) if row[7] else None,
        "updated_at": str(row[8]) if row[8] else None
    }


def get_upstox_market_holidays_preview_service(
    search: str = "",
    holiday_type: str = "all",
    exchange: str = "all",
    trading_status: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_market_holidays_preview_filters(
            search=search,
            holiday_type=holiday_type,
            exchange=exchange,
            trading_status=trading_status
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_market_holidays
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                holiday_date,
                description,
                holiday_type,
                CAST(COALESCE(closed_exchanges, '[]') AS VARCHAR) AS closed_exchanges,
                CAST(COALESCE(open_exchanges, '[]') AS VARCHAR) AS open_exchanges,
                is_trading_day,
                source_provider,
                synced_at,
                updated_at
            FROM upstox_market_holidays
            {where_sql}
            ORDER BY holiday_date DESC
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_market_holidays_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def build_ohlcv_preview_filters(
    search: str,
    source: str,
    mode: str,
    interval: str,
    segment: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_source = source.strip() if source else "all"
    clean_mode = mode.strip() if mode else "all"
    clean_interval = interval.strip() if interval else "all"
    clean_segment = segment.strip() if segment else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(name, '')) LIKE ?
                OR LOWER(COALESCE(exchange, '')) LIKE ?
                OR LOWER(COALESCE(segment, '')) LIKE ?
                OR LOWER(COALESCE(instrument_type, '')) LIKE ?
                OR LOWER(COALESCE(instrument_source, '')) LIKE ?
                OR LOWER(COALESCE(candle_mode, '')) LIKE ?
                OR LOWER(COALESCE(interval_label, '')) LIKE ?
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
            search_value,
            search_value,
            search_value
        ])

    if clean_source != "all":
        where_clauses.append("instrument_source = ?")
        params.append(clean_source)

    if clean_mode != "all":
        where_clauses.append("candle_mode = ?")
        params.append(clean_mode)

    if clean_interval != "all":
        interval_key = normalize_ohlcv_interval_key(clean_interval)
        interval_definition = OHLCV_INTERVAL_OPTIONS.get(interval_key)

        if interval_definition:
            where_clauses.append("unit = ? AND interval_value = ?")
            params.extend([
                interval_definition["unit"],
                interval_definition["interval_value"]
            ])
        else:
            where_clauses.append("LOWER(COALESCE(interval_label, '')) = ?")
            params.append(clean_interval.lower())

    if clean_segment != "all":
        where_clauses.append("segment = ?")
        params.append(clean_segment)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_ohlcv_preview(row):
    return {
        "instrument_key": row[0],
        "trading_symbol": row[1],
        "source": row[2],
        "mode": row[3],
        "unit": row[4],
        "interval_value": row[5],
        "interval_label": row[6],
        "timestamp": str(row[7]) if row[7] else None,
        "date": str(row[8]) if row[8] else None,
        "open": row[9],
        "high": row[10],
        "low": row[11],
        "close": row[12],
        "volume": row[13],
        "open_interest": row[14],
        "exchange": row[15],
        "segment": row[16],
        "instrument_type": row[17],
        "expiry": str(row[18]) if row[18] else None,
        "name": row[19],
        "isin": row[20],
        "ingested_at": str(row[21]) if row[21] else None,
        "updated_at": str(row[22]) if row[22] else None
    }


def get_upstox_ohlcv_preview_service(
    search: str = "",
    source: str = "all",
    mode: str = "all",
    interval: str = "all",
    segment: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_ohlcv_preview_filters(
            search=search,
            source=source,
            mode=mode,
            interval=interval,
            segment=segment
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_ohlcv_candles
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                instrument_source,
                candle_mode,
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
                exchange,
                segment,
                instrument_type,
                expiry,
                name,
                isin,
                ingested_at,
                updated_at
            FROM upstox_ohlcv_candles
            {where_sql}
            ORDER BY candle_timestamp DESC, ingested_at DESC, instrument_key
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_ohlcv_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()

def normalize_page(value: int) -> int:
    try:
        page = int(value)
    except Exception:
        return 1

    return max(page, 1)


def normalize_page_size(value: int) -> int:
    try:
        page_size = int(value)
    except Exception:
        return 50

    if page_size < 10:
        return 10

    if page_size > 2000:
        return 2000

    return page_size


def build_preview_filters(
    search: str,
    source_type: str,
    segment: str,
    instrument_type: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_source_type = source_type.strip() if source_type else "all"
    clean_segment = segment.strip() if segment else "all"
    clean_instrument_type = instrument_type.strip() if instrument_type else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(name, '')) LIKE ?
                OR LOWER(COALESCE(segment, '')) LIKE ?
                OR LOWER(COALESCE(exchange, '')) LIKE ?
                OR LOWER(COALESCE(instrument_type, '')) LIKE ?
                OR LOWER(COALESCE(underlying_symbol, '')) LIKE ?
                OR LOWER(COALESCE(underlying_key, '')) LIKE ?
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
            search_value,
            search_value
        ])

    if clean_source_type != "all":
        where_clauses.append("source_type = ?")
        params.append(clean_source_type)

    if clean_segment != "all":
        where_clauses.append("segment = ?")
        params.append(clean_segment)

    if clean_instrument_type != "all":
        where_clauses.append("instrument_type = ?")
        params.append(clean_instrument_type)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_instrument_preview(row):
    return {
        "instrument_key": row[0],
        "trading_symbol": row[1],
        "name": row[2],
        "segment": row[3],
        "exchange": row[4],
        "instrument_type": row[5],
        "expiry": str(row[6]) if row[6] else None,
        "strike_price": row[7],
        "lot_size": row[8],
        "source_type": row[9],
        "underlying_key": row[10],
        "underlying_symbol": row[11],
        "synced_at": str(row[12]) if row[12] else None
    }


def get_upstox_instruments_preview_service(
    search: str = "",
    source_type: str = "all",
    segment: str = "all",
    instrument_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_preview_filters(
            search=search,
            source_type=source_type,
            segment=segment,
            instrument_type=instrument_type
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_instruments
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                segment,
                exchange,
                instrument_type,
                expiry,
                strike_price,
                lot_size,
                source_type,
                underlying_key,
                underlying_symbol,
                synced_at
            FROM upstox_instruments
            {where_sql}
            ORDER BY synced_at DESC, segment, trading_symbol
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_instrument_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def get_upstox_expired_instruments_preview_service(
    search: str = "",
    source_type: str = "all",
    segment: str = "all",
    instrument_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_preview_filters(
            search=search,
            source_type=source_type,
            segment=segment,
            instrument_type=instrument_type
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_expired_instruments
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                segment,
                exchange,
                instrument_type,
                expiry,
                strike_price,
                lot_size,
                source_type,
                underlying_key,
                underlying_symbol,
                synced_at
            FROM upstox_expired_instruments
            {where_sql}
            ORDER BY synced_at DESC, expiry DESC, segment, trading_symbol
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_instrument_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()
