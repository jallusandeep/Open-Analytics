import hashlib
import json

from app.engines.news_event.news_event_service import VERSION, calculate_news_events


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_news_event_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS news_event_engine_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL, as_of TIMESTAMPTZ NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    for table in ('events', 'daily_features'):
        conn.execute(f'''CREATE TABLE IF NOT EXISTS news_event_engine_{table} (
            run_id VARCHAR NOT NULL, record_key VARCHAR NOT NULL, data JSON NOT NULL,
            PRIMARY KEY(run_id, record_key))''')


def build_news_events(conn, request):
    ensure_news_event_schema(conn)
    content = encode(request.model_dump(mode='json'))
    run_id = hashlib.sha256((VERSION+content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM news_event_engine_runs WHERE run_id=?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    result = calculate_news_events(request)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('INSERT INTO news_event_engine_runs VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)',
                     [run_id, request.snapshot_id, request.as_of, VERSION, 'complete', content])
        for table, records in (('events', result['events']), ('daily_features', result['daily_features'])):
            if records:
                conn.executemany(f'INSERT INTO news_event_engine_{table} VALUES (?,?,?)',
                    [(run_id, hashlib.sha256(encode(row).encode()).hexdigest(), encode(row)) for row in records])
        conn.commit()
    except Exception:
        conn.rollback(); raise
    return dict(run_id=run_id, status='complete', reused=False,
                event_count=len(result['events']), feature_count=len(result['daily_features']))


def get_run(conn, run_id):
    ensure_news_event_schema(conn)
    row = conn.execute('''SELECT snapshot_id,as_of,calculation_version,status,input_json,created_at
                          FROM news_event_engine_runs WHERE run_id=?''', [run_id]).fetchone()
    if row is None:
        raise LookupError('News event run not found')
    return dict(run_id=run_id, snapshot_id=row[0], as_of=row[1], calculation_version=row[2],
                status=row[3], configuration=json.loads(row[4]), created_at=row[5])


def get_records(conn, run_id, collection, limit=1000, offset=0):
    if collection not in {'events', 'daily_features'}:
        raise ValueError('Unknown news event collection')
    get_run(conn, run_id)
    total = conn.execute(f'SELECT count(*) FROM news_event_engine_{collection} WHERE run_id=?', [run_id]).fetchone()[0]
    rows = conn.execute(f'''SELECT data FROM news_event_engine_{collection} WHERE run_id=?
                            ORDER BY record_key LIMIT ? OFFSET ?''', [run_id, limit, offset]).fetchall()
    return dict(run_id=run_id, collection=collection, total=total, rows=[json.loads(row[0]) for row in rows])
