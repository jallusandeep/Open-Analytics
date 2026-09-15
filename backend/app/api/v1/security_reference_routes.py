import csv
import json
import math
from datetime import date, datetime
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.database import get_connection
from app.dependencies import require_admin_or_super_admin
from app.services.security_reference import TABLES, MASTER_EDITABLE, LISTING_EDITABLE, valid_isin, sync_reference, write_record

router = APIRouter(prefix="/reference-data", tags=["Reference Data"], dependencies=[Depends(require_admin_or_super_admin)])


class Upload(BaseModel):
    rows: list[dict] = Field(min_length=1, max_length=2000)


def config(view):
    if view not in TABLES:
        raise HTTPException(404, "Reference table not found.")
    return TABLES[view]


def query_parts(view, search, filters, sort_by, sort_direction):
    table, columns, keys = config(view)
    sort_by = sort_by or keys[0]
    if sort_by not in columns or sort_direction not in {"asc", "desc"}:
        raise HTTPException(400, "Invalid table sort.")
    clauses, params = [], []
    if search.strip():
        clauses.append('(' + ' OR '.join(f"CAST({key} AS VARCHAR) ILIKE ?" for key in columns) + ')')
        params.extend(['%' + search.strip() + '%'] * len(columns))
    try:
        selected = json.loads(filters)
        if not isinstance(selected, dict):
            raise ValueError()
        for key, values in selected.items():
            if key not in columns or not isinstance(values, list) or len(values) > 20000 or not all(isinstance(value, str) for value in values):
                raise ValueError()
            if values:
                clauses.append(f"COALESCE(CAST({key} AS VARCHAR), '') IN ({','.join('?' for _ in values)})")
                params.extend(values)
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid table filters.") from None
    select_columns = ', '.join("(effective_from <= CURRENT_DATE AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)) AS is_current" if view == 'indices' and key == 'is_current' else key for key in columns)
    query = f"SELECT {select_columns} FROM {table}" + (' WHERE ' + ' AND '.join(clauses) if clauses else '')
    return query, params, f"{sort_by} {sort_direction}, {', '.join(keys)}"


@router.post("/sync")
def pull_upstox(user: dict = Depends(require_admin_or_super_admin)):
    from app.services.reference_sync import run_reference_refresh, JOB_KEY
    from app.services.data_collection_queue_service import enqueue_data_collection_job
    position = enqueue_data_collection_job(run_reference_refresh, job_name=JOB_KEY, job_key=JOB_KEY, kwargs={'current_user': user})
    return {'status': 'queued', 'queue_position': position, 'message': 'Upstox instruments and ISIN profiles queued for reference sync.'}


@router.get("/sync/status")
def sync_status():
    from app.services.reference_sync import state
    return state()


@router.get("/tables/{view}")
def list_rows(view: str, search: str = "", filters: str = "{}", sort_by: str = "", sort_direction: str = "asc", page: int = Query(1, ge=1), page_size: int = Query(50, ge=10, le=500)):
    table, columns, keys = config(view)
    query, params, order = query_parts(view, search, filters, sort_by, sort_direction)
    conn = get_connection()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM ({query})", params).fetchone()[0]
        rows = conn.execute(f"{query} ORDER BY {order} LIMIT ? OFFSET ?", params + [page_size, (page - 1) * page_size]).fetchall()
        base, base_params, _ = query_parts(view, search, '{}', sort_by, sort_direction)
        values = {key: [row[0] for row in conn.execute(f"SELECT DISTINCT COALESCE(CAST({key} AS VARCHAR), '') AS filter_value FROM ({base}) ORDER BY filter_value", base_params).fetchall()] for key in columns}
        return {"rows": [dict(zip(columns, row)) for row in rows], "columns": [{"key": key, "label": key.replace('_', ' ').title(), "group": group(key, view)} for key in columns], "header_values": values, "page": page, "total_records": total, "total_pages": max(1, (total + page_size - 1) // page_size)}
    finally:
        conn.close()


def group(key, view):
    if view != 'securities':
        return None
    if key in {'macro_sector', 'sector', 'industry', 'basic_industry', 'market_cap_bucket'}:
        return 'Classification'
    if key in {'has_nse_listing', 'has_bse_listing', 'is_cross_listed', 'listing_count', 'primary_exchange', 'primary_symbol', 'primary_instrument_key'}:
        return 'Listing'
    if key in {'listing_status', 'is_active', 'is_listed', 'is_suspended', 'is_delisted'}:
        return 'Status'
    if key in {'listing_date', 'face_value'}:
        return 'Other'
    if key in {'fno_eligible', 'futures_available', 'options_available'}:
        return 'Derivatives'
    if key in {'classification_source', 'instrument_source', 'source_updated_at', 'record_updated_at'}:
        return 'Source'
    return 'Identity'


@router.get("/tables/{view}/download")
def download(view: str, template: bool = False, search: str = "", filters: str = "{}", sort_by: str = "", sort_direction: str = "asc"):
    table, columns, keys = config(view)
    query, params, order = query_parts(view, search, filters, sort_by, sort_direction)
    conn = get_connection()
    try:
        rows = conn.execute(f"{query} ORDER BY {order} LIMIT 100001", params).fetchall()
    finally:
        conn.close()
    if len(rows) > 100000:
        raise HTTPException(413, "Download exceeds 100,000 rows. Narrow the search.")
    output = StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(list(columns) + (['flag'] if template else []))
    for row in rows:
        values = list(row) + ([''] if template else [])
        writer.writerow(["'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')) else value for value in values])
    name = table + ('_template' if template else '_data') + '.csv'
    return Response(output.getvalue().encode('utf-8-sig'), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename={name}'})


def convert(value, kind, row, field):
    if value is None or str(value).strip() == '':
        return None
    text = str(value).strip()
    try:
        if kind == 'BOOLEAN':
            if text.lower() not in {'true', 'false', '1', '0', 'yes', 'no'}:
                raise ValueError()
            return text.lower() in {'true', '1', 'yes'}
        if kind == 'DATE':
            return date.fromisoformat(text)
        if kind == 'TIMESTAMP':
            return datetime.fromisoformat(text)
        if kind in {'DOUBLE', 'INTEGER', 'BIGINT'}:
            number = float(text)
            if not math.isfinite(number) or number < 0 or kind != 'DOUBLE' and not number.is_integer():
                raise ValueError()
            return number if kind == 'DOUBLE' else int(number)
        if len(text) > 2000:
            raise ValueError()
        return ' '.join(text.split())
    except (ValueError, TypeError, OverflowError):
        raise HTTPException(400, f'Row {row}: invalid {field} ({kind.lower()}).') from None


@router.post("/tables/{view}/upload")
def upload(view: str, payload: Upload):
    table, columns, keys = config(view)
    editable = MASTER_EDITABLE if view == 'securities' else LISTING_EDITABLE if view == 'listings' else set(columns) - set(keys)
    conn = get_connection()
    counts = dict(added=0, updated=0, deleted=0, skipped=0)
    try:
        conn.execute('BEGIN TRANSACTION')
        for index, source in enumerate(payload.rows, 1):
            unknown = set(source) - set(columns) - {'flag'}
            if unknown:
                raise HTTPException(400, f'Row {index}: unknown columns: {", ".join(sorted(unknown))}.')
            flag = str(source.get('flag') or '').strip().upper()
            if flag not in {'', 'A', 'U', 'D'}:
                raise HTTPException(400, f'Row {index}: use A, U, D, or blank flag.')
            if not flag:
                counts['skipped'] += 1
                continue
            record = {key: convert(value, columns[key], index, key) for key, value in source.items() if key in columns}
            if view == 'indices' and record.get('index_code'):
                record['index_code'] = record['index_code'].upper()
            if 'isin' in record:
                record['isin'] = valid_isin(record['isin'])
            if any(record.get(key) is None for key in keys) or 'isin' in columns and not record.get('isin'):
                raise HTTPException(400, f'Row {index}: valid ISIN and all identity columns are required.')
            where = ' AND '.join(f'{key}=?' for key in keys)
            params = [record[key] for key in keys]
            result = conn.execute(f'SELECT * FROM {table} WHERE {where}', params)
            names = [column[0] for column in result.description]
            existing_row = result.fetchone()
            old = dict(zip(names, existing_row)) if existing_row else None
            if view in {'indices', 'identifiers'} and not conn.execute('SELECT 1 FROM security_reference WHERE isin=?', [record['isin']]).fetchone():
                raise HTTPException(400, f'Row {index}: ISIN is not in the security master.')
            if flag == 'A' and old or flag == 'D' and not old:
                counts['skipped'] += 1
                continue
            if view == 'listings' and not old:
                raise HTTPException(400, f'Row {index}: listings must come from Upstox current instruments.')
            if flag == 'U' and not old:
                raise HTTPException(400, f'Row {index}: record not found; use A to add.')
            if old:
                for key in set(record) - editable - set(keys):
                    if record[key] is not None and record[key] != old.get(key):
                        raise HTTPException(400, f'Row {index}: {key} is managed by Upstox and cannot be changed.')
            if flag == 'D' and view in {'indices', 'identifiers'}:
                conn.execute(f'DELETE FROM {table} WHERE {where}', params)
                counts['deleted'] += 1
                continue
            merged = {key: (old or {}).get(key) for key in columns}
            merged.update({key: record[key] for key in keys})
            manual = set(json.loads((old or {}).get('manual_fields') or '[]'))
            if flag == 'D':
                # Clear uploaded enrichment; source identity remains intact.
                for key in manual:
                    if key in editable:
                        merged[key] = None
                manual.clear()
            else:
                for key in editable:
                    if key in record:
                        merged[key] = record[key]
                        if view in {'securities', 'listings'}:
                            manual.add(key)
            if view == 'securities' and flag != 'D':
                suspended = merged.get('is_suspended') is True
                delisted = merged.get('is_delisted') is True
                if suspended and delisted or (suspended or delisted) and merged.get('is_active') is True or delisted and merged.get('is_listed') is True:
                    raise HTTPException(400, f'Row {index}: active, listed, suspended and delisted flags conflict.')
            if view in {'indices', 'identifiers'}:
                if not merged.get('effective_from') or merged.get('effective_to') and merged['effective_to'] < merged['effective_from']:
                    raise HTTPException(400, f'Row {index}: invalid effective date range.')
                if view == 'indices':
                    if not merged.get('index_name'):
                        raise HTTPException(400, f'Row {index}: index name is required.')
                    merged['index_code'] = merged['index_code'].upper()
                    merged['is_current'] = merged['effective_from'] <= date.today() and (not merged.get('effective_to') or merged['effective_to'] >= date.today())
                    overlap = conn.execute("SELECT 1 FROM security_index_membership WHERE isin=? AND index_code=? AND effective_from<>? AND effective_from <= COALESCE(?, DATE '9999-12-31') AND COALESCE(effective_to, DATE '9999-12-31') >= ?", [merged['isin'], merged['index_code'], merged['effective_from'], merged.get('effective_to'), merged['effective_from']]).fetchone()
                    if overlap:
                        raise HTTPException(400, f'Row {index}: index membership dates overlap an existing period.')
            if old and all(old.get(key) == merged.get(key) for key in columns if key != 'record_updated_at') and manual == set(json.loads(old.get('manual_fields') or '[]')):
                counts['skipped'] += 1
                continue
            if view == 'securities':
                merged['record_updated_at'] = datetime.now()
            if view in {'securities', 'listings'}:
                merged['manual_fields'] = json.dumps(sorted(manual))
            write_record(conn, table, columns, keys, merged)
            counts['deleted' if flag == 'D' else 'updated' if old else 'added'] += 1
        sync_reference(conn)
        conn.commit()
        return counts
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
