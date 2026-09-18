import csv
import json
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.database import get_connection
from app.dependencies import require_admin_or_super_admin


router = APIRouter(prefix="/reference-data", tags=["Reference Data"], dependencies=[Depends(require_admin_or_super_admin)])

EQUITY_SQL = """
    WITH current_equities AS (
        SELECT
            UPPER(COALESCE(NULLIF(TRIM(split_part(instrument_key, '|', 2)), ''), NULLIF(TRIM(isin), ''))) AS isin,
            trading_symbol, name, exchange, segment, synced_at,
            ROW_NUMBER() OVER (
                PARTITION BY UPPER(COALESCE(NULLIF(TRIM(split_part(instrument_key, '|', 2)), ''), NULLIF(TRIM(isin), ''))), exchange, segment
                ORDER BY synced_at DESC, trading_symbol
            ) AS row_number
        FROM upstox_instruments
        WHERE (UPPER(TRIM(instrument_type)) = 'EQ' AND UPPER(TRIM(segment)) = 'NSE_EQ')
           OR UPPER(TRIM(segment)) = 'BSE_EQ'
    ), live AS (
        SELECT current_equities.isin, current_equities.trading_symbol,
               COALESCE(NULLIF(reference_equity_details.name, ''), current_equities.name) AS name,
               current_equities.exchange, current_equities.segment
        FROM current_equities
        LEFT JOIN reference_equity_details ON reference_equity_details.isin = current_equities.isin
            AND reference_equity_details.exchange = current_equities.exchange
            AND reference_equity_details.segment = current_equities.segment
        WHERE current_equities.row_number = 1 AND current_equities.isin IS NOT NULL
    ), external AS (
        SELECT reference_equity_details.isin, reference_equity_details.trading_symbol, reference_equity_details.name,
               reference_equity_details.exchange, reference_equity_details.segment
        FROM reference_equity_details
        WHERE NOT EXISTS (
            SELECT 1 FROM live WHERE live.isin = reference_equity_details.isin
                AND live.exchange = reference_equity_details.exchange AND live.segment = reference_equity_details.segment
        )
    )
    SELECT * FROM live UNION ALL SELECT * FROM external
"""


class ReferenceEquity(BaseModel):
    isin: str = ""
    trading_symbol: str = ""
    exchange: str = ""
    segment: str = ""
    reference_name: str = ""
    flag: str = ""


class ReferenceUpload(BaseModel):
    rows: list[ReferenceEquity] = Field(min_length=1, max_length=2000)


FILTER_COLUMNS = ["isin", "trading_symbol", "name", "exchange", "segment"]


def equity_query(search: str, filters: str = "{}"):
    search = search.strip()
    clauses, params = [], []
    if search:
        clauses.append("(" + " OR ".join(f"{key} ILIKE ?" for key in FILTER_COLUMNS) + ")")
        params.extend([f"%{search}%"] * 5)
    try:
        selected = json.loads(filters)
        if not isinstance(selected, dict):
            raise ValueError()
        for key, values in selected.items():
            if key not in FILTER_COLUMNS or not isinstance(values, list) or len(values) > 20000 or not all(isinstance(value, str) for value in values):
                raise ValueError()
            if values:
                clauses.append(f"COALESCE({key}, '') IN ({','.join('?' for _ in values)})")
                params.extend(values)
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid table filters.")
    return (f"SELECT * FROM ({EQUITY_SQL}) AS equities WHERE " + " AND ".join(clauses), params) if clauses else (EQUITY_SQL, [])


def sort_order(sort_by: str, sort_direction: str):
    if sort_by not in FILTER_COLUMNS or sort_direction not in {"asc", "desc"}:
        raise HTTPException(400, "Invalid table sort.")
    return f"{sort_by} {sort_direction}, isin, exchange, segment"


@router.get("/equities")
def list_reference_equities(search: str = "", page: int = Query(1, ge=1), page_size: int = Query(500, ge=10, le=500), filters: str = "{}", sort_by: str = "trading_symbol", sort_direction: str = "asc"):
    query, params = equity_query(search, filters)
    order = sort_order(sort_by, sort_direction)
    conn = get_connection()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM ({query}) AS results", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM ({query}) AS results ORDER BY {order} LIMIT ? OFFSET ?",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()
        base_query, base_params = equity_query(search)
        header_values = {key: [row[0] for row in conn.execute(
            f"SELECT DISTINCT COALESCE({key}, '') AS value FROM ({base_query}) ORDER BY value", base_params
        ).fetchall()] for key in FILTER_COLUMNS}
    finally:
        conn.close()
    return {"rows": [dict(zip(["isin", "trading_symbol", "name", "exchange", "segment"], row)) for row in rows],
            "header_values": header_values, "page": page, "page_size": page_size, "total_records": total,
            "total_pages": max(1, (total + page_size - 1) // page_size)}


@router.get("/equities/download")
def download_reference_equities(search: str = "", template: bool = False, filters: str = "{}", sort_by: str = "trading_symbol", sort_direction: str = "asc"):
    query, params = equity_query(search, filters)
    order = sort_order(sort_by, sort_direction)
    conn = get_connection()
    try:
        rows = conn.execute(f"SELECT * FROM ({query}) AS results ORDER BY {order} LIMIT 100001", params).fetchall()
    finally:
        conn.close()
    if len(rows) > 100000:
        raise HTTPException(413, "Download exceeds 100,000 rows. Narrow the search.")
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["isin", "trading_symbol", "exchange", "segment", "reference_name", "flag"] if template
                    else ["isin", "trading_symbol", "name", "exchange", "segment"])
    for isin, symbol, name, exchange, segment in rows:
        values = (isin, symbol, exchange, segment, name, "") if template else (isin, symbol, name, exchange, segment)
        writer.writerow(["'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value for value in values])
    filename = "reference_equities_template.csv" if template else "reference_equities_data.csv"
    return Response(output.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post("/equities/upload")
def upload_reference_equities(payload: ReferenceUpload):
    cleaned = []
    for index, row in enumerate(payload.rows, start=1):
        isin = row.isin.strip().upper()
        symbol = row.trading_symbol.strip()
        exchange = row.exchange.strip().upper()
        segment = row.segment.strip().upper()
        name = row.reference_name.strip()
        flag = row.flag.strip().upper()
        if flag not in {"", "A", "U", "D"}:
            raise HTTPException(400, f"Row {index} has an invalid flag. Use A, U, D, or leave it blank.")
        if not all((isin, symbol, exchange, segment)) or flag in {"A", "U"} and not name or segment not in {"NSE_EQ", "BSE_EQ"}:
            raise HTTPException(400, f"Row {index} needs ISIN, trading symbol, exchange, segment, and a reference name for A/U.")
        if exchange != segment.split("_", 1)[0]:
            raise HTTPException(400, f"Row {index} has an exchange that does not match its segment.")
        cleaned.append((isin, symbol, name, exchange, segment, flag))
    conn = get_connection()
    counts = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0}
    try:
        conn.execute("BEGIN TRANSACTION")
        for isin, symbol, name, exchange, segment, flag in cleaned:
            if not flag:
                counts["skipped"] += 1
                continue
            current = conn.execute("""
                SELECT trading_symbol, name FROM upstox_instruments
                WHERE UPPER(COALESCE(NULLIF(TRIM(split_part(instrument_key, '|', 2)), ''), NULLIF(TRIM(isin), ''))) = ?
                  AND exchange = ? AND segment = ?
                  AND ((UPPER(TRIM(instrument_type)) = 'EQ' AND segment = 'NSE_EQ') OR segment = 'BSE_EQ')
                ORDER BY synced_at DESC LIMIT 1
            """, [isin, exchange, segment]).fetchone()
            if current and current[0] != symbol:
                raise HTTPException(400, f"{isin}: trading symbol must match current instruments ({current[0]}).")
            existing = conn.execute("SELECT trading_symbol, name FROM reference_equity_details WHERE isin = ? AND exchange = ? AND segment = ?",
                                    [isin, exchange, segment]).fetchone()
            if flag == "D":
                if existing:
                    conn.execute("DELETE FROM reference_equity_details WHERE isin = ? AND exchange = ? AND segment = ?", [isin, exchange, segment])
                    counts["deleted"] += 1
                else:
                    counts["skipped"] += 1
                continue
            if flag == "A" and (existing or current):
                counts["skipped"] += 1
                continue
            if existing == (symbol, name) or not existing and current == (symbol, name):
                counts["skipped"] += 1
                continue
            conn.execute("DELETE FROM reference_equity_details WHERE isin = ? AND exchange = ? AND segment = ?", [isin, exchange, segment])
            conn.execute("INSERT INTO reference_equity_details (isin, trading_symbol, name, exchange, segment) VALUES (?, ?, ?, ?, ?)",
                         [isin, symbol, name, exchange, segment])
            counts["updated" if existing or current else "added"] += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return counts
