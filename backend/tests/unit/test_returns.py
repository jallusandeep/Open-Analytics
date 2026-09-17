from datetime import date, timedelta
import json

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.engines.returns.returns_schema import ReturnsRequest, LabelRequest
from app.engines.returns.returns_service import calculate_returns, calculate_labels, HORIZONS
from app.engines.returns.returns_repository import ensure_returns_schema, build_returns, build_labels, get_rows
from app.engines.returns import returns_routes
from app.dependencies import get_current_user

pytestmark = pytest.mark.unit


def request_for(values=(100, 110, 121), keys=('A',), sessions=None):
    sessions = sessions or [date(2026, 1, 5)+timedelta(days=i) for i in range(len(values))]
    prices, eligibility = [], []
    for key in keys:
        for day, value in zip(sessions, values):
            prices.append(dict(instrument_key=key, date=day, available_on=day,
                raw_open=value, raw_close=value, adjusted_open=value,
                adjusted_close=value, adjusted_high=value+1, adjusted_low=value-1,
                total_return_close=value, volume=100, quality_valid=True,
                adjustment_valid=True, adjustment_source='fixture', adjustment_version='1'))
            eligibility.append(dict(instrument_key=key, date=day, available_on=day,
                eligible_horizons=list(HORIZONS), universe_id='U', sector_id='S'))
    return ReturnsRequest(snapshot_id='fixture', calendar_version='fixture', as_of=sessions[-1],
        sessions=sessions, instrument_keys=list(keys), prices=prices, eligibility=eligibility)


def test_daily_log_and_compounding():
    request = request_for()
    result = calculate_returns(request)['rows']
    assert result[1]['metrics']['return_1d'] == pytest.approx(.1)
    assert result[2]['metrics']['return_2d'] == pytest.approx(.21)
    assert result[2]['metrics']['cumulative_return'] == pytest.approx(.21)
    assert result[0]['metrics']['return_1d'] is None
    assert result[0]['metrics']['intraday_return'] == 0
    import math
    assert result[1]['metrics']['log_return_1d'] == pytest.approx(math.log(1.1))


def test_split_separates_raw_and_adjusted_returns():
    request = request_for((50, 50))
    request.prices[0].raw_close = 100
    request.prices[1].corporate_action_flag = True
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['return_1d'] == 0
    assert row['metrics']['raw_return_1d'] == -.5


def test_raw_range_metrics_never_mix_adjusted_prices():
    request = request_for((50, 50))
    request.price_basis = 'raw'
    request.prices[0].raw_open = 100
    request.prices[0].raw_close = 100
    row = calculate_returns(request)['rows'][0]
    assert row['metrics']['open_to_high_return'] is None
    request.prices[0].raw_high = 102
    request.prices[0].raw_low = 98
    assert calculate_returns(request)['rows'][0]['metrics']['open_to_high_return'] == pytest.approx(.02)


def test_dividend_series_is_not_counted_twice():
    request = request_for((100, 98))
    request.prices[1].total_return_close = 100
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['price_return_1d'] == pytest.approx(-.02)
    assert row['metrics']['total_return_1d'] == 0
    assert row['metrics']['dividend_return_component'] == pytest.approx(.02)


def test_overnight_intraday_interaction():
    request = request_for((100, 110))
    request.prices[1].adjusted_open = 105
    request.prices[1].adjusted_low = 104
    m = calculate_returns(request)['rows'][1]['metrics']
    assert (1+m['overnight_return'])*(1+m['intraday_return'])-1 == pytest.approx(m['return_1d'])


def test_missing_prior_close_does_not_block_intraday():
    request = request_for()
    request.prices[0].adjusted_close = None
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['return_1d'] is None
    assert row['metrics']['intraday_return'] == 0


def test_missing_current_close_does_not_block_overnight():
    request = request_for()
    request.prices[1].adjusted_close = None
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['return_1d'] is None
    assert row['metrics']['overnight_return'] == pytest.approx(.1)


def test_calendar_sessions_do_not_skip_missing_prices():
    request = request_for(sessions=[date(2026, 1, 9), date(2026, 1, 12), date(2026, 1, 13)])
    assert calculate_returns(request)['rows'][1]['metrics']['return_1d'] == pytest.approx(.1)
    request.prices.pop(1)
    row = calculate_returns(request)['rows'][2]
    assert row['metrics']['return_1d'] is None
    assert row['metrics']['return_2d'] is None


@pytest.mark.parametrize('field,value', [('suspended', True), ('volume', 0),
    ('quality_valid', False), ('adjustment_valid', False), ('unresolved_corporate_action', True)])
def test_unusable_rows_have_null_returns(field, value):
    request = request_for()
    setattr(request.prices[1], field, value)
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['return_1d'] is None
    assert row['invalid_reasons']['return_1d']


def test_late_data_and_duplicate_dates_are_excluded():
    request = request_for()
    request.prices[1].available_on = request.sessions[2]
    assert calculate_returns(request)['rows'][1]['metrics']['return_1d'] is None
    request = request_for()
    request.prices.append(request.prices[1].model_copy())
    assert calculate_returns(request)['rows'][1]['invalid_reasons']['return_1d'] == 'DUPLICATE_PRICE'


def test_calendar_returns_and_closed_periods():
    sessions = [date(2025, 12, 31), date(2026, 1, 30), date(2026, 2, 2)]
    request = request_for(sessions=sessions)
    report = calculate_returns(request)
    assert report['rows'][1]['metrics']['mtd_return'] == pytest.approx(.1)
    assert report['rows'][2]['metrics']['previous_monthly_return'] == pytest.approx(.1)
    assert report['rows'][2]['metrics']['ytd_return'] == pytest.approx(.21)
    assert any(r['frequency'] == 'monthly' and r['date'] == '2026-01-30' for r in report['periods'])


def test_benchmark_missing_does_not_block_stock():
    request = request_for(keys=('A', 'INDEX'))
    request.instrument_keys = ['A']
    for e in request.eligibility:
        if e.instrument_key == 'A':
            e.benchmark_id = 'INDEX'
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['excess_return_1d'] == 0
    request.prices = [p for p in request.prices if not (p.instrument_key == 'INDEX' and p.date == request.sessions[1])]
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['return_1d'] is not None
    assert row['metrics']['excess_return_1d'] is None


def test_ranking_ties_zero_variance_and_incomplete_membership():
    request = request_for(values=(100, 100, 100, 100, 100, 100), keys=('A', 'B', 'C'))
    ranks = [r for r in calculate_returns(request)['rankings'] if r['date'] == request.sessions[-1].isoformat() and r['horizon'] == 5]
    assert all(r['percentile'] == 50 and r['z_score'] is None for r in ranks)
    request.instrument_keys = ['A', 'B']
    ranks = calculate_returns(request)['rankings']
    assert all(r['invalid_reason'] == 'INCOMPLETE_UNIVERSE' for r in ranks)


def test_future_data_does_not_change_past_features_and_labels_are_separate():
    request = request_for()
    original = calculate_returns(request)['rows'][:2]
    request.prices[2].adjusted_close = 1000
    request.prices[2].adjusted_high = 1001
    assert calculate_returns(request)['rows'][:2] == original
    assert 'forward_return' not in json.dumps(original)
    labels = calculate_labels(request, [1])
    assert labels[0]['forward_return'] == pytest.approx(.1)
    assert labels[-1]['forward_return'] is None
    assert labels[0]['available_on'] == request.sessions[1].isoformat()


def test_versioned_storage_idempotency_and_label_isolation():
    conn = duckdb.connect(':memory:')
    try:
        ensure_returns_schema(conn)
        request = request_for()
        first = build_returns(conn, request)
        assert build_returns(conn, request)['reused']
        assert conn.execute('SELECT count(*) FROM return_features').fetchone()[0] == 3
        build_labels(conn, LabelRequest(run_id=first['run_id']))
        assert get_rows(conn, 'labels', first['run_id'])['total'] == 18
        assert 'forward_return' not in json.dumps(get_rows(conn, 'features', first['run_id']))
        request.snapshot_id = 'corrected'
        assert build_returns(conn, request)['run_id'] != first['run_id']
        assert conn.execute('SELECT count(*) FROM returns_runs').fetchone()[0] == 2
    finally:
        conn.close()


def test_api_auth_and_calculation():
    app = FastAPI()
    app.include_router(returns_routes.router)
    client = TestClient(app)
    body = request_for().model_dump(mode='json')
    assert client.post('/returns/calculate', json=body).status_code in (401, 403)
    app.dependency_overrides[get_current_user] = lambda: {'user_id': 'test'}
    response = client.post('/returns/calculate', json=body)
    assert response.status_code == 200
    assert len(response.json()['rows']) == 3
    assert client.post('/returns/calculate', json={**body, 'sessions': body['sessions']*2}).status_code == 422


def test_horizon_eligibility_and_large_real_move():
    request = request_for((100, 150, 160))
    request.eligibility[1].eligible_horizons = [1]
    row = calculate_returns(request)['rows'][1]
    assert row['metrics']['return_1d'] == .5
    assert row['return_outlier_flag'] and row['return_valid']
    assert row['metrics']['return_252d'] is None
    request.eligibility[1].available_on = request.sessions[2]
    assert calculate_returns(request)['rows'][1]['invalid_reasons']['return_1d'] == 'MISSING_ELIGIBILITY'


def test_cagr_uses_elapsed_years_and_preserves_delisting_metadata():
    sessions = [date(2024, 1, 2), date(2025, 1, 2), date(2026, 1, 2)]
    request = request_for((100, 110, 121), sessions=sessions)
    request.prices[-1].terminal_status = 'DELISTED'
    row = calculate_returns(request)['rows'][-1]
    years = (sessions[-1]-sessions[0]).days/365.2425
    assert row['metrics']['cagr_2y'] == pytest.approx(1.21**(1/years)-1)
    assert row['terminal_status'] == 'DELISTED'
    assert row['last_trade_date'] == '2026-01-02'


def test_failed_build_rolls_back_run_and_feature_rows():
    conn = duckdb.connect(':memory:')
    class FailingConnection:
        def execute(self, *args):
            return conn.execute(*args)
        def executemany(self, query, values):
            if 'return_features' in query:
                raise RuntimeError('Injected storage failure')
            return conn.executemany(query, values)
        def rollback(self):
            conn.rollback()
    try:
        ensure_returns_schema(conn)
        with pytest.raises(RuntimeError, match='Injected'):
            build_returns(FailingConnection(), request_for())
        assert conn.execute('SELECT count(*) FROM returns_runs').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM historical_returns').fetchone()[0] == 0
    finally:
        conn.close()


def test_returns_routes_registered_and_documented_example_runs():
    from pathlib import Path
    from app.main import app
    paths = app.openapi()['paths']
    assert '/api/v1/returns/build' in paths
    assert '/api/v1/returns/labels/build' in paths
    import re
    guide = Path(__file__).resolve().parents[3] / 'docs' / 'returns.md'
    payload = json.loads(re.findall(r'```json\n(.*?)\n```', guide.read_text(encoding='utf-8'), re.S)[0])
    row = calculate_returns(ReturnsRequest.model_validate(payload))['rows'][-1]
    assert row['metrics']['return_1d'] == pytest.approx(.03)
