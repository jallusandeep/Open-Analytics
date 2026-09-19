"""Versioned, explainable factor construction and research diagnostics."""
from collections import defaultdict
from math import log1p
from statistics import fmean, median, pstdev

from app.engines.factor.factor_schema import FactorRequest

VERSION = '1'
INVALID_QUALITY = {'INVALID', 'ERROR', 'FAILED', 'STALE', 'LOW_DATA_QUALITY'}


def quantile(values, probability):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered)-1)*probability
    lower = int(position)
    upper = min(lower+1, len(ordered)-1)
    return ordered[lower] + (ordered[upper]-ordered[lower])*(position-lower)


def transform(value, method):
    if value is None:
        return None
    if method == 'LOG':
        return log1p(value) if value > -1 else None
    if method == 'SIGNED_LOG':
        return (1 if value >= 0 else -1)*log1p(abs(value))
    return value


def normalized(values, value, method):
    if value is None or len(values) < 2:
        return None
    if method == 'RANK':
        below = sum(item < value for item in values)
        tied = sum(item == value for item in values)
        return 2*(below+(tied-1)/2)/(len(values)-1)-1
    center = median(values) if method == 'ROBUST_Z' else fmean(values)
    if method == 'ROBUST_Z':
        scale = 1.4826*median([abs(item-center) for item in values])
    else:
        scale = pstdev(values)
    return (value-center)/scale if scale else 0.0


def rank_details(values, value):
    if value is None or len(values) < 2:
        return None, None, None
    stronger = sum(item > value for item in values)
    tied = sum(item == value for item in values)
    rank = stronger+(tied+1)/2
    percentile = 100*(sum(item < value for item in values)+(tied-1)/2)/(len(values)-1)
    return rank, percentile, min(10, int(percentile/10)+1)


def pearson(left, right):
    if len(left) < 2:
        return None
    left_mean, right_mean = fmean(left), fmean(right)
    numerator = sum((x-left_mean)*(y-right_mean) for x, y in zip(left, right))
    denominator = (sum((x-left_mean)**2 for x in left)*sum((y-right_mean)**2 for y in right))**.5
    return numerator/denominator if denominator else None


def ranks(values):
    return [rank_details(values, value)[1] for value in values]


def _component_scores(request):
    registry = {component.metric_name: component for factor in request.definitions for component in factor.components}
    source = defaultdict(list)
    for row in request.observations:
        definition = registry[row.metric_name]
        value = transform(row.value, definition.transform)
        valid = row.metric_valid and row.quality_status.upper() not in INVALID_QUALITY and value is not None
        source[(row.date.isoformat(), row.universe_id, row.metric_name)].append((row, value, valid))
    scores = {}
    for key, population in source.items():
        definition = registry[key[2]]
        groups = defaultdict(list)
        for row, value, valid in population:
            peer = row.sector if definition.peer_group == 'SECTOR' else row.industry if definition.peer_group == 'INDUSTRY' else row.universe_id
            groups[peer].append((row, value, valid))
        for peer_rows in groups.values():
            valid_values = [value for _, value, valid in peer_rows if valid]
            low, high = quantile(valid_values, definition.winsor_lower), quantile(valid_values, definition.winsor_upper)
            for row, value, valid in peer_rows:
                identity = (row.instrument_key, row.date.isoformat(), row.universe_id, row.metric_name)
                if not valid or len(valid_values) < request.minimum_peer_count:
                    scores[identity] = dict(raw_value=row.value, transformed_value=value, winsorized_value=None,
                                            normalized_score=None, quality_status='LOW_PEER_COUNT' if valid else 'INVALID_INPUT')
                    continue
                capped = min(high, max(low, value))
                z = normalized([min(high, max(low, item)) for item in valid_values], capped, definition.normalization)
                if z is not None and definition.direction == 'LOWER_IS_BETTER':
                    z = -z
                scores[identity] = dict(raw_value=row.value, transformed_value=value, winsorized_value=capped,
                                        normalized_score=z, quality_status='VALID')
    return scores


def _neutralize(rows, method, minimum):
    field = {'SECTOR': 'sector', 'INDUSTRY': 'industry', 'SIZE': 'size_bucket'}[method]
    groups = defaultdict(list)
    for row in rows:
        if row[field] and row['neutralized_factor_z'] is not None:
            groups[row[field]].append(row['neutralized_factor_z'])
    for row in rows:
        peers = groups.get(row[field], [])
        if len(peers) >= minimum and row['neutralized_factor_z'] is not None:
            row['neutralized_factor_z'] -= fmean(peers)
            row['neutralization_applied'].append(method)


def _build_factors(request, component_scores):
    metadata = {}
    for observation in request.observations:
        metadata[(observation.instrument_key, observation.date.isoformat(), observation.universe_id)] = observation
    output = []
    for factor in (item for item in request.definitions if item.active):
        for identity, observation in metadata.items():
            components = []
            for definition in factor.components:
                score = component_scores.get((*identity, definition.metric_name))
                if score:
                    components.append(dict(metric_name=definition.metric_name, source_engine=definition.source_engine,
                                           configured_weight=definition.weight, direction=definition.direction, **score))
            available = [item for item in components if item['normalized_score'] is not None]
            required = len(factor.components) if factor.missing_value_rule == 'REQUIRE_ALL' else factor.minimum_component_count
            usable = len(available) >= required
            weighted = (sum(item['normalized_score']*next(c.weight for c in factor.components if c.metric_name == item['metric_name']) for item in available) /
                        sum(next(c.weight for c in factor.components if c.metric_name == item['metric_name']) for item in available)) if usable else None
            status = 'VALID' if len(available) == len(factor.components) else ('PARTIAL_COMPONENTS' if usable else 'INVALID')
            confidence = 100*len(available)/len(factor.components)
            output.append(dict(date=identity[1], universe_id=identity[2], instrument_key=identity[0],
                sector=observation.sector, industry=observation.industry, size_bucket=observation.size_bucket,
                factor_name=factor.factor_name, factor_version=factor.factor_version,
                raw_factor_z=weighted, neutralized_factor_z=weighted,
                factor_rank=None, factor_percentile=None, factor_decile=None,
                factor_quality_status=status, factor_confidence=confidence,
                neutralization_applied=[], components=components,
                rebalance_frequency=factor.rebalance_frequency, holding_horizon=factor.holding_horizon))
    grouped = defaultdict(list)
    definitions = {(item.factor_name, item.factor_version): item for item in request.definitions}
    for row in output:
        grouped[(row['date'], row['universe_id'], row['factor_name'], row['factor_version'])].append(row)
    for key, rows in grouped.items():
        definition = definitions[(key[2], key[3])]
        for method in definition.neutralization:
            _neutralize(rows, method, request.minimum_peer_count)
        values = [row['neutralized_factor_z'] for row in rows if row['neutralized_factor_z'] is not None]
        for row in rows:
            row['factor_rank'], row['factor_percentile'], row['factor_decile'] = rank_details(values, row['neutralized_factor_z'])
            if row['neutralized_factor_z'] is not None and len(values) < request.minimum_peer_count:
                row['factor_quality_status'] = 'LOW_PEER_COUNT'
    return output


def _composites(rows, request):
    wide = {}
    for row in rows:
        key = (row['instrument_key'], row['date'], row['universe_id'])
        record = wide.setdefault(key, dict(instrument_key=key[0], date=key[1], universe_id=key[2], factors={}))
        record['factors'][row['factor_name']] = row['neutralized_factor_z']
    weights = request.composite_weights
    for record in wide.values():
        available = [(value, weights.get(name, 1)) for name, value in record['factors'].items()
                     if value is not None and (not weights or weights.get(name, 0) > 0)]
        record['multi_factor_score'] = sum(value*weight for value, weight in available)/sum(weight for _, weight in available) if available else None
        record['factor_count'] = len(available)
    return list(wide.values())


def _diagnostics(rows, request):
    returns = {(item.instrument_key, item.factor_date.isoformat(), item.horizon): item.return_value for item in request.forward_returns}
    groups = defaultdict(list)
    for row in rows:
        for horizon in {item.horizon for item in request.forward_returns if item.factor_date.isoformat() == row['date']}:
            value = returns.get((row['instrument_key'], row['date'], horizon))
            if value is not None and row['neutralized_factor_z'] is not None:
                groups[(row['date'], row['universe_id'], row['factor_name'], row['factor_version'], horizon)].append((row, value))
    diagnostics = []
    for key, pairs in sorted(groups.items()):
        if len(pairs) < request.minimum_peer_count:
            continue
        factor_values = [row['neutralized_factor_z'] for row, _ in pairs]
        return_values = [value for _, value in pairs]
        factor_ranks, return_ranks = ranks(factor_values), ranks(return_values)
        top = [value for (row, value) in pairs if row['factor_percentile'] is not None and row['factor_percentile'] >= 80]
        bottom = [value for (row, value) in pairs if row['factor_percentile'] is not None and row['factor_percentile'] <= 20]
        spread = fmean(top)-fmean(bottom) if top and bottom else None
        diagnostics.append(dict(date=key[0], universe_id=key[1], factor_name=key[2], factor_version=key[3],
            forward_horizon=key[4], ic=pearson(factor_values, return_values), rank_ic=pearson(factor_ranks, return_ranks),
            top_quantile_return=fmean(top) if top else None, bottom_quantile_return=fmean(bottom) if bottom else None,
            long_short_spread=spread, net_long_short_spread=(spread-2*request.transaction_cost_bps/10000 if spread is not None else None),
            dispersion=pstdev(factor_values), breadth=len(pairs)))
    correlations = []
    by_date = defaultdict(list)
    for row in rows:
        by_date[(row['date'], row['universe_id'])].append(row)
    for (day, universe), values in by_date.items():
        factors = sorted(set(row['factor_name'] for row in values))
        lookup = {(row['instrument_key'], row['factor_name']): row['neutralized_factor_z'] for row in values}
        instruments = sorted(set(row['instrument_key'] for row in values))
        for index, left in enumerate(factors):
            for right in factors[index+1:]:
                pairs = [(lookup.get((instrument, left)), lookup.get((instrument, right))) for instrument in instruments]
                pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
                if len(pairs) >= request.minimum_peer_count:
                    correlations.append(dict(date=day, universe_id=universe, factor_a=left, factor_b=right,
                                             correlation=pearson([a for a, _ in pairs], [b for _, b in pairs]), count=len(pairs)))
    return diagnostics, correlations


def _research_summaries(rows, diagnostics):
    grouped_diagnostics = defaultdict(list)
    for item in diagnostics:
        grouped_diagnostics[(item['universe_id'], item['factor_name'], item['factor_version'], item['forward_horizon'])].append(item)
    stability = defaultdict(list)
    grouped_rows = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        grouped_rows[(row['universe_id'], row['factor_name'], row['factor_version'])][row['date']][row['instrument_key']] = row
    for key, days in grouped_rows.items():
        ordered = sorted(days)
        for previous_day, current_day in zip(ordered, ordered[1:]):
            common = sorted(set(days[previous_day]) & set(days[current_day]))
            pairs = [(days[previous_day][name]['factor_percentile'], days[current_day][name]['factor_percentile']) for name in common]
            pairs = [(left, right) for left, right in pairs if left is not None and right is not None]
            if len(pairs) >= 2:
                stability[key].append(dict(
                    rank_autocorrelation=pearson([left for left, _ in pairs], [right for _, right in pairs]),
                    turnover=fmean([abs(right-left)/100 for left, right in pairs])))
    factor_keys = {(row['universe_id'], row['factor_name'], row['factor_version']) for row in rows}
    summaries = []
    for factor_key in sorted(factor_keys):
        horizons = sorted({key[3] for key in grouped_diagnostics if key[:3] == factor_key}) or [None]
        for horizon in horizons:
            items = grouped_diagnostics.get((*factor_key, horizon), [])
            ics = [item['rank_ic'] for item in items if item['rank_ic'] is not None]
            spreads = [item['net_long_short_spread'] for item in items if item['net_long_short_spread'] is not None]
            mean_ic = fmean(ics) if ics else None
            ic_std = pstdev(ics) if len(ics) >= 2 else None
            temporal = stability.get(factor_key, [])
            summaries.append(dict(universe_id=factor_key[0], factor_name=factor_key[1], factor_version=factor_key[2],
                forward_horizon=horizon, observation_count=len(items), mean_rank_ic=mean_ic,
                ic_information_ratio=(mean_ic/ic_std if mean_ic is not None and ic_std else None),
                positive_ic_frequency=(sum(value > 0 for value in ics)/len(ics) if ics else None),
                factor_hit_rate=(sum(value > 0 for value in spreads)/len(spreads) if spreads else None),
                mean_net_long_short_spread=(fmean(spreads) if spreads else None),
                rank_autocorrelation=mean_present([item['rank_autocorrelation'] for item in temporal]),
                turnover=mean_present([item['turnover'] for item in temporal])))
    return summaries


def mean_present(values):
    values = [value for value in values if value is not None]
    return fmean(values) if values else None


def calculate_factors(request: FactorRequest):
    components = _component_scores(request)
    rows = _build_factors(request, components)
    composites = _composites(rows, request)
    diagnostics, correlations = _diagnostics(rows, request)
    summaries = _research_summaries(rows, diagnostics)
    return dict(version=VERSION, snapshot_id=request.snapshot_id, as_of=request.as_of.isoformat(),
                rows=rows, composites=composites, diagnostics=diagnostics,
                research_summaries=summaries, correlations=correlations)
