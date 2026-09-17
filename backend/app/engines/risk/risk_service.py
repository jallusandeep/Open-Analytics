"""Daily risk features, with point-in-time inputs and per-metric eligibility."""
from math import ceil, isfinite, log, sqrt
from statistics import NormalDist, fmean, stdev

from app.engines.risk.observations import prepare
from app.engines.risk.statistics import drawdowns, moments, quantile, regression

VERSION = '1'
WINDOWS = (5, 10, 21, 42, 63, 126, 252)
HARD_FAILURES = {'DATA_QUALITY_FAILURE', 'CORPORATE_ACTION_UNRESOLVED', 'DUPLICATE_PRICE',
                 'INVALID_PRICE', 'SUSPENDED', 'NO_TRADING', 'STALE_PRICE', 'ILLIQUID', 'NOT_TRADING'}


def put(row, name, value, count=0, reason=None):
    if isinstance(value, float) and not isfinite(value):
        value, reason = None, 'NUMERIC_OVERFLOW'
    row['metrics'][name] = value
    row['metric_quality'][name] = dict(valid=value is not None, observation_count=count,
                                      invalid_reason=None if value is not None else reason or 'MISSING_INPUT')


def window_data(observations, i, window, options, field='daily', minimum=2):
    chunk = observations[max(0, i-window+1):i+1]
    values = [o[field] for o in chunk if o[field] is not None]
    reasons = [o['reason'] if field == 'daily' else o.get('price_reason') for o in chunk]
    hard = next((reason for reason in reasons if reason in HARD_FAILURES), None)
    if hard:
        return values, hard
    if i+1 < window:
        return values, 'INSUFFICIENT_HISTORY'
    if len(values) < max(minimum, ceil(window*options.minimum_coverage)):
        return values, 'TOO_MANY_MISSING_OBSERVATIONS'
    if chunk[-1][field] is None:
        return values, chunk[-1]['reason'] or 'BAD_RETURN_DATA'
    return values, None


def calculate_risk(request, report=None):
    options = request.options
    series, groups = prepare(request, report)
    output = []
    annual = sqrt(options.annualization_sessions)
    for key, observations in groups.items():
        previous_rows = []
        for i, observation in enumerate(observations):
            source = observation['source']
            row = dict(instrument_key=key, date=observation['date'], universe_id=source['universe_id'],
                sector_id=source['sector_id'], benchmark_id=source['benchmark_id'],
                sector_benchmark_id=None, price_basis=request.returns.price_basis,
                metrics={}, metric_quality={}, warnings=list(observation['warnings']),
                downside_target_type=options.downside_target_type)
            # Resolve membership independently of the Returns benchmark identifier.
            eligibility = series.eligibility.get((key, series.sessions[i]))
            row['sector_id'] = eligibility.sector_id if eligibility else None
            benchmark = eligibility.benchmark_id if eligibility else None
            sector = eligibility.sector_benchmark_id if eligibility else None
            row['sector_benchmark_id'] = sector
            refs = {}
            for label, reference in (('market', benchmark), ('sector', sector)):
                refs[label] = [series.change(reference, j-1, j)[0] if reference else None for j in range(max(0, i-251), i+1)]

            for window in WINDOWS:
                chunk = observations[max(0, i-window+1):i+1]
                values, reason = window_data(observations, i, window, options)
                count = len(values)
                sd = stdev(values) if reason is None else None
                put(row, f'vol_{window}d', sd, count, reason)
                put(row, f'ann_vol_{window}d', sd*annual if sd is not None else None, count, reason)
                logs = [log(1+v) for v in values if v > -1]
                put(row, f'log_vol_{window}d', stdev(logs) if reason is None and len(logs) == count else None,
                    len(logs), reason or 'BAD_RETURN_DATA')
                negatives, positives = [v for v in values if v < 0], [v for v in values if v > 0]
                for name, subset in (('downside', negatives), ('upside', positives)):
                    put(row, f'{name}_vol_{window}d', stdev(subset) if reason is None and len(subset) >= 2 else None,
                        len(subset), reason or 'INSUFFICIENT_CONDITIONAL_OBSERVATIONS')
                targets = []
                for entry in chunk:
                    target = 0. if options.downside_target_type == 'ZERO' else options.minimum_acceptable_return
                    if options.downside_target_type == 'RISK_FREE':
                        target = entry['risk_free']
                    if options.downside_target_type == 'BENCHMARK':
                        target = series.change(benchmark, entry['index']-1, entry['index'])[0] if benchmark else None
                    if entry['daily'] is not None and target is not None:
                        targets.append(min(entry['daily']-target, 0.)**2)
                put(row, f'downside_semidev_{window}d', sqrt(fmean(targets)) if reason is None and len(targets) == count else None,
                    len(targets), reason or 'TARGET_MISSING')
                skew, kurt = moments(values) if reason is None else (None, None)
                put(row, f'skew_{window}d', skew, count, reason or 'ZERO_VARIANCE')
                put(row, f'kurtosis_{window}d', kurt, count, reason or 'ZERO_VARIANCE')
                tail_reason = reason or ('INSUFFICIENT_TAIL_OBSERVATIONS' if count < options.minimum_tail_observations else None)
                for confidence in (95, 99):
                    cutoff = quantile(values, 1-confidence/100) if not tail_reason else None
                    losses = [v for v in values if cutoff is not None and v <= cutoff]
                    put(row, f'var_{confidence}_{window}d', max(0., -cutoff) if cutoff is not None else None, count, tail_reason)
                    put(row, f'cvar_{confidence}_{window}d', max(0., -fmean(losses)) if losses else None, count, tail_reason)
                    put(row, f'parametric_var_{confidence}_{window}d',
                        max(0., NormalDist().inv_cdf(confidence/100)*sd-fmean(values)) if not tail_reason else None, count, tail_reason)
                put(row, f'worst_1d_return_{window}d', min(values) if not reason else None, count, reason)
                put(row, f'best_1d_return_{window}d', max(values) if not reason else None, count, reason)

                for label, reference in (('market', benchmark), ('sector', sector)):
                    reference_values = refs[label][-len(chunk):]
                    pairs = [(entry['daily'], ref) for entry, ref in zip(chunk, reference_values)
                             if entry['daily'] is not None and ref is not None]
                    n = len(pairs)
                    error = reason or ('BENCHMARK_MISSING' if not reference else None)
                    if not error and n < max(options.minimum_beta_observations, ceil(window*options.minimum_coverage)):
                        error = 'INSUFFICIENT_OVERLAP'
                    fit = regression([b for _, b in pairs], [a for a, _ in pairs]) if not error else None
                    fit_error = error or 'ZERO_BENCHMARK_VARIANCE'
                    prefix = '' if label == 'market' else 'sector_'
                    put(row, f'{prefix}beta_{window}d', fit['beta'] if fit else None, n, fit_error)
                    put(row, f'{label}_corr_{window}d', fit['correlation'] if fit else None, n,
                        fit_error if not fit else 'ZERO_STOCK_VARIANCE')
                    if label == 'market':
                        put(row, f'r_squared_{window}d', fit['r_squared'] if fit else None, n, fit_error)
                        put(row, f'idio_vol_{window}d', fit['idio_vol'] if fit else None, n, fit_error)
                        put(row, f'idiosyncratic_volatility_{window}d', fit['idio_vol'] if fit else None, n, fit_error)
                        active = [a-b for a, b in pairs]
                        te = stdev(active) if not error else None
                        put(row, f'tracking_error_{window}d', te, n, error)
                        put(row, f'ann_tracking_error_{window}d', te*annual if te is not None else None, n, error)
                        put(row, f'mean_active_return_{window}d', fmean(active) if not error else None, n, error)
                        rf_pairs = [(entry['daily']-entry['risk_free'], ref-entry['risk_free'])
                            for entry, ref in zip(chunk, reference_values)
                            if entry['daily'] is not None and ref is not None and entry['risk_free'] is not None]
                        excess_fit = regression([b for _, b in rf_pairs], [a for a, _ in rf_pairs]) if not error and len(rf_pairs) == n else None
                        alpha = excess_fit['alpha'] if excess_fit else None
                        put(row, f'alpha_{window}d', alpha, len(rf_pairs), error or 'RISK_FREE_MISSING_OR_ZERO_VARIANCE')
                        put(row, f'ann_alpha_{window}d', alpha*options.annualization_sessions if alpha is not None else None,
                            len(rf_pairs), error or 'RISK_FREE_MISSING_OR_ZERO_VARIANCE')

            # EWMA is a forecast at t, using returns only through t-1.
            for window in (21, 63):
                values, error = window_data(observations, i-1, window, options) if i else ([], 'INSUFFICIENT_HISTORY')
                variance = None
                if not error:
                    variance = values[0]**2
                    for value in values[1:]:
                        variance = options.ewma_lambda*variance+(1-options.ewma_lambda)*value**2
                put(row, f'ewma_vol_{window}d', sqrt(variance) if variance is not None else None, len(values), error)

            add_price_risk(row, observations, i, options)
            add_history(row, previous_rows, options)
            put(row, 'active_return', observation['daily']-refs['market'][-1]
                if observation['daily'] is not None and refs['market'][-1] is not None else None,
                int(observation['daily'] is not None and refs['market'][-1] is not None), observation['reason'] or 'BENCHMARK_MISSING')
            previous_rows.append(row)
            output.append(row)
    from app.engines.risk.ranking import rank_risk
    rank_risk(output, request)
    for row in output:
        required = ['vol_21d', 'vol_63d', 'vol_126d', 'vol_252d', 'downside_vol_63d',
                    'atr_14', 'current_drawdown', 'max_drawdown_252d', 'beta_63d', 'beta_252d',
                    'market_corr_252d', 'sector_corr_252d', 'idio_vol_252d', 'var_95_252d',
                    'cvar_95_252d', 'skew_252d', 'kurtosis_252d', 'tracking_error_252d']
        valid = sum(row['metrics'][name] is not None for name in required)
        row['risk_valid'] = valid == len(required)
        row['risk_quality_status'] = 'INVALID' if valid == 0 else 'PARTIAL' if valid < len(required) else 'WARNING' if row['warnings'] else 'HEALTHY'
        row['risk_invalid_reasons'] = sorted({row['metric_quality'][name]['invalid_reason'] for name in required
                                            if not row['metric_quality'][name]['valid']})
    return dict(calculation_version=VERSION, snapshot_id=request.returns.snapshot_id,
                as_of=request.returns.as_of.isoformat(), options=options.model_dump(mode='json'), rows=output)


def add_price_risk(row, observations, i, options):
    for window in (14, 21, 63):
        chunk = observations[max(0, i-window+1):i+1]
        ranges, parkinson, garman = [], [], []
        for item in chunk:
            fields, index = item['fields'], item['index']
            opening, high, low, close = [fields[f'adjusted_{name}'] for name in ('open', 'high', 'low', 'close')]
            if high is not None and low is not None:
                parkinson.append(log(high/low)**2/(4*log(2)))
                prior = observations[index-1]['fields']['adjusted_close'] if index else None
                if prior is not None:
                    ranges.append(max(high-low, abs(high-prior), abs(low-prior)))
                if opening is not None and close is not None:
                    garman.append(.5*log(high/low)**2-(2*log(2)-1)*log(close/opening)**2)
        for name, values in (('atr', ranges), ('parkinson_vol', parkinson), ('garman_klass_vol', garman)):
            error = 'INSUFFICIENT_HISTORY' if i+1 < window else 'INVALID_OR_MISSING_OHLC'
            value = fmean(values) if len(values) == window else None
            if value is not None and name != 'atr':
                value = sqrt(max(0., value))
            suffix = str(window) if name == 'atr' else f'{window}d'
            put(row, f'{name}_{suffix}', value, len(values), error)
            if name == 'atr':
                current = observations[i]['fields']['adjusted_close']
                put(row, f'atr_pct_{window}', value/current if value is not None and current else None, len(values), error)
    # All-history means all supplied known history, not pre-listing synthetic data.
    history = observations[:i+1]
    first = next((j for j, item in enumerate(history) if item['close'] is not None), len(history))
    history = history[first:]
    for label, window in [('all', None), ('21d', 21), ('63d', 63), ('126d', 126), ('252d', 252), ('3y', 756), ('5y', 1260)]:
        chunk = history if window is None else observations[max(0, i-window):i+1]
        count = sum(item['close'] is not None for item in chunk)
        enough = bool(chunk) and (window is None or len(chunk) == window+1)
        error = 'INSUFFICIENT_HISTORY' if not enough else 'INVALID_PRICE_PATH'
        stats = drawdowns([item['close'] for item in chunk], [item['date'] for item in chunk]) if enough and count == len(chunk) else None
        put(row, f'max_drawdown_{label}', stats['max_drawdown'] if stats else None, count, error)
        if label == 'all':
            for name in ('current_drawdown', 'current_drawdown_duration', 'max_drawdown_duration',
                         'average_drawdown_duration', 'last_recovery_days', 'average_recovery_days', 'max_recovery_days'):
                put(row, name, stats[name] if stats else None, count, error if not stats else 'NO_COMPLETED_EPISODE')
            row['drawdown_context'] = {name: stats[name] if stats else None for name in
                ('recovered', 'max_drawdown_start_date', 'max_drawdown_trough_date', 'max_drawdown_recovery_date')}
            row['drawdown_history_start'] = chunk[0]['date'] if chunk else None
        else:
            put(row, f'ulcer_index_{label}', stats['ulcer_index'] if stats else None, count, error)
    for window in (21, 63, 252):
        gaps, error = window_data(observations, i, window, options, 'overnight')
        metrics = dict(overnight_volatility=stdev(gaps) if not error else None,
            gap_up_frequency=sum(v > 0 for v in gaps)/len(gaps) if not error else None,
            gap_down_frequency=sum(v < 0 for v in gaps)/len(gaps) if not error else None,
            large_gap_frequency=sum(abs(v) >= options.large_gap_threshold for v in gaps)/len(gaps) if not error else None,
            max_positive_gap=max(0., max(gaps)) if not error else None,
            max_negative_gap=min(0., min(gaps)) if not error else None)
        for name, value in metrics.items():
            put(row, f'{name}_{window}d', value, len(gaps), error)


def add_history(row, previous_rows, options):
    metrics = row['metrics']
    for lag in (5, 21):
        prior = previous_rows[-lag]['metrics'].get('ann_vol_21d') if len(previous_rows) >= lag else None
        now = metrics['ann_vol_21d']
        put(row, f'vol_change_{lag}d', now-prior if now is not None and prior is not None else None,
            2 if now is not None and prior is not None else 0, 'INSUFFICIENT_HISTORY')
    short, long = metrics['ann_vol_21d'], metrics['ann_vol_252d']
    put(row, 'vol_ratio_21_252', short/long if short is not None and long else None, 0, 'MISSING_OR_ZERO_LONG_VOL')
    history = [r['metrics']['ann_vol_21d'] for r in previous_rows[-options.historical_rank_window:]
               if r['metrics']['ann_vol_21d'] is not None]
    enough = short is not None and len(history) >= options.minimum_historical_observations
    percentile = 100*(sum(v < short for v in history)+.5*sum(v == short for v in history))/len(history) if enough else None
    put(row, 'volatility_historical_percentile', percentile, len(history), 'INSUFFICIENT_HISTORY')
    deviation = stdev(history) if enough else None
    put(row, 'historical_vol_zscore', (short-fmean(history))/deviation if deviation else None,
        len(history), 'ZERO_VARIANCE' if enough else 'INSUFFICIENT_HISTORY')
    row['risk_regime'] = None if percentile is None else 'EXTREME_VOL' if percentile >= 95 else 'HIGH_VOL' if percentile >= 80 else 'LOW_VOL' if percentile < 20 else 'NORMAL_VOL'
    change = metrics['vol_change_21d']
    row['risk_trend'] = None if change is None else 'RISING' if change > 1e-12 else 'FALLING' if change < -1e-12 else 'STABLE'
