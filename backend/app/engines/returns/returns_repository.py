"""Immutable, content-addressed input snapshots and transactional return builds."""
import hashlib
import json

from app.engines.returns.returns_schema import ReturnsRequest
from app.engines.returns.returns_service import VERSION, calculate_returns, calculate_labels


def ensure_returns_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS returns_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL, calculation_version VARCHAR NOT NULL,
        status VARCHAR NOT NULL, input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    for table in ('historical_returns', 'return_features', 'return_periods'):
        conn.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
            run_id VARCHAR NOT NULL, instrument_key VARCHAR NOT NULL, date DATE NOT NULL,
            frequency VARCHAR NOT NULL, data JSON NOT NULL,
            PRIMARY KEY (run_id, instrument_key, date, frequency))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS return_rankings (
        run_id VARCHAR, instrument_key VARCHAR, date DATE, universe_id VARCHAR,
        sector_id VARCHAR, horizon INTEGER, data JSON)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS forward_return_labels (
        run_id VARCHAR, instrument_key VARCHAR, date DATE, horizon INTEGER, data JSON,
        PRIMARY KEY (run_id, instrument_key, date, horizon))''')


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def build_returns(conn, request):
    payload = request.model_dump(mode='json')
    content = encode(payload)
    run_id = hashlib.sha256((VERSION+content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM returns_runs WHERE run_id = ?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    report = calculate_returns(request)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('INSERT INTO returns_runs (run_id, snapshot_id, calculation_version, status, input_json) VALUES (?, ?, ?, ?, ?)',
                     [run_id, request.snapshot_id, VERSION, 'complete', content])
        for table in ('historical_returns', 'return_features'):
            rows = []
            for row in report['rows']:
                stored = dict(row)
                if table == 'historical_returns':
                    names = {'return_1d', 'log_return_1d', 'intraday_return', 'overnight_return',
                             'price_return_1d', 'total_return_1d', 'raw_return_1d', 'gap_return', 'open_to_open_return'}
                    stored['metrics'] = {k: v for k, v in row['metrics'].items() if k in names}
                    stored['invalid_reasons'] = {k: v for k, v in row['invalid_reasons'].items() if k in names}
                rows.append((run_id, row['instrument_key'], row['date'], 'daily', encode(stored)))
            if rows:
                conn.executemany(f'INSERT INTO {table} VALUES (?, ?, ?, ?, ?)', rows)
        if report.get('periods'):
            conn.executemany('INSERT INTO return_periods VALUES (?, ?, ?, ?, ?)',
                [(run_id, r['instrument_key'], r['date'], r['frequency'], encode(r)) for r in report['periods']])
        if report['rankings']:
            conn.executemany('INSERT INTO return_rankings VALUES (?, ?, ?, ?, ?, ?, ?)',
                [(run_id, r['instrument_key'], r['date'], r['universe_id'], r['sector_id'], r['horizon'], encode(r)) for r in report['rankings']])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(run_id=run_id, status='complete', reused=False, record_count=len(report['rows']))


def build_labels(conn, request):
    row = conn.execute('SELECT input_json FROM returns_runs WHERE run_id = ?', [request.run_id]).fetchone()
    if row is None:
        raise LookupError('Returns run not found')
    snapshot = ReturnsRequest.model_validate_json(row[0])
    labels = calculate_labels(snapshot, request.horizons)
    conn.execute('BEGIN TRANSACTION')
    try:
        if labels:
            conn.executemany('INSERT OR REPLACE INTO forward_return_labels VALUES (?, ?, ?, ?, ?)',
                [(request.run_id, r['instrument_key'], r['date'], r['horizon'], encode(r)) for r in labels])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(run_id=request.run_id, label_count=len(labels))


def get_rows(conn, kind, run_id, instrument_key=None, limit=1000, offset=0):
    table = {'series': 'historical_returns', 'features': 'return_features',
             'rankings': 'return_rankings', 'labels': 'forward_return_labels', 'periods': 'return_periods'}[kind]
    params = [run_id]
    where = 'run_id = ?'
    if instrument_key:
        where += ' AND instrument_key = ?'
        params.append(instrument_key)
    order = 'date, instrument_key'
    if kind in ('rankings', 'labels'):
        order += ', horizon'
    if kind == 'rankings':
        order += ', universe_id, sector_id'
    if kind == 'periods':
        order += ', frequency'
    total = conn.execute(f'SELECT count(*) FROM {table} WHERE {where}', params).fetchone()[0]
    rows = conn.execute(f'SELECT data FROM {table} WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?', params+[limit, offset]).fetchall()
    return dict(run_id=run_id, total=total, rows=[json.loads(r[0]) for r in rows])
