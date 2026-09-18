"""ISIN master and exchange listings, sourced from the current Upstox universe."""
import json
import re
from datetime import datetime, date

MASTER = {
    "isin": "VARCHAR", "company_name": "VARCHAR", "short_name": "VARCHAR", "security_class": "VARCHAR", "instrument_type": "VARCHAR",
    "macro_sector": "VARCHAR", "sector": "VARCHAR", "industry": "VARCHAR", "basic_industry": "VARCHAR", "market_cap_bucket": "VARCHAR",
    "index_memberships": "VARCHAR",
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
INDEX = {"isin": "VARCHAR", "company_name": "VARCHAR", "index_code": "VARCHAR", "index_name": "VARCHAR", "effective_from": "DATE", "effective_to": "DATE", "is_current": "BOOLEAN"}
HISTORY = {"isin": "VARCHAR", "identifier_type": "VARCHAR", "old_value": "VARCHAR", "new_value": "VARCHAR", "effective_from": "DATE", "effective_to": "DATE", "change_reason": "VARCHAR"}
TYPE_MAPPING = {"exchange": "VARCHAR", "segment": "VARCHAR", "source_type": "VARCHAR", "security_type": "VARCHAR", "instrument_type": "VARCHAR", "gbo_type": "VARCHAR", "description": "VARCHAR", "mapping_source": "VARCHAR", "mapping_updated_at": "TIMESTAMP", "history_json": "VARCHAR", "is_active": "BOOLEAN", "source_updated_at": "TIMESTAMP"}
TABLES = {
    "securities": ("security_reference", MASTER, ["isin"]),
    "listings": ("security_listing_reference", LISTING, ["instrument_key"]),
    "indices": ("security_index_membership", INDEX, ["isin", "index_code", "effective_from"]),
    "identifiers": ("security_identifier_history", HISTORY, ["isin", "identifier_type", "old_value", "new_value", "effective_from"]),
    "types": ("security_type_mapping", TYPE_MAPPING, ["exchange", "segment", "source_type", "security_type"])
}
MASTER_EDITABLE = {"company_name", "short_name", "security_class", "macro_sector", "sector", "industry", "basic_industry", "market_cap_bucket", "listing_status", "is_active", "is_listed", "is_suspended", "is_delisted", "listing_date", "face_value", "classification_source"}
LISTING_EDITABLE = {"series", "listing_status", "is_active"}
TYPE_EDITABLE = {"instrument_type", "gbo_type", "description", "is_active"}


def default_type_mapping(exchange, source_type, security_type):
    """Return conservative normalized mappings based on exchange-published series."""
    source_type = source_type.upper()
    security_type = security_type.upper()
    if exchange == "BSE":
        mapping = {
            "E": ("ETF", "ETF", "BSE ETF group"),
            "F": ("DEBT", "FIXED_INCOME", "BSE fixed-income group"),
            "G": ("GOVERNMENT_SECURITY", "FIXED_INCOME", "BSE government-security group"),
            "IF": ("INVIT", "ALTERNATIVE_LISTED", "BSE infrastructure investment trust group"),
            "M": ("SME_EQUITY", "COMMON_EQUITY", "BSE SME equity group"),
            "MS": ("SME_EQUITY", "COMMON_EQUITY", "BSE SME equity group"),
            "MT": ("SME_EQUITY", "COMMON_EQUITY", "BSE SME trade-to-trade equity group"),
        }
        if source_type in mapping:
            return mapping[source_type]
        if source_type in {"A", "B", "P", "R", "T", "TS", "X", "XT", "Z", "ZP"}:
            return "EQUITY", "COMMON_EQUITY", "BSE equity trading group"
    if exchange == "NSE":
        if source_type in {"EQ", "BE", "BZ"}:
            return "EQUITY", "COMMON_EQUITY", "NSE fully paid equity/ETF series; review ETFs manually"
        if source_type in {"SM", "ST", "SZ"}:
            return "SME_EQUITY", "COMMON_EQUITY", "NSE SME equity series"
        if source_type in {"MF", "ME"}:
            return "MUTUAL_FUND", "FUND", "NSE mutual-fund unit series"
        if source_type == "IV":
            return "INVIT", "ALTERNATIVE_LISTED", "NSE InvIT unit series"
        if source_type in {"RR", "RT"}:
            return "REIT", "ALTERNATIVE_LISTED", "NSE REIT unit series"
        if source_type == "GB":
            return "GOLD_BOND", "FIXED_INCOME", "NSE sovereign gold-bond series"
        if source_type in {"GS", "SG", "TB"}:
            return "GOVERNMENT_SECURITY", "FIXED_INCOME", "NSE government-security series"
        if source_type.startswith("W"):
            return "WARRANT", "OTHER_SECURITY", "NSE convertible-warrant series"
    if security_type in {"SME", "IPO", "RELIST", "PCA", "NORMAL"}:
        return None, None, f"Upstox security status: {security_type}"
    return None, None, None

def is_equity_instrument(segment, instrument_type):
    segment = str(segment or "").strip().upper()
    return segment in {"NSE_EQ", "BSE_EQ"}


def ensure_reference_schema(conn):
    for table, columns, keys in TABLES.values():
        definition = ", ".join(f"{key} {kind}" for key, kind in columns.items())
        extra = ", manual_fields VARCHAR DEFAULT '[]'" if table in {"security_reference", "security_listing_reference"} else ""
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({definition}{extra}, PRIMARY KEY ({', '.join(keys)}))")
    mapping_columns = {row[1] for row in conn.execute("PRAGMA table_info('security_type_mapping')").fetchall()}
    if "source_type" not in mapping_columns:
        conn.execute("ALTER TABLE security_type_mapping RENAME COLUMN instrument_type TO source_type")
        conn.execute("ALTER TABLE security_type_mapping ADD COLUMN instrument_type VARCHAR")
        mapping_columns = {row[1] for row in conn.execute("PRAGMA table_info('security_type_mapping')").fetchall()}
    for column in ("mapping_source", "mapping_updated_at", "history_json"):
        if column not in mapping_columns:
            conn.execute(f"ALTER TABLE security_type_mapping ADD COLUMN {column} {TYPE_MAPPING[column]}")
    master_columns = {row[1] for row in conn.execute("PRAGMA table_info('security_reference')").fetchall()}
    if "index_memberships" not in master_columns:
        conn.execute("ALTER TABLE security_reference ADD COLUMN index_memberships VARCHAR")
    index_columns = {row[1] for row in conn.execute("PRAGMA table_info('security_index_membership')").fetchall()}
    if "company_name" not in index_columns:
        conn.execute("ALTER TABLE security_index_membership ADD COLUMN company_name VARCHAR")
    conn.execute("""
        UPDATE security_index_membership AS membership
        SET company_name = security.company_name
        FROM security_reference AS security
        WHERE security.isin = membership.isin
          AND membership.company_name IS DISTINCT FROM security.company_name
    """)


def refresh_security_index_memberships(conn):
    """Materialize current normalized memberships on each security for table use."""
    conn.execute("""
        UPDATE security_reference AS security
        SET index_memberships = memberships.value,
            record_updated_at = CASE
                WHEN COALESCE(security.index_memberships, '[]') <> memberships.value THEN CURRENT_TIMESTAMP
                ELSE security.record_updated_at
            END
        FROM (
            SELECT security.isin,
                   COALESCE(
                       '[' || STRING_AGG('"' || REPLACE(member.index_code, '"', '\\"') || '"', ',' ORDER BY member.index_code)
                           FILTER (WHERE member.index_code IS NOT NULL) || ']',
                       '[]'
                   ) AS value
            FROM security_reference AS security
            LEFT JOIN security_index_membership AS member
              ON member.isin = security.isin
             AND member.effective_from <= CURRENT_DATE
             AND (member.effective_to IS NULL OR member.effective_to >= CURRENT_DATE)
            GROUP BY security.isin
        ) AS memberships
        WHERE memberships.isin = security.isin
    """)


def mapping_history(value):
    try:
        history = json.loads(value or "[]")
        return history if isinstance(history, list) else []
    except (TypeError, ValueError):
        return []


def append_mapping_history(old, record, action, source, changed_fields=None, occurred_at=None, actor=None, tab="Security Type Mapping"):
    """Append a compact JSON audit event and return the serialized history."""
    history = mapping_history((old or {}).get("history_json"))
    tracked = changed_fields or ["instrument_type", "gbo_type", "description", "is_active"]
    changes = {
        field: {"from": (old or {}).get(field), "to": record.get(field)}
        for field in tracked if (old or {}).get(field) != record.get(field)
    }
    if not old or not history or changes:
        history.append({
            "at": (occurred_at or datetime.now()).isoformat(),
            "action": action,
            "source": source,
            "actor": actor or ("System / Upstox Sync" if source == "UPSTOX_SYNC" else "System"),
            "tab": tab,
            "changes": changes,
        })
    return json.dumps(history, separators=(",", ":"), default=str)


def type_mapping_summary(conn):
    """Return completeness across active source-type combinations."""
    rows = conn.execute("""
        SELECT exchange,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE instrument_type IS NOT NULL AND TRIM(instrument_type) <> ''
                                  AND gbo_type IS NOT NULL AND TRIM(gbo_type) <> '') AS complete,
               COUNT(*) FILTER (WHERE (instrument_type IS NULL OR TRIM(instrument_type) = '')
                                  AND (gbo_type IS NULL OR TRIM(gbo_type) = '')) AS unmapped
        FROM security_type_mapping WHERE is_active IS TRUE
        GROUP BY exchange ORDER BY exchange
    """).fetchall()
    exchanges = [{"exchange": row[0], "total": row[1], "complete": row[2], "partial": row[1] - row[2] - row[3], "unmapped": row[3]} for row in rows]
    total = sum(row["total"] for row in exchanges)
    complete = sum(row["complete"] for row in exchanges)
    unmapped = sum(row["unmapped"] for row in exchanges)
    return {"total": total, "complete": complete, "partial": total - complete - unmapped,
            "unmapped": unmapped, "completion_percent": round(complete * 100 / total, 1) if total else 0,
            "exchanges": exchanges}


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


def valid_upstox_isin(value, supplied_value):
    """Validate an identifier from the trusted Upstox instrument master.

    Some exchange-issued Indian government-security identifiers are published as
    ISINs by Upstox/NSE/BSE but do not pass the generic ISO 6166 Luhn check. Keep
    manual input strict while accepting these source identifiers only when the
    instrument-key suffix and the separate ISIN field match exactly.
    """
    value = str(value or "").strip().upper()
    supplied = str(supplied_value or "").strip().upper()
    if not re.fullmatch(r"IN[A-Z0-9]{9}[0-9]", value):
        return None
    return value if supplied == value else None


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


def write_records(conn, table, columns, keys, records):
    if not records:
        return
    fields = list(columns)
    if any("manual_fields" in record for record in records):
        fields.append("manual_fields")
    updates = ', '.join(f"{key}=excluded.{key}" for key in fields if key not in keys)
    sql = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({','.join('?' for _ in fields)}) ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {updates}"
    values = [[record.get(key) for key in fields] for record in records]
    if hasattr(conn, "executemany"):
        conn.executemany(sql, values)
    else:
        for params in values:
            conn.execute(sql, params)


def sync_reference(conn):
    ensure_reference_schema(conn)
    current = row_dicts(conn, "upstox_instruments")
    # Dependency order: discover type mappings, then listings/security master,
    # then identifier history and profile enrichment.
    type_mapping_count = sync_type_mappings(conn, current)
    normalized_types = {
        (row["exchange"], row["segment"], row["source_type"], row["security_type"]): row.get("instrument_type")
        for row in row_dicts(conn, "security_type_mapping")
        if row.get("is_active") is True
    }
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
        key_isin = parts[1] if len(parts) == 2 else None
        supplied = str(row.get("isin") or "").strip().upper()
        isin = valid_isin(key_isin) or valid_upstox_isin(key_isin, supplied)
        if not isin or len(parts) != 2 or parts[0] != segment:
            skipped += 1
            continue
        row.update(isin=isin, exchange=segment.split('_')[0], segment=segment, instrument_key=instrument_key)
        groups.setdefault(isin, {})[instrument_key] = max([row, groups.get(isin, {}).get(instrument_key, row)], key=lambda item: (str(item.get("synced_at") or ""), str(item.get("trading_symbol") or "")))
    counts = {"securities": len(groups), "listings": sum(len(rows) for rows in groups.values()),
              "type_mappings": type_mapping_count, "identifier_changes": 0,
              "invalid_skipped": skipped, "added": 0, "updated": 0}
    now = datetime.now()
    pending = {"securities": [], "listings": [], "identifiers": []}
    def history(isin, kind, before, after, observed_at):
        if before and after and before != after:
            record = dict(isin=isin, identifier_type=kind, old_value=before, new_value=after, effective_from=observed_at.date(), effective_to=None, change_reason="Observed in Upstox instrument sync; effective date is observation date")
            pending["identifiers"].append(record)
            counts["identifier_changes"] += 1
    def persist(table_key, record, old, manual):
        record["manual_fields"] = json.dumps(sorted(manual))
        comparable = [key for key in TABLES[table_key][1] if key not in {"record_updated_at"}]
        if old and all(old.get(key) == record.get(key) for key in comparable):
            return
        pending[table_key].append(record)
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
        normalized_instrument_type = next((normalized_types.get((row["exchange"], row["segment"], str(row.get("instrument_type") or "").strip().upper(), str(row.get("security_type") or "").strip().upper())) for row in ordered if normalized_types.get((row["exchange"], row["segment"], str(row.get("instrument_type") or "").strip().upper(), str(row.get("security_type") or "").strip().upper()))), None)
        record.update(isin=isin, instrument_type=normalized_instrument_type, has_nse_listing=any(row["exchange"] == "NSE" for row in ordered), has_bse_listing=any(row["exchange"] == "BSE" for row in ordered), is_cross_listed=len({row["exchange"] for row in ordered}) > 1, listing_count=len(ordered), primary_exchange=primary["exchange"], primary_symbol=primary.get("trading_symbol"), primary_instrument_key=primary["instrument_key"], fno_eligible=bool(kinds), futures_available="FUT" in kinds, options_available=bool(kinds & {"CE", "PE"}), instrument_source="Upstox", source_updated_at=max([row.get("synced_at") or now for row in ordered] + ([old["source_updated_at"]] if old.get("source_updated_at") else [])), record_updated_at=now)
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
            listing.update(instrument_key=key, isin=isin, exchange=row["exchange"], segment=row["segment"], symbol=row.get("trading_symbol"), trading_symbol=row.get("trading_symbol"), exchange_token=row.get("exchange_token"), instrument_type=str(row.get("instrument_type") or "").strip().upper() or None, lot_size=row.get("lot_size"), tick_size=row.get("tick_size"), is_primary_listing=key == primary["instrument_key"])
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
    for table_key in ("listings", "securities", "identifiers"):
        write_records(conn, *TABLES[table_key], pending[table_key])
    counts["profile_updated"] = enrich_reference_from_profiles(conn)
    return counts


def sync_reference_if_empty(conn):
    """Seed new/empty reference tables from an existing instrument master."""
    ensure_reference_schema(conn)
    reference_count = conn.execute("SELECT COUNT(*) FROM security_reference").fetchone()[0]
    if reference_count:
        return None
    instrument_count = conn.execute("SELECT COUNT(*) FROM upstox_instruments").fetchone()[0]
    if not instrument_count:
        return None
    return sync_reference(conn)


def sync_type_mappings(conn, current=None):
    """Discover exchange type combinations without overwriting manual GBO mappings."""
    ensure_reference_schema(conn)
    current = current if current is not None else row_dicts(conn, "upstox_instruments")
    observed = {}
    for row in current:
        segment = str(row.get("segment") or "").strip().upper()
        if segment not in {"NSE_EQ", "BSE_EQ"}:
            continue
        exchange = str(row.get("exchange") or segment.split("_")[0]).strip().upper()
        source_type = str(row.get("instrument_type") or "").strip().upper()
        security_type = str(row.get("security_type") or "").strip().upper()
        if not exchange or not source_type:
            continue
        observed[(exchange, segment, source_type, security_type)] = row.get("synced_at") or datetime.now()
    existing = {
        (row["exchange"], row["segment"], row["source_type"], row["security_type"]): row
        for row in row_dicts(conn, "security_type_mapping")
    }
    for key, updated_at in observed.items():
        old = existing.get(key, {})
        default_instrument, default_gbo, default_description = default_type_mapping(key[0], key[2], key[3])
        inferred_source = old.get("mapping_source")
        if not inferred_source:
            if old and (old.get("instrument_type"), old.get("gbo_type")) != (default_instrument, default_gbo):
                inferred_source = "MANUAL_UPLOAD"
            else:
                inferred_source = "EXCHANGE_RULE" if default_instrument and default_gbo else "UNMAPPED"
        record = dict(exchange=key[0], segment=key[1], source_type=key[2], security_type=key[3],
                      instrument_type=old.get("instrument_type") or default_instrument,
                      gbo_type=old.get("gbo_type") or default_gbo,
                      description=old.get("description") or default_description,
                      mapping_source=inferred_source,
                      mapping_updated_at=old.get("mapping_updated_at") or datetime.now(),
                      is_active=True, source_updated_at=updated_at)
        action = "DISCOVERED" if not old else "REACTIVATED" if old.get("is_active") is False else "BASELINE"
        record["history_json"] = append_mapping_history(old, record, action, "UPSTOX_SYNC", occurred_at=updated_at)
        write_record(conn, *TABLES["types"], record)
    for key, old in existing.items():
        if key not in observed and old.get("is_active") is not False:
            record = dict(old, is_active=False, mapping_updated_at=datetime.now())
            record["history_json"] = append_mapping_history(old, record, "DEACTIVATED", "UPSTOX_SYNC")
            write_record(conn, *TABLES["types"], record)
    return len(observed)


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
