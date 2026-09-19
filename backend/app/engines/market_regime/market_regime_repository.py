import hashlib
import json

from app.engines.market_regime.market_regime_service import VERSION, calculate_market_regime


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_market_regime_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS market_regime_engine_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL, as_of DATE NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, result_json JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS market_regime_engine_snapshots (
        run_id VARCHAR NOT NULL, date DATE NOT NULL, scope VARCHAR NOT NULL,
        market_id VARCHAR NOT NULL, data JSON NOT NULL,
        PRIMARY KEY (run_id, date, scope, market_id))''')


def build_market_regime(conn, request):
    ensure_market_regime_schema(conn)
    content = request.model_dump(mode='json')
    content['observations'].sort(key=lambda row: (row['date'], row['scope'], row['market_id']))
    encoded = encode(content)
    run_id = hashlib.sha256((VERSION + encoded).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM market_regime_engine_runs WHERE run_id=?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    result = calculate_market_regime(request)
    metadata = {key: value for key, value in result.items() if key != 'rows'}
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('''INSERT INTO market_regime_engine_runs
            (run_id,snapshot_id,as_of,calculation_version,status,input_json,result_json)
            VALUES (?,?,?,?,?,?,?)''',
                     [run_id, request.snapshot_id, request.as_of, VERSION, 'complete', encoded, encode(metadata)])
        conn.executemany('INSERT INTO market_regime_engine_snapshots VALUES (?,?,?,?,?)',
                         [(run_id, row['date'], row['scope'], row['market_id'], encode(row)) for row in result['rows']])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(run_id=run_id, status='complete', reused=False, snapshot_count=len(result['rows']))


def get_run(conn, run_id):
    ensure_market_regime_schema(conn)
    row = conn.execute('''SELECT snapshot_id,as_of,calculation_version,status,input_json,result_json,created_at
        FROM market_regime_engine_runs WHERE run_id=?''', [run_id]).fetchone()
    if row is None:
        raise LookupError('Market regime run not found')
    return dict(run_id=run_id, snapshot_id=row[0], as_of=row[1], calculation_version=row[2],
                status=row[3], configuration=json.loads(row[4]), summary=json.loads(row[5]), created_at=row[6])


def get_records(conn, run_id, limit=1000, offset=0):
    if not 1 <= limit <= 5000 or offset < 0:
        raise ValueError('invalid pagination')
    get_run(conn, run_id)
    total = conn.execute('SELECT count(*) FROM market_regime_engine_snapshots WHERE run_id=?', [run_id]).fetchone()[0]
    rows = conn.execute('''SELECT data FROM market_regime_engine_snapshots WHERE run_id=?
        ORDER BY date,scope,market_id LIMIT ? OFFSET ?''', [run_id, limit, offset]).fetchall()
    return dict(run_id=run_id, total=total, rows=[json.loads(row[0]) for row in rows])
