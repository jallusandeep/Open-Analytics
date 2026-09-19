"""Generic point-in-time rankings with explicit direction, peers and quality."""
from collections import defaultdict
from statistics import fmean
from types import SimpleNamespace

from app.engines.cross_sectional_ranking.ranking_schema import RankingRequest
from app.engines.cross_sectional_ranking.statistics import (
    average_strength, bucket, distribution, normalized, percentile, quantile,
    residual_z, transform,
)

VERSION = '1'
INVALID_QUALITY = {'INVALID', 'ERROR', 'FAILED', 'STALE', 'INVALID_SOURCE_METRIC'}
PEER_FIELDS = {
    'sector': 'sector', 'industry': 'industry', 'subindustry': 'sub_industry',
    'size': 'market_cap_bucket', 'liquidity': 'liquidity_bucket',
}


def _preference(value, metric):
    if metric.direction == 'LOWER_IS_BETTER':
        return -value
    if metric.direction == 'TARGET_RANGE':
        target = transform(metric.target, metric.transform)
        return -abs(value - target) if target is not None else None
    return value


def _rank_group(population, metric, minimum_count):
    valid = [row for row in population if row['_valid']]
    if len(valid) < minimum_count:
        return {}, len(valid), 'LOW_PEER_COUNT'
    source_values = [row['_transformed'] for row in valid]
    low = quantile(source_values, metric.winsor_lower) if metric.winsorization_method == 'PERCENTILE' else min(source_values)
    high = quantile(source_values, metric.winsor_upper) if metric.winsorization_method == 'PERCENTILE' else max(source_values)
    capped = {row['_identity']: min(high, max(low, row['_transformed'])) for row in valid}
    preferences = {identity: _preference(value, metric) for identity, value in capped.items()}
    strengths = list(preferences.values())
    transformed_values = list(capped.values())
    output = {}
    for row in valid:
        identity = row['_identity']
        raw_z, raw_robust = normalized(transformed_values, capped[identity])
        adjusted_z, adjusted_robust = normalized(strengths, preferences[identity])
        strength_rank = average_strength(strengths, preferences[identity])
        output[identity] = dict(
            rank=len(strengths) - strength_rank + 1,
            percentile=percentile(strengths, preferences[identity]),
            z=adjusted_z, raw_z=raw_z, robust_z=adjusted_robust,
            raw_robust_z=raw_robust, winsorized_value=capped[identity],
            winsorized=capped[identity] != row['_transformed'],
        )
    return output, len(valid), None


def _empty_record(row, metric):
    return dict(
        date=row.date.isoformat(), universe_id=row.universe_id,
        instrument_key=row.instrument_key, metric_name=row.metric_name,
        raw_value=row.raw_value, input_valid=row.metric_valid,
        input_quality_status=row.metric_quality_status,
        transformed_value=None, winsorized_value=None, winsorized=False,
        universe_rank=None, universe_percentile=None, raw_z=None,
        direction_adjusted_z=None, robust_z=None, clipped_z=None,
        sector_rank=None, sector_percentile=None, sector_z=None,
        sector_neutral_value=None, sector_neutral_z=None,
        industry_rank=None, industry_percentile=None, industry_z=None,
        subindustry_rank=None, subindustry_percentile=None, subindustry_z=None,
        size_rank=None, size_percentile=None, size_z=None,
        size_neutral_value=None, size_neutral_z=None,
        liquidity_rank=None, liquidity_percentile=None, liquidity_z=None,
        rank_scaled=None, quartile=None, quintile=None, decile=None,
        top_10pct_flag=None, top_20pct_flag=None,
        bottom_10pct_flag=None, bottom_20pct_flag=None,
        outlier_flag=None, outlier_method=None,
        rank_change_1d=None, rank_change_5d=None, rank_change_21d=None,
        percentile_change_5d=None, percentile_change_21d=None,
        peer_count=0, peer_valid_count=0, peer_missing_count=0,
        sector_peer_count=0, industry_peer_count=0, size_peer_count=0,
        rank_valid=False, rank_quality_status='INVALID_SOURCE_METRIC',
        sector_neutralization_method=None, size_neutralization_method=None,
        normalization_version=VERSION, metric_version=metric.version,
    )


def calculate_rankings(request: RankingRequest):
    registry = {metric.metric_name: metric for metric in request.metrics if metric.active}
    groups = defaultdict(list)
    for observation in request.observations:
        metric = registry.get(observation.metric_name)
        if not metric:
            continue
        transformed = transform(observation.raw_value, metric.transform) if observation.raw_value is not None else None
        available_at_date = observation.available_on <= observation.date
        valid = (available_at_date and observation.metric_valid and transformed is not None and
                 observation.metric_quality_status.upper() not in INVALID_QUALITY)
        row = observation.model_dump()
        row.update(_metric=metric, _transformed=transformed, _valid=valid,
                   _invalid_reason='NOT_AVAILABLE_AT_DATE' if not available_at_date else 'INVALID_SOURCE_METRIC',
                   _identity=(observation.instrument_key, observation.date.isoformat(),
                              observation.universe_id, observation.metric_name))
        groups[(observation.date.isoformat(), observation.universe_id, observation.metric_name)].append(row)

    records, distributions = [], []
    for (day, universe, metric_name), population in sorted(groups.items()):
        metric = registry[metric_name]
        universe_results, valid_count, universe_error = _rank_group(population, metric, metric.minimum_peer_count)
        peer_results = {}
        for prefix, field in PEER_FIELDS.items():
            grouped = defaultdict(list)
            for row in population:
                if row[field]:
                    grouped[row[field]].append(row)
            peer_results[prefix] = {}
            for peer, members in grouped.items():
                result, count, error = _rank_group(members, metric, metric.minimum_peer_count)
                peer_results[prefix][peer] = (result, count, error)

        valid_rows = [row for row in population if row['_valid']]
        if valid_rows:
            raw_values = [row['raw_value'] for row in valid_rows]
            transformed_values = [row['_transformed'] for row in valid_rows]
            stats = distribution(raw_values)
            transformed_stats = distribution(transformed_values)
            distributions.append(dict(date=day, universe_id=universe, metric_name=metric_name,
                **stats, transformed_mean=transformed_stats['mean'],
                transformed_median=transformed_stats['median'],
                transformed_std=transformed_stats['std'], transformed_mad=transformed_stats['mad'],
                valid_count=valid_count, missing_count=len(population)-valid_count,
                top_decile_threshold=quantile(raw_values, .9), bottom_decile_threshold=quantile(raw_values, .1),
                normalization_version=VERSION, metric_version=metric.version))

        sector_groups = defaultdict(list)
        size_groups = defaultdict(list)
        for row in valid_rows:
            if row['sector']:
                sector_groups[row['sector']].append(row['_transformed'])
            if row['market_cap_bucket']:
                size_groups[row['market_cap_bucket']].append(row['_transformed'])
        sector_residual_inputs = [(row['_transformed'], sector_groups[row['sector']]) for row in valid_rows if row['sector'] in sector_groups]
        size_residual_inputs = [(row['_transformed'], size_groups[row['market_cap_bucket']]) for row in valid_rows if row['market_cap_bucket'] in size_groups]

        for source in population:
            metric_model = source['_metric']
            observation = SimpleNamespace(**source)
            record = _empty_record(observation, metric_model)
            record['transformed_value'] = source['_transformed']
            record.update(peer_count=len(population), peer_valid_count=valid_count,
                          peer_missing_count=len(population)-valid_count)
            identity = source['_identity']
            universe_result = universe_results.get(identity)
            if universe_result:
                record.update(
                    winsorized_value=universe_result['winsorized_value'], winsorized=universe_result['winsorized'],
                    universe_rank=universe_result['rank'], universe_percentile=universe_result['percentile'],
                    raw_z=universe_result['raw_z'], direction_adjusted_z=universe_result['z'],
                    robust_z=universe_result['robust_z'],
                    clipped_z=max(-request.z_clip, min(request.z_clip, universe_result['z'])) if request.z_clip and universe_result['z'] is not None else universe_result['z'])
                pct = record['universe_percentile']
                record.update(rank_scaled=2*pct/100-1, quartile=bucket(pct, 4), quintile=bucket(pct, 5),
                              decile=bucket(pct, 10), top_10pct_flag=pct >= 90, top_20pct_flag=pct >= 80,
                              bottom_10pct_flag=pct <= 10, bottom_20pct_flag=pct <= 20,
                              outlier_flag=abs(universe_result['raw_z']) >= request.outlier_z if universe_result['raw_z'] is not None else False,
                              outlier_method='STANDARD_Z' if universe_result['raw_z'] is not None and abs(universe_result['raw_z']) >= request.outlier_z else None,
                              rank_valid=True, rank_quality_status='VALID')
            elif source['_valid']:
                record['rank_quality_status'] = universe_error
            else:
                record['rank_quality_status'] = source['_invalid_reason']

            for prefix, field in PEER_FIELDS.items():
                peer = source[field]
                result_map, count, _ = peer_results[prefix].get(peer, ({}, 0, 'MISSING_PEER_GROUP'))
                result = result_map.get(identity)
                if prefix in {'sector', 'industry', 'size'}:
                    record[f'{prefix}_peer_count'] = count
                if result:
                    record[f'{prefix}_rank'] = result['rank']
                    record[f'{prefix}_percentile'] = result['percentile']
                    record[f'{prefix}_z'] = result['z']

            if source['_valid'] and metric_model.allow_sector_neutralization and source['sector'] and len(sector_groups[source['sector']]) >= metric_model.minimum_peer_count:
                value, z = residual_z(sector_residual_inputs, source['_transformed'], sector_groups[source['sector']])
                record['sector_neutral_value'], record['sector_neutral_z'] = value, z
                record['sector_neutralization_method'] = 'SECTOR_MEAN'
            if source['_valid'] and metric_model.allow_size_neutralization and source['market_cap_bucket'] and len(size_groups[source['market_cap_bucket']]) >= metric_model.minimum_peer_count:
                value, z = residual_z(size_residual_inputs, source['_transformed'], size_groups[source['market_cap_bucket']])
                record['size_neutral_value'], record['size_neutral_z'] = value, z
                record['size_neutralization_method'] = 'SIZE_BUCKET_MEAN'
            records.append(record)

    positions = {day.isoformat(): index for index, day in enumerate(request.sessions)}
    history = {(row['instrument_key'], row['universe_id'], row['metric_name'], row['date']): row for row in records}
    for row in records:
        index = positions[row['date']]
        for lag in (1, 5, 21):
            prior = history.get((row['instrument_key'], row['universe_id'], row['metric_name'],
                                 request.sessions[index-lag].isoformat())) if index >= lag else None
            row[f'rank_change_{lag}d'] = (prior['universe_rank'] - row['universe_rank']) if prior and prior['universe_rank'] is not None and row['universe_rank'] is not None else None
            if lag in (5, 21):
                row[f'percentile_change_{lag}d'] = (row['universe_percentile'] - prior['universe_percentile']) if prior and prior['universe_percentile'] is not None and row['universe_percentile'] is not None else None
    return dict(version=VERSION, snapshot_id=request.snapshot_id, as_of=request.as_of.isoformat(),
                rows=records, distributions=distributions)
