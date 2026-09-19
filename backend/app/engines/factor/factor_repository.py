import hashlib
import json

from app.engines.factor.factor_service import VERSION, calculate_factors


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_factor_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS factor_engine_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL, as_of DATE NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    for table in ('features', 'composites', 'diagnostics', 'research_summaries', 'correlations'):
        conn.execute(f'''CREATE TABLE IF NOT EXISTS factor_engine_{table} (
            run_id VARCHAR NOT NULL, record_key VARCHAR NOT NULL, data JSON NOT NULL,
            PRIMARY KEY(run_id, record_key))''')


def build_factors(conn, request):
    ensure_factor_schema(conn)
    content = encode(request.model_dump(mode='json'))
    run_id = hashlib.sha256((VERSION+content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM factor_engine_runs WHERE run_id=?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    result = calculate_factors(request)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('INSERT INTO factor_engine_runs VALUES (?,?,?,?,?, ?,CURRENT_TIMESTAMP)',
                     [run_id, request.snapshot_id, request.as_of, VERSION, 'complete', content])
        collections = {'features': result['rows'], 'composites': result['composites'],
                       'diagnostics': result['diagnostics'], 'research_summaries': result['research_summaries'],
                       'correlations': result['correlations']}
        for table, records in collections.items():
            if records:
                conn.executemany(f'INSERT INTO factor_engine_{table} VALUES (?,?,?)',
                                 [(run_id, hashlib.sha256(encode(row).encode()).hexdigest(), encode(row)) for row in records])
        conn.commit()
    except Exception:
        conn.rollback(); raise
    return dict(run_id=run_id, status='complete', reused=False,
                record_count=len(result['rows']), diagnostic_count=len(result['diagnostics']))


def get_run(conn, run_id):
    ensure_factor_schema(conn)
    row = conn.execute('''SELECT snapshot_id,as_of,calculation_version,status,input_json,created_at
                          FROM factor_engine_runs WHERE run_id=?''', [run_id]).fetchone()
    if row is None:
        raise LookupError('Factor run not found')
    return dict(run_id=run_id, snapshot_id=row[0], as_of=row[1], calculation_version=row[2],
                status=row[3], configuration=json.loads(row[4]), created_at=row[5])


def get_records(conn, run_id, collection, limit=1000, offset=0):
    if collection not in {'features', 'composites', 'diagnostics', 'research_summaries', 'correlations'}:
        raise ValueError('Unknown factor collection')
    get_run(conn, run_id)
    total = conn.execute(f'SELECT count(*) FROM factor_engine_{collection} WHERE run_id=?', [run_id]).fetchone()[0]
    rows = conn.execute(f'''SELECT data FROM factor_engine_{collection} WHERE run_id=?
                            ORDER BY record_key LIMIT ? OFFSET ?''', [run_id, limit, offset]).fetchall()
    return dict(run_id=run_id, collection=collection, total=total, rows=[json.loads(row[0]) for row in rows])
