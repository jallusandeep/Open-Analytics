"""Ranks use explicit historical membership and retain incomplete-universe errors."""
from collections import defaultdict
from statistics import fmean, pstdev

from app.engines.risk.risk_service import put
from app.engines.risk.statistics import quantile


def rank_risk(rows, request):
    options = request.options
    window = options.ranking_window
    names = dict(volatility=f'ann_vol_{window}d', downside=f'downside_vol_{window}d',
                 beta=f'beta_{window}d', drawdown=f'max_drawdown_{window}d',
                 var='var_95_252d', cvar='cvar_95_252d', idiosyncratic=f'idio_vol_{window}d')
    memberships, groups = defaultdict(set), defaultdict(list)
    for e in request.returns.eligibility:
        if e.available_on <= e.date and e.universe_id:
            memberships[(e.date.isoformat(), e.universe_id)].add(e.instrument_key)
    for row in rows:
        groups[(row['date'], row['universe_id'])].append(row)
    for identity, population in groups.items():
        complete = bool(identity[1]) and memberships[identity] <= {r['instrument_key'] for r in population}
        for component, metric in names.items():
            usable = [r for r in population if r['metrics'][metric] is not None]
            # Magnitude defines drawdown severity and sensitivity for negative betas.
            values = [abs(r['metrics'][metric]) for r in usable]
            enough = complete and len(values) >= options.minimum_rank_count
            error = 'INCOMPLETE_UNIVERSE' if not complete else 'INSUFFICIENT_PEERS'
            if enough:
                low, high = quantile(values, options.winsor_lower), quantile(values, options.winsor_upper)
                capped = [min(high, max(low, v)) for v in values]
                mean, deviation = fmean(capped), pstdev(capped)
            for row in population:
                value = row['metrics'][metric]
                rank = percentile = z = None
                if enough and value is not None:
                    value = abs(value)
                    ascending = sum(v < value for v in values)+(values.count(value)+1)/2
                    rank = len(values)-ascending+1
                    percentile = 100*(ascending-1)/(len(values)-1)
                    z = (min(high, max(low, value))-mean)/deviation if deviation else None
                for suffix, result in (('rank', rank), ('percentile', percentile), ('z', z)):
                    put(row, f'{component}_{suffix}', result, len(values),
                        error if not enough else 'SOURCE_METRIC_INVALID' if value is None else 'ZERO_VARIANCE')
        scores = []
        for row in population:
            values = [row['metrics'][f'{k}_percentile'] for k in options.composite_weights]
            score = sum(options.composite_weights[k]*row['metrics'][f'{k}_percentile'] for k in options.composite_weights)/sum(options.composite_weights.values()) if values and all(v is not None for v in values) else None
            put(row, 'risk_score', score, len(values), 'WEIGHTS_NOT_CONFIGURED' if not values else 'COMPONENT_UNAVAILABLE')
            if score is not None:
                scores.append(score)
        for row in population:
            score = row['metrics']['risk_score']
            percentile = None
            if score is not None and len(scores) >= options.minimum_rank_count:
                rank = sum(s < score for s in scores)+(scores.count(score)+1)/2
                percentile = 100*(rank-1)/(len(scores)-1)
            put(row, 'risk_percentile', percentile, len(scores), 'INSUFFICIENT_SCORED_PEERS')
            row['risk_bucket'] = None if percentile is None else 'EXTREME' if percentile >= 90 else 'HIGH' if percentile >= 50 else 'MEDIUM' if percentile >= 25 else 'LOW'
            row['flags'] = {}
            for flag, component in [('high_volatility_flag', 'volatility'), ('high_beta_flag', 'beta'),
                                    ('high_downside_vol_flag', 'downside'), ('high_tail_risk_flag', 'cvar')]:
                value = row['metrics'][f'{component}_percentile']
                row['flags'][flag] = value >= options.flag_percentile if value is not None else None
            dd = row['metrics']['current_drawdown']
            gap = row['metrics']['max_negative_gap_63d']
            row['flags']['deep_drawdown_flag'] = dd <= -options.deep_drawdown_threshold if dd is not None else None
            row['flags']['high_gap_risk_flag'] = abs(gap) >= options.large_gap_threshold if gap is not None else None
            # Descriptive aliases named in the research document.
            for alias, original in [('volatility_universe_percentile', 'volatility_percentile'),
                                    ('downside_risk_percentile', 'downside_percentile'),
                                    ('tail_risk_percentile', 'cvar_percentile')]:
                row['metrics'][alias] = row['metrics'][original]
                row['metric_quality'][alias] = dict(row['metric_quality'][original])
