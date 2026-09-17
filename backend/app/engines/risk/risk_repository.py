"""Immutable risk runs reference saved Returns snapshots; no forward labels are read."""
import hashlib
import json
from math import ceil, sqrt

from app.engines.returns.returns_schema import ReturnsRequest
from app.engines.returns.returns_service import VERSION as RETURNS_VERSION
from app.engines.risk.risk_schema import RiskRequest
from app.engines.risk.risk_service import VERSION, calculate_risk, HARD_FAILURES
from app.engines.risk.observations import prepare
from app.engines.risk.statistics import covariance


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_risk_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS risk_runs (
        run_id VARCHAR PRIMARY KEY, returns_run_id VARCHAR NOT NULL,
        calculation_version VARCHAR NOT NULL, status VARCHAR NOT NULL,
        input_json JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS risk_features (
        run_id VARCHAR NOT NULL, instrument_key VARCHAR NOT NULL, date DATE NOT NULL,
        data JSON NOT NULL, PRIMARY KEY(run_id, instrument_key, date))''')


def load_source(conn, request):
    stored = conn.execute('SELECT input_json, status, calculation_version FROM returns_runs WHERE run_id = ?',
                          [request.returns_run_id]).fetchone()
    if stored is None:
        raise LookupError('Returns run not found')
    if stored[1] != 'complete' or stored[2] != RETURNS_VERSION:
        raise ValueError('Risk requires a complete Returns run with the supported calculation version')
    source = RiskRequest(returns=ReturnsRequest.model_validate_json(stored[0]), options=request.options,
                         trading_checks=request.trading_checks)
    rows = conn.execute('SELECT data FROM return_features WHERE run_id = ? ORDER BY instrument_key, date',
                        [request.returns_run_id]).fetchall()
    report = dict(rows=[json.loads(row[0]) for row in rows])
    expected = {(key, day.isoformat()) for key in source.returns.instrument_keys for day in source.returns.sessions
                if day <= source.returns.as_of}
    if {(row['instrument_key'], row['date']) for row in report['rows']} != expected:
        raise ValueError('Returns run has an incomplete feature grid')
    return source, report


def build_risk(conn, request):
    content = encode(request.model_dump(mode='json'))
    run_id = hashlib.sha256((VERSION+content).encode()).hexdigest()
    existing = conn.execute('SELECT status FROM risk_runs WHERE run_id = ?', [run_id]).fetchone()
    if existing:
        return dict(run_id=run_id, status=existing[0], reused=True)
    source, report = load_source(conn, request)
    result = calculate_risk(source, report)
    conn.execute('BEGIN TRANSACTION')
    try:
        conn.execute('INSERT INTO risk_runs (run_id, returns_run_id, calculation_version, status, input_json) VALUES (?, ?, ?, ?, ?)',
                     [run_id, request.returns_run_id, VERSION, 'complete', content])
        if result['rows']:
            conn.executemany('INSERT INTO risk_features VALUES (?, ?, ?, ?)',
                [(run_id, row['instrument_key'], row['date'], encode(row)) for row in result['rows']])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(run_id=run_id, returns_run_id=request.returns_run_id, status='complete', reused=False,
                record_count=len(result['rows']))


def get_run(conn, run_id):
    row = conn.execute('SELECT returns_run_id, calculation_version, status, input_json, created_at FROM risk_runs WHERE run_id = ?', [run_id]).fetchone()
    if row is None:
        raise LookupError('Risk run not found')
    return dict(run_id=run_id, returns_run_id=row[0], calculation_version=row[1], status=row[2],
                configuration=json.loads(row[3]), created_at=row[4])


def get_features(conn, run_id, instrument_key=None, limit=1000, offset=0):
    get_run(conn, run_id)
    where, params = 'run_id = ?', [run_id]
    if instrument_key:
        where += ' AND instrument_key = ?'
        params.append(instrument_key)
    total = conn.execute(f'SELECT count(*) FROM risk_features WHERE {where}', params).fetchone()[0]
    rows = conn.execute(f'SELECT data FROM risk_features WHERE {where} ORDER BY date, instrument_key LIMIT ? OFFSET ?',
                        params+[limit, offset]).fetchall()
    return dict(run_id=run_id, total=total, rows=[json.loads(row[0]) for row in rows])


def calculate_covariance(conn, request):
    source, report = load_source(conn, request)
    if request.as_of > source.returns.as_of or request.as_of not in source.returns.sessions:
        raise ValueError('Covariance as_of must be a session within the Returns snapshot cutoff')
    if not set(request.instrument_keys) <= set(source.returns.instrument_keys):
        raise ValueError('Covariance instrument is absent from the Returns run')
    series, groups = prepare(source, report)
    end = series.positions[request.as_of]
    indices = list(range(max(0, end-request.window+1), end+1))
    complete = [i for i in indices if all(groups[key][i]['daily'] is not None for key in request.instrument_keys)]
    reason = next((groups[key][i]['reason'] for key in request.instrument_keys for i in indices
                   if groups[key][i]['reason'] in HARD_FAILURES), None)
    if not reason and len(indices) < request.window:
        reason = 'INSUFFICIENT_HISTORY'
    if not reason and (len(complete) < max(3, ceil(request.window*request.options.minimum_coverage)) or end not in complete):
        reason = 'INSUFFICIENT_OVERLAP'
    matrix = correlation = None
    if not reason:
        vectors = [[groups[key][i]['daily'] for i in complete] for key in request.instrument_keys]
        matrix = [[covariance(left, right) for right in vectors] for left in vectors]
        correlation = [[value/sqrt(matrix[i][i]*matrix[j][j]) if matrix[i][i] > 1e-24 and matrix[j][j] > 1e-24 else None
                        for j, value in enumerate(row)] for i, row in enumerate(matrix)]
    return dict(instrument_keys=request.instrument_keys, as_of=request.as_of.isoformat(), window=request.window,
        observation_count=len(complete), alignment='LISTWISE_COMPLETE', valid=reason is None, invalid_reason=reason,
        covariance=matrix, annualized_covariance=[[v*request.options.annualization_sessions for v in r] for r in matrix] if matrix else None,
        correlation=correlation)
