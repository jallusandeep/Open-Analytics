"""Content-addressed ranking runs and long-form historical ranking output."""
import hashlib
import json

from app.engines.cross_sectional_ranking.ranking_service import VERSION, calculate_rankings


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_ranking_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS cross_sectional_ranking_runs (
        run_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS cross_sectional_rankings (
        run_id VARCHAR NOT NULL, instrument_key VARCHAR NOT NULL, date DATE NOT NULL,
        universe_id VARCHAR NOT NULL, metric_name VARCHAR NOT NULL, data JSON NOT NULL,
        PRIMARY KEY(run_id, instrument_key, date, universe_id, metric_name))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS cross_sectional_distributions (
        run_id VARCHAR NOT NULL, date DATE NOT NULL, universe_id VARCHAR NOT NULL,
        metric_name VARCHAR NOT NULL, data JSON NOT NULL,
        PRIMARY KEY(run_id, date, universe_id, metric_name))''')


def build_rankings(conn, request):
    ensure_ranking_schema(conn)
    content = encode(request.model_dump(mode='json'))
    run_id = hashlib.sha256((VERSION + content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM cross_sectional_ranking_runs WHERE run_id=?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    result = calculate_rankings(request)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('''INSERT INTO cross_sectional_ranking_runs
            (run_id, snapshot_id, calculation_version, status, input_json)
            VALUES (?, ?, ?, ?, ?)''', [run_id, request.snapshot_id, VERSION, 'complete', content])
        conn.executemany('INSERT INTO cross_sectional_rankings VALUES (?, ?, ?, ?, ?, ?)', [
            (run_id, row['instrument_key'], row['date'], row['universe_id'], row['metric_name'], encode(row))
            for row in result['rows']])
        conn.executemany('INSERT INTO cross_sectional_distributions VALUES (?, ?, ?, ?, ?)', [
            (run_id, row['date'], row['universe_id'], row['metric_name'], encode(row))
            for row in result['distributions']])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(run_id=run_id, status='complete', reused=False,
                record_count=len(result['rows']), distribution_count=len(result['distributions']))


def get_run(conn, run_id):
    ensure_ranking_schema(conn)
    row = conn.execute('''SELECT snapshot_id, calculation_version, status, input_json, created_at
                          FROM cross_sectional_ranking_runs WHERE run_id=?''', [run_id]).fetchone()
    if row is None:
        raise LookupError('Cross-sectional ranking run not found')
    return dict(run_id=run_id, snapshot_id=row[0], calculation_version=row[1], status=row[2],
                configuration=json.loads(row[3]), created_at=row[4])


def get_rankings(conn, run_id, instrument_key=None, metric_name=None, limit=1000, offset=0):
    get_run(conn, run_id)
    where, params = ['run_id=?'], [run_id]
    if instrument_key:
        where.append('instrument_key=?')
        params.append(instrument_key)
    if metric_name:
        where.append('metric_name=?')
        params.append(metric_name)
    clause = ' AND '.join(where)
    total = conn.execute(f'SELECT count(*) FROM cross_sectional_rankings WHERE {clause}', params).fetchone()[0]
    rows = conn.execute(f'''SELECT data FROM cross_sectional_rankings WHERE {clause}
                            ORDER BY date, metric_name, instrument_key LIMIT ? OFFSET ?''',
                        params + [limit, offset]).fetchall()
    return dict(run_id=run_id, total=total, rows=[json.loads(row[0]) for row in rows])


def get_distributions(conn, run_id, metric_name=None, limit=1000, offset=0):
    get_run(conn, run_id)
    where, params = ['run_id=?'], [run_id]
    if metric_name:
        where.append('metric_name=?')
        params.append(metric_name)
    clause = ' AND '.join(where)
    total = conn.execute(f'SELECT count(*) FROM cross_sectional_distributions WHERE {clause}', params).fetchone()[0]
    rows = conn.execute(f'''SELECT data FROM cross_sectional_distributions WHERE {clause}
                            ORDER BY date, metric_name LIMIT ? OFFSET ?''', params + [limit, offset]).fetchall()
    return dict(run_id=run_id, total=total, rows=[json.loads(row[0]) for row in rows])
