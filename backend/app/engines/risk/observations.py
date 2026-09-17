"""Retain the exchange-session grid; never fill missing or invalid returns."""
from collections import defaultdict

from app.engines.returns.returns_service import Series, calculate_returns


def prepare(request, report=None):
    series = Series(request.returns)
    report = report if report is not None else calculate_returns(request.returns)
    checks = {(c.instrument_key, c.date.isoformat()): c for c in request.trading_checks
              if c.available_on <= c.date}
    groups = defaultdict(list)
    for source in report['rows']:
        groups[source['instrument_key']].append(source)
    output = {}
    for key, rows in groups.items():
        result, unchanged, previous = [], 0, None
        for i, source in enumerate(rows):
            day = series.sessions[i]
            price = series.rows.get(key, {}).get(day)
            close, price_reason = series.price(key, i)
            check = checks.get((key, source['date']))
            unchanged = unchanged + 1 if close is not None and close == previous else 1
            previous = close
            suspect = unchanged >= request.options.stale_sessions or bool(check and check.stale_price_flag)
            unsafe = 'STALE_PRICE' if suspect else 'ILLIQUID' if check and check.liquidity_status == 'ILLIQUID' else (
                'NOT_TRADING' if check and check.trading_status != 'ACTIVE' else None)
            reason = unsafe or price_reason or source['invalid_reasons'].get('return_1d')
            daily = source['metrics']['return_1d'] if not reason else None
            observation = dict(date=source['date'], source=source, daily=daily, reason=reason,
                close=close if not unsafe else None, price_reason=unsafe or price_reason,
                warnings=[], fields={}, field_reasons={})
            if not check or check.liquidity_status == 'UNKNOWN':
                observation['warnings'].append('LIQUIDITY_UNVERIFIED')
            if source['return_quality_status'] == 'WARNING':
                observation['warnings'].append('RETURN_OUTLIER')
            if price and price.available_on <= day:
                observation['risk_free'] = price.risk_free_return
            else:
                observation['risk_free'] = None
            for field in ('adjusted_open', 'adjusted_high', 'adjusted_low', 'adjusted_close'):
                value, error = series.price(key, i, field)
                observation['fields'][field] = value if not unsafe else None
                observation['field_reasons'][field] = unsafe or error
            observation['overnight'] = source['metrics']['overnight_return'] if not unsafe else None
            # Use the current date's point-in-time benchmark mapping consistently
            # across each rolling regression window (resolved in the calculator).
            observation['index'] = i
            result.append(observation)
        output[key] = result
    return series, output
