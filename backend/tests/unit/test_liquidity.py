from datetime import date, datetime, time, timedelta, timezone

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dependencies import get_current_user
from app.engines.liquidity.liquidity_schema import LiquidityRequest
from app.engines.liquidity.liquidity_service import calculate_liquidity
from app.engines.liquidity.liquidity_repository import build_liquidity, ensure_liquidity_schema, get_features
from app.engines.liquidity.liquidity_routes import router

pytestmark = pytest.mark.unit


def payload(n=65, keys=('A', 'B', 'C')):
    sessions = []
    day = date(2025, 1, 1)
    while len(sessions) < n:
        if day.weekday() < 5:
            sessions.append(day)
        day += timedelta(days=1)
    observations, memberships = [], []
    for k, key in enumerate(keys):
        for i, day in enumerate(sessions):
            stamp = datetime.combine(day, time(15, 30), timezone.utc)
            observations.append(dict(instrument_key=key, date=day, available_on=day,
                open=100, high=101, low=99, close=100, volume=1000000*(k+1),
                adjusted_close=100+i, adjustment_valid=True, quality_valid=True, trading_status='ACTIVE',
                quote_timestamp=stamp, observation_timestamp=stamp, bid_price=99.9, ask_price=100.1,
                bid_size=1000, ask_size=1000, lot_size=1, tick_size=.05,
                order_value=1e6, position_value=1e7, market_cap=1e10, free_float_market_cap=5e9))
            memberships.append(dict(instrument_key=key, date=day, available_on=day, universe_id='historical', sector_id='sector', size_bucket='large'))
    return dict(snapshot_id='test', calendar_version='test-calendar', as_of=sessions[-1], sessions=sessions,
                instrument_keys=list(keys), observations=observations, memberships=memberships)


def calculate(p):
    return calculate_liquidity(LiquidityRequest.model_validate(p))['rows']


def test_daily_rolling_capacity_and_execution():
    r = calculate(payload())[-1]
    assert r['daily_volume'] == 3000000
    assert r['adv'] == r['median_traded_value_20d'] == 300000000
    assert r['trading_frequency_60d'] == 1
    assert r['avg_traded_value_252d'] is None
    assert r['spread_pct'] == pytest.approx(.002)
    assert r['total_depth_value'] == 200000
    assert r['max_daily_order_value'] == 15000000
    assert r['days_to_liquidate'] == pytest.approx(2/3)
    assert r['turnover_ratio'] == .03
    assert r['execution_eligible']
    assert r['liquidity_score'] > 50
    assert r['expected_slippage_bps'] is None


def test_missing_is_not_zero_volume():
    p = payload(25, ('A',))
    p['observations'][-1]['volume'] = 0
    r = calculate(p)[-1]
    assert r['zero_volume_days_20d'] == 1
    assert r['trading_frequency_20d'] == .95
    assert not r['execution_eligible']
    assert 'NO_TRADING_ACTIVITY' in r['liquidity_exclusion_detail']
    p['observations'].pop()
    r = calculate(p)[-1]
    assert r['daily_volume'] is None
    assert r['adv'] is None
    assert r['zero_volume_days_20d'] is None
    assert not r['execution_eligible']


@pytest.mark.parametrize('change', ['missing', 'stale', 'future', 'crossed'])
def test_untrusted_quotes_are_null(change):
    p = payload(22, ('A',))
    o = p['observations'][-1]
    if change == 'missing':
        o['quote_timestamp'] = None
    elif change == 'stale':
        o['quote_timestamp'] -= timedelta(hours=1)
    elif change == 'future':
        o['quote_timestamp'] += timedelta(seconds=1)
    else:
        o['ask_price'] = 99
    r = calculate(p)[-1]
    assert r['spread_pct'] is None and r['total_depth_value'] is None
    assert r['liquidity_quality_status'] == 'LIMITED'
    assert 'MISSING_OR_STALE_SPREAD' in r['liquidity_exclusion_detail']


def test_no_lookahead_and_late_data():
    p = payload(45)
    old = calculate(p)
    for o in p['observations']:
        if o['date'] > p['sessions'][30]:
            o['volume'] *= 100
    new = calculate(p)
    assert [r for r in old if r['date'] <= p['sessions'][30].isoformat()] == [r for r in new if r['date'] <= p['sessions'][30].isoformat()]
    p['observations'][20]['available_on'] += timedelta(days=1)
    assert calculate(p)[20]['daily_volume'] is None


def test_amihud_requires_adjustment_and_adjacent_session():
    p = payload(22, ('A',))
    r = calculate(p)[-1]
    assert r['amihud'] == pytest.approx((121/120-1)/1e8)
    assert r['amihud_20d'] is not None
    p['observations'][-2]['adjustment_valid'] = False
    assert calculate(p)[-1]['amihud'] is None
    p['observations'].pop(-2)
    assert calculate(p)[-1]['amihud'] is None


def test_rank_directions_and_incomplete_universe():
    p = payload(22)
    rows = [r for r in calculate(p) if r['date'] == p['as_of'].isoformat()]
    assert [r['adv_percentile'] for r in rows] == [0, 50, 100]
    assert [r['amihud_percentile'] for r in rows] == [0, 50, 100]
    assert [r['spread_percentile'] for r in rows] == [50, 50, 50]
    p['memberships'].append(dict(instrument_key='not-loaded', date=p['as_of'], available_on=p['as_of'], universe_id='historical'))
    r = calculate(p)[-1]
    assert r['liquidity_score'] is None and r['ranking_invalid_reason'] == 'INCOMPLETE_UNIVERSE'


@pytest.mark.parametrize('field,value,reason', [
    ('order_value', 1e9, 'PARTICIPATION_LIMIT'), ('position_value', 1e10, 'EXIT_CAPACITY_LIMIT'),
    ('trading_status', 'DELISTED', 'TRADING_STATUS_NOT_ACTIVE'), ('settlement_issue_flag', True, 'SETTLEMENT_ISSUE_FLAG'),
    ('order_price', 100.01, 'INVALID_TICK_SIZE'), ('upper_circuit_price', 100, 'CIRCUIT_RISK')])
def test_rejection_reasons_preserve_research(field, value, reason):
    p = payload(22, ('A',))
    p['observations'][-1][field] = value
    r = calculate(p)[-1]
    assert r['research_eligible']
    assert not r['execution_eligible']
    assert reason in r['liquidity_exclusion_detail']


def test_snapshot_idempotence_pagination_and_rollback():
    request = LiquidityRequest.model_validate(payload(22, ('A',)))
    with duckdb.connect(':memory:') as conn:
        ensure_liquidity_schema(conn)
        run = build_liquidity(conn, request)
        assert build_liquidity(conn, request)['reused']
        assert get_features(conn, run['run_id'], 'A', 2, 20)['rows'][-1]['adv'] == 1e8
        assert get_features(conn, run['run_id'])['total'] == 22
        class FailingConnection:
            def execute(self, *args): return conn.execute(*args)
            def executemany(self, *args): raise RuntimeError('storage failed')
            def rollback(self): conn.rollback()
        request.snapshot_id = 'other'
        with pytest.raises(RuntimeError, match='storage failed'):
            build_liquidity(FailingConnection(), request)
        assert conn.execute('SELECT count(*) FROM liquidity_runs').fetchone()[0] == 1


def test_api_auth_schema_and_registration():
    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    client = TestClient(app)
    data = LiquidityRequest.model_validate(payload(22, ('A',))).model_dump(mode='json')
    assert client.post('/api/v1/liquidity/calculate', json=data).status_code in (401, 403)
    app.dependency_overrides[get_current_user] = lambda: {'user_id': 'test'}
    assert client.post('/api/v1/liquidity/calculate', json=data).status_code == 200
    data['observations'][0]['volume'] = -1
    assert client.post('/api/v1/liquidity/calculate', json=data).status_code == 422
    from app.main import app as main_app
    assert '/api/v1/liquidity/build' in main_app.openapi()['paths']


def test_invalid_duplicate_and_options():
    p = payload(22, ('A',))
    p['observations'].append(p['observations'][0])
    with pytest.raises(ValidationError):
        LiquidityRequest.model_validate(p)
    p['observations'].pop()
    p['options'] = {'composite_weights': {'adv': 1}}
    with pytest.raises(ValidationError):
        LiquidityRequest.model_validate(p)


def test_exchange_value_depth_and_configured_impact():
    p = payload(25, ('A',))
    p['options'] = {'impact_coefficient': .5}
    for o in p['observations']:
        o['traded_value'] = 2e8
        o['bids'] = [dict(price=99.9-i*.1, size=100) for i in range(5)]
        o['asks'] = [dict(price=100.1+i*.1, size=100) for i in range(5)]
    r = calculate(p)[-1]
    assert r['adv'] == 2e8 and r['traded_value_source'] == 'EXCHANGE'
    assert r['bid_depth_l5'] == 500
    assert r['bid_depth_value'] == pytest.approx(49850)
    assert r['expected_slippage_bps'] >= 10
    assert r['impact_model'] == 'CONFIGURED_SQUARE_ROOT_PROXY'


def test_volume_event_is_retained_and_shock_detected():
    p = payload(45, ('A',))
    p['observations'][-2]['volume'] *= 100
    rows = calculate(p)
    assert rows[-2]['volume_outlier_flag']
    assert rows[-2]['daily_volume'] == 1e8
    assert rows[-1]['liquidity_shock_flag']


def test_share_order_cannot_bypass_capacity():
    p = payload(22, ('A',))
    o = p['observations'][-1]
    o['order_value'] = None
    o['order_shares'] = 1000000
    r = calculate(p)[-1]
    assert r['requested_order_value'] == 1e8
    assert 'PARTICIPATION_LIMIT' in r['liquidity_exclusion_detail']


def test_full_year_window_and_zero_variance():
    r = calculate(payload(253, ('A',)))[-1]
    assert r['avg_volume_252d'] == 1e6
    assert r['median_traded_value_252d'] == 1e8
    assert r['amihud_252d'] is not None
    assert r['volume_zscore_20d'] is None
    assert r['volume_cv_20d'] == 0


def test_late_membership_does_not_admit_security():
    p = payload(22, ('A',))
    p['memberships'][-1]['available_on'] += timedelta(days=1)
    r = calculate(p)[-1]
    assert not r['research_eligible'] and not r['execution_eligible']


def test_activity_statistics_against_hand_calculated_series():
    from statistics import fmean, median, pstdev
    p = payload(25, ('A',))
    for i, o in enumerate(p['observations']):
        o.update(volume=(i+1)*100, traded_value=(i+1)*10000,
                 delivery_percentage=20+i, trade_count=10)
    r = calculate(p)[-1]
    volumes = list(range(600, 2600, 100))
    assert r['avg_volume_20d'] == fmean(volumes)
    assert r['median_volume_20d'] == median(volumes)
    assert r['volume_std_20d'] == pytest.approx(pstdev(volumes))
    assert r['volume_cv_20d'] == pytest.approx(pstdev(volumes)/fmean(volumes))
    assert r['rvol_20d'] == pytest.approx(2500/fmean(volumes))
    assert r['traded_value_std_20d'] == pytest.approx(pstdev(volumes)*100)
    assert r['delivery_zscore'] == pytest.approx((44-34.5)/pstdev(range(25, 45)))
    assert r['avg_delivery_pct_20d'] == 34.5
    assert r['avg_trade_size'] == 250 and r['avg_trade_value'] == 25000
    assert r['avg_trade_count_20d'] == 10
    assert r['turnover_20d'] == pytest.approx(155000/1e10)
    assert r['free_float_turnover'] == pytest.approx(250000/5e9)
    assert r['turnover_velocity'] == pytest.approx(155000*20/5e9)


@pytest.mark.parametrize('side,execution,expected', [('BUY', 101, 1), ('SELL', 99, 1), ('BUY', 99, -1), ('SELL', 101, -1)])
def test_effective_spread_and_realized_slippage(side, execution, expected):
    p = payload(22, ('A',))
    p['observations'][-1].update(side=side, execution_price=execution, reference_price=100, trade_price=100.05)
    r = calculate(p)[-1]
    assert r['slippage'] == expected and r['slippage_bps'] == expected*100
    assert r['effective_spread'] == pytest.approx(.1)
    assert r['effective_spread_pct'] == pytest.approx(.001)
    assert r['avg_spread_pct_20d'] == pytest.approx(.002)
    assert r['median_spread_pct_20d'] == pytest.approx(.002)


@pytest.mark.parametrize('options,reason', [
    ({'max_price_impact': 0}, 'UNKNOWN_PRICE_IMPACT'),
    ({'max_expected_slippage_bps': 0}, 'UNKNOWN_SLIPPAGE'),
    ({'impact_coefficient': 1, 'max_price_impact': 0}, 'HIGH_PRICE_IMPACT'),
    ({'impact_coefficient': 1, 'max_expected_slippage_bps': 1}, 'HIGH_SLIPPAGE'),
    ({'require_derivatives': True}, 'DERIVATIVES_UNAVAILABLE'),
    ({'require_stable_order_book': True}, 'ORDER_BOOK_STABILITY_UNCONFIRMED'),
    ({'require_short_sale': True}, 'SHORT_SALE_UNAVAILABLE'),
    ({'min_adv': 1e12}, 'LOW_ADV'),
    ({'max_spread_pct': .0001}, 'WIDE_SPREAD'),
    ({'min_price': 101}, 'PRICE_INELIGIBLE')])
def test_strategy_specific_restrictions(options, reason):
    p = payload(22, ('A',))
    p['options'] = options
    r = calculate(p)[-1]
    assert reason in r['liquidity_exclusion_detail']
    assert not r['execution_eligible'] and r['research_eligible']


def test_impact_ranking_and_configurable_composite():
    p = payload(22)
    p['options'] = {'impact_coefficient': 1, 'composite_weights': {'adv': 1, 'impact': 1}}
    rows = [r for r in calculate(p) if r['date'] == p['as_of'].isoformat()]
    assert [r['impact_percentile'] for r in rows] == [0, 50, 100]
    assert [r['liquidity_score'] for r in rows] == [0, 50, 100]
    assert [r['liquidity_bucket'] for r in rows] == ['VERY_LOW', 'MEDIUM', 'VERY_HIGH']
    assert [r['sector_liquidity_percentile'] for r in rows] == [0, 50, 100]
    assert [r['size_bucket_liquidity_percentile'] for r in rows] == [0, 50, 100]


def test_invalid_rows_keep_nullable_output_contract():
    p = payload(22, ('A',))
    healthy = calculate(p)[-1]
    p['observations'][-1]['quality_valid'] = False
    invalid = calculate(p)[-1]
    assert healthy.keys() == invalid.keys()
    for field in ('spread_abs', 'bid_depth_value', 'delivery_quantity', 'slippage', 'quote_age'):
        assert invalid[field] is None
    assert invalid['liquidity_quality_status'] == 'INVALID'
    assert not invalid['research_eligible']


def test_asof_truncation_and_survivor_retention():
    p = payload(45, ('A',))
    original = calculate(p)
    p['observations'][-1]['trading_status'] = 'DELISTED'
    changed = calculate(p)
    assert changed[:-1] == original[:-1]
    assert len(changed) == 45 and changed[-1]['trading_status'] == 'DELISTED'
    p['as_of'] = p['sessions'][21]
    assert calculate(p) == original[:22]


@pytest.mark.parametrize('factor,trend', [(10, 'IMPROVING'), (.1, 'DETERIORATING'), (1, 'STABLE')])
def test_adv_trend_without_other_available_components(factor, trend):
    p = payload(45, ('A',))
    for i, o in enumerate(p['observations']):
        o.update(adjustment_valid=False, quote_timestamp=None)
        if i >= 24:
            o['volume'] *= factor
    r = calculate(p)[-1]
    assert r['adv_change_21d'] == pytest.approx(factor-1)
    assert r['liquidity_trend'] == trend


def test_circuit_metadata_unknown_flags_and_restrictions():
    p = payload(22, ('A',))
    assert calculate(p)[-1]['circuit_risk_flag'] is None
    p['observations'][-1].update(upper_circuit_price=101, lower_circuit_price=90,
                               market_cap=1e8, block_deal_value=123, bulk_deal_value=456)
    r = calculate(p)[-1]
    assert r['upper_circuit_price'] == 101 and r['lower_circuit_price'] == 90
    assert r['circuit_hit_flag'] and r['microcap_liquidity_warning']
    assert r['block_deal_value'] == 123 and r['bulk_deal_value'] == 456


def test_zero_capacity_and_inconsistent_exchange_value():
    p = payload(22, ('A',))
    for o in p['observations']:
        o['volume'] = 0
    r = calculate(p)[-1]
    assert r['adv'] == 0 and r['days_to_liquidate'] is None
    assert r['max_daily_order_value'] == 0
    assert 'EXIT_CAPACITY_LIMIT' in r['liquidity_exclusion_detail']
    p['observations'][-1]['traded_value'] = 100
    assert not calculate(p)[-1]['traded_value_valid']


def test_api_build_get_features_errors_and_immutable_configuration(monkeypatch):
    from app.engines.liquidity import liquidity_routes
    with duckdb.connect(':memory:') as conn:
        ensure_liquidity_schema(conn)
        class Proxy:
            def execute(self, *args): return conn.execute(*args)
            def executemany(self, *args): return conn.executemany(*args)
            def commit(self): conn.commit()
            def rollback(self): conn.rollback()
            def close(self): pass
        monkeypatch.setattr(liquidity_routes, 'get_connection', Proxy)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: {'user_id': 'test'}
        client = TestClient(app)
        data = LiquidityRequest.model_validate(payload(22, ('A',))).model_dump(mode='json')
        response = client.post('/liquidity/build', json=data)
        assert response.status_code == 200
        run_id = response.json()['run_id']
        assert client.post('/liquidity/build', json=data).json()['reused']
        saved = client.get(f'/liquidity/runs/{run_id}').json()
        assert saved['configuration']['snapshot_id'] == data['snapshot_id']
        assert client.get('/liquidity/features', params={'run_id': run_id, 'limit': 1, 'offset': 21}).json()['rows'][0]['adv'] == 1e8
        assert client.get('/liquidity/features', params={'run_id': run_id, 'limit': 0}).status_code == 422
        assert client.get('/liquidity/runs/missing').status_code == 404
        data['options']['min_adv'] *= 2
        assert client.post('/liquidity/build', json=data).json()['run_id'] != run_id
        assert client.get(f'/liquidity/runs/{run_id}').json() == saved


def test_documentation_example_runs():
    import json
    import re
    from pathlib import Path
    guide = Path(__file__).resolve().parents[2] / 'docs' / 'liquidity.md'
    example = json.loads(re.findall(r'```json\n(.*?)\n```', guide.read_text(encoding='utf-8'), re.S)[0])
    r = calculate(example)[-1]
    assert r['daily_traded_value'] == 101000000
    assert r['adv'] is None and not r['execution_eligible']


def test_recommended_record_fields_match_research_spec():
    import re
    from pathlib import Path
    spec = (Path(__file__).resolve().parents[3] / 'Research' / '06_liquidity_tradability_engine.md').read_text(encoding='utf-8')
    section = spec.split('# 6.54 Recommended Daily Liquidity Record')[1].split('# 6.55')[0]
    fields = {line.strip() for block in re.findall(r'```text\n(.*?)\n```', section, re.S)
              for line in block.splitlines() if line.strip() and not line.lstrip().startswith('#')}
    assert fields <= calculate(payload(22, ('A',)))[-1].keys()


@pytest.mark.parametrize('field', ['auction_flag', 'trade_to_trade_flag', 'special_series_flag', 'corporate_event_restriction'])
def test_market_restrictions_reject_execution(field):
    p = payload(22, ('A',))
    p['observations'][-1][field] = True
    r = calculate(p)[-1]
    assert field.upper() in r['liquidity_exclusion_detail']


def test_order_book_stability_derivatives_and_variability_options():
    p = payload(22, ('A',))
    p['options'] = {'require_stable_order_book': True, 'require_derivatives': True,
                    'require_short_sale': True, 'max_volume_cv': 0}
    p['observations'][-1].update(order_book_stable=True, derivatives_available=True, short_sale_available=True)
    assert calculate(p)[-1]['execution_eligible']
    p['observations'][-1]['volume'] *= 2
    assert 'UNSTABLE_VOLUME' in calculate(p)[-1]['liquidity_exclusion_detail']


def test_order_lot_rounding_depth_limits_and_boundary_participation():
    p = payload(22, ('A',))
    p['observations'][-1].update(lot_size=3, order_value=5e6)
    r = calculate(p)[-1]
    assert r['max_position_shares'] == 49998
    assert r['execution_eligible']  # Exactly the participation limit is accepted.
    p['observations'][-1].update(order_value=None, order_shares=4)
    assert 'INVALID_LOT_SIZE' in calculate(p)[-1]['liquidity_exclusion_detail']
    p['observations'][-1].update(order_shares=None, ask_size=0)
    assert 'EMPTY_BOOK_SIDE' in calculate(p)[-1]['liquidity_exclusion_detail']


def test_invalid_depth_order_is_not_trusted():
    p = payload(22, ('A',))
    p['observations'][-1]['bids'] = [{'price': 99.9, 'size': 100}, {'price': 100, 'size': 100}]
    r = calculate(p)[-1]
    assert r['spread_available'] and not r['depth_available']
    assert r['total_depth_value'] is None
    assert 'INSUFFICIENT_DEPTH' in r['liquidity_exclusion_detail']
