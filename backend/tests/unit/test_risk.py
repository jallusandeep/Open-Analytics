from datetime import date, timedelta
import json
import math
from statistics import stdev

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dependencies import get_current_user
from app.engines.returns.returns_repository import ensure_returns_schema, build_returns
from app.engines.risk.risk_schema import RiskRequest, RiskBuildRequest, CovarianceRequest, RiskOptions
from app.engines.risk.risk_service import calculate_risk
from app.engines.risk.risk_repository import ensure_risk_schema, build_risk, get_features, calculate_covariance
from app.engines.risk.statistics import drawdowns, moments
from app.engines.risk import risk_routes

pytestmark = pytest.mark.unit


def fixture_request(count=70, keys=('A',), weights=None):
    # An authoritative test calendar; no inference of holidays/weekends by engine.
    days = [date(2024, 1, 1)+timedelta(days=i) for i in range(count)]
    market = [0.] + [((i % 7)-3)*.002 + .0003 for i in range(1, count)]
    prices, memberships = [], []
    for index, key in enumerate((*keys, 'M', 'S')):
        close = 100.
        for i, day in enumerate(days):
            factor = index+2 if key in keys else 1.
            ret = .0002+factor*market[i] if key in keys else market[i]
            close *= 1+ret if i else 1
            prices.append(dict(instrument_key=key, date=day, available_on=day,
                adjusted_open=close*.999, adjusted_high=close*1.01, adjusted_low=close*.99,
                adjusted_close=close, volume=100, quality_valid=True, adjustment_valid=True,
                adjustment_source='test', adjustment_version='1', risk_free_return=0.))
            if key in keys:
                memberships.append(dict(instrument_key=key, date=day, available_on=day,
                    eligible_horizons=[1], universe_id='U', sector_id='TECH', benchmark_id='M', sector_benchmark_id='S'))
    return RiskRequest(returns=dict(snapshot_id='risk-test', calendar_version='test', as_of=days[-1],
        sessions=days, instrument_keys=list(keys), prices=prices, eligibility=memberships),
        options=dict(composite_weights=weights or {}))


def last(request):
    return calculate_risk(request)['rows'][-1]


def test_known_regression_volatility_alpha_and_active_risk():
    request = fixture_request()
    row = last(request)
    m = row['metrics']
    returns = [.0002+2*(((i % 7)-3)*.002+.0003) for i in range(7, 70)]
    assert m['vol_63d'] == pytest.approx(stdev(returns))
    assert m['ann_vol_63d'] == pytest.approx(stdev(returns)*math.sqrt(252))
    assert m['beta_63d'] == pytest.approx(2)
    assert m['sector_beta_63d'] == pytest.approx(2)
    assert m['market_corr_63d'] == pytest.approx(1)
    assert m['r_squared_63d'] == pytest.approx(1)
    assert m['idio_vol_63d'] == pytest.approx(0, abs=1e-12)
    assert m['alpha_63d'] == pytest.approx(.0002)
    assert m['ann_alpha_63d'] == pytest.approx(.0002*252)
    assert m['tracking_error_63d'] == pytest.approx(stdev(returns)/2)
    assert row['sector_id'] == 'TECH'
    assert row['sector_benchmark_id'] == 'S'
    assert row['metric_quality']['beta_63d']['observation_count'] == 63
    assert m['vol_252d'] is None
    assert row['risk_quality_status'] == 'PARTIAL'
    assert row['metric_quality']['risk_score']['invalid_reason'] == 'WEIGHTS_NOT_CONFIGURED'
    json.dumps(row, allow_nan=False)


def test_tail_quantiles_shortfall_and_moments():
    row = last(fixture_request(260))
    m = row['metrics']
    assert m['var_95_252d'] >= 0
    assert m['cvar_95_252d'] >= m['var_95_252d']
    assert m['var_99_252d'] >= m['var_95_252d']
    assert m['var_95_63d'] is None
    assert row['metric_quality']['var_95_63d']['invalid_reason'] == 'INSUFFICIENT_TAIL_OBSERVATIONS'
    assert moments([-2, -1, 0, 1, 2]) == pytest.approx((0., -1.2))
    assert moments([1, 1, 1, 1]) == (None, None)
    # The repeated analytical return pattern has its lower 1%/5% quantiles
    # entirely at the minimum return, so historical VaR and CVaR agree here.
    assert m['var_95_252d'] == pytest.approx(.0112)
    assert m['cvar_95_252d'] == pytest.approx(.0112)


def test_drawdown_recovery_and_unresolved_episode():
    prices = [100, 80, 90, 100, 110, 55]
    dates = [str(i) for i in range(len(prices))]
    stats = drawdowns(prices, dates)
    assert stats['current_drawdown'] == -.5
    assert stats['max_drawdown'] == -.5
    assert stats['last_recovery_days'] == 2
    assert stats['max_drawdown_duration'] == 2
    assert stats['recovered'] is False
    assert stats['max_drawdown_start_date'] == '4'
    assert stats['max_drawdown_trough_date'] == '5'
    assert stats['max_drawdown_recovery_date'] is None
    assert drawdowns([100, 80, 100], ['a', 'b', 'c'])['max_drawdown_recovery_date'] == 'c'


def test_missing_data_keeps_session_window_and_bad_data_never_fills():
    request = fixture_request()
    request.returns.prices = [p for p in request.returns.prices if not (p.instrument_key == 'A' and p.date == request.returns.sessions[-10])]
    row = last(request)
    assert row['metrics']['vol_21d'] is None
    assert row['metric_quality']['vol_21d']['observation_count'] == 19
    assert row['metrics']['current_drawdown'] is None
    request.options.minimum_coverage = .8
    assert last(request)['metrics']['vol_21d'] is not None
    target = next(p for p in request.returns.prices if p.instrument_key == 'A' and p.date == request.returns.sessions[-5])
    target.unresolved_corporate_action = True
    row = last(request)
    assert row['metrics']['vol_21d'] is None
    assert row['metric_quality']['vol_21d']['invalid_reason'] == 'CORPORATE_ACTION_UNRESOLVED'


def test_current_invalid_observation_cannot_reuse_old_metric():
    request = fixture_request()
    request.options.minimum_coverage = .8
    for p in request.returns.prices:
        if p.instrument_key == 'A' and p.date == request.returns.as_of:
            p.quality_valid = False
    assert last(request)['metrics']['vol_21d'] is None


def test_benchmark_alignment_and_absent_risk_free_rate():
    request = fixture_request()
    for p in request.returns.prices:
        p.risk_free_return = None
    request.returns.prices = [p for p in request.returns.prices if not (p.instrument_key == 'M' and p.date == request.returns.sessions[-3])]
    row = last(request)
    assert row['metrics']['vol_63d'] is not None
    assert row['metrics']['beta_63d'] is None
    assert row['metric_quality']['beta_63d']['observation_count'] == 61
    request.options.minimum_coverage = .8
    row = last(request)
    assert row['metrics']['beta_63d'] == pytest.approx(2)
    assert row['metrics']['alpha_63d'] is None


def test_no_future_leakage_and_late_prices_are_not_backfilled():
    request = fixture_request(80)
    full = calculate_risk(request)['rows']
    request.returns.as_of = request.returns.sessions[69]
    assert calculate_risk(request)['rows'] == full[:70]
    for p in request.returns.prices:
        if p.instrument_key == 'A' and p.date == request.returns.sessions[68]:
            p.available_on = request.returns.sessions[70]
    assert last(request)['metrics']['vol_21d'] is None


def test_ewma_uses_prior_returns_and_range_risk_uses_adjusted_ohlc():
    request = fixture_request()
    before = last(request)
    day = request.returns.as_of
    for p in request.returns.prices:
        if p.instrument_key == 'A' and p.date == day:
            p.adjusted_close *= 1.1
            p.adjusted_high = p.adjusted_close*1.01
    after = last(request)
    assert before['metrics']['ewma_vol_21d'] == after['metrics']['ewma_vol_21d']
    assert before['metrics']['atr_14'] < after['metrics']['atr_14']
    assert before['metrics']['parkinson_vol_21d'] > 0
    assert before['metrics']['garman_klass_vol_21d'] > 0


def test_stale_and_illiquid_prices_cannot_look_safe():
    request = fixture_request()
    for p in request.returns.prices:
        if p.instrument_key == 'A' and p.date >= request.returns.sessions[-7]:
            p.adjusted_close = 100
            p.adjusted_open = 100
            p.adjusted_high = 101
            p.adjusted_low = 99
    row = last(request)
    assert row['metric_quality']['vol_21d']['invalid_reason'] == 'STALE_PRICE'
    request = fixture_request()
    payload = request.model_dump(mode='json')
    payload['trading_checks'] = [dict(instrument_key='A', date=str(request.returns.as_of),
        available_on=str(request.returns.as_of), liquidity_status='ILLIQUID')]
    assert last(RiskRequest.model_validate(payload))['metric_quality']['vol_21d']['invalid_reason'] == 'ILLIQUID'


def test_point_in_time_ranking_and_explicit_composite():
    request = fixture_request(70, ('A', 'B', 'C'), {'volatility': 2., 'beta': 1.})
    rows = [r for r in calculate_risk(request)['rows'] if r['date'] == str(request.returns.as_of)]
    assert [r['metrics']['volatility_percentile'] for r in rows] == [0., 50., 100.]
    assert [r['metrics']['risk_score'] for r in rows] == pytest.approx([0, 50, 100])
    assert rows[-1]['risk_bucket'] == 'EXTREME'
    request.returns.instrument_keys = ['A', 'B']
    request.options.minimum_rank_count = 2
    row = last(request)
    assert row['metrics']['volatility_percentile'] is None
    assert row['metric_quality']['volatility_percentile']['invalid_reason'] == 'INCOMPLETE_UNIVERSE'


def test_schema_rejects_raw_inputs_and_arbitrary_weights():
    payload = fixture_request(3).model_dump(mode='json')
    payload['returns']['price_basis'] = 'raw'
    with pytest.raises(ValidationError):
        RiskRequest.model_validate(payload)
    for config in ({'composite_weights': {'made_up': 1}}, {'composite_weights': {'beta': -1}},
                   {'downside_target_type': 'MINIMUM_ACCEPTABLE'}, {'minimum_tail_observations': 5}):
        with pytest.raises(ValidationError):
            RiskOptions.model_validate(config)


def test_zero_benchmark_variance_and_unavailable_ranges():
    request = fixture_request()
    for p in request.returns.prices:
        if p.instrument_key == 'M':
            p.adjusted_close = p.adjusted_open = 100
            p.adjusted_high, p.adjusted_low = 101, 99
        if p.instrument_key == 'A':
            p.adjusted_high = None
    row = last(request)
    assert row['metrics']['vol_63d'] is not None
    assert row['metrics']['beta_63d'] is None
    assert row['metric_quality']['beta_63d']['invalid_reason'] == 'ZERO_BENCHMARK_VARIANCE'
    assert row['metrics']['atr_14'] is None


def test_semideviation_target_and_range_formula():
    request = fixture_request()
    request.options.downside_target_type = 'MINIMUM_ACCEPTABLE'
    request.options.minimum_acceptable_return = .001
    row = last(request)
    returns = [.0002+2*(((i % 7)-3)*.002+.0003) for i in range(7, 70)]
    expected = math.sqrt(sum(min(r-.001, 0)**2 for r in returns)/63)
    assert row['metrics']['downside_semidev_63d'] == pytest.approx(expected)
    assert row['metrics']['parkinson_vol_21d'] == pytest.approx(math.log(1.01/.99)/math.sqrt(4*math.log(2)))


def test_failed_build_rolls_back_run_metadata_and_all_features():
    request = fixture_request(5)
    with duckdb.connect(':memory:') as conn:
        ensure_returns_schema(conn)
        ensure_risk_schema(conn)
        source = build_returns(conn, request.returns)
        # Force a real DuckDB constraint error after risk run metadata is inserted.
        conn.execute('DROP TABLE risk_features')
        conn.execute('''CREATE TABLE risk_features (
            run_id VARCHAR, instrument_key VARCHAR CHECK (instrument_key != 'A'), date DATE, data JSON)''')
        with pytest.raises(duckdb.ConstraintException):
            build_risk(conn, RiskBuildRequest(returns_run_id=source['run_id']))
        assert conn.execute('SELECT count(*) FROM risk_runs').fetchone() == (0,)
        assert conn.execute('SELECT count(*) FROM risk_features').fetchone() == (0,)


def test_persisted_build_reuse_covariance_and_missing_runs():
    request = fixture_request(70, ('A', 'B'))
    with duckdb.connect(':memory:') as conn:
        ensure_returns_schema(conn)
        ensure_risk_schema(conn)
        source = build_returns(conn, request.returns)
        build = RiskBuildRequest(returns_run_id=source['run_id'])
        result = build_risk(conn, build)
        assert result['record_count'] == 140
        assert build_risk(conn, build)['reused'] is True
        saved = get_features(conn, result['run_id'], 'A', 2, 1)
        assert saved['total'] == 70
        assert len(saved['rows']) == 2
        cov = calculate_covariance(conn, CovarianceRequest(returns_run_id=source['run_id'],
            instrument_keys=['A', 'B'], as_of=request.returns.as_of))
        assert cov['valid'] is True
        assert cov['observation_count'] == 63
        assert cov['covariance'][0][1] == cov['covariance'][1][0]
        assert cov['correlation'][0][1] == pytest.approx(1)
        assert cov['covariance'][1][1]/cov['covariance'][0][0] == pytest.approx(2.25)
        with pytest.raises(LookupError):
            build_risk(conn, RiskBuildRequest(returns_run_id='missing'))
        changed = build.model_copy(update={'options': RiskOptions(annualization_sessions=250)})
        assert build_risk(conn, changed)['run_id'] != result['run_id']
        with pytest.raises(ValueError):
            calculate_covariance(conn, CovarianceRequest(returns_run_id=source['run_id'],
                instrument_keys=['A', 'B'], as_of=request.returns.as_of+timedelta(days=1)))


def test_routes_auth_validation_and_registration():
    app = FastAPI()
    app.include_router(risk_routes.router, prefix='/api/v1')
    client = TestClient(app)
    assert client.post('/api/v1/risk/calculate', json={}).status_code in (401, 403)
    app.dependency_overrides[get_current_user] = lambda: {'user_id': 'test'}
    response = client.post('/api/v1/risk/calculate', json=fixture_request(25).model_dump(mode='json'))
    assert response.status_code == 200
    assert len(response.json()['rows']) == 25
    assert client.post('/api/v1/risk/calculate', json={}).status_code == 422
    from app.main import app as main_app
    assert '/api/v1/risk/build' in main_app.openapi()['paths']
