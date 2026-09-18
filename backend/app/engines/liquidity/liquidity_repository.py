"""Immutable, content-addressed inputs and historical daily outputs."""
import hashlib
import json

from app.engines.liquidity.liquidity_service import VERSION, calculate_liquidity


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_liquidity_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS liquidity_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS liquidity_features (
        run_id VARCHAR NOT NULL, instrument_key VARCHAR NOT NULL, date DATE NOT NULL,
        data JSON NOT NULL, PRIMARY KEY(run_id, instrument_key, date))''')


def build_liquidity(conn, request):
    content = encode(request.model_dump(mode='json'))
    run_id = hashlib.sha256((VERSION+content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM liquidity_runs WHERE run_id=?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    result = calculate_liquidity(request)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('INSERT INTO liquidity_runs (run_id, snapshot_id, calculation_version, status, input_json) VALUES (?, ?, ?, ?, ?)',
                     [run_id, request.snapshot_id, VERSION, 'complete', content])
        conn.executemany('INSERT INTO liquidity_features VALUES (?, ?, ?, ?)',
                         [(run_id, r['instrument_key'], r['date'], encode(r)) for r in result['rows']])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(run_id=run_id, status='complete', reused=False, record_count=len(result['rows']))


def get_run(conn, run_id):
    row = conn.execute('SELECT snapshot_id, calculation_version, status, input_json, created_at FROM liquidity_runs WHERE run_id=?', [run_id]).fetchone()
    if row is None:
        raise LookupError('Liquidity run not found')
    return dict(run_id=run_id, snapshot_id=row[0], calculation_version=row[1], status=row[2], configuration=json.loads(row[3]), created_at=row[4])


def get_features(conn, run_id, instrument_key=None, limit=1000, offset=0):
    get_run(conn, run_id)
    where, params = 'run_id=?', [run_id]
    if instrument_key:
        where += ' AND instrument_key=?'
        params.append(instrument_key)
    total = conn.execute(f'SELECT count(*) FROM liquidity_features WHERE {where}', params).fetchone()[0]
    rows = conn.execute(f'SELECT data FROM liquidity_features WHERE {where} ORDER BY date, instrument_key LIMIT ? OFFSET ?', params+[limit, offset]).fetchall()
    return dict(run_id=run_id, total=total, rows=[json.loads(r[0]) for r in rows])
