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
from app.services.security_reference import TABLES, MASTER_EDITABLE, LISTING_EDITABLE, TYPE_EDITABLE, append_mapping_history, type_mapping_summary, valid_isin, sync_reference, write_record

router = APIRouter(prefix="/reference-data", tags=["Reference Data"], dependencies=[Depends(require_admin_or_super_admin)])


class Upload(BaseModel):
    rows: list[dict] = Field(min_length=1, max_length=2000)


def config(view):
    if view not in TABLES:
        raise HTTPException(404, "Reference table not found.")
    return TABLES[view]


def visible_columns(view, columns):
    hidden = {'types': {'history_json'}, 'listings': {'symbol'}}
    return {key: kind for key, kind in columns.items() if key not in hidden.get(view, set())}


def query_parts(view, search, filters, sort_by, sort_direction):
    table, columns, keys = config(view)
    columns = visible_columns(view, columns)
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
    select_columns = ', '.join(columns)
    query = f"SELECT {select_columns} FROM {table}" + (' WHERE ' + ' AND '.join(clauses) if clauses else '')
    return query, params, f"{sort_by} {sort_direction}, {', '.join(keys)}"


@router.post("/sync")
def pull_upstox(user: dict = Depends(require_admin_or_super_admin)):
    from app.services.reference_sync import run_reference_refresh, JOB_KEY
    from app.services.data_collection_queue_service import enqueue_data_collection_job
    position = enqueue_data_collection_job(run_reference_refresh, job_name=JOB_KEY, job_key=JOB_KEY, kwargs={'current_user': user})
    return {'status': 'queued', 'queue_position': position, 'message': 'Instruments, index memberships, and ISIN profiles queued for reference sync.'}


@router.get("/sync/status")
def sync_status():
    from app.services.reference_sync import state
    return state()


@router.post("/universe/refresh")
def refresh_universe_metrics(as_of_date: date | None = None):
    from app.engines.universe import run_universe_engine
    conn = get_connection()
    try:
        result = run_universe_engine(conn, as_of_date)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.get("/universe/summary")
def universe_metrics_summary(as_of_date: date | None = None):
    conn = get_connection()
    try:
        selected_date = as_of_date or conn.execute("SELECT MAX(as_of_date) FROM universe_ohlcv_metrics").fetchone()[0]
        if not selected_date:
            return {"as_of_date": None, "instruments": 0, "research_eligible": 0, "trading_eligible": 0}
        row = conn.execute("""
            SELECT COUNT(*), COUNT(*) FILTER (WHERE research_eligible),
                   COUNT(*) FILTER (WHERE trading_eligible),
                   COUNT(*) FILTER (WHERE price_eligible),
                   COUNT(*) FILTER (WHERE liquidity_eligible),
                   ROUND(AVG(trading_coverage_pct), 2)
            FROM universe_ohlcv_metrics WHERE as_of_date=?
        """, [selected_date]).fetchone()
        return {"as_of_date": selected_date, "instruments": row[0], "research_eligible": row[1],
                "trading_eligible": row[2], "price_eligible": row[3], "liquidity_eligible": row[4],
                "average_coverage_pct": row[5]}
    finally:
        conn.close()


@router.post("/data-quality/refresh")
def refresh_data_quality(as_of_date: date | None = None):
    from app.engines.data_quality import run_data_quality_engine
    conn = get_connection()
    try:
        result = run_data_quality_engine(conn, as_of_date)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.get("/data-quality/summary")
def data_quality_summary():
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT run_id, as_of_date, status, total_records_checked, total_issues,
                   critical_issues, warning_issues, info_issues, started_at, finished_at
            FROM data_quality_runs ORDER BY started_at DESC LIMIT 1
        """).fetchone()
        if not row:
            return {"run_id": None, "status": "NOT_RUN", "datasets": []}
        datasets = conn.execute("""
            SELECT dataset, records_checked, issue_count, critical_issue_count,
                   warning_issue_count, info_issue_count, quality_status
            FROM data_quality_dataset_summary WHERE run_id=? ORDER BY dataset
        """, [row[0]]).fetchall()
        return {"run_id": row[0], "as_of_date": row[1], "status": row[2], "records_checked": row[3],
                "issues": row[4], "critical": row[5], "warning": row[6], "info": row[7],
                "started_at": row[8], "finished_at": row[9],
                "datasets": [{"dataset": item[0], "records_checked": item[1], "issues": item[2],
                              "critical": item[3], "warning": item[4], "info": item[5], "status": item[6]}
                             for item in datasets]}
    finally:
        conn.close()


@router.post("/corporate-actions/refresh")
def refresh_corporate_action_adjustments(as_of_date: date | None = None):
    from app.engines.corporate_actions import run_corporate_action_engine
    conn = get_connection()
    try:
        result = run_corporate_action_engine(conn, as_of_date)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.get("/corporate-actions/summary")
def corporate_action_summary():
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT run_id, as_of_date, status, actions_loaded, actions_valid, actions_review,
                   instruments_adjusted, rows_written, started_at, finished_at
            FROM corporate_action_adjustment_runs ORDER BY started_at DESC LIMIT 1
        """).fetchone()
        if not row:
            return {"run_id": None, "status": "NOT_RUN"}
        return {"run_id": row[0], "as_of_date": row[1], "status": row[2], "actions_loaded": row[3],
                "actions_valid": row[4], "actions_review": row[5], "instruments_adjusted": row[6],
                "rows_written": row[7], "started_at": row[8], "finished_at": row[9]}
    finally:
        conn.close()


@router.get("/tables/{view}")
def list_rows(view: str, search: str = "", filters: str = "{}", sort_by: str = "", sort_direction: str = "asc", page: int = Query(1, ge=1), page_size: int = Query(500, ge=10, le=500)):
    table, columns, keys = config(view)
    columns = visible_columns(view, columns)
    query, params, order = query_parts(view, search, filters, sort_by, sort_direction)
    conn = get_connection()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM ({query})", params).fetchone()[0]
        rows = conn.execute(f"{query} ORDER BY {order} LIMIT ? OFFSET ?", params + [page_size, (page - 1) * page_size]).fetchall()
        base, base_params, _ = query_parts(view, search, '{}', sort_by, sort_direction)
        values = {key: [row[0] for row in conn.execute(f"SELECT DISTINCT COALESCE(CAST({key} AS VARCHAR), '') AS filter_value FROM ({base}) ORDER BY filter_value", base_params).fetchall()] for key in columns}
        response = {"rows": [dict(zip(columns, row)) for row in rows], "columns": [{"key": key, "label": key.replace('_', ' ').title(), "group": group(key, view)} for key in columns], "header_values": values, "page": page, "total_records": total, "total_pages": max(1, (total + page_size - 1) // page_size)}
        if view == 'types':
            response['summary'] = type_mapping_summary(conn)
        return response
    finally:
        conn.close()


@router.get("/tables/types/audit")
def type_mapping_audit(limit: int = Query(500, ge=1, le=2000)):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT exchange, segment, source_type, security_type, history_json
            FROM security_type_mapping
            WHERE history_json IS NOT NULL AND TRIM(history_json) <> ''
        """).fetchall()
        events = []
        for exchange, segment, source_type, security_type, raw_history in rows:
            try:
                history = json.loads(raw_history or '[]')
            except (TypeError, ValueError):
                history = []
            if not isinstance(history, list):
                continue
            identity = {"exchange": exchange, "segment": segment, "source_type": source_type, "security_type": security_type}
            for event in history:
                if isinstance(event, dict):
                    source = event.get("source")
                    events.append({**identity, "at": event.get("at"), "action": event.get("action"),
                                   "source": source,
                                   "actor": event.get("actor") or ("System / Upstox Sync" if source == "UPSTOX_SYNC" else "Administrator (legacy record)"),
                                   "tab": event.get("tab") or "Security Type Mapping",
                                   "changes": event.get("changes") or {}})
        events.sort(key=lambda event: str(event.get('at') or ''), reverse=True)
        return {"events": events[:limit], "total": len(events)}
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
    columns = visible_columns(view, columns)
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
def upload(view: str, payload: Upload, current_user: dict = Depends(require_admin_or_super_admin)):
    table, columns, keys = config(view)
    editable = MASTER_EDITABLE if view == 'securities' else LISTING_EDITABLE if view == 'listings' else TYPE_EDITABLE
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
            if view == 'types':
                actor = "System"
                if isinstance(current_user, dict):
                    actor = current_user.get('full_name') or current_user.get('email') or current_user.get('user_id') or actor
                record['security_type'] = str(record.get('security_type') or '').strip().upper()
                for key in {'exchange', 'segment', 'source_type', 'instrument_type', 'gbo_type'}:
                    if record.get(key):
                        record[key] = record[key].upper()
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
            if view == 'types':
                if flag == 'D':
                    for key in TYPE_EDITABLE:
                        if key != 'is_active':
                            merged[key] = None
                    merged['is_active'] = False
                    merged['mapping_source'] = 'MANUAL_CLEAR'
                    merged['mapping_updated_at'] = datetime.now()
                    action = 'MANUAL_CLEAR'
                else:
                    merged['mapping_source'] = 'MANUAL_UPLOAD'
                    merged['mapping_updated_at'] = datetime.now()
                    action = 'MANUAL_ADD' if not old else 'MANUAL_UPDATE'
                merged['history_json'] = append_mapping_history(old, merged, action, 'CSV_UPLOAD', actor=actor)
            if view == 'securities' and flag != 'D':
                suspended = merged.get('is_suspended') is True
                delisted = merged.get('is_delisted') is True
                if suspended and delisted or (suspended or delisted) and merged.get('is_active') is True or delisted and merged.get('is_listed') is True:
                    raise HTTPException(400, f'Row {index}: active, listed, suspended and delisted flags conflict.')
            if old and all(old.get(key) == merged.get(key) for key in columns if key != 'record_updated_at') and manual == set(json.loads(old.get('manual_fields') or '[]')):
                counts['skipped'] += 1
                continue
            if view == 'securities':
                merged['record_updated_at'] = datetime.now()
            if view in {'securities', 'listings'}:
                merged['manual_fields'] = json.dumps(sorted(manual))
            write_record(conn, table, columns, keys, merged)
            counts['deleted' if flag == 'D' else 'updated' if old else 'added'] += 1
        if view in {'securities', 'listings'}:
            sync_reference(conn)
        conn.commit()
        return counts
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
