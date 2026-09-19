from datetime import date, timedelta

import duckdb
import pytest
from pydantic import ValidationError

from app.engines.cross_sectional_ranking.ranking_repository import build_rankings, get_distributions, get_rankings
from app.engines.cross_sectional_ranking.ranking_schema import RankingRequest
from app.engines.cross_sectional_ranking.ranking_service import calculate_rankings

pytestmark = pytest.mark.unit


def request(values=(1, 2, 3, 4), direction='HIGHER_IS_BETTER', dates=None, valid=None):
    sessions = [date(2026, 1, 1) + timedelta(days=index) for index in range(22)]
    dates = dates or [sessions[-1]]
    valid = valid or [True] * len(values)
    observations = []
    for day in dates:
        for index, value in enumerate(values):
            observations.append(dict(
                instrument_key=chr(65 + index), date=day, available_on=day,
                universe_id='U', metric_name='signal', raw_value=value,
                metric_valid=valid[index], metric_quality_status='VALID',
                sector='S1' if index < 2 else 'S2', industry='I1' if index < 2 else 'I2',
                market_cap_bucket='LARGE' if index % 2 == 0 else 'SMALL'))
    return RankingRequest.model_validate(dict(
        snapshot_id='fixture', as_of=sessions[-1], sessions=sessions,
        metrics=[dict(metric_name='signal', source_engine='test', direction=direction,
                      target=1 if direction == 'TARGET_RANGE' else None,
                      minimum_peer_count=2, winsor_lower=0.01, winsor_upper=0.99)],
        observations=observations))


def rows_by_key(result):
    return {row['instrument_key']: row for row in result['rows']}


def test_higher_direction_percentile_rank_buckets_and_raw_preservation():
    result = calculate_rankings(request())
    rows = rows_by_key(result)
    assert rows['D']['universe_rank'] == 1
    assert rows['D']['universe_percentile'] == 100
    assert rows['D']['decile'] == 10 and rows['D']['top_10pct_flag']
    assert rows['A']['universe_rank'] == 4
    assert rows['A']['universe_percentile'] == 0
    assert rows['A']['decile'] == 1 and rows['A']['bottom_10pct_flag']
    assert rows['A']['raw_value'] == 1
    assert rows['A']['winsorized_value'] > rows['A']['raw_value']
    assert result['distributions'][0]['count'] == 4


def test_lower_direction_reverses_desirability_but_preserves_raw_z_direction():
    rows = rows_by_key(calculate_rankings(request(direction='LOWER_IS_BETTER')))
    assert rows['A']['universe_rank'] == 1 and rows['A']['universe_percentile'] == 100
    assert rows['A']['raw_z'] < 0
    assert rows['A']['direction_adjusted_z'] > 0
    assert rows['D']['direction_adjusted_z'] < 0


def test_target_preference_and_no_winsorization_are_explicit_registry_rules():
    req = request(values=(0, 1, 2, 3), direction='TARGET_RANGE')
    req.metrics[0].winsorization_method = 'NONE'
    rows = rows_by_key(calculate_rankings(req))
    assert rows['B']['universe_rank'] == 1
    assert rows['A']['winsorized_value'] == rows['A']['raw_value']
    assert not rows['A']['winsorized']


def test_ties_use_average_rank_and_zero_variance_remains_explicit():
    rows = rows_by_key(calculate_rankings(request(values=(5, 5, 5, 5))))
    assert all(row['universe_rank'] == 2.5 for row in rows.values())
    assert all(row['universe_percentile'] == 50 for row in rows.values())
    assert all(row['direction_adjusted_z'] is None for row in rows.values())
    assert all(row['rank_valid'] for row in rows.values())


def test_invalid_inputs_are_not_ranked_and_peer_counts_are_reported():
    rows = rows_by_key(calculate_rankings(request(valid=[True, True, False, True])))
    assert rows['C']['universe_rank'] is None
    assert rows['C']['rank_quality_status'] == 'INVALID_SOURCE_METRIC'
    assert rows['A']['peer_count'] == 4
    assert rows['A']['peer_valid_count'] == 3
    assert rows['A']['peer_missing_count'] == 1
    assert rows['C']['sector_percentile'] is None


def test_sector_size_peers_and_neutralization_are_point_in_time():
    rows = rows_by_key(calculate_rankings(request()))
    assert rows['B']['sector_rank'] == 1 and rows['B']['sector_percentile'] == 100
    assert rows['C']['size_rank'] == 1 and rows['C']['size_percentile'] == 100
    assert rows['A']['sector_neutral_value'] == pytest.approx(-0.5)
    assert rows['D']['size_neutral_value'] == pytest.approx(1.0)


def test_rank_and_percentile_changes_use_authoritative_session_lags():
    req = request(dates=[date(2026, 1, 1), date(2026, 1, 22)])
    for row in req.observations:
        if row.date == date(2026, 1, 22):
            row.raw_value = 5 - row.raw_value
    latest = [row for row in calculate_rankings(req)['rows'] if row['date'] == '2026-01-22']
    a = next(row for row in latest if row['instrument_key'] == 'A')
    assert a['rank_change_21d'] == 3
    assert a['percentile_change_21d'] == 100
    assert a['rank_change_5d'] is None


def test_schema_blocks_lookahead_duplicates_and_unknown_metrics():
    payload = request().model_dump()
    payload['observations'][0]['available_on'] = payload['as_of'] + timedelta(days=1)
    with pytest.raises(ValidationError, match='known by as_of'):
        RankingRequest.model_validate(payload)
    payload = request().model_dump()
    payload['observations'].append(payload['observations'][0])
    with pytest.raises(ValidationError, match='unique'):
        RankingRequest.model_validate(payload)
    payload = request().model_dump()
    payload['observations'][0]['metric_name'] = 'unknown'
    with pytest.raises(ValidationError, match='metadata'):
        RankingRequest.model_validate(payload)


def test_metric_known_after_ranking_date_is_not_used_historically():
    req = request(dates=[date(2026, 1, 1)])
    req.observations[0].available_on = req.observations[0].date + timedelta(days=1)
    row = rows_by_key(calculate_rankings(req))['A']
    assert row['universe_rank'] is None
    assert row['rank_quality_status'] == 'NOT_AVAILABLE_AT_DATE'
    assert row['peer_missing_count'] == 1


def test_versioned_storage_is_idempotent_and_queryable():
    conn = duckdb.connect(':memory:')
    try:
        first = build_rankings(conn, request())
        second = build_rankings(conn, request())
        assert second['reused'] and second['run_id'] == first['run_id']
        assert get_rankings(conn, first['run_id'], metric_name='signal')['total'] == 4
        assert get_distributions(conn, first['run_id'], metric_name='signal')['total'] == 1
    finally:
        conn.close()
