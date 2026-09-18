from datetime import date, datetime, timezone, timedelta

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.engines.data_quality.data_quality_routes import router
from app.dependencies import get_current_user
from app.engines.data_quality.data_quality_schema import StoredQualityRequest
from app.engines.data_quality.data_quality_repository import validate_stored_daily
from app.engines.data_quality.data_quality_service import validate_ohlcv, validate_records

pytestmark = pytest.mark.unit


def candle(day='2026-09-14', close=100, **overrides):
    return dict(date=day, open=close, high=close + 2, low=close - 2,
                close=close, volume=1000, trading_symbol='ABC', **overrides)


def codes(row):
    return {i['code'] for i in row['issues']}


def test_calendar_excludes_weekend_holiday_and_pre_listing_dates():
    sessions = ['2026-09-11', '2026-09-15']
    report = validate_ohlcv('A', [candle(day) for day in sessions], sessions)
    assert report['summary']['coverage_pct'] == 100
    assert report['summary']['expected_sessions'] == 2
    assert report['summary']['data_quality_status'] == 'HEALTHY'


@pytest.mark.parametrize('field,value', [('open', None), ('close', 0), ('low', -1),
    ('high', 99), ('close', float('nan')), ('open', float('inf')), ('volume', -1), ('volume', None)])
def test_invalid_prices_and_volume_are_excluded(field, value):
    row = candle()
    row[field] = value
    result = validate_ohlcv('A', [row], [row['date']])
    assert not result['rows'][0]['is_valid']
    assert result['summary']['latest_valid_date'] is None


def test_duplicates_are_not_arbitrarily_selected():
    result = validate_ohlcv('A', [candle(), candle(close=110)], ['2026-09-14'])
    assert result['summary']['available_sessions'] == 1
    assert result['summary']['duplicate_count'] == 1
    assert not result['rows'][0]['is_valid']


def test_long_missing_runs_escalate_every_missing_session():
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(80)]
    sessions = [d for d in days if d.weekday() < 5][:50]
    result = validate_ohlcv('A', [], sessions)
    assert result['summary']['largest_missing_streak'] == 50
    assert all(r['quality_status'] == 'CRITICAL' for r in result['rows'])
    isolated = validate_ohlcv('A', [], sessions[:1])
    assert isolated['rows'][0]['quality_status'] == 'WARNING'


def test_split_is_informational_but_never_excuses_invalid_prices():
    sessions = ['2026-09-14', '2026-09-15']
    actions = [dict(instrument_key='A', action_type='split', ex_date=sessions[1], adjustment_factor=0.5)]
    rows = [candle(sessions[0]), candle(sessions[1], close=50)]
    result = validate_ohlcv('A', rows, sessions, corporate_actions=actions)
    assert codes(result['rows'][1]) == {'CORPORATE_ACTION_MOVE'}
    assert result['rows'][1]['is_valid']
    assert 'UNEXPLAINED_MOVE' in codes(validate_ohlcv('A', rows, sessions)['rows'][1])
    rows[1]['high'] = 1
    assert not validate_ohlcv('A', rows, sessions, corporate_actions=actions)['rows'][1]['is_valid']


def test_stale_series_and_missing_session_reset():
    sessions = ['2026-09-14', '2026-09-15', '2026-09-16']
    result = validate_ohlcv('A', [candle(d) for d in sessions], sessions, stale_sessions=3)
    assert result['summary']['stale_price_days'] == 1
    result = validate_ohlcv('A', [candle(sessions[0]), candle(sessions[2])], sessions, stale_sessions=2)
    assert result['summary']['stale_price_days'] == 0


def test_bad_date_and_unexpected_session_are_reported():
    result = validate_ohlcv('A', [candle('bad'), candle('2026-09-13')], ['2026-09-14'])
    assert result['summary']['available_sessions'] == 0
    assert 'INVALID_DATE' in codes(result['rows'][0])
    assert 'UNEXPECTED_SESSION' in codes(result['rows'][1])


def test_news_duplicates_future_dates_and_mapping():
    rows = [dict(instrument_key='A', trading_symbol='WRONG', url='https://example.test/story',
                 title='Story', source='Exchange', published_at='2027-01-01T00:00:00Z')] * 2
    result = validate_records('news', rows, reference={'A': 'ABC'}, as_of=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert result['summary']['invalid_records'] == 2
    assert codes(result['rows'][0]) == {'TICKER_MISMATCH', 'FUTURE_TIMESTAMP', 'DUPLICATE'}


def test_fundamental_revisions_currency_and_missing_periods():
    base = dict(instrument_key='A', period_end='2025-12-31', report_date='2026-02-01', currency='INR')
    result = validate_records('fundamentals', [base, dict(base, revision=1, currency='USD')],
                              expected_periods=['2025-09-30', '2025-12-31'])
    assert result['summary']['invalid_records'] == 0
    assert codes(result['rows'][1]) == {'RESTATEMENT', 'CURRENCY_CHANGE', 'MISSING_FISCAL_PERIODS'}
    invalid = validate_records('fundamentals', [dict(base, report_date='2025-01-01', ratios={'fii_holding_pct': 101})])
    assert codes(invalid['rows'][0]) == {'REPORT_DATE_ORDER', 'INVALID_RATIO'}


def test_conflicting_actions_and_reference_order():
    base = dict(instrument_key='A', action_type='split', ex_date='2026-09-14', adjustment_factor=0.5)
    result = validate_records('corporate_actions', [base, dict(base, adjustment_factor=0.25)])
    assert result['summary']['invalid_records'] == 2
    assert 'CONFLICTING_ACTION' in codes(result['rows'][1])
    result = validate_records('reference', [dict(instrument_key='A', trading_symbol='ABC', exchange='NSE',
        listing_date='2026-01-01', delisting_date='2025-01-01')])
    assert 'REFERENCE_DATE_ORDER' in codes(result['rows'][0])


def test_stored_adapter_scopes_daily_source_and_does_not_write():
    conn = duckdb.connect(':memory:')
    try:
        conn.execute('''CREATE TABLE upstox_ohlcv_candles AS SELECT 'upstox' provider, 'A' instrument_key,
            'current' instrument_source, 'historical' candle_mode, 'days' unit, 1 interval_value,
            DATE '2026-09-14' candle_date, TIMESTAMP '2026-09-14 00:00:00' candle_timestamp,
            'ABC' trading_symbol, 100.0 open_price, 102.0 high_price, 98.0 low_price, 100.0 close_price, 1000 volume''')
        conn.execute('CREATE TABLE corporate_actions (instrument_key VARCHAR, action_type VARCHAR, ex_date DATE)')
        conn.execute("INSERT INTO upstox_ohlcv_candles SELECT * REPLACE ('minutes' AS unit) FROM upstox_ohlcv_candles")
        result = validate_stored_daily(conn, StoredQualityRequest(instrument_key='A', sessions=['2026-09-14']))
        assert result['summary']['available_sessions'] == 1
        assert result['summary']['duplicate_count'] == 0
        assert conn.execute('SELECT count(*) FROM upstox_ohlcv_candles').fetchone()[0] == 2
    finally:
        conn.close()


def test_api_auth_validation_and_response():
    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    client = TestClient(app)
    payload = dict(instrument_key='A', sessions=['2026-09-14'], records=[candle()])
    assert client.post('/api/v1/data-quality/ohlcv', json=payload).status_code in (401, 403)
    app.dependency_overrides[get_current_user] = lambda: {'user_id': 'test'}
    response = client.post('/api/v1/data-quality/ohlcv', json=payload)
    assert response.status_code == 200
    assert response.json()['summary']['data_quality_score'] == 100
    assert client.post('/api/v1/data-quality/ohlcv', json=dict(payload, stale_sessions=0)).status_code == 422
    assert client.post('/api/v1/data-quality/records', json={'dataset': 'fundamentals', 'records': [{'ratios': []}]}).status_code == 422


def test_routes_registered_in_application():
    from app.main import app
    paths = app.openapi()['paths']
    assert all('/api/v1/data-quality/' + name in paths for name in ('ohlcv', 'records', 'stored-daily'))
