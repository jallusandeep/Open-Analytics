"""ISIN master and exchange listings, sourced from the current Upstox universe."""
import json
import re
from datetime import datetime, date

MASTER = {
    "isin": "VARCHAR", "company_name": "VARCHAR", "short_name": "VARCHAR", "security_class": "VARCHAR", "instrument_type": "VARCHAR",
    "macro_sector": "VARCHAR", "sector": "VARCHAR", "industry": "VARCHAR", "basic_industry": "VARCHAR", "market_cap_bucket": "VARCHAR",
    "has_nse_listing": "BOOLEAN", "has_bse_listing": "BOOLEAN", "is_cross_listed": "BOOLEAN", "listing_count": "INTEGER",
    "primary_exchange": "VARCHAR", "primary_symbol": "VARCHAR", "primary_instrument_key": "VARCHAR",
    "listing_status": "VARCHAR", "is_active": "BOOLEAN", "is_listed": "BOOLEAN", "is_suspended": "BOOLEAN", "is_delisted": "BOOLEAN",
    "listing_date": "DATE", "face_value": "DOUBLE", "fno_eligible": "BOOLEAN", "futures_available": "BOOLEAN", "options_available": "BOOLEAN",
    "classification_source": "VARCHAR", "instrument_source": "VARCHAR", "source_updated_at": "TIMESTAMP", "record_updated_at": "TIMESTAMP"
}
LISTING = {
    "instrument_key": "VARCHAR", "isin": "VARCHAR", "exchange": "VARCHAR", "segment": "VARCHAR", "symbol": "VARCHAR", "trading_symbol": "VARCHAR",
    "exchange_token": "VARCHAR", "instrument_type": "VARCHAR", "series": "VARCHAR", "lot_size": "BIGINT", "tick_size": "DOUBLE",
    "listing_status": "VARCHAR", "is_active": "BOOLEAN", "is_primary_listing": "BOOLEAN"
}
INDEX = {"isin": "VARCHAR", "index_code": "VARCHAR", "index_name": "VARCHAR", "effective_from": "DATE", "effective_to": "DATE", "is_current": "BOOLEAN"}
HISTORY = {"isin": "VARCHAR", "identifier_type": "VARCHAR", "old_value": "VARCHAR", "new_value": "VARCHAR", "effective_from": "DATE", "effective_to": "DATE", "change_reason": "VARCHAR"}
TABLES = {
    "securities": ("security_reference", MASTER, ["isin"]),
    "listings": ("security_listing_reference", LISTING, ["instrument_key"]),
    "indices": ("security_index_membership", INDEX, ["isin", "index_code", "effective_from"]),
    "identifiers": ("security_identifier_history", HISTORY, ["isin", "identifier_type", "old_value", "new_value", "effective_from"])
}
MASTER_EDITABLE = {"company_name", "short_name", "security_class", "macro_sector", "sector", "industry", "basic_industry", "market_cap_bucket", "listing_status", "is_active", "is_listed", "is_suspended", "is_delisted", "listing_date", "face_value", "classification_source"}
LISTING_EDITABLE = {"series", "listing_status", "is_active"}

def is_equity_instrument(segment, instrument_type):
    segment = str(segment or "").strip().upper()
    return segment in {"NSE_EQ", "BSE_EQ"}


def ensure_reference_schema(conn):
    for table, columns, keys in TABLES.values():
        definition = ", ".join(f"{key} {kind}" for key, kind in columns.items())
        extra = ", manual_fields VARCHAR DEFAULT '[]'" if table in {"security_reference", "security_listing_reference"} else ""
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({definition}{extra}, PRIMARY KEY ({', '.join(keys)}))")


def valid_isin(value):
    # ISO 6166 format and Luhn check digit; reject instrument tokens masquerading as ISINs.
    value = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value):
        return None
    digits = ''.join(str(ord(char) - 55) if char.isalpha() else char for char in value)
    total = 0
    for index, digit in enumerate(reversed(digits)):
        number = int(digit) * (2 if index % 2 else 1)
        total += number // 10 + number % 10
    return value if total % 10 == 0 else None


def row_dicts(conn, table):
    result = conn.execute(f"SELECT * FROM {table}")
    keys = [column[0] for column in result.description]
    return [dict(zip(keys, row)) for row in result.fetchall()]


def write_record(conn, table, columns, keys, record):
    fields = list(columns)
    if "manual_fields" in record:
        fields.append("manual_fields")
    updates = ', '.join(f"{key}=excluded.{key}" for key in fields if key not in keys)
    conn.execute(f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({','.join('?' for _ in fields)}) ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {updates}", [record.get(key) for key in fields])


def sync_reference(conn):
    ensure_reference_schema(conn)
    current = row_dicts(conn, "upstox_instruments")
    old_master = {row["isin"]: row for row in row_dicts(conn, "security_reference")}
    old_listings = {row["instrument_key"]: row for row in row_dicts(conn, "security_listing_reference")}
    groups, contracts = {}, {}
    skipped = 0
    for row in current:
        kind = str(row.get("instrument_type") or "").strip().upper()
        if kind in {"FUT", "CE", "PE"} and (not row.get("expiry") or row["expiry"] >= date.today()):
            underlying = str(row.get("underlying_key") or "").strip()
            if underlying:
                contracts.setdefault(underlying, set()).add(kind)
        segment = str(row.get("segment") or "").strip().upper()
        if not is_equity_instrument(segment, kind):
            continue
        instrument_key = str(row.get("instrument_key") or "").strip()
        parts = instrument_key.split('|')
        isin = valid_isin(parts[1] if len(parts) == 2 else row.get("isin"))
        supplied = str(row.get("isin") or "").strip().upper()
        if not isin or len(parts) != 2 or parts[0] != segment or (supplied and supplied != isin):
            skipped += 1
            continue
        row.update(isin=isin, exchange=segment.split('_')[0], segment=segment, instrument_key=instrument_key)
        groups.setdefault(isin, {})[instrument_key] = max([row, groups.get(isin, {}).get(instrument_key, row)], key=lambda item: (str(item.get("synced_at") or ""), str(item.get("trading_symbol") or "")))
    counts = {"securities": len(groups), "listings": sum(len(rows) for rows in groups.values()), "invalid_skipped": skipped, "added": 0, "updated": 0}
    now = datetime.now()
    def history(isin, kind, before, after, observed_at):
        if before and after and before != after:
            record = dict(isin=isin, identifier_type=kind, old_value=before, new_value=after, effective_from=observed_at.date(), effective_to=None, change_reason="Observed in Upstox instrument sync; effective date is observation date")
            write_record(conn, *TABLES["identifiers"], record)
    def persist(table_key, record, old, manual):
        record["manual_fields"] = json.dumps(sorted(manual))
        comparable = [key for key in TABLES[table_key][1] if key not in {"record_updated_at"}]
        if old and all(old.get(key) == record.get(key) for key in comparable):
            return
        write_record(conn, *TABLES[table_key], record)
        counts["updated" if old else "added"] += 1
    live_keys = set()
    for isin, listing_rows in groups.items():
        ordered = sorted(listing_rows.values(), key=lambda row: (row["exchange"] != "NSE", row["instrument_key"]))
        primary = ordered[0]
        old = old_master.get(isin, {})
        manual = set(json.loads(old.get("manual_fields") or "[]"))
        record = {key: old.get(key) for key in MASTER}
        for key, value in {"company_name": primary.get("name"), "short_name": primary.get("short_name")}.items():
            if key not in manual:
                if key == "company_name":
                    history(isin, "COMPANY_NAME", old.get(key), value, primary.get("synced_at") or now)
                record[key] = value
        kinds = set().union(*(contracts.get(row["instrument_key"], set()) for row in ordered))
        record.update(isin=isin, instrument_type="EQ", has_nse_listing=any(row["exchange"] == "NSE" for row in ordered), has_bse_listing=any(row["exchange"] == "BSE" for row in ordered), is_cross_listed=len({row["exchange"] for row in ordered}) > 1, listing_count=len(ordered), primary_exchange=primary["exchange"], primary_symbol=primary.get("trading_symbol"), primary_instrument_key=primary["instrument_key"], fno_eligible=bool(kinds), futures_available="FUT" in kinds, options_available=bool(kinds & {"CE", "PE"}), instrument_source="Upstox", source_updated_at=max([row.get("synced_at") or now for row in ordered] + ([old["source_updated_at"]] if old.get("source_updated_at") else [])), record_updated_at=now)
        for key, value in {"listing_status": "ACTIVE", "is_active": True, "is_listed": True}.items():
            if key not in manual:
                record[key] = value
        # Absence from current instruments is not evidence of suspension or delisting.
        persist("securities", record, old, manual)
        for row in ordered:
            key = row["instrument_key"]
            live_keys.add(key)
            old = old_listings.get(key, {})
            manual = set(json.loads(old.get("manual_fields") or "[]"))
            raw = json.loads(row.get("raw_json") or "{}") if isinstance(row.get("raw_json"), str) else (row.get("raw_json") or {})
            raw = raw if isinstance(raw, dict) else {}
            listing = {field: old.get(field) for field in LISTING}
            listing.update(instrument_key=key, isin=isin, exchange=row["exchange"], segment=row["segment"], symbol=row.get("trading_symbol"), trading_symbol=row.get("trading_symbol"), exchange_token=row.get("exchange_token"), instrument_type="EQ", lot_size=row.get("lot_size"), tick_size=row.get("tick_size"), is_primary_listing=key == primary["instrument_key"])
            for field, value in {"series": raw.get("series"), "listing_status": "ACTIVE", "is_active": True}.items():
                if field not in manual:
                    listing[field] = value
            history(isin, "SYMBOL:" + row["exchange"], old.get("trading_symbol"), listing["trading_symbol"], row.get("synced_at") or now)
            persist("listings", listing, old, manual)
    for key, old in old_listings.items():
        if key not in live_keys:
            manual = set(json.loads(old.get("manual_fields") or "[]"))
            record = dict(old, is_primary_listing=False)
            if "listing_status" not in manual:
                record["listing_status"] = "NOT_IN_CURRENT_INSTRUMENTS"
            if "is_active" not in manual:
                record["is_active"] = False
            persist("listings", record, old, manual)
    for isin, old in old_master.items():
        if isin not in groups:
            manual = set(json.loads(old.get("manual_fields") or "[]"))
            record = dict(old, has_nse_listing=False, has_bse_listing=False, is_cross_listed=False, listing_count=0, primary_exchange=None, primary_symbol=None, primary_instrument_key=None, futures_available=False, options_available=False, fno_eligible=False, record_updated_at=now)
            for key, value in {"listing_status": "NOT_IN_CURRENT_INSTRUMENTS", "is_active": False}.items():
                if key not in manual:
                    record[key] = value
            persist("securities", record, old, manual)
    counts["profile_updated"] = enrich_reference_from_profiles(conn)
    return counts


def migrate_legacy_reference(conn):
    if not conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='reference_equity_details'").fetchone()[0]:
        return
    for old in sorted(row_dicts(conn, "reference_equity_details"), key=lambda row: (row["exchange"] != "NSE", row["isin"])):
        isin = valid_isin(old["isin"])
        if not isin or not old.get("name"):
            continue
        existing = conn.execute("SELECT company_name, manual_fields FROM security_reference WHERE isin=?", [isin]).fetchone()
        if not existing:
            record = dict(isin=isin, company_name=old['name'], listing_count=0, instrument_source='Legacy upload', listing_status='NOT_IN_CURRENT_INSTRUMENTS', manual_fields=json.dumps(['company_name']), record_updated_at=datetime.now())
            write_record(conn, *TABLES['securities'], record)
        elif 'company_name' not in json.loads(existing[1] or '[]'):
            conn.execute("UPDATE security_reference SET company_name=?, manual_fields=?, record_updated_at=CURRENT_TIMESTAMP WHERE isin=?", [old["name"], json.dumps(['company_name']), isin])


def enrich_reference_from_profiles(conn):
    if not conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='upstox_company_fundamentals'").fetchone()[0]:
        return 0
    rows = conn.execute("""SELECT UPPER(TRIM(isin)), sector, synced_at FROM upstox_company_fundamentals
        WHERE endpoint='company_profile' AND data_status='success' AND NULLIF(TRIM(sector), '') IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (PARTITION BY UPPER(TRIM(isin)) ORDER BY synced_at DESC, fundamental_id DESC)=1""").fetchall()
    count = 0
    for isin, sector, updated in rows:
        old = conn.execute('SELECT sector, classification_source, manual_fields FROM security_reference WHERE isin=?', [isin]).fetchone()
        if not old or 'sector' in json.loads(old[2] or '[]') or old[0] == sector:
            continue
        manual = set(json.loads(old[2] or '[]'))
        source = old[1] if 'classification_source' in manual else 'Upstox Company Profile'
        conn.execute('UPDATE security_reference SET sector=?, classification_source=?, source_updated_at=GREATEST(source_updated_at, ?), record_updated_at=CURRENT_TIMESTAMP WHERE isin=?', [sector.strip(), source, updated, isin])
        count += 1
    return count
