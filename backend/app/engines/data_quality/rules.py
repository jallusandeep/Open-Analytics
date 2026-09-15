"""Shared deterministic action, fiscal-calendar and exchange-calendar rules."""
import calendar
from datetime import date, timedelta


def action_type(value):
    value = str(value or '').strip().lower().replace(' ', '_').replace('-', '_')
    return {'stock_split': 'split', 'bonus_issue': 'bonus', 'cash_dividend': 'dividend',
            'rights': 'rights_issue', 'reverse_stock_split': 'reverse_split'}.get(value, value)


def fiscal_periods(first, last, period_type):
    """Infer only interior missing periods; never guess an issuer's listing history."""
    step = {'quarterly': 3, 'quarter': 3, 'annual': 12, 'yearly': 12,
            'half_yearly': 6, 'semiannual': 6}.get(str(period_type or '').lower())
    if not step or not first or not last:
        return set()
    result = set()
    offset = 0
    month_end = first.day == calendar.monthrange(first.year, first.month)[1]
    while True:
        year, month = divmod(first.year * 12 + first.month - 1 + offset, 12)
        month += 1
        end = calendar.monthrange(year, month)[1]
        current = date(year, month, end if month_end else min(first.day, end))
        if current > last:
            return result
        result.add(current)
        offset += step


def trading_sessions(start, end, *, holidays=(), special_sessions=(), listing_date=None, delisting_date=None):
    if end < start or (end - start).days > 36600:
        raise ValueError('Invalid or excessive calendar range')
    start = max(start, listing_date) if listing_date else start
    end = min(end, delisting_date) if delisting_date else end
    holidays, special = set(holidays), set(special_sessions)
    result = []
    while start <= end:
        if start in special or (start.weekday() < 5 and start not in holidays):
            result.append(start)
        start += timedelta(days=1)
    return result
