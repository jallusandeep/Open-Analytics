"""Read stored daily candles without altering or deduplicating raw source data."""
import json
from app.engines.data_quality.data_quality_service import validate_ohlcv, validate_records
from app.engines.data_quality.rules import trading_sessions


def rows_from_query(conn, query, parameters=()):
    cursor = conn.execute(query, parameters)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def stored_sessions(conn, request):
    if request.sessions is not None:
        return request.sessions, []
    rows = rows_from_query(conn, '''SELECT holiday_date, closed_exchanges, open_exchanges
        FROM upstox_market_holidays WHERE holiday_date BETWEEN ? AND ?''',
        [request.start_date, request.end_date])
    closed, opened = set(), set()
    for row in rows:
        for field, target in [('closed_exchanges', closed), ('open_exchanges', opened)]:
            entries = json.loads(row[field] or '[]')
            if not isinstance(entries, list):
                raise ValueError('Malformed stored exchange calendar')
            for entry in entries:
                name = entry.get('exchange') if isinstance(entry, dict) else entry
                if name == request.exchange:
                    target.add(row['holiday_date'])
    notes = ['Calendar uses weekdays plus stored exchange closures/special openings; upstream calendar completeness is not certified.']
    if not request.listing_date:
        notes.append('Listing date not supplied; eligibility begins at requested start_date.')
    return trading_sessions(request.start_date, request.end_date, holidays=closed,
                            special_sessions=opened, listing_date=request.listing_date,
                            delisting_date=request.delisting_date), notes


def validate_stored_daily(conn, request):
    sessions, notes = stored_sessions(conn, request)
    if not sessions:
        return dict(summary={'instrument_key': request.instrument_key, 'data_quality_status': 'NO_DATA'}, rows=[], notes=notes)
    start, end = min(sessions), max(sessions)
    cursor = conn.execute('''
        SELECT candle_date AS date, trading_symbol, open_price AS open,
               high_price AS high, low_price AS low, close_price AS close, volume
        FROM upstox_ohlcv_candles
        WHERE provider = 'upstox' AND instrument_key = ?
          AND instrument_source = ? AND candle_mode = ?
          AND unit = 'days' AND interval_value = 1
          AND candle_date BETWEEN ? AND ?
        ORDER BY candle_date, candle_timestamp
        LIMIT 20001
    ''', [request.instrument_key, request.instrument_source, request.candle_mode, start, end])
    columns = [column[0] for column in cursor.description]
    records = [dict(zip(columns, row)) for row in cursor.fetchall()]
    if len(records) > 20000:
        raise ValueError('Too many candles; request a shorter session range')
    actions = rows_from_query(conn, '''
        SELECT * FROM corporate_actions
        WHERE instrument_key = ? AND ex_date BETWEEN ? AND ?
    ''', [request.instrument_key, start, end])
    actions = [normalize_action(row) for row in actions]
    if conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'upstox_company_fundamentals'").fetchone()[0]:
        collected = rows_from_query(conn, "SELECT * FROM upstox_company_fundamentals WHERE instrument_key = ? AND endpoint = 'corporate_actions' LIMIT 20001", [request.instrument_key])
        if collected:
            actions = normalize_collected(collected, 'corporate_actions')
    report = validate_ohlcv(request.instrument_key, records, sessions, corporate_actions=actions)
    report['source'] = 'upstox_ohlcv_candles'
    report['calendar_source'] = 'caller_supplied_eligible_sessions' if request.sessions else 'stored_exchange_calendar'
    report['notes'] = notes
    report['calendar_verified'] = request.sessions is not None
    return report


def raw_object(value):
    if isinstance(value, dict):
        return value
    try:
        result = json.loads(value or '{}')
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


def normalize_action(row):
    raw = raw_object(row.get('raw_json'))
    # Explicit numeric factors only: ratio strings differ in meaning across providers.
    return {**raw, **row, 'adjustment_factor': row.get('adjustment_factor') or raw.get('adjustment_factor')}


def validate_stored_records(conn, request):
    tables = {'news': 'equity_news', 'reference': 'upstox_instruments',
              'corporate_actions': 'corporate_actions', 'fundamentals': 'fundamentals'}
    table = tables[request.dataset]
    clause = ''
    if request.source == 'collected' and request.dataset in {'fundamentals', 'corporate_actions'}:
        table = 'upstox_company_fundamentals'
        clause = " AND endpoint = 'corporate_actions'" if request.dataset == 'corporate_actions' else " AND endpoint IN ('balance_sheet', 'income_statement', 'cash_flow', 'key_ratios', 'share_holdings')"
    records = rows_from_query(conn, f'SELECT * FROM {table} WHERE instrument_key = ? {clause} LIMIT 20001', [request.instrument_key])
    if len(records) > 20000:
        raise ValueError('Too many records for a single validation request')
    reference_rows = rows_from_query(conn, 'SELECT instrument_key, trading_symbol FROM upstox_instruments WHERE instrument_key = ?', [request.instrument_key])
    reference = {r['instrument_key']: r['trading_symbol'] for r in reference_rows}
    if table == 'upstox_company_fundamentals':
        records = normalize_collected(records, request.dataset)
        if len(records) > 20000:
            raise ValueError('Expanded vendor history exceeds 20000 records')
    elif request.dataset == 'corporate_actions':
        records = [normalize_action(row) for row in records]
    elif request.dataset == 'fundamentals':
        normalized = []
        for row in records:
            raw = raw_object(row.get('raw_json'))
            normalized.append({**raw, **row, 'period_end': raw.get('period_end'),
                               'currency': raw.get('currency'), 'revision': raw.get('revision', 0),
                               'ratios': {k: row[k] for k in ('pe_ratio', 'debt_to_equity', 'roe', 'promoter_holding_pct', 'fii_holding_pct', 'dii_holding_pct') if row.get(k) is not None}})
        records = normalized
    report = validate_records(request.dataset, records, reference=None if request.dataset == 'reference' else reference,
                              as_of=request.as_of, expected_periods=request.expected_periods)
    report['source'] = table
    report['notes'] = ['Ticker mapping uses the current instrument master; historical renames require a point-in-time mapping.']
    report['summary']['data_quality_status'] = 'NO_DATA' if not records else 'CRITICAL' if report['summary']['critical_issue_count'] else 'WARNING' if any(r['quality_status'] == 'WARNING' for r in report['rows']) else 'HEALTHY'
    return report


def normalize_collected(records, dataset):
    """Expand known stored list/history shapes; missing metadata remains missing."""
    result = []
    for stored in records:
        response = raw_object(stored.get('raw_json'))
        data = response.get('data')
        if data is None:
            try:
                data = json.loads(stored.get('history_json') or stored.get('summary_json') or '{}')
            except (ValueError, TypeError):
                data = {}
        metadata = data if isinstance(data, dict) else {}
        entries = data if isinstance(data, list) else next((metadata[k] for k in
            ('history', 'income_statement', 'cash_flow', 'balance_sheet', 'corporate_actions', 'actions', 'key_ratios', 'ratios', 'share_holdings')
            if isinstance(metadata.get(k), list)), [metadata])
        for entry in entries or [{}]:
            entry = entry if isinstance(entry, dict) else {}
            history = entry.get('history') if isinstance(entry.get('history'), list) else [entry]
            for point in history or [{}]:
                point = point if isinstance(point, dict) else {}
                common = dict(instrument_key=stored.get('instrument_key'), trading_symbol=stored.get('trading_symbol'))
                if dataset == 'corporate_actions':
                    result.append({**entry, **point, **common,
                                   'action_type': point.get('action_type') or point.get('type')})
                else:
                    ratios = point.get('ratios') if isinstance(point.get('ratios'), dict) else {}
                    if stored.get('endpoint') == 'key_ratios' and 'value' in point:
                        ratios = {str(entry.get('name') or entry.get('category') or 'ratio'): point['value']}
                    result.append({**common, 'period_end': point.get('period_end') or point.get('period'),
                        'report_date': point.get('report_date') or metadata.get('report_date') or stored.get('report_date'),
                        'currency': point.get('currency') or metadata.get('currency'),
                        'revision': point.get('revision', 0), 'ratios': ratios,
                        'statement_type': '|'.join(str(v or '') for v in (stored.get('endpoint'), stored.get('statement_type'), entry.get('category') or entry.get('name'))),
                        'period_type': point.get('period_type') or stored.get('time_period')})
    return result
