from datetime import date, timedelta

import duckdb
import pytest
from pydantic import ValidationError

from app.engines.market_regime.market_regime_repository import build_market_regime, get_records, get_run
from app.engines.market_regime.market_regime_schema import MarketRegimeRequest
from app.engines.market_regime.market_regime_service import calculate_market_regime

pytestmark = pytest.mark.unit
START = date(2026, 1, 1)


def observation(index=0, **changes):
    day = START + timedelta(days=index)
    row = dict(date=day, available_on=day, market_id='NIFTY_50', source_reference='test://snapshot',
               market_return_21d=.08, market_return_63d=.12, price_vs_sma50=.08,
               price_vs_sma200=.12, market_slope_63d=.002,
               realized_volatility_21d=.12, realized_volatility_63d=.14, current_drawdown=-.01,
               breadth_score=85, breadth_coverage=.95, institutional_flow_score=80,
               market_liquidity_score=85, derivatives_sentiment_score=75, derivatives_risk_score=20,
               correlation=.3, cross_sectional_dispersion=.02)
    row.update(changes)
    return row


def request(rows=None, **changes):
    rows = rows if rows is not None else [observation()]
    end = max(row['date'] for row in rows)
    values = dict(snapshot_id='regime-fixture', as_of=end,
                  sessions=[START + timedelta(days=i) for i in range((end - START).days + 1)], observations=rows)
    values.update(changes)
    return MarketRegimeRequest.model_validate(values)


def calculate(rows=None, **changes):
    return calculate_market_regime(request(rows, **changes))['rows']


def test_bull_dimensions_probabilities_and_explainability():
    row = calculate()[0]
    assert row['regime_label'] == 'BULL_LOW_VOL'
    assert row['trend_regime'] == 'STRONG_UPTREND'
    assert row['breadth_regime'] == 'VERY_STRONG'
    assert row['flow_regime'] == 'STRONG_ACCUMULATION'
    assert row['liquidity_regime'] == 'ABUNDANT'
    assert row['derivatives_regime'] == 'RISK_ON'
    assert row['risk_on_off_state'] == 'RISK_ON'
    assert row['bull_probability'] > row['bear_probability']
    assert sum(row[k] for k in ('bull_probability', 'bear_probability', 'sideways_probability')) == pytest.approx(1)
    assert sum(row['score_contributions'].values()) == pytest.approx(row['regime_score'])
    assert row['regime_confidence'] > 90
    assert row['regime_quality_status'] == 'VALID'
    assert row['recommended_risk_budget_multiplier'] == 1


def test_stress_and_configured_risk_budget():
    row = calculate([observation(market_return_21d=-.1, market_return_63d=-.2,
                                price_vs_sma50=-.1, price_vs_sma200=-.2, market_slope_63d=-.002,
                                realized_volatility_21d=.6, realized_volatility_63d=.5,
                                current_drawdown=-.4, breadth_score=5, institutional_flow_score=5,
                                market_liquidity_score=5, derivatives_risk_score=95,
                                derivatives_sentiment_score=5, correlation=.95)],
                    options={'risk_budget_by_regime': {'STRESS': .4}})[0]
    assert row['regime_label'] == 'STRESS'
    assert row['trend_vol_regime'] == 'BEAR_HIGH_VOL'
    assert row['market_stress_score'] >= 90
    assert row['bear_probability'] > .8
    assert row['recommended_risk_budget_multiplier'] == .4
    assert row['correlation_regime'] == 'CRISIS_CORRELATION'


def test_empty_inputs_are_invalid_and_partial_inputs_reduce_confidence():
    empty = dict(date=START, available_on=START, market_id='EMPTY', source_reference='test://empty')
    row = calculate([empty])[0]
    assert row['regime_quality_status'] == 'INVALID'
    assert row['regime_label'] is None and row['bull_probability'] is None
    assert row['regime_confidence'] == 0 and row['recommended_risk_budget_multiplier'] is None
    partial = calculate([observation(institutional_flow_score=None, derivatives_risk_score=None,
                                     derivatives_sentiment_score=None, breadth_coverage=.4)])[0]
    assert {'MISSING_FLOW', 'MISSING_DERIVATIVES', 'LOW_BREADTH_COVERAGE'} <= set(partial['quality_flags'])
    assert partial['regime_confidence'] < calculate()[0]['regime_confidence']


def test_conflicting_dimensions_and_recovery():
    conflicted = calculate([observation(breadth_score=10, institutional_flow_score=5)])[0]
    assert conflicted['conflicted_regime_flag']
    assert {'breadth', 'flow'} <= set(conflicted['disagreeing_inputs'])
    rows = calculate([observation(0, price_vs_sma200=-.05, breadth_score=30, institutional_flow_score=30,
                                  realized_volatility_21d=.3),
                      observation(1, price_vs_sma200=-.05, breadth_score=50, institutional_flow_score=50,
                                  realized_volatility_21d=.2)])
    assert rows[1]['recovery_regime_flag'] and rows[1]['regime_label'] == 'RECOVERY'


def test_hysteresis_and_minimum_persistence():
    rows = calculate([observation(0, realized_volatility_21d=.32, realized_volatility_63d=.32),
                      observation(1, realized_volatility_21d=.28, realized_volatility_63d=.28),
                      observation(2, realized_volatility_21d=.2, realized_volatility_63d=.2)])
    assert [r['high_volatility_flag'] for r in rows] == [True, True, False]
    bear = dict(market_return_21d=-.1, market_return_63d=-.1, price_vs_sma50=-.1,
                price_vs_sma200=-.1, market_slope_63d=-.002)
    rows = calculate([observation(), observation(1, **bear), observation(2, **bear)],
                     options={'minimum_persistence_sessions': 2})
    assert rows[1]['raw_regime_label'] == 'BEAR_LOW_VOL'
    assert rows[1]['regime_label'] == 'BULL_LOW_VOL'
    assert rows[2]['regime_label'] == 'BEAR_LOW_VOL'


def test_causal_prefix_invariance_gaps_and_market_isolation():
    prefix = [observation(i) for i in range(3)]
    initial = calculate(prefix)
    extended = calculate(prefix + [observation(3, breadth_score=0), observation(2, market_id='BANK_NIFTY')])
    assert [r for r in extended if r['market_id'] == 'NIFTY_50'][:3] == initial
    assert initial[-1]['days_in_current_regime'] == 3
    assert initial[-1]['regime_persistence_probability'] == 1
    assert next(r for r in extended if r['market_id'] == 'BANK_NIFTY')['days_in_current_regime'] == 1
    assert calculate([observation(), observation(2)])[-1]['days_in_current_regime'] == 1


@pytest.mark.parametrize('changes', [
    {'available_on': START + timedelta(days=1)}, {'breadth_score': 101},
    {'realized_volatility_21d': float('nan')}, {'current_drawdown': .1},
])
def test_invalid_or_future_inputs_rejected(changes):
    with pytest.raises(ValidationError):
        request([observation(**changes)])


def test_request_and_configuration_validation():
    for kwargs in ({'observations': [observation(), observation()]},
                   {'sessions': [START + timedelta(days=1), START]},
                   {'options': {'high_vol_exit': 80}},
                   {'options': {'risk_budget_by_regime': {'UNKNOWN': 1}}}):
        with pytest.raises(ValidationError):
            request(**kwargs)


def test_repository_roundtrip_reuse_and_configuration_identity():
    with duckdb.connect(':memory:') as conn:
        inputs = request([observation(), observation(1)])
        built = build_market_regime(conn, inputs)
        assert not built['reused']
        assert build_market_regime(conn, request([observation(1), observation()]))['reused']
        stored = get_records(conn, built['run_id'])
        assert stored['rows'] == calculate_market_regime(inputs)['rows']
        assert get_records(conn, built['run_id'], 1, 1)['rows'] == stored['rows'][1:]
        assert get_run(conn, built['run_id'])['configuration'] == inputs.model_dump(mode='json')
        changed = build_market_regime(conn, request(options={'trend_threshold': .3}))
        assert changed['run_id'] != built['run_id']
        with pytest.raises(LookupError):
            get_run(conn, 'unknown')


def test_api_auth_validation_and_calculation():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.dependencies import get_current_user
    from app.engines.market_regime.market_regime_routes import router

    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    client = TestClient(app)
    payload = request().model_dump(mode='json')
    assert client.post('/api/v1/market-regime/calculate', json=payload).status_code in (401, 403)
    app.dependency_overrides[get_current_user] = lambda: {'id': 1}
    response = client.post('/api/v1/market-regime/calculate', json=payload)
    assert response.status_code == 200
    assert response.json()['rows'][0]['regime_label'] == 'BULL_LOW_VOL'
    payload['observations'][0]['available_on'] = '2027-01-01'
    assert client.post('/api/v1/market-regime/calculate', json=payload).status_code == 422
