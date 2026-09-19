"""Small deterministic statistical primitives used by the ranking engine."""
from math import ceil, copysign, log, sqrt
from statistics import fmean, median, pstdev


def quantile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def transform(value, rule):
    if rule == 'LOG':
        return log(value) if value > 0 else None
    if rule == 'SIGNED_LOG':
        return copysign(log(1 + abs(value)), value)
    return value


def average_strength(values, value):
    """Average tie rank on ascending desirability: weakest=1, strongest=n."""
    return sum(item < value for item in values) + (sum(item == value for item in values) + 1) / 2


def percentile(values, value):
    return 50.0 if len(values) == 1 else 100 * (average_strength(values, value) - 1) / (len(values) - 1)


def distribution(values):
    ordered = sorted(values)
    center = median(ordered)
    mad = median([abs(value - center) for value in ordered])
    return dict(count=len(ordered), mean=fmean(ordered), median=center, std=pstdev(ordered), mad=mad,
                min=ordered[0], max=ordered[-1],
                **{f'p{int(q*100):02d}': quantile(ordered, q) for q in (.01, .05, .10, .25, .50, .75, .90, .95, .99)})


def normalized(values, value):
    mean, deviation = fmean(values), pstdev(values)
    raw_z = (value - mean) / deviation if deviation else None
    center = median(values)
    mad = median([abs(item - center) for item in values])
    robust_z = (value - center) / (1.4826 * mad) if mad else None
    return raw_z, robust_z


def bucket(percentile_value, count):
    if percentile_value is None:
        return None
    return min(count, max(1, ceil((percentile_value / 100) * count)))


def residual_z(values, value, group_values):
    residuals = [item - fmean(group) for item, group in values]
    residual = value - fmean(group_values)
    deviation = pstdev(residuals)
    return residual, residual / deviation if deviation else None
