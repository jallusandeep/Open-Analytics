import hashlib
import json

from app.engines.institutional_flow.institutional_flow_service import VERSION, calculate_institutional_flows


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_institutional_flow_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS institutional_flow_engine_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL, as_of VARCHAR NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    for table in ('market', 'sector', 'stock'):
        conn.execute(f'''CREATE TABLE IF NOT EXISTS institutional_flow_engine_{table} (
            run_id VARCHAR NOT NULL, record_key VARCHAR NOT NULL, data JSON NOT NULL,
            PRIMARY KEY(run_id, record_key))''')


def build_institutional_flows(conn, request):
    ensure_institutional_flow_schema(conn)
    content = encode(request.model_dump(mode='json'))
    run_id = hashlib.sha256((VERSION+content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM institutional_flow_engine_runs WHERE run_id=?', [run_id]).fetchone()
    if existing: return dict(run_id=run_id, status=existing[0], reused=True)
    result = calculate_institutional_flows(request)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('INSERT INTO institutional_flow_engine_runs VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)',
                     [run_id, request.snapshot_id, request.as_of.isoformat(), VERSION, 'complete', content])
        for table, records in (('market', result['market_rows']), ('sector', result['sector_rows']), ('stock', result['stock_rows'])):
            if records:
                conn.executemany(f'INSERT INTO institutional_flow_engine_{table} VALUES (?,?,?)',
                    [(run_id, hashlib.sha256(encode(row).encode()).hexdigest(), encode(row)) for row in records])
        conn.commit()
    except Exception:
        conn.rollback(); raise
    return dict(run_id=run_id, status='complete', reused=False,
                market_count=len(result['market_rows']), sector_count=len(result['sector_rows']), stock_count=len(result['stock_rows']))


def get_run(conn, run_id):
    ensure_institutional_flow_schema(conn)
    row = conn.execute('''SELECT snapshot_id,as_of,calculation_version,status,input_json,created_at
                          FROM institutional_flow_engine_runs WHERE run_id=?''', [run_id]).fetchone()
    if row is None: raise LookupError('Institutional flow run not found')
    return dict(run_id=run_id, snapshot_id=row[0], as_of=row[1], calculation_version=row[2],
                status=row[3], configuration=json.loads(row[4]), created_at=row[5])


def get_records(conn, run_id, collection, limit=1000, offset=0):
    if collection not in {'market', 'sector', 'stock'}: raise ValueError('Unknown institutional flow collection')
    get_run(conn, run_id)
    total = conn.execute(f'SELECT count(*) FROM institutional_flow_engine_{collection} WHERE run_id=?', [run_id]).fetchone()[0]
    rows = conn.execute(f'''SELECT data FROM institutional_flow_engine_{collection} WHERE run_id=?
                            ORDER BY record_key LIMIT ? OFFSET ?''', [run_id, limit, offset]).fetchall()
    return dict(run_id=run_id, collection=collection, total=total, rows=[json.loads(row[0]) for row in rows])
