"""Historical-universe statistics; missing participants cannot silently shrink scope."""
from collections import defaultdict
from math import sqrt

from app.engines.returns.returns_service import RANK_HORIZONS


def quantile(values, fraction):
    position = (len(values)-1)*fraction
    lower = int(position)
    upper = min(lower+1, len(values)-1)
    return values[lower]+(values[upper]-values[lower])*(position-lower)


def rank_returns(rows, request):
    groups = defaultdict(list)
    memberships = defaultdict(set)
    for e in request.eligibility:
        if e.available_on <= e.date and e.universe_id:
            memberships[(e.date.isoformat(), e.universe_id, None)].add(e.instrument_key)
            if e.sector_id:
                memberships[(e.date.isoformat(), e.universe_id, e.sector_id)].add(e.instrument_key)
    for row in rows:
        if row['universe_id']:
            groups[(row['date'], row['universe_id'], None)].append(row)
            if row['sector_id']:
                groups[(row['date'], row['universe_id'], row['sector_id'])].append(row)
    output = []
    for (day, universe, sector), population in groups.items():
        represented = {r['instrument_key'] for r in population}
        expected = memberships[(day, universe, sector)]
        complete = expected <= represented
        for h in RANK_HORIZONS:
            usable = [r for r in population if r['metrics'][f'return_{h}d'] is not None]
            values = sorted(r['metrics'][f'return_{h}d'] for r in usable)
            if not complete or len(values) < request.minimum_rank_count:
                for row in population:
                    output.append(dict(instrument_key=row['instrument_key'], date=day, universe_id=universe,
                        sector_id=sector, horizon=h, rank=None, percentile=None, z_score=None,
                        invalid_reason='INCOMPLETE_UNIVERSE' if not complete else 'INSUFFICIENT_PEERS',
                        population_count=len(values)))
                continue
            lower, upper = quantile(values, request.winsor_lower), quantile(values, request.winsor_upper)
            capped = [max(lower, min(upper, v)) for v in values]
            mean = sum(capped)/len(capped)
            std = sqrt(sum((v-mean)**2 for v in capped)/len(capped))
            for row in usable:
                value = row['metrics'][f'return_{h}d']
                less, equal = sum(v < value for v in values), values.count(value)
                average_rank = less+(equal+1)/2
                winsorized = max(lower, min(upper, value))
                output.append(dict(instrument_key=row['instrument_key'], date=day,
                    universe_id=universe, sector_id=sector, horizon=h, raw_return=value,
                    rank=len(values)-average_rank+1, percentile=100*(average_rank-1)/(len(values)-1),
                    winsorized_return=winsorized, z_score=(winsorized-mean)/std if std else None,
                    invalid_reason=None if std else 'ZERO_VARIANCE', population_count=len(values)))
    return output
