"""Daily, calendar and aligned relative returns on an authoritative session grid."""
from collections import defaultdict
from datetime import date
from math import log, isfinite

from app.engines.returns.returns_schema import ReturnsRequest

HORIZONS = (1, 2, 3, 5, 10, 21, 42, 63, 126, 189, 252, 504, 756, 1260)
RANK_HORIZONS = (5, 21, 63, 126, 252)
VERSION = '1'


def period_key(day, frequency):
    if frequency == 'weekly':
        return day.isocalendar()[:2]
    if frequency == 'monthly':
        return day.year, day.month
    if frequency == 'quarterly':
        return day.year, (day.month - 1) // 3
    return (day.year,)


class Series:
    def __init__(self, request):
        self.request = request
        self.sessions = [d for d in request.sessions if d <= request.as_of]
        self.positions = {d: i for i, d in enumerate(self.sessions)}
        self.rows = defaultdict(dict)
        self.duplicates = set()
        for row in request.prices:
            if row.date not in self.positions or row.available_on > request.as_of:
                continue
            key = row.instrument_key, row.date
            if row.date in self.rows[row.instrument_key]:
                self.duplicates.add(key)
            self.rows[row.instrument_key][row.date] = row
        self.eligibility = {(e.instrument_key, e.date): e for e in request.eligibility if e.available_on <= e.date}
        self.prefix = {}
        for key in set(self.rows) | set(request.instrument_keys):
            prefix = [0]
            for i in range(len(self.sessions)):
                prefix.append(prefix[-1] + (self.price(key, i)[1] is not None))
            self.prefix[key] = prefix
        self.field_prefix = {}

    def price(self, key, index, field=None):
        if index < 0 or index >= len(self.sessions):
            return None, 'INSUFFICIENT_HISTORY'
        day = self.sessions[index]
        row = self.rows.get(key, {}).get(day)
        if not row:
            return None, 'MISSING_PRICE'
        if (key, day) in self.duplicates:
            return None, 'DUPLICATE_PRICE'
        if row.available_on > day:
            return None, 'NOT_KNOWN_AT_SESSION'
        if not row.quality_valid:
            return None, 'DATA_QUALITY_FAILURE'
        if row.suspended:
            return None, 'SUSPENDED'
        if row.volume is not None and row.volume <= 0:
            return None, 'NO_TRADING' if row.volume == 0 else 'DATA_QUALITY_FAILURE'
        if row.unresolved_corporate_action:
            return None, 'CORPORATE_ACTION_UNRESOLVED'
        field = field or {'raw': 'raw_close', 'adjusted': 'adjusted_close', 'total_return': 'total_return_close'}[self.request.price_basis]
        if field.startswith('adjusted') or field == 'total_return_close':
            if not row.adjustment_valid or not row.adjustment_source or not row.adjustment_version:
                return None, 'CORPORATE_ACTION_UNRESOLVED'
        if field.startswith('adjusted') and row.adjusted_high is not None and row.adjusted_low is not None:
            available = [v for v in (row.adjusted_open, row.adjusted_close, row.adjusted_high, row.adjusted_low) if v is not None]
            if row.adjusted_high < max(available) or row.adjusted_low > min(available):
                return None, 'DATA_QUALITY_FAILURE'
        value = getattr(row, field)
        if value is None or value <= 0 or not isfinite(value):
            return None, 'MISSING_PRICE' if value is None else 'INVALID_PRICE'
        return value, None

    def change(self, key, start, end, field=None, end_field=None):
        left, error = self.price(key, start, field)
        right, other = self.price(key, end, end_field or field)
        if error or other:
            return None, error or other
        if start > end:
            return None, 'INVALID_WINDOW'
        # Preserve all session gaps; do not bridge a missing interior observation.
        prefix = self.prefix.get(key)
        if field is not None:
            # Each metric depends on its own fields, not the run's selected close basis.
            identity = key, field, end_field or field
            if identity not in self.field_prefix:
                counts = [0]
                for index in range(len(self.sessions)):
                    invalid = self.price(key, index, field)[1] is not None
                    counts.append(counts[-1]+invalid)
                self.field_prefix[identity] = counts
            prefix = self.field_prefix[identity]
        if prefix is None or (end > start + 1 and prefix[end] - prefix[start+1]):
            return None, 'INVALID_OBSERVATION_IN_WINDOW'
        result = right / left - 1
        return (result, None) if isfinite(result) else (None, 'NUMERIC_OVERFLOW')


def calculate_returns(request: ReturnsRequest):
    series = Series(request)
    output = []
    for key in request.instrument_keys:
        positive = negative = max_positive = max_negative = 0
        last_trade_date = last_valid_return = None
        for i, day in enumerate(series.sessions):
            observation = series.rows.get(key, {}).get(day)
            eligibility = series.eligibility.get((key, day))
            record = dict(instrument_key=key, date=day.isoformat(), frequency='daily',
                          price_basis=request.price_basis, metrics={}, invalid_reasons={},
                          universe_id=eligibility.universe_id if eligibility else None,
                          sector_id=eligibility.sector_id if eligibility else None,
                          corporate_action_adjusted=bool(observation and observation.adjustment_valid),
                          adjustment_source=observation.adjustment_source if observation else None,
                          adjustment_version=observation.adjustment_version if observation else None,
                          corporate_action_flag=bool(observation and observation.corporate_action_flag),
                          terminal_status=observation.terminal_status if observation else None,
                          available_on=day.isoformat())

            def put(name, value, reason=None):
                record['metrics'][name] = value
                if value is None:
                    record['invalid_reasons'][name] = reason or 'MISSING_INPUT'

            for h in HORIZONS:
                value, reason = series.change(key, i - h, i)
                if not eligibility or h not in eligibility.eligible_horizons:
                    value, reason = None, 'HORIZON_INELIGIBLE' if eligibility else 'MISSING_ELIGIBILITY'
                put(f'return_{h}d', value, reason)
            daily = record['metrics']['return_1d']
            put('log_return_1d', log(1 + daily) if daily is not None and daily > -1 else None)
            open_field = 'raw_open' if request.price_basis == 'raw' else 'adjusted_open'
            close_field = 'raw_close' if request.price_basis == 'raw' else 'adjusted_close'
            high_field = 'raw_high' if request.price_basis == 'raw' else 'adjusted_high'
            low_field = 'raw_low' if request.price_basis == 'raw' else 'adjusted_low'
            # Intraday decomposition is explicitly price-based, even in a total-return run.
            for name, start, end, first, last in (
                ('intraday_return', i, i, open_field, close_field),
                ('overnight_return', i-1, i, close_field, open_field),
                ('open_to_open_return', i-1, i, open_field, open_field),
                ('price_return_1d', i-1, i, close_field, close_field),
                ('raw_return_1d', i-1, i, 'raw_close', 'raw_close'),
                ('total_return_1d', i-1, i, 'total_return_close', 'total_return_close'),
                ('high_low_range_pct', i, i, low_field, high_field),
                ('open_to_high_return', i, i, open_field, high_field),
                ('open_to_low_return', i, i, open_field, low_field),
                ('close_to_high_distance', i, i, close_field, high_field),
                ('close_to_low_distance', i, i, close_field, low_field)):
                value, reason = series.change(key, start, end, first, last)
                put(name, value, reason)
            overnight = record['metrics']['overnight_return']
            intra = record['metrics']['intraday_return']
            put('gap_return', overnight)
            record['gap_classification'] = None if overnight is None else 'gap_up' if overnight > request.gap_threshold else 'gap_down' if overnight < -request.gap_threshold else 'no_material_gap'
            put('gap_intraday_interaction', overnight * intra if overnight is not None and intra is not None else None)
            price_return, total = record['metrics']['price_return_1d'], record['metrics']['total_return_1d']
            put('dividend_return_component', total-price_return if request.price_basis != 'raw' and total is not None and price_return is not None else None)
            rf = observation.risk_free_return if observation else None
            put('risk_free_excess_return', daily-rf if daily is not None and rf is not None else None)
            record.update(is_positive_return=daily > 0 if daily is not None else None,
                          is_negative_return=daily < 0 if daily is not None else None,
                          is_zero_return=daily == 0 if daily is not None else None)
            positive = positive+1 if daily is not None and daily > 0 else 0
            negative = negative+1 if daily is not None and daily < 0 else 0
            max_positive, max_negative = max(max_positive, positive), max(max_negative, negative)
            record.update(positive_streak_days=positive, negative_streak_days=negative,
                          max_positive_streak=max_positive, max_negative_streak=max_negative)
            for name, frequency in [('mtd', 'monthly'), ('qtd', 'quarterly'), ('ytd', 'annual'), ('wtd', 'weekly')]:
                current_key = period_key(day, frequency)
                prior = next((j for j in range(i-1, -1, -1) if period_key(series.sessions[j], frequency) != current_key), -1)
                put(f'{name}_return', *series.change(key, prior, i))
                previous_key = period_key(series.sessions[prior], frequency) if prior >= 0 else None
                before = next((j for j in range(prior-1, -1, -1) if period_key(series.sessions[j], frequency) != previous_key), -1)
                put(f'previous_{frequency}_return', *series.change(key, before, prior))
            start = series.positions.get(request.cumulative_start, -1) if request.cumulative_start else 0
            put('cumulative_return', *series.change(key, start, i))
            for years in (2, 3, 5):
                if day.year <= years:
                    put(f'cagr_{years}y', None, 'INSUFFICIENT_HISTORY')
                    continue
                try:
                    anniversary = day.replace(year=day.year-years)
                except ValueError:
                    anniversary = date(day.year-years, 2, 28)
                j = next((j for j in range(i, -1, -1) if series.sessions[j] <= anniversary), -1)
                growth, reason = series.change(key, j, i)
                if not eligibility or years*252 not in eligibility.eligible_horizons:
                    growth, reason = None, 'HORIZON_INELIGIBLE'
                elapsed = (day-series.sessions[j]).days/365.2425 if j >= 0 else 0
                put(f'cagr_{years}y', (1+growth)**(1/elapsed)-1 if growth is not None and elapsed else None, reason)
            for label, reference in [('benchmark', eligibility.benchmark_id if eligibility else None),
                                     ('sector', eligibility.sector_benchmark_id if eligibility else None),
                                     ('industry', eligibility.industry_benchmark_id if eligibility else None)]:
                record[f'{label}_id'] = reference
                for h in HORIZONS:
                    value, reason = series.change(reference, i-h, i) if reference else (None, 'MISSING_MAPPING')
                    put(f'{label}_return_{h}d', value, reason)
                    own = record['metrics'][f'return_{h}d']
                    put(f'{"excess" if label == "benchmark" else label+"_relative"}_return_{h}d', own-value if own is not None and value is not None else None, reason)
            record['return_valid'] = daily is not None
            if daily is not None:
                last_valid_return = daily
            if series.price(key, i)[1] is None:
                last_trade_date = day.isoformat()
            record.update(last_trade_date=last_trade_date, last_valid_return=last_valid_return)
            record['return_outlier_flag'] = daily is not None and abs(daily) > request.outlier_threshold
            record['return_outlier_reason'] = 'EXTREME_DAILY_RETURN' if record['return_outlier_flag'] else None
            record['return_quality_status'] = 'INVALID' if daily is None else 'WARNING' if record['return_outlier_flag'] else 'HEALTHY'
            output.append(record)
    from app.engines.returns.cross_sectional import rank_returns
    periods = []
    calendar_positions = {day: index for index, day in enumerate(request.sessions)}
    for row in output:
        day = date.fromisoformat(row['date'])
        index = calendar_positions[day]
        # A supplied subsequent session proves the current period's final session.
        if index+1 >= len(request.sessions):
            continue
        next_day = request.sessions[index+1]
        for frequency, metric in [('weekly', 'wtd_return'), ('monthly', 'mtd_return'), ('quarterly', 'qtd_return'), ('annual', 'ytd_return')]:
            if period_key(day, frequency) != period_key(next_day, frequency):
                value = row['metrics'][metric]
                periods.append(dict(instrument_key=row['instrument_key'], date=row['date'], frequency=frequency,
                    period_return=value, return_valid=value is not None, invalid_reason=row['invalid_reasons'].get(metric), price_basis=request.price_basis))
    return dict(calculation_version=VERSION, snapshot_id=request.snapshot_id,
                rows=output, periods=periods, rankings=rank_returns(output, request))


def calculate_labels(request, horizons):
    series = Series(request)
    output = []
    for key in request.instrument_keys:
        for i, day in enumerate(series.sessions):
            for h in horizons:
                target = i+h
                value, reason = series.change(key, i, target)
                label = dict(instrument_key=key, date=day.isoformat(), horizon=h,
                    target_date=series.sessions[target].isoformat() if target < len(series.sessions) else None,
                    available_on=series.sessions[target].isoformat() if target < len(series.sessions) else None,
                    forward_return=value, label_valid=value is not None,
                    invalid_reason=reason, price_basis=request.price_basis)
                if h == 1:
                    open_field = 'raw_open' if request.price_basis == 'raw' else 'adjusted_open'
                    close_field = 'raw_close' if request.price_basis == 'raw' else 'adjusted_close'
                    label['forward_overnight_return_1d'], label['overnight_invalid_reason'] = series.change(key, i, target, close_field, open_field)
                    label['forward_intraday_return_1d'], label['intraday_invalid_reason'] = series.change(key, target, target, open_field, close_field)
                output.append(label)
    return output
