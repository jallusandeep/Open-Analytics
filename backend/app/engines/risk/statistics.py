"""Explicit statistical conventions, using only the Python standard library."""
from math import sqrt
from statistics import fmean, stdev


def quantile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered)-1)*fraction
    lower = int(position)
    upper = min(lower+1, len(ordered)-1)
    return ordered[lower] + (ordered[upper]-ordered[lower])*(position-lower)


def covariance(x, y):
    mx, my = fmean(x), fmean(y)
    return sum((a-mx)*(b-my) for a, b in zip(x, y))/(len(x)-1)


def regression(x, y):
    """x = benchmark, y = security, sample covariance and residual std (ddof=1)."""
    variance = covariance(x, x)
    if variance <= 1e-24:
        return None
    beta = covariance(x, y)/variance
    alpha = fmean(y)-beta*fmean(x)
    residuals = [b-alpha-beta*a for a, b in zip(x, y)]
    sy = stdev(y)
    correlation = max(-1., min(1., covariance(x, y)/(sqrt(variance)*sy))) if sy > 1e-12 else None
    return dict(beta=beta, alpha=alpha, correlation=correlation,
                r_squared=correlation**2 if correlation is not None else None,
                idio_vol=stdev(residuals))


def moments(values):
    n, mean = len(values), fmean(values)
    m2 = fmean((v-mean)**2 for v in values)
    if m2 <= 1e-24:
        return None, None
    skew = sqrt(n*(n-1))/(n-2)*fmean((v-mean)**3 for v in values)/m2**1.5 if n > 2 else None
    g2 = fmean((v-mean)**4 for v in values)/m2**2-3
    kurt = (n-1)/((n-2)*(n-3))*((n+1)*g2+6) if n > 3 else None
    return skew, kurt


def drawdowns(prices, dates):
    """Prices include the initial level; recovery durations run from trough to recovery."""
    peak, peak_date, worst, current_duration = prices[0], dates[0], 0., 0
    durations, recoveries, series = [], [], []
    episode_trough, episode_index = peak, 0
    worst_start = worst_trough = worst_recovery = None
    worst_episode_start = None
    for index, (price, day) in enumerate(zip(prices, dates)):
        dd = price/peak-1
        if price >= peak:
            if current_duration:
                durations.append(current_duration)
                recoveries.append(index-episode_index)
                if worst_episode_start == peak_date:
                    worst_recovery = day
            peak, peak_date, current_duration = price, day, 0
            episode_trough, episode_index = price, index
            dd = 0.
        else:
            current_duration += 1
            if price < episode_trough:
                episode_trough, episode_index = price, index
            if dd < worst:
                worst, worst_start, worst_trough = dd, peak_date, day
                worst_episode_start, worst_recovery = peak_date, None
        series.append(dd)
    return dict(current_drawdown=series[-1], max_drawdown=worst,
        current_drawdown_duration=current_duration,
        max_drawdown_duration=max(durations+[current_duration]),
        average_drawdown_duration=fmean(durations) if durations else None,
        last_recovery_days=recoveries[-1] if recoveries else None,
        average_recovery_days=fmean(recoveries) if recoveries else None,
        max_recovery_days=max(recoveries) if recoveries else None,
        recovered=current_duration == 0,
        max_drawdown_start_date=worst_start, max_drawdown_trough_date=worst_trough,
        max_drawdown_recovery_date=worst_recovery,
        ulcer_index=sqrt(fmean(v*v for v in series)))
