"""Deterministic daily model. Probabilities are heuristic, not fitted forecasts."""
from collections import Counter, defaultdict
from math import exp
from statistics import fmean, pstdev

from app.engines.market_regime.market_regime_schema import MarketRegimeRequest

VERSION = '1'


def _clip(value, low=0, high=100):
    return max(low, min(high, value))


def _mean(values):
    values = [value for value in values if value is not None]
    return fmean(values) if values else None


def _band(value, thresholds, labels):
    if value is None:
        return None
    return labels[sum(value >= threshold for threshold in thresholds)]


def _z(value, history):
    values = [v for v in history if v is not None]
    if value is None or len(values) < 2:
        return None
    deviation = pstdev(values)
    return (value - fmean(values)) / deviation if deviation else 0.0


def _classify(item, options, previous, history):
    trend = _mean([
        _clip(value / scale, -1, 1) if value is not None else None
        for value, scale in (
            (item.market_return_21d, options.return_scale),
            (item.market_return_63d, options.return_scale),
            (item.price_vs_sma50, options.return_scale),
            (item.price_vs_sma200, options.return_scale),
            (item.market_slope_63d, options.slope_scale),
        )
    ])
    vol = _mean([
        _clip(100 * (value - options.volatility_floor) / (options.volatility_ceiling - options.volatility_floor))
        for value in (item.realized_volatility_21d, item.realized_volatility_63d,
                      item.atm_iv, item.india_vix / 100 if item.india_vix is not None else None)
        if value is not None
    ] + ([item.iv_percentile] if item.iv_percentile is not None else []))
    breadth = item.breadth_score
    if breadth is None:
        fraction = _mean([item.pct_above_sma50, item.pct_above_sma200])
        breadth = fraction * 100 if fraction is not None else None
    flow, liquidity = item.institutional_flow_score, item.market_liquidity_score
    derivative = _mean([item.derivatives_sentiment_score,
                        100 - item.derivatives_risk_score if item.derivatives_risk_score is not None else None])
    dimensions = {'trend': trend, 'volatility': 1 - vol / 50 if vol is not None else None,
                  **{k: v / 50 - 1 if v is not None else None for k, v in
                     [('breadth', breadth), ('flow', flow), ('liquidity', liquidity), ('derivatives', derivative)]}}
    total_weight = sum(options.weights[k] for k, v in dimensions.items() if v is not None)
    contributions = {k: options.weights[k] * v / total_weight for k, v in dimensions.items()
                     if v is not None and total_weight > 0}
    score = sum(contributions.values()) if contributions else None
    stress = _mean([vol, _clip(-item.current_drawdown / options.drawdown_stress * 100) if item.current_drawdown is not None else None,
                    100 - breadth if breadth is not None else None,
                    100 - liquidity if liquidity is not None else None,
                    100 - flow if flow is not None else None,
                    item.derivatives_risk_score,
                    _clip(item.correlation * 100) if item.correlation is not None else None])
    stress = _clip(stress) if stress is not None else None
    high_vol = vol is not None and vol >= (options.high_vol_exit if previous and previous['high_volatility_flag'] else options.high_vol_enter)
    t = options.trend_threshold
    trend_state = _band(trend, [-options.strong_trend_threshold, -t, t, options.strong_trend_threshold],
                        ['STRONG_DOWNTREND', 'DOWNTREND', 'SIDEWAYS', 'UPTREND', 'STRONG_UPTREND'])
    family = None if trend is None else 'BULL' if trend >= t else 'BEAR' if trend < -t else 'SIDEWAYS'
    matrix = f'{family}_{"HIGH" if high_vol else "LOW"}_VOL' if family and vol is not None else None
    changes = {}
    for name, value in [('breadth_regime_score', breadth), ('flow_regime_score', flow), ('volatility_regime_score', vol)]:
        old = previous.get(name) if previous else None
        changes[name] = value - old if value is not None and old is not None else None
    improving = (changes['breadth_regime_score'] is not None and changes['breadth_regime_score'] > 0
                 and changes['flow_regime_score'] is not None and changes['flow_regime_score'] > 0
                 and changes['volatility_regime_score'] is not None and changes['volatility_regime_score'] < 0)
    recovery = bool(improving and item.price_vs_sma200 is not None and item.price_vs_sma200 < 0)
    distribution = bool(family == 'BULL' and all(changes[k] is not None for k in changes)
                        and changes['breadth_regime_score'] < 0 and changes['flow_regime_score'] < 0
                        and changes['volatility_regime_score'] > 0)
    valid = trend is not None and vol is not None and total_weight > 0
    label = ('STRESS' if stress is not None and stress >= options.stress_threshold else
             'RECOVERY' if recovery else matrix) if valid else None
    probabilities = dict(bull_probability=None, bear_probability=None, sideways_probability=None)
    if valid:
        logits = [2 * score + trend, -2 * score - trend, 1 - 2 * abs(trend)]
        values = [exp(v - max(logits)) for v in logits]
        probabilities = dict(zip(probabilities, [v / sum(values) for v in values]))
    active = {k: v for k, v in dimensions.items() if v is not None and options.weights[k] > 0}
    direction = 1 if score is not None and score >= t else -1 if score is not None and score < -t else 0
    disagrees = [k for k, v in active.items() if (v < -t if direction > 0 else v > t if direction < 0 else abs(v) > t)]
    agreement = 100 * (1 - len(disagrees) / len(active)) if active else 0
    coverage = sum(options.weights[k] for k in active) / sum(options.weights.values())
    conflict = any(v > t for v in active.values()) and any(v < -t for v in active.values())
    flags = []
    if not valid:
        flags.append('INVALID')
    if any(v is None for v in dimensions.values()) or item.breadth_coverage is None:
        flags.append('PARTIAL_INPUTS')
    if item.breadth_coverage is not None and item.breadth_coverage < options.minimum_breadth_coverage:
        flags.append('LOW_BREADTH_COVERAGE')
    if flow is None:
        flags.append('MISSING_FLOW')
    if derivative is None:
        flags.append('MISSING_DERIVATIVES')
    if conflict:
        flags.append('CONFLICTED_SIGNALS')
    breadth_coverage = item.breadth_coverage if item.breadth_coverage is not None else (0.5 if breadth is not None else 0)
    confidence = coverage * agreement * (.5 + .5 * breadth_coverage) if valid else 0
    dispersion_z = _z(item.cross_sectional_dispersion, [r['cross_sectional_dispersion'] for r in history[-252:]])
    correlation_z = _z(item.correlation, [r['correlation'] for r in history[-252:]])
    correlation_regime = _band(item.correlation, [.3, .6, .85], ['LOW_CORRELATION', 'NORMAL_CORRELATION', 'HIGH_CORRELATION', 'CRISIS_CORRELATION'])
    opportunity = (None if dispersion_z is None or item.correlation is None or breadth is None else
                   'HIGH_STOCK_SELECTION_OPPORTUNITY' if dispersion_z >= 1 and item.correlation < .6 and breadth >= 40 else
                   'LOW' if item.correlation >= .85 or dispersion_z < -1 or breadth < 20 else 'NORMAL')
    return dict(date=item.date.isoformat(), market_id=item.market_id, scope=item.scope,
                source_reference=item.source_reference, available_on=item.available_on.isoformat(),
                regime_model_version=VERSION, trend_regime=trend_state, trend_regime_score=trend,
                volatility_regime=_band(vol, [20, 40, options.high_vol_enter, 90], ['VERY_LOW', 'LOW', 'NORMAL', 'HIGH', 'EXTREME']),
                volatility_regime_score=vol, high_volatility_flag=high_vol,
                breadth_regime=_band(breadth, [20, 40, 60, 80], ['VERY_WEAK', 'WEAK', 'NEUTRAL', 'STRONG', 'VERY_STRONG']),
                breadth_regime_score=breadth,
                liquidity_regime=_band(liquidity, [20, 40, 75], ['STRESSED', 'TIGHT', 'NORMAL', 'ABUNDANT']),
                liquidity_regime_score=liquidity,
                flow_regime=_band(flow, [20, 40, 60, 80], ['STRONG_DISTRIBUTION', 'DISTRIBUTION', 'NEUTRAL', 'ACCUMULATION', 'STRONG_ACCUMULATION']),
                flow_regime_score=flow,
                derivatives_regime=('VOLATILITY_STRESS' if item.derivatives_risk_score is not None and item.derivatives_risk_score >= 80 else
                                    _band(derivative, [40, 60], ['RISK_OFF', 'NEUTRAL', 'RISK_ON'])),
                derivatives_regime_score=derivative, correlation=item.correlation,
                correlation_regime=correlation_regime, market_correlation_z=correlation_z,
                cross_sectional_dispersion=item.cross_sectional_dispersion, dispersion_z=dispersion_z,
                dispersion_regime=_band(dispersion_z, [-1, 1], ['LOW_DISPERSION', 'NORMAL', 'HIGH_DISPERSION']),
                factor_opportunity_regime=opportunity, trend_vol_regime=matrix,
                risk_on_off_state=('RISK_OFF' if label == 'STRESS' else _band(score, [-t, t], ['RISK_OFF', 'NEUTRAL', 'RISK_ON'])) if valid else None,
                market_stress_score=stress, stress_probability=stress / 100 if stress is not None and valid else None,
                **probabilities, regime_score=score, regime_label=label, raw_regime_label=label,
                regime_confidence=confidence, regime_feature_agreement=agreement,
                disagreeing_inputs=disagrees, score_contributions=contributions,
                conflicted_regime_flag=conflict, recovery_regime_flag=recovery,
                distribution_regime_flag=distribution, accumulation_regime_flag=bool(improving and family == 'SIDEWAYS'),
                regime_quality_status=flags[0] if flags else 'VALID', quality_flags=flags or ['VALID'])


def calculate_market_regime(request: MarketRegimeRequest):
    history = defaultdict(list)
    transitions = defaultdict(Counter)
    session_index = {day.isoformat(): index for index, day in enumerate(request.sessions)}
    pending = {}
    rows = []
    for item in sorted(request.observations, key=lambda r: (r.date, r.scope, r.market_id)):
        key = (item.scope, item.market_id)
        prior = history[key]
        previous = prior[-1] if prior else None
        consecutive = previous is not None and session_index[item.date.isoformat()] == session_index[previous['date']] + 1
        if not consecutive or previous['regime_label'] is None:
            previous = None
            pending.pop(key, None)
        row = _classify(item, request.options, previous, prior)
        label = row['regime_label']
        if previous and label is not None and label != previous['regime_label'] and label != 'STRESS':
            candidate, count = pending.get(key, (None, 0))
            count = count + 1 if candidate == label else 1
            pending[key] = (label, count)
            if count < request.options.minimum_persistence_sessions:
                row['regime_label'] = previous['regime_label']
        else:
            pending.pop(key, None)
        label = row['regime_label']
        old = previous['regime_label'] if previous else None
        row['days_in_current_regime'] = (previous['days_in_current_regime'] + 1 if old == label else 1) if label else 0
        row['regime_transition_state'] = f'{old}_TO_{label}' if old and label and old != label else 'STABLE' if old and label else None
        if old and label:
            transitions[key][(old, label)] += 1
        counts = {target: count for (source, target), count in transitions[key].items() if source == label}
        total = sum(counts.values())
        row['next_regime_probabilities'] = {target: count / total for target, count in sorted(counts.items())}
        row['regime_persistence_probability'] = counts.get(label, 0) / total if total else None
        concentration = max(row[name] for name in ('bull_probability', 'bear_probability', 'sideways_probability')) if label else 0
        row['regime_stability_score'] = 100 * fmean([concentration, min(row['days_in_current_regime'] / 20, 1), row['regime_feature_agreement'] / 100]) if label else None
        row['recommended_risk_budget_multiplier'] = request.options.risk_budget_by_regime.get(label, 1.0) if label else None
        row['risk_budget_status'] = 'CONFIGURED' if label in request.options.risk_budget_by_regime else 'UNVALIDATED_NEUTRAL' if label else 'UNAVAILABLE'
        prior.append(row)
        rows.append(row)
    matrices = []
    for (scope, market), counts in sorted(transitions.items()):
        totals = Counter()
        for (source, target), count in counts.items():
            totals[source] += count
        matrices.extend(dict(scope=scope, market_id=market, from_regime=source, to_regime=target,
                             count=count, probability=count / totals[source])
                        for (source, target), count in sorted(counts.items()))
    return dict(version=VERSION, snapshot_id=request.snapshot_id, as_of=request.as_of.isoformat(),
                probability_method='HEURISTIC_NOT_CALIBRATED', rows=rows, transition_matrix=matrices)
