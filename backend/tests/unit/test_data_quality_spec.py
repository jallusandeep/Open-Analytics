"""Regression and specification cases missing from the initial implementation."""
from datetime import date
import json

import duckdb
import pytest

from app.engines.data_quality.data_quality_service import validate_ohlcv, validate_records, require_quality
from app.engines.data_quality.data_quality_repository import stored_sessions, validate_stored_records, normalize_collected
from app.engines.data_quality.data_quality_schema import StoredQualityRequest, StoredRecordsRequest

pytestmark = pytest.mark.unit


def candle(day, close=100):
    return dict(date=day, open=close, high=close+1, low=close-1, close=close, volume=100)


def codes(report, index=0):
    return {i['code'] for i in report['rows'][index]['issues']}


def test_missing_streak_ignores_unexpected_sunday_and_missing_rows_fail_gate():
    report = validate_ohlcv('A', [candle('2026-09-13')], ['2026-09-11', '2026-09-14'], critical_missing_streak=2)
    assert report['summary']['largest_missing_streak'] == 2
    assert report['rows'][0]['quality_status'] == 'CRITICAL'
    isolated = validate_ohlcv('A', [], ['2026-09-14'])
    assert isolated['rows'][0]['quality_status'] == 'WARNING'
    assert isolated['rows'][0]['is_valid'] is False
    with pytest.raises(ValueError):
        require_quality(isolated)


@pytest.mark.parametrize('action', [dict(action_type='symbol_change'), dict(action_type='split'),
    dict(action_type='split', adjustment_factor=0.25), dict(action_type='split', adjustment_factor=-0.5)])
def test_action_date_without_matching_factor_cannot_explain_drop(action):
    action.update(instrument_key='A', ex_date='2026-09-14')
    report = validate_ohlcv('A', [candle('2026-09-11'), candle('2026-09-14', 50)],
                            ['2026-09-11', '2026-09-14'], corporate_actions=[action])
    assert 'UNEXPLAINED_MOVE' in codes(report, 1)
    assert report['rows'][1]['quality_status'] == 'WARNING'


def test_known_market_move_and_dividend():
    rows = [candle('2026-09-11'), candle('2026-09-14', 50)]
    sessions = [r['date'] for r in rows]
    report = validate_ohlcv('A', rows, sessions, confirmed_market_moves=['2026-09-14'])
    assert 'CONFIRMED_MARKET_MOVE' in codes(report, 1)
    report = validate_ohlcv('A', rows, sessions, corporate_actions=[dict(instrument_key='A', action_type='cash dividend', ex_date='2026-09-14', amount=50)])
    assert 'CORPORATE_ACTION_MOVE' in codes(report, 1)


@pytest.mark.parametrize('field', ['effective_date', 'record_date', 'announcement_date'])
def test_malformed_action_dates_excluded(field):
    action = dict(instrument_key='A', action_type='split', ex_date='2026-09-14', adjustment_factor=0.5)
    action[field] = 'bad'
    report = validate_records('corporate_actions', [action])
    assert 'INVALID_ACTION_DATE' in codes(report)
    assert not report['rows'][0]['is_valid']


def test_action_aliases_cannot_hide_conflicts():
    base = dict(instrument_key='A', ex_date='2026-09-14', adjustment_factor=0.5)
    report = validate_records('corporate_actions', [dict(base, action_type='split'),
                              dict(base, action_type='Stock Split', adjustment_factor=0.25)])
    assert report['summary']['invalid_records'] == 2
    assert 'CONFLICTING_ACTION' in codes(report, 1)


def test_restatement_order_and_inferred_quarterly_gap():
    base = dict(instrument_key='A', period_type='quarterly', currency='INR')
    rows = [dict(base, period_end='2025-03-31', report_date='2025-05-01'),
            dict(base, period_end='2025-09-30', report_date='2025-11-01'),
            dict(base, period_end='2025-09-30', report_date='2025-10-01', revision=1)]
    report = validate_records('fundamentals', rows)
    assert 'MISSING_FISCAL_PERIODS' in codes(report)
    assert 'RESTATEMENT_DATE_ORDER' in codes(report, 2)


def test_ratio_bounds_do_not_reject_negative_earnings_ratios():
    base = dict(instrument_key='A', currency='INR', period_end='2025-03-31', report_date='2025-05-01')
    report = validate_records('fundamentals', [dict(base, ratios={'pe_ratio': -5, 'roe': -10})])
    assert report['rows'][0]['is_valid']
    report = validate_records('fundamentals', [dict(base, ratios={'current_ratio': -1, 'custom': 12})], ratio_bounds={'custom': (0, 10)})
    assert {'INVALID_RATIO', 'RATIO_OUT_OF_BOUNDS'} <= codes(report)


def test_calendar_exchange_scope_special_weekend_and_listing():
    conn = duckdb.connect(':memory:')
    try:
        conn.execute('CREATE TABLE upstox_market_holidays (holiday_date DATE, closed_exchanges JSON, open_exchanges JSON)')
        conn.execute('INSERT INTO upstox_market_holidays VALUES (?, ?, ?), (?, ?, ?), (?, ?, ?)',
            ['2026-09-14', '["NSE"]', '[]', '2026-09-12', '[]', '[{"exchange":"NSE"}]',
             '2026-09-15', '["BSE"]', '[]'])
        request = StoredQualityRequest(instrument_key='A', start_date='2026-09-10', end_date='2026-09-15', listing_date='2026-09-12')
        sessions, notes = stored_sessions(conn, request)
        assert sessions == [date(2026, 9, 12), date(2026, 9, 15)]
        assert notes
    finally:
        conn.close()


def test_stored_news_loads_mapping_and_reports_missing_timestamp():
    conn = duckdb.connect(':memory:')
    try:
        conn.execute("CREATE TABLE upstox_instruments AS SELECT 'A' instrument_key, 'ABC' trading_symbol")
        conn.execute("CREATE TABLE equity_news AS SELECT 'A' instrument_key, 'WRONG' trading_symbol, NULL::TIMESTAMP published_at, 'Story' title, 'Exchange' AS source")
        report = validate_stored_records(conn, StoredRecordsRequest(dataset='news', instrument_key='A'))
        assert {'TICKER_MISMATCH', 'INVALID_TIMESTAMP'} <= codes(report)
    finally:
        conn.close()


def test_collected_histories_keep_missing_publication_dates_visible():
    stored = dict(instrument_key='A', endpoint='income_statement', time_period='quarterly',
        raw_json=json.dumps({'data': {'currency': 'INR', 'income_statement': [
            {'category': 'revenue', 'history': [{'period': '2025-03-31', 'value': 12}]}]}}))
    rows = normalize_collected([stored], 'fundamentals')
    assert rows[0]['period_end'] == '2025-03-31'
    assert rows[0]['report_date'] is None
    assert 'REPORT_DATE_ORDER' in codes(validate_records('fundamentals', rows))


def test_collected_action_loader_preserves_explicit_factor():
    conn = duckdb.connect(':memory:')
    try:
        conn.execute("CREATE TABLE upstox_instruments AS SELECT 'A' instrument_key, 'ABC' trading_symbol")
        conn.execute('CREATE TABLE upstox_company_fundamentals (instrument_key VARCHAR, trading_symbol VARCHAR, endpoint VARCHAR, raw_json JSON)')
        conn.execute('INSERT INTO upstox_company_fundamentals VALUES (?, ?, ?, ?)',
            ['A', 'ABC', 'corporate_actions', json.dumps({'data': [dict(action_type='split', ex_date='2026-09-14', adjustment_factor=0.5)]})])
        report = validate_stored_records(conn, StoredRecordsRequest(dataset='corporate_actions', instrument_key='A'))
        assert report['rows'][0]['is_valid']
    finally:
        conn.close()


def test_preflight_http_blocks_missing_and_unverified_data(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.dependencies import get_current_user
    from app.engines.data_quality import data_quality_routes as routes
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_current_user] = lambda: {'user_id': 'test'}
    client = TestClient(app)
    payload = dict(instrument_key='A', sessions=['2026-09-14'])
    report = validate_ohlcv('A', [], payload['sessions'])
    monkeypatch.setattr(routes, 'check_stored_daily', lambda request: report)
    assert client.post('/data-quality/preflight', json=payload).status_code == 409
    report = validate_ohlcv('A', [candle('2026-09-14')], payload['sessions'])
    assert client.post('/data-quality/preflight', json=payload).status_code == 200
    report['calendar_verified'] = False
    assert client.post('/data-quality/preflight', json=payload).status_code == 409


def test_empty_auxiliary_data_is_not_certified():
    with pytest.raises(ValueError):
        require_quality(validate_records('news', []))


def test_holdings_total_and_bad_source_record():
    report = validate_records('fundamentals', [dict(instrument_key='A', period_end='2025-03-31',
        report_date='2025-05-01', currency='INR', ratios={'fii_holding_pct': 60, 'dii_holding_pct': 60})])
    assert 'HOLDINGS_TOTAL' in codes(report)
    report = validate_records('news', [dict(instrument_key='A', title=' ', source={}, published_at='2025-01-01T00:00:00Z')])
    assert 'BAD_SOURCE_RECORD' in codes(report)
