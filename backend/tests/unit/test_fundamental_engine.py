from datetime import date, timedelta

import duckdb
import pytest
from pydantic import ValidationError

from app.engines.fundamental.fundamental_repository import build_fundamentals, get_features
from app.engines.fundamental.fundamental_schema import FundamentalRequest
from app.engines.fundamental.fundamental_service import calculate_fundamentals, growth, ratio

pytestmark = pytest.mark.unit


PERIODS = [
    date(2024, 3, 31), date(2024, 6, 30), date(2024, 9, 30), date(2024, 12, 31),
    date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31),
]


def statement(period, index, **overrides):
    values = dict(
        instrument_key='NSE_EQ|ACME', company_id='ACME', sector='Industrials',
        period_end_date=period, period_type='QUARTERLY',
        announcement_date=period + timedelta(days=30),
        data_available_date=period + timedelta(days=30), revision=0, currency='INR',
        revenue=100 + index*10, gross_profit=40 + index*4, ebitda=20 + index*2,
        ebit=16 + index*2, profit_before_tax=14 + index*2, tax_expense=3 + index*.4,
        net_income=11 + index*1.5, eps=1.1 + index*.15,
        cash=30, total_assets=300 + index*10, current_assets=120,
        current_liabilities=60, inventory=20, receivables=25,
        total_debt=80-index*2, shareholders_equity=160+index*5,
        operating_cash_flow=15+index*2, capital_expenditure=5,
        interest_expense=2, shares_outstanding=10,
    )
    values.update(overrides)
    return values


def request(rows=None, as_of=date(2026, 3, 1), stale_after_days=550):
    rows = rows or [statement(period, index) for index, period in enumerate(PERIODS)]
    return FundamentalRequest.model_validate(dict(snapshot_id='fundamental-fixture', as_of=as_of,
                                                   stale_after_days=stale_after_days, statements=rows))


def calculated(req=None):
    return calculate_fundamentals(req or request())['rows'][0]


def test_ttm_growth_margins_returns_leverage_and_cash_metrics():
    row = calculated()
    assert row['period_type'] == 'TTM'
    assert row['revenue_ttm'] == 620
    assert row['revenue_growth_yoy'] == pytest.approx(620/460-1)
    assert row['ebitda_margin'] == pytest.approx(124/620)
    assert row['net_debt'] == 36
    assert row['net_debt_to_ebitda'] == pytest.approx(36/124)
    assert row['current_ratio'] == 2
    assert row['free_cash_flow_ttm'] == 84
    assert row['fundamental_quality_status'] == 'VALID'
    assert row['fundamental_valid']


def test_latest_known_restatement_wins_without_destroying_source_history():
    rows = [statement(period, index) for index, period in enumerate(PERIODS)]
    rows.append(statement(PERIODS[-1], 7, revision=1,
                          data_available_date=date(2026, 2, 20), revenue=200))
    row = calculated(request(rows))
    assert row['source_revision'] == 1
    assert row['revenue_ttm'] == 650
    assert len(rows) == 9


def test_sign_changes_and_unsafe_denominators_are_missing_not_fake_growth():
    assert growth(5, -2) is None
    assert growth(-5, -2) == 1.5
    assert ratio(10, 0) is None
    assert ratio(10, -2, positive_denominator=True) is None
    rows = [statement(period, index) for index, period in enumerate(PERIODS)]
    for row in rows[:4]:
        row['net_income'] = -1
        row['eps'] = -0.1
    output = calculated(request(rows))
    assert output['net_income_growth_yoy'] is None
    assert output['eps_growth_yoy'] is None


def test_incomplete_quarter_history_falls_back_to_annual_statement():
    annual = statement(date(2025, 3, 31), 0, period_type='ANNUAL', revenue=900,
                       data_available_date=date(2025, 5, 1), announcement_date=date(2025, 5, 1))
    row = calculated(request([annual], as_of=date(2025, 6, 1)))
    assert row['period_type'] == 'ANNUAL'
    assert row['revenue_ttm'] == 900


def test_staleness_and_missing_core_values_are_explicit_quality_states():
    stale = calculated(request(as_of=date(2028, 1, 1)))
    assert stale['fundamental_staleness_flag']
    assert stale['fundamental_quality_status'] == 'STALE'
    rows = [statement(period, index, shareholders_equity=None) for index, period in enumerate(PERIODS)]
    partial = calculated(request(rows))
    assert partial['fundamental_quality_status'] == 'PARTIAL'
    assert 'shareholders_equity' in partial['fundamental_invalid_reason']


def test_schema_enforces_point_in_time_versions_currency_and_public_dates():
    payload = request().model_dump()
    payload['statements'][0]['data_available_date'] = payload['as_of'] + timedelta(days=1)
    with pytest.raises(ValidationError, match='known by as_of'):
        FundamentalRequest.model_validate(payload)
    payload = request().model_dump()
    payload['statements'][0]['currency'] = 'USD'
    with pytest.raises(ValidationError, match='currency normalization'):
        FundamentalRequest.model_validate(payload)
    bad = statement(PERIODS[0], 0, data_available_date=PERIODS[0]+timedelta(days=2))
    with pytest.raises(ValidationError, match='public filing date'):
        FundamentalRequest.model_validate(dict(snapshot_id='x', as_of=date(2026, 1, 1), statements=[bad]))


def test_storage_is_content_addressed_idempotent_and_queryable():
    conn = duckdb.connect(':memory:')
    try:
        first = build_fundamentals(conn, request())
        second = build_fundamentals(conn, request())
        assert second['reused'] and second['run_id'] == first['run_id']
        result = get_features(conn, first['run_id'], instrument_key='NSE_EQ|ACME')
        assert result['total'] == 1
        assert result['rows'][0]['revenue_ttm'] == 620
    finally:
        conn.close()
