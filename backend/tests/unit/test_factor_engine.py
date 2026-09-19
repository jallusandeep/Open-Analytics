from datetime import date, timedelta

import duckdb
import pytest
from pydantic import ValidationError

from app.engines.factor.factor_repository import build_factors, get_records
from app.engines.factor.factor_schema import FactorRequest
from app.engines.factor.factor_service import calculate_factors

pytestmark = pytest.mark.unit
DAY = date(2026, 3, 31)


def definitions(neutralize=False):
    return [
        dict(factor_name='MOMENTUM', factor_version='MOMENTUM_V1', minimum_component_count=1,
             neutralization=['SECTOR'] if neutralize else [], components=[
                 dict(metric_name='mom_12_1', source_engine='returns', weight=2),
                 dict(metric_name='mom_6_1', source_engine='returns', weight=1),
             ]),
        dict(factor_name='LOW_VOL', factor_version='LOW_VOL_V1', components=[
                 dict(metric_name='ann_vol_252d', source_engine='risk', direction='LOWER_IS_BETTER'),
             ]),
    ]


def observations(missing=False):
    rows = []
    for index, key in enumerate('ABCDE'):
        metadata = dict(instrument_key=key, date=DAY, available_on=DAY, universe_id='U',
                        sector='S1' if index < 3 else 'S2', industry='I1' if index < 3 else 'I2',
                        size_bucket='MID')
        rows.append(dict(**metadata, metric_name='mom_12_1', value=index+1))
        if not (missing and key == 'C'):
            rows.append(dict(**metadata, metric_name='mom_6_1', value=index+2))
        rows.append(dict(**metadata, metric_name='ann_vol_252d', value=.5-index*.05))
    return rows


def request(rows=None, defs=None, returns=None, **overrides):
    values = dict(snapshot_id='factor-fixture', as_of=DAY+timedelta(days=30),
                  definitions=defs or definitions(), observations=rows or observations(),
                  forward_returns=returns or [], minimum_peer_count=2)
    values.update(overrides)
    return FactorRequest.model_validate(values)


def factor_rows(result, name):
    return {row['instrument_key']: row for row in result['rows'] if row['factor_name'] == name}


def test_weighted_normalized_components_rank_and_deciles_are_explainable():
    result = calculate_factors(request())
    momentum = factor_rows(result, 'MOMENTUM')
    assert momentum['E']['factor_rank'] == 1
    assert momentum['E']['factor_percentile'] == 100
    assert momentum['E']['factor_decile'] == 10
    assert momentum['A']['factor_percentile'] == 0
    assert len(momentum['E']['components']) == 2
    assert momentum['E']['components'][0]['raw_value'] == 5
    assert momentum['E']['components'][0]['winsorized_value'] < 5


def test_low_volatility_reverses_direction_so_lower_risk_is_stronger():
    low_vol = factor_rows(calculate_factors(request()), 'LOW_VOL')
    assert low_vol['E']['factor_rank'] == 1
    assert low_vol['E']['factor_percentile'] == 100
    assert low_vol['A']['factor_percentile'] == 0


def test_missing_components_are_renormalized_and_quality_is_partial():
    momentum = factor_rows(calculate_factors(request(observations(missing=True))), 'MOMENTUM')
    assert momentum['C']['raw_factor_z'] is not None
    assert momentum['C']['factor_quality_status'] == 'PARTIAL_COMPONENTS'
    assert momentum['C']['factor_confidence'] == 50
    strict = definitions()
    strict[0]['missing_value_rule'] = 'REQUIRE_ALL'
    momentum = factor_rows(calculate_factors(request(observations(missing=True), strict)), 'MOMENTUM')
    assert momentum['C']['raw_factor_z'] is None
    assert momentum['C']['factor_quality_status'] == 'INVALID'


def test_sector_neutralization_is_explicit_and_demeans_each_peer_group():
    momentum = factor_rows(calculate_factors(request(defs=definitions(neutralize=True))), 'MOMENTUM')
    s1 = [momentum[key]['neutralized_factor_z'] for key in 'ABC']
    s2 = [momentum[key]['neutralized_factor_z'] for key in 'DE']
    assert sum(s1)/len(s1) == pytest.approx(0)
    assert sum(s2)/len(s2) == pytest.approx(0)
    assert all(row['neutralization_applied'] == ['SECTOR'] for row in momentum.values())


def test_composites_diagnostics_and_correlations_are_separate_outputs():
    forward = [dict(instrument_key=key, factor_date=DAY, horizon=21,
                    return_value=index*.02, available_on=DAY+timedelta(days=21))
               for index, key in enumerate('ABCDE')]
    result = calculate_factors(request(returns=forward, transaction_cost_bps=10))
    assert len(result['composites']) == 5
    assert set(result['composites'][0]['factors']) == {'MOMENTUM', 'LOW_VOL'}
    momentum = next(row for row in result['diagnostics'] if row['factor_name'] == 'MOMENTUM')
    assert momentum['rank_ic'] == pytest.approx(1)
    assert momentum['net_long_short_spread'] < momentum['long_short_spread']
    summary = next(row for row in result['research_summaries'] if row['factor_name'] == 'MOMENTUM')
    assert summary['mean_rank_ic'] == pytest.approx(1)
    assert summary['positive_ic_frequency'] == 1
    assert result['correlations'][0]['correlation'] == pytest.approx(1)


def test_schema_blocks_lookahead_duplicates_unknown_and_conflicting_components():
    payload = request().model_dump()
    payload['observations'][0]['available_on'] = payload['observations'][0]['date']+timedelta(days=1)
    with pytest.raises(ValidationError, match='available on the factor date'):
        FactorRequest.model_validate(payload)
    payload = request().model_dump()
    payload['observations'].append(payload['observations'][0])
    with pytest.raises(ValidationError, match='unique'):
        FactorRequest.model_validate(payload)
    payload = request().model_dump()
    payload['observations'][0]['metric_name'] = 'unknown'
    with pytest.raises(ValidationError, match='registered component'):
        FactorRequest.model_validate(payload)
    payload = request().model_dump()
    payload['definitions'][1]['components'][0] = dict(
        metric_name='mom_12_1', source_engine='risk', direction='LOWER_IS_BETTER')
    with pytest.raises(ValidationError, match='consistent normalization metadata'):
        FactorRequest.model_validate(payload)


def test_storage_is_content_addressed_idempotent_and_collections_queryable():
    conn = duckdb.connect(':memory:')
    try:
        first = build_factors(conn, request())
        second = build_factors(conn, request())
        assert second['reused'] and second['run_id'] == first['run_id']
        assert get_records(conn, first['run_id'], 'features')['total'] == 10
        assert get_records(conn, first['run_id'], 'composites')['total'] == 5
    finally:
        conn.close()
