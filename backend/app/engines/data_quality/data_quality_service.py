"""Deterministic, non-mutating research validation over normalized records.

Scores are diagnostics, not probabilities. Critical issues exclude a record;
warnings retain it for review. Callers provide the eligible exchange sessions.
"""
from collections import defaultdict
from datetime import date, datetime, timezone
from math import isfinite
from app.engines.data_quality.rules import action_type, fiscal_periods


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def number(value):
    try:
        result = float(value)
        return result if isfinite(result) and not isinstance(value, bool) else None
    except (ValueError, TypeError, OverflowError):
        return None


def issue(result, code, severity, message):
    result['issues'].append(dict(code=code, severity=severity, message=message))


def finish(result):
    issues = result['issues']
    critical = sum(i['severity'] == 'CRITICAL' for i in issues)
    warnings = sum(i['severity'] == 'WARNING' for i in issues)
    excluded_codes = {'MISSING_SESSION', 'UNEXPECTED_SESSION'}
    excluded = critical or any(i['code'] in excluded_codes for i in issues)
    if 'date' in result:
        for flag in ('missing_flag', 'duplicate_flag', 'invalid_ohlc_flag', 'stale_flag',
                     'outlier_flag', 'corporate_action_flag', 'zero_volume_flag'):
            result.setdefault(flag, False)
    result.update(
        is_valid=not excluded, issue_count=len(issues), critical_issue_count=critical,
        quality_status='CRITICAL' if critical else 'WARNING' if warnings else 'HEALTHY',
        quality_score=max(0, 100 - 50 * critical - 10 * warnings),
        exclusion_reason='; '.join(i['code'] for i in issues if i['severity'] == 'CRITICAL' or i['code'] in excluded_codes) or None,
    )
    return result


def validate_ohlcv(instrument_key, records, sessions, *, corporate_actions=(),
                   stale_sessions=5, critical_missing_streak=10, gap_threshold=0.3,
                   action_tolerance=0.1, confirmed_market_moves=()):
    """Validate one daily series; sessions must already reflect listing eligibility."""
    parsed_sessions = set(as_date(d) for d in sessions)
    if None in parsed_sessions:
        raise ValueError('Sessions must contain valid dates')
    expected = sorted(parsed_sessions)
    if stale_sessions < 2 or critical_missing_streak < 2 or not 0 < gap_threshold <= 10:
        raise ValueError('Invalid validation thresholds')
    grouped = defaultdict(list)
    results = []
    for index, record in enumerate(records):
        day = as_date(record.get('date'))
        if day is None:
            result = dict(instrument_key=instrument_key, date=None, source_row=index, issues=[])
            issue(result, 'INVALID_DATE', 'CRITICAL', 'Missing or invalid candle date')
            results.append(finish(result))
        else:
            grouped[day].append(record)
    action_dates = {as_date(a.get('ex_date')) for a in corporate_actions
                    if a.get('instrument_key') == instrument_key and a.get('action_type')
                    and as_date(a.get('ex_date')) is not None}
    action_report = validate_records('corporate_actions', list(corporate_actions))
    valid_actions = defaultdict(list)
    for action, checked in zip(corporate_actions, action_report['rows']):
        if checked['is_valid'] and action.get('instrument_key') == instrument_key:
            valid_actions[as_date(action.get('ex_date'))].append(action)
    confirmed = {as_date(d) for d in confirmed_market_moves}
    expected_set = set(expected)
    previous = None
    stale_run = missing_run = largest_missing = 0
    for day in sorted(expected_set | set(grouped)):
        rows = grouped.get(day, [])
        result = dict(instrument_key=instrument_key, date=day.isoformat(), issues=[],
                      missing_flag=not rows, duplicate_flag=len(rows) > 1,
                      invalid_ohlc_flag=False, stale_flag=False, outlier_flag=False,
                      corporate_action_flag=day in action_dates, zero_volume_flag=False,
                      duplicate_rows=max(0, len(rows) - 1))
        if day not in expected_set:
            issue(result, 'UNEXPECTED_SESSION', 'WARNING', 'Candle outside eligible trading sessions')
        if not rows:
            missing_run += 1
            largest_missing = max(largest_missing, missing_run)
            issue(result, 'MISSING_SESSION', 'WARNING', 'Expected daily candle is missing')
            previous, stale_run = None, 0
        else:
            if day in expected_set:
                missing_run = 0
            if len(rows) > 1:
                issue(result, 'DUPLICATE', 'CRITICAL', 'Multiple candles for instrument and date')
            for row in rows:
                if row.get('instrument_key', instrument_key) != instrument_key:
                    issue(result, 'INSTRUMENT_MISMATCH', 'CRITICAL', 'Candle belongs to another instrument')
                prices = [number(row.get(k)) for k in ('open', 'high', 'low', 'close')]
                if any(p is None or p <= 0 for p in prices) or not (
                    prices[1] >= max(prices) and prices[2] <= min(prices)
                ):
                    result['invalid_ohlc_flag'] = True
                volume = number(row.get('volume'))
                if volume is None or volume < 0:
                    issue(result, 'INVALID_VOLUME', 'CRITICAL', 'Volume must be finite and nonnegative')
                elif volume == 0:
                    result['zero_volume_flag'] = True
            if result['invalid_ohlc_flag']:
                issue(result, 'INVALID_OHLC', 'CRITICAL', 'Prices must be positive, finite and obey high/low bounds')
            if result['zero_volume_flag']:
                issue(result, 'ZERO_VOLUME', 'WARNING', 'No reported trading volume')
            row = rows[0]
            if not any(i['severity'] == 'CRITICAL' for i in result['issues']) and day in expected_set:
                close = number(row.get('close'))
                stale_run = stale_run + 1 if previous and close == previous['close'] else 1
                if stale_run >= stale_sessions:
                    result['stale_flag'] = True
                    issue(result, 'STALE_PRICE', 'WARNING', 'Close unchanged for configured consecutive sessions')
                if previous:
                    if row.get('trading_symbol') != previous['symbol']:
                        issue(result, 'SYMBOL_CHANGE', 'WARNING', 'Symbol changed; verify reference history')
                    if abs(close / previous['close'] - 1) >= gap_threshold:
                        result['outlier_flag'] = True
                        factor = 1.0
                        explained = False
                        for action in valid_actions[day]:
                            kind = action_type(action.get('action_type'))
                            if kind in {'split', 'reverse_split', 'bonus', 'rights_issue'}:
                                factor *= number(action.get('adjustment_factor'))
                                explained = True
                            elif kind == 'dividend' and number(action.get('amount')) is not None:
                                factor -= number(action['amount']) / previous['close']
                                explained = True
                        explained = explained and len(valid_actions[day]) == 1 and factor > 0 and abs(close / (previous['close'] * factor) - 1) <= action_tolerance
                        code = 'CORPORATE_ACTION_MOVE' if explained else 'CONFIRMED_MARKET_MOVE' if day in confirmed else 'UNEXPLAINED_MOVE'
                        result['move_classification'] = code
                        issue(result, code, 'INFO' if explained or day in confirmed else 'WARNING',
                              'Move matches validated action factors' if explained else
                              'Caller supplied verified market-move evidence' if day in confirmed else
                              'Large move requires review; action date alone is insufficient evidence')
                previous = dict(close=close, symbol=row.get('trading_symbol'))
            elif day in expected_set:
                previous, stale_run = None, 0
        results.append(result)
    # Mark every member of a long missing run, not just its final candle.
    run = []
    for result in [r for r in results if as_date(r['date']) in expected_set] + [{'missing_flag': False}]:
        if result.get('missing_flag'):
            run.append(result)
        else:
            if len(run) >= critical_missing_streak:
                for missing in run:
                    missing['issues'][0]['severity'] = 'CRITICAL'
            run = []
    results = [finish(r) for r in results]
    eligible = [r for r in results if as_date(r['date']) in expected_set]
    available = sum(not r['missing_flag'] for r in eligible)
    valid = [r['date'] for r in eligible if not r['missing_flag'] and r['is_valid']]
    critical = sum(r['critical_issue_count'] for r in results)
    summary = dict(instrument_key=instrument_key, expected_sessions=len(expected),
                   available_sessions=available, missing_sessions=len(expected) - available,
                   coverage_pct=round(100 * available / len(expected), 2) if expected else None,
                   duplicate_count=sum(r.get('duplicate_rows', 0) for r in results),
                   invalid_ohlc_count=sum(r.get('invalid_ohlc_flag', False) for r in results),
                   zero_volume_count=sum(r.get('zero_volume_flag', False) for r in results),
                   stale_price_days=sum(r.get('stale_flag', False) for r in results),
                   largest_missing_streak=largest_missing, latest_valid_date=max(valid) if valid else None,
                   data_quality_score=round(sum(r['quality_score'] for r in results) / len(results), 2) if results else 0,
                   data_quality_status='CRITICAL' if critical else 'WARNING' if any(r['quality_status'] == 'WARNING' for r in results) else 'HEALTHY' if expected else 'NO_DATA',
                   latest_data_status=eligible[-1]['quality_status'] if eligible else 'NO_DATA')
    return dict(summary=summary, rows=results)


def validate_records(dataset, records, *, reference=None, as_of=None, expected_periods=(), ratio_bounds=None):
    """Validate normalized auxiliary records without interpreting vendor JSON."""
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    seen = {}
    currencies = defaultdict(set)
    periods = defaultdict(set)
    results = []
    revisions = defaultdict(list)
    for index, row in enumerate(records):
        key = row.get('instrument_key')
        result = dict(source_row=index, instrument_key=key, issues=[])
        if not key or (reference is not None and key not in reference):
            issue(result, 'UNKNOWN_INSTRUMENT', 'CRITICAL', 'Instrument missing or absent from supplied reference')
        elif reference is not None and row.get('trading_symbol') and reference[key] != row['trading_symbol']:
            issue(result, 'TICKER_MISMATCH', 'CRITICAL', 'Ticker does not match supplied reference')
        identity = None
        if dataset == 'news':
            identity = (key, row.get('url')) if row.get('url') else (key, row.get('title'), row.get('published_at'))
            try:
                timestamp = datetime.fromisoformat(str(row.get('published_at')).replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    issue(result, 'TIMESTAMP_TIMEZONE', 'WARNING', 'Naive timestamp interpreted as UTC')
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                if timestamp > now:
                    issue(result, 'FUTURE_TIMESTAMP', 'CRITICAL', 'Publication is after validation time')
            except (ValueError, TypeError):
                issue(result, 'INVALID_TIMESTAMP', 'CRITICAL', 'Missing or invalid publication timestamp')
            if not all(isinstance(row.get(field), str) and row[field].strip() for field in ('source', 'title')):
                issue(result, 'BAD_SOURCE_RECORD', 'CRITICAL', 'News needs a source and title')
        elif dataset == 'corporate_actions':
            ex = as_date(row.get('ex_date'))
            kind = action_type(row.get('action_type'))
            identity = (key, kind, ex)
            record = as_date(row.get('record_date'))
            if ex is None or (record and record < ex) or not row.get('action_type'):
                issue(result, 'INVALID_ACTION', 'CRITICAL', 'Check action type, ex-date and record-date ordering')
            for field in ('record_date', 'effective_date', 'announcement_date'):
                if row.get(field) is not None and as_date(row[field]) is None:
                    issue(result, 'INVALID_ACTION_DATE', 'CRITICAL', f'Malformed {field}')
            announced = as_date(row.get('announcement_date'))
            effective = as_date(row.get('effective_date'))
            if (announced and ex and announced > ex) or (effective and announced and effective < announced):
                issue(result, 'ACTION_DATE_ORDER', 'CRITICAL', 'Action dates contradict announcement ordering')
            if kind in {'split', 'reverse_split', 'bonus', 'rights_issue'}:
                factor = number(row.get('adjustment_factor'))
                if factor is None or factor <= 0:
                    issue(result, 'MISSING_ADJUSTMENT_FACTOR', 'CRITICAL', 'Action requires a positive adjustment factor')
                elif (kind in {'split', 'bonus'} and factor >= 1) or (kind == 'reverse_split' and factor <= 1):
                    issue(result, 'INVALID_ADJUSTMENT_FACTOR', 'CRITICAL', 'Factor direction contradicts action type')
            if kind == 'dividend' and (number(row.get('amount')) is None or number(row['amount']) < 0):
                issue(result, 'INVALID_DIVIDEND', 'CRITICAL', 'Dividend requires a nonnegative amount')
            if identity in seen and records[seen[identity]].get('adjustment_factor') != row.get('adjustment_factor'):
                issue(result, 'CONFLICTING_ACTION', 'CRITICAL', 'Same action has different adjustment factors')
        elif dataset == 'fundamentals':
            period = as_date(row.get('period_end'))
            report = as_date(row.get('report_date'))
            group = (key, row.get('statement_type'), row.get('period_type'))
            identity = (*group, period, row.get('revision', 0))
            revision = row.get('revision', 0)
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
                issue(result, 'INVALID_REVISION', 'CRITICAL', 'Revision must be a nonnegative integer')
            else:
                revisions[(*group, period)].append((revision, report, result))
            if period is None or report is None or report < period or report > now.date():
                issue(result, 'REPORT_DATE_ORDER', 'CRITICAL', 'Require period end <= report date <= as-of date')
            periods[group].add(period)
            currency = row.get('currency')
            if not currency:
                issue(result, 'MISSING_CURRENCY', 'WARNING', 'Currency is required to compare financial values')
            else:
                currencies[group].add(currency)
                if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or not currency.isupper():
                    issue(result, 'INVALID_CURRENCY', 'CRITICAL', 'Currency must be a three-letter uppercase code')
            for field, value in row.get('ratios', {}).items():
                numeric = number(value)
                if numeric is None or (field.endswith('_holding_pct') and not 0 <= numeric <= 100):
                    issue(result, 'INVALID_RATIO', 'CRITICAL', f'Invalid ratio: {field}')
                bounds = (ratio_bounds or {}).get(field)
                if bounds and numeric is not None and ((bounds[0] is not None and numeric < bounds[0]) or (bounds[1] is not None and numeric > bounds[1])):
                    issue(result, 'RATIO_OUT_OF_BOUNDS', 'CRITICAL', f'{field} outside configured domain bounds')
                if field in {'current_ratio', 'quick_ratio', 'cash_ratio', 'dividend_yield'} and numeric is not None and numeric < 0:
                    issue(result, 'INVALID_RATIO', 'CRITICAL', f'{field} cannot be negative')
            holdings = [number(v) for k, v in row.get('ratios', {}).items() if k.endswith('_holding_pct')]
            if len(holdings) > 1 and all(v is not None and 0 <= v <= 100 for v in holdings) and sum(holdings) > 100.01:
                issue(result, 'HOLDINGS_TOTAL', 'CRITICAL', 'Mutually exclusive holding percentages exceed 100')
            if row.get('revision', 0):
                issue(result, 'RESTATEMENT', 'INFO', 'Retain revision and its report date for point-in-time use')
        elif dataset == 'reference':
            identity = (key,)
            if not row.get('trading_symbol') or not row.get('exchange'):
                issue(result, 'INCOMPLETE_REFERENCE', 'CRITICAL', 'Reference needs a symbol and exchange')
            listing, delisting = as_date(row.get('listing_date')), as_date(row.get('delisting_date'))
            if (row.get('listing_date') and listing is None) or (row.get('delisting_date') and delisting is None):
                issue(result, 'INVALID_REFERENCE_DATE', 'CRITICAL', 'Invalid listing or delisting date')
            if listing and delisting and delisting < listing:
                issue(result, 'REFERENCE_DATE_ORDER', 'CRITICAL', 'Delisting predates listing')
        else:
            raise ValueError('Unsupported dataset')
        if identity in seen:
            issue(result, 'DUPLICATE', 'CRITICAL', 'Duplicate logical record')
            original = results[seen[identity]]
            if not any(i['code'] == 'DUPLICATE' for i in original['issues']):
                issue(original, 'DUPLICATE', 'CRITICAL', 'Duplicate logical record')
        else:
            seen[identity] = index
        results.append(result)
    if dataset == 'fundamentals':
        for versions in revisions.values():
            ordered = sorted(versions, key=lambda value: value[0])
            for previous, current in zip(ordered, ordered[1:]):
                if current[0] > previous[0] and current[1] and previous[1] and current[1] < previous[1]:
                    issue(current[2], 'RESTATEMENT_DATE_ORDER', 'CRITICAL', 'Revision cannot be published before its predecessor')
        for row, result in zip(records, results):
            group = (row.get('instrument_key'), row.get('statement_type'), row.get('period_type'))
            if len(currencies[group]) > 1:
                issue(result, 'CURRENCY_CHANGE', 'WARNING', 'Currency differs across this financial series')
            observed = {p for p in periods[group] if p is not None}
            inferred = fiscal_periods(min(observed), max(observed), group[2]) if observed else set()
            missing = (set(map(as_date, expected_periods)) | inferred) - periods[group]
            if missing:
                issue(result, 'MISSING_FISCAL_PERIODS', 'WARNING', 'Missing expected fiscal periods: ' + ', '.join(str(p) for p in sorted(missing)))
    results = [finish(r) for r in results]
    return dict(dataset=dataset, rows=results, summary=dict(
        record_count=len(results), invalid_records=sum(not r['is_valid'] for r in results),
        issue_count=sum(r['issue_count'] for r in results),
        critical_issue_count=sum(r['critical_issue_count'] for r in results)))


def require_quality(report):
    """Fail closed at a research boundary; warnings with actual records remain usable."""
    if report.get('calendar_verified') is False:
        raise ValueError('Research blocked: supply authoritative eligible sessions to verify the calendar')
    if not report.get('rows') or any(not row['is_valid'] for row in report['rows']):
        raise ValueError('Research blocked: data quality report contains missing or invalid records')
    return report
