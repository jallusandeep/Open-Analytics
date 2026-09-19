from datetime import date, timedelta

import duckdb
import pytest
from pydantic import ValidationError

from app.engines.valuation.valuation_repository import build_valuations, get_features
from app.engines.valuation.valuation_schema import ValuationRequest
from app.engines.valuation.valuation_service import calculate_valuations

pytestmark = pytest.mark.unit


def observation(key='A', day=date(2026, 1, 31), price=10, **overrides):
    values = dict(
        instrument_key=key, date=day, price_available_date=day,
        fundamental_available_date=day-timedelta(days=30), shares_available_date=day-timedelta(days=30),
        price=price, shares_outstanding=100, sector='Technology', industry='Software', size_bucket='MID',
        revenue_ttm=500, ebitda_ttm=100, ebit_ttm=80, net_income_ttm=50, eps_ttm=.5,
        shareholders_equity=250, operating_cash_flow_ttm=70, free_cash_flow_ttm=60,
        total_debt=40, cash=20, dividends_per_share_ttm=.2, eps_growth_yoy=.2,
        fundamental_quality_score=70, financial_strength_score=75,
    )
    values.update(overrides)
    return values


def request(rows=None, **overrides):
    values = dict(snapshot_id='valuation-fixture', as_of=date(2026, 3, 31),
                  minimum_history=2, minimum_peer_count=2,
                  observations=rows or [observation()])
    values.update(overrides)
    return ValuationRequest.model_validate(values)


def test_market_cap_enterprise_value_multiples_yields_and_dividend():
    row = calculate_valuations(request())['rows'][0]
    assert row['market_cap'] == 1000
    assert row['enterprise_value'] == 1020
    assert row['pe_ttm'] == 20
    assert row['earnings_yield'] == .05
    assert row['price_to_book'] == 4
    assert row['book_to_price'] == .25
    assert row['ev_ebitda'] == pytest.approx(10.2)
    assert row['ebit_to_ev'] == pytest.approx(80/1020)
    assert row['fcf_yield'] == .06
    assert row['dividend_yield'] == .02
    assert row['valuation_quality_status'] == 'VALID'


def test_invalid_multiples_remain_missing_and_reasons_are_explainable():
    row = calculate_valuations(request([observation(net_income_ttm=-10, eps_ttm=-.1,
                                                        shareholders_equity=-20, ebitda_ttm=-5)]))['rows'][0]
    assert row['pe_ttm'] is None and not row['pe_valid']
    assert row['price_to_book'] is None and not row['pb_valid']
    assert row['ev_ebitda'] is None and not row['ev_ebitda_valid']
    assert 'NEGATIVE_EARNINGS' in row['valuation_invalid_reason']
    assert 'NEGATIVE_EQUITY' in row['valuation_invalid_reason']
    assert 'NEGATIVE_EBITDA' in row['valuation_invalid_reason']


def test_historical_percentiles_use_only_information_available_so_far():
    days = [date(2026, month, 28) for month in (1, 2, 3)]
    rows = [observation(day=day, price=price) for day, price in zip(days, (20, 15, 10))]
    full = calculate_valuations(request(rows))['rows']
    assert full[0]['pe_hist_percentile_5y'] is None
    assert full[1]['pe_hist_percentile_5y'] == 100
    assert full[2]['pe_hist_percentile_5y'] == 100
    prefix = calculate_valuations(request(rows[:2], as_of=days[1]))['rows'][-1]
    assert prefix['pe_hist_percentile_5y'] == full[1]['pe_hist_percentile_5y']
    old = observation(day=date(2020, 1, 31), price=30,
                      fundamental_available_date=date(2020, 1, 1), shares_available_date=date(2020, 1, 1))
    recent = observation(day=date(2026, 1, 31), price=10)
    latest = calculate_valuations(request([old, recent]))['rows'][-1]
    assert latest['pe_hist_percentile_5y'] is None
    assert latest['history_observation_count'] == 1


def test_peer_value_scores_rank_cheap_stock_and_supply_sector_context():
    rows = [observation('A', price=20), observation('B', price=10),
            observation('C', price=5, sector='Healthcare', industry='Pharma')]
    output = {row['instrument_key']: row for row in calculate_valuations(request(rows))['rows']}
    assert output['C']['value_percentile'] > output['B']['value_percentile'] > output['A']['value_percentile']
    assert output['B']['sector_value_percentile'] == 100
    assert output['A']['sector_value_percentile'] == 0
    assert output['C']['sector_value_percentile'] is None
    assert output['B']['sector_neutral_value_z'] is not None


def test_staleness_and_distress_reduce_confidence_without_hiding_raw_value():
    row = observation(fundamental_available_date=date(2024, 1, 1),
                      fundamental_quality_score=20, financial_strength_score=20)
    output = calculate_valuations(request([row]))['rows'][0]
    assert output['valuation_staleness_flag']
    assert output['distress_trap_flag']
    assert output['market_cap'] == 1000
    assert 'STALE_FUNDAMENTALS' in output['valuation_invalid_reason']
    assert 'DISTRESS_RISK' in output['valuation_invalid_reason']


def test_schema_blocks_lookahead_duplicates_and_inconsistent_market_cap():
    payload = request().model_dump()
    payload['observations'][0]['fundamental_available_date'] = payload['observations'][0]['date'] + timedelta(days=1)
    with pytest.raises(ValidationError, match='fundamentals must be known'):
        ValuationRequest.model_validate(payload)
    payload = request().model_dump()
    payload['observations'].append(payload['observations'][0])
    with pytest.raises(ValidationError, match='unique'):
        ValuationRequest.model_validate(payload)
    with pytest.raises(ValidationError, match='market_cap conflicts'):
        request([observation(market_cap=500)])


def test_storage_is_content_addressed_idempotent_and_date_queryable():
    rows = [observation(day=date(2026, 1, 31)), observation(day=date(2026, 2, 28), price=11)]
    conn = duckdb.connect(':memory:')
    try:
        first = build_valuations(conn, request(rows))
        second = build_valuations(conn, request(rows))
        assert second['reused'] and second['run_id'] == first['run_id']
        result = get_features(conn, first['run_id'], start_date=date(2026, 2, 1))
        assert result['total'] == 1
        assert result['rows'][0]['date'] == '2026-02-28'
    finally:
        conn.close()
