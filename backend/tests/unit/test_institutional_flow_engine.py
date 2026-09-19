from datetime import date, datetime, timedelta, timezone

import duckdb
import pytest
from pydantic import ValidationError

from app.engines.institutional_flow.institutional_flow_repository import build_institutional_flows, get_records
from app.engines.institutional_flow.institutional_flow_schema import InstitutionalFlowRequest
from app.engines.institutional_flow.institutional_flow_service import calculate_institutional_flows

pytestmark = pytest.mark.unit
UTC = timezone.utc
START = date(2026, 1, 1)


def market_observation(index, **overrides):
    day = START+timedelta(days=index-1)
    published = datetime.combine(day, datetime.min.time(), UTC)+timedelta(hours=17)
    fii_net, dii_net = index*10, -index*3
    values = dict(source_date=day, published_at=published, data_available_at=published+timedelta(hours=1),
                  ingested_at=published+timedelta(hours=1, minutes=5), revision=0,
                  source_name='NSE', source_reference=f'nse://flow/{day}',
                  fii_gross_buy=2000+fii_net, fii_gross_sell=2000, fii_net=fii_net,
                  dii_gross_buy=1500, dii_gross_sell=1500-dii_net, dii_net=dii_net,
                  market_turnover=100000, market_return=.001*index, market_breadth=.4,
                  india_vix=15, fii_index_futures_long=1000+index,
                  fii_index_futures_short=500, fii_stock_futures_long=700,
                  fii_stock_futures_short=600)
    values.update(overrides)
    return values


def evaluation(day, hour=20):
    return dict(date=day, evaluated_at=datetime.combine(day, datetime.min.time(), UTC)+timedelta(hours=hour))


def request(observations=None, evaluations=None, **overrides):
    observations = observations or [market_observation(index) for index in range(1, 66)]
    latest = START+timedelta(days=64)
    values = dict(snapshot_id='flow-fixture', as_of=datetime.combine(latest+timedelta(days=2), datetime.min.time(), UTC),
                  evaluations=evaluations or [evaluation(latest)], market_observations=observations)
    values.update(overrides)
    return InstitutionalFlowRequest.model_validate(values)


def test_market_cash_rolling_momentum_normalization_states_and_lineage():
    row = calculate_institutional_flows(request())['market_rows'][0]
    assert row['fii_gross_buy'] == 2650 and row['fii_gross_sell'] == 2000
    assert row['fii_net'] == 650 and row['dii_net'] == -195
    assert row['institutional_net'] == 455
    assert row['fii_net_5d'] == 3150
    assert row['fii_net_20d'] == 11100
    assert row['fii_net_60d'] == 21300
    assert row['fii_flow_momentum'] == pytest.approx(75)
    assert row['fii_flow_acceleration'] == pytest.approx(0)
    assert row['fii_flow_z_60d'] > 1
    assert row['fii_flow_percentile_252d'] == 100
    assert row['institutional_flow_state'] == 'FII_BUY_DII_SELL'
    assert row['flow_price_state'] == 'MARKET_UP_FII_BUYING'
    assert row['flow_breadth_confirmation'] == 'CONFIRMED'
    assert row['cash_futures_alignment'] == 'CASH_BUY_FUTURES_LONG'
    assert row['fii_index_futures_net_change'] == 1
    assert row['flow_confidence'] == 100
    assert row['flow_quality_status'] == 'VALID'
    assert row['source_reference'].startswith('nse://')


def test_incomplete_windows_and_missing_sessions_remain_null_not_zero():
    observations = [market_observation(index) for index in range(1, 4)]
    day = START+timedelta(days=2)
    row = calculate_institutional_flows(request(observations, [evaluation(day)]))['market_rows'][0]
    assert row['fii_net_5d'] is None
    assert row['fii_flow_momentum'] is None
    missing_day = day+timedelta(days=1)
    missing = calculate_institutional_flows(request(observations, [evaluation(missing_day)]))['market_rows'][0]
    assert not missing['flow_valid']
    assert missing['flow_quality_status'] == 'SOURCE_MISSING'


def test_revision_is_used_only_after_its_public_availability_timestamp():
    day = START
    original = market_observation(1)
    revision_time = datetime.combine(day, datetime.min.time(), UTC)+timedelta(hours=21)
    revised = market_observation(1, revision=1, published_at=revision_time,
                                 data_available_at=revision_time, ingested_at=revision_time,
                                 fii_gross_buy=2200, fii_gross_sell=2000, fii_net=200)
    evaluations = [evaluation(day, 20), evaluation(day, 22)]
    rows = calculate_institutional_flows(request([original, revised], evaluations))['market_rows']
    assert rows[0]['fii_net'] == 10 and rows[0]['revision'] == 0
    assert rows[1]['fii_net'] == 200 and rows[1]['revision'] == 1


def test_sector_rotation_has_historical_windows_and_cross_sectional_ranks():
    latest = START+timedelta(days=4)
    sectors = []
    for index in range(5):
        day = START+timedelta(days=index)
        available = datetime.combine(day, datetime.min.time(), UTC)+timedelta(hours=18)
        sectors.extend([
            dict(date=day, data_available_at=available, sector_id='IT', flow_value=100+index, source_name='Direct'),
            dict(date=day, data_available_at=available, sector_id='BANK', flow_value=-50-index, source_name='Direct'),
        ])
    result = calculate_institutional_flows(request(
        [market_observation(index) for index in range(1, 6)], [evaluation(latest)], sector_observations=sectors))
    rows = {row['sector_id']: row for row in result['sector_rows']}
    assert rows['IT']['sector_flow_5d'] == 510
    assert rows['IT']['sector_flow_rank'] == 1
    assert rows['IT']['sector_flow_percentile'] == 100
    assert rows['BANK']['sector_flow_percentile'] == 0


def test_stock_direct_evidence_and_delivery_proxy_are_not_conflated():
    day = START
    available = datetime.combine(day, datetime.min.time(), UTC)+timedelta(hours=18)
    stocks = [
        dict(date=day, data_available_at=available, instrument_key='A', institutional_buy_value=80,
             institutional_sell_value=20, direct_observation=True, source_name='Deal data'),
        dict(date=day, data_available_at=available, instrument_key='B', delivery_pct=75,
             delivery_z=2, direct_observation=False, source_name='Exchange volume'),
    ]
    result = calculate_institutional_flows(request([market_observation(1)], [evaluation(day)], stock_observations=stocks))
    rows = {row['instrument_key']: row for row in result['stock_rows']}
    assert rows['A']['institutional_net_value'] == 60
    assert rows['A']['flow_quality_status'] == 'VALID'
    assert rows['B']['flow_quality_status'] == 'PROXY_ONLY'
    assert rows['B']['institutional_net_value'] is None
    assert not rows['B']['delivery_is_institutional_flow']


def test_schema_enforces_net_identity_timezone_availability_and_source_consistency():
    with pytest.raises(ValidationError, match='conflicts'):
        request([market_observation(1, fii_net=999)], [evaluation(START)])
    payload = request([market_observation(1)], [evaluation(START)]).model_dump()
    payload['market_observations'][0]['published_at'] = payload['market_observations'][0]['published_at'].replace(tzinfo=None)
    with pytest.raises(ValidationError, match='timezone'):
        InstitutionalFlowRequest.model_validate(payload)
    payload = request([market_observation(1)], [evaluation(START)]).model_dump()
    payload['market_observations'].append(market_observation(2, source_name='Different Source'))
    with pytest.raises(ValidationError, match='consistent source'):
        InstitutionalFlowRequest.model_validate(payload)


def test_storage_is_content_addressed_idempotent_and_collections_queryable():
    conn = duckdb.connect(':memory:')
    try:
        req = request()
        first = build_institutional_flows(conn, req)
        second = build_institutional_flows(conn, req)
        assert second['reused'] and second['run_id'] == first['run_id']
        assert get_records(conn, first['run_id'], 'market')['total'] == 1
        assert get_records(conn, first['run_id'], 'sector')['total'] == 0
    finally:
        conn.close()
