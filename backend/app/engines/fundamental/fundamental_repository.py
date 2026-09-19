import hashlib
import json

from app.engines.fundamental.fundamental_service import VERSION, calculate_fundamentals


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_fundamental_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS fundamental_engine_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL, as_of DATE NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS fundamental_engine_features (
        run_id VARCHAR NOT NULL, instrument_key VARCHAR NOT NULL, as_of DATE NOT NULL,
        data JSON NOT NULL, PRIMARY KEY(run_id, instrument_key))''')


def build_fundamentals(conn, request):
    ensure_fundamental_schema(conn)
    content = encode(request.model_dump(mode='json'))
    run_id = hashlib.sha256((VERSION+content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM fundamental_engine_runs WHERE run_id=?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    result = calculate_fundamentals(request)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('''INSERT INTO fundamental_engine_runs
            (run_id,snapshot_id,as_of,calculation_version,status,input_json) VALUES (?,?,?,?,?,?)''',
            [run_id, request.snapshot_id, request.as_of, VERSION, 'complete', content])
        conn.executemany('INSERT INTO fundamental_engine_features VALUES (?,?,?,?)',
                         [(run_id, row['instrument_key'], request.as_of, encode(row)) for row in result['rows']])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(run_id=run_id, status='complete', reused=False, record_count=len(result['rows']))


def get_run(conn, run_id):
    ensure_fundamental_schema(conn)
    row = conn.execute('''SELECT snapshot_id,as_of,calculation_version,status,input_json,created_at
                          FROM fundamental_engine_runs WHERE run_id=?''', [run_id]).fetchone()
    if row is None:
        raise LookupError('Fundamental run not found')
    return dict(run_id=run_id, snapshot_id=row[0], as_of=row[1], calculation_version=row[2],
                status=row[3], configuration=json.loads(row[4]), created_at=row[5])


def get_features(conn, run_id, instrument_key=None, limit=1000, offset=0):
    get_run(conn, run_id)
    where, params = ['run_id=?'], [run_id]
    if instrument_key:
        where.append('instrument_key=?')
        params.append(instrument_key)
    clause = ' AND '.join(where)
    total = conn.execute(f'SELECT count(*) FROM fundamental_engine_features WHERE {clause}', params).fetchone()[0]
    rows = conn.execute(f'''SELECT data FROM fundamental_engine_features WHERE {clause}
                            ORDER BY instrument_key LIMIT ? OFFSET ?''', params+[limit, offset]).fetchall()
    return dict(run_id=run_id, total=total, rows=[json.loads(row[0]) for row in rows])
