"""Daily point-in-time valuation, history comparison and peer-relative value."""
from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean, median, pstdev

from app.engines.valuation.valuation_schema import ValuationRequest

VERSION = '1'
INVALID_FUNDAMENTAL = {'INVALID', 'ERROR', 'FAILED'}


def safe_ratio(numerator, denominator, *, positive_denominator=False):
    if numerator is None or denominator is None or denominator == 0:
        return None
    if positive_denominator and denominator <= 0:
        return None
    return numerator / denominator


def percentile(values, value, higher_is_cheaper=True):
    if value is None or len(values) < 2:
        return None
    below = sum(candidate < value for candidate in values)
    tied = sum(candidate == value for candidate in values)
    result = 100 * (below + (tied-1)/2) / (len(values)-1)
    return result if higher_is_cheaper else 100-result


def robust_z(values, value):
    if value is None or len(values) < 2:
        return None
    center = median(values)
    mad = median([abs(item-center) for item in values])
    if mad:
        return (value-center)/(1.4826*mad)
    std = pstdev(values)
    return (value-center)/std if std else 0.0


def mean_present(values):
    values = [value for value in values if value is not None]
    return fmean(values) if values else None


def _base(row, stale_after_days):
    market_cap = row.market_cap or row.price*row.shares_outstanding
    preferred = row.preferred_equity or 0
    minority = row.minority_interest or 0
    complete_ev = row.total_debt is not None and row.cash is not None
    enterprise_value = (market_cap + row.total_debt + preferred + minority - row.cash) if complete_ev else None
    stale_days = (row.date-row.fundamental_available_date).days
    stale = stale_days > stale_after_days or row.fundamental_quality_status.upper() == 'STALE'
    pe = safe_ratio(market_cap, row.net_income_ttm, positive_denominator=True)
    pb = safe_ratio(market_cap, row.shareholders_equity, positive_denominator=True)
    ev_ebitda = safe_ratio(enterprise_value, row.ebitda_ttm, positive_denominator=True)
    ev_ebit = safe_ratio(enterprise_value, row.ebit_ttm, positive_denominator=True)
    ev_sales = safe_ratio(enterprise_value, row.revenue_ttm, positive_denominator=True)
    forward_pe = safe_ratio(row.price, row.forward_eps_fy1, positive_denominator=True)
    reasons = []
    if row.net_income_ttm is None:
        reasons.append('MISSING_EARNINGS')
    elif row.net_income_ttm <= 0:
        reasons.append('NEGATIVE_EARNINGS')
    if row.shareholders_equity is None:
        reasons.append('MISSING_EQUITY')
    elif row.shareholders_equity <= 0:
        reasons.append('NEGATIVE_EQUITY')
    if row.ebitda_ttm is None:
        reasons.append('MISSING_EBITDA')
    elif row.ebitda_ttm <= 0:
        reasons.append('NEGATIVE_EBITDA')
    if not complete_ev:
        reasons.append('MISSING_ENTERPRISE_VALUE_INPUT')
    if enterprise_value is not None and enterprise_value <= 0:
        reasons.append('NEGATIVE_ENTERPRISE_VALUE')
    if stale:
        reasons.append('STALE_FUNDAMENTALS')
    if row.fundamental_quality_status.upper() in INVALID_FUNDAMENTAL:
        reasons.append('INVALID_FUNDAMENTALS')
    distress = ((row.fundamental_quality_score is not None and row.fundamental_quality_score < 35) or
                (row.financial_strength_score is not None and row.financial_strength_score < 30))
    if distress:
        reasons.append('DISTRESS_RISK')
    return dict(
        instrument_key=row.instrument_key, date=row.date.isoformat(), price=row.price,
        price_available_date=row.price_available_date.isoformat(),
        fundamental_available_date=row.fundamental_available_date.isoformat(),
        shares_available_date=row.shares_available_date.isoformat(), sector=row.sector,
        industry=row.industry, size_bucket=row.size_bucket,
        shares_outstanding=row.shares_outstanding, market_cap=market_cap,
        free_float_market_cap=row.free_float_market_cap, enterprise_value=enterprise_value,
        enterprise_value_formula=('MARKET_CAP+DEBT+PREFERRED_EQUITY+MINORITY_INTEREST-CASH' if complete_ev else None),
        revenue_ttm=row.revenue_ttm, ebitda_ttm=row.ebitda_ttm, ebit_ttm=row.ebit_ttm,
        net_income_ttm=row.net_income_ttm, eps_ttm=row.eps_ttm,
        shareholders_equity=row.shareholders_equity, operating_cash_flow_ttm=row.operating_cash_flow_ttm,
        free_cash_flow_ttm=row.free_cash_flow_ttm, total_debt=row.total_debt, cash=row.cash,
        pe_ttm=pe, forward_pe_fy1=forward_pe,
        earnings_yield=safe_ratio(row.net_income_ttm, market_cap),
        price_to_book=pb, book_to_price=safe_ratio(row.shareholders_equity, market_cap),
        price_to_sales=safe_ratio(market_cap, row.revenue_ttm, positive_denominator=True),
        sales_yield=safe_ratio(row.revenue_ttm, market_cap), ev_sales=ev_sales,
        ev_ebitda=ev_ebitda, ebitda_to_ev=safe_ratio(row.ebitda_ttm, enterprise_value, positive_denominator=True),
        ev_ebit=ev_ebit, ebit_to_ev=safe_ratio(row.ebit_ttm, enterprise_value, positive_denominator=True),
        fcf_yield=safe_ratio(row.free_cash_flow_ttm, market_cap),
        ocf_yield=safe_ratio(row.operating_cash_flow_ttm, market_cap),
        dividend_yield=safe_ratio(row.dividends_per_share_ttm, row.price),
        peg=safe_ratio(pe, row.eps_growth_yoy, positive_denominator=True),
        growth_adjusted_value=(safe_ratio(row.net_income_ttm, market_cap) + row.eps_growth_yoy
                               if row.net_income_ttm is not None and row.eps_growth_yoy is not None else None),
        quality_adjusted_value=None, pe_valid=pe is not None, pb_valid=pb is not None,
        ev_ebitda_valid=ev_ebitda is not None, fcf_yield_valid=row.free_cash_flow_ttm is not None,
        days_since_fundamental_update=stale_days, valuation_staleness_flag=stale,
        distress_trap_flag=distress, valuation_quality_status='VALID' if not reasons else reasons[0],
        valuation_invalid_reason=', '.join(reasons) if reasons else None,
    )


def _history(rows, minimum):
    by_instrument = defaultdict(list)
    for row in sorted(rows, key=lambda item: (item['date'], item['instrument_key'])):
        history = by_instrument[row['instrument_key']]
        current_date = date.fromisoformat(row['date'])
        window = [prior for prior in history
                  if date.fromisoformat(prior['date']) >= current_date-timedelta(days=1827)]
        for metric, prefix, higher in (
            ('pe_ttm', 'pe', False), ('price_to_book', 'pb', False),
            ('ev_ebitda', 'ev_ebitda', False), ('fcf_yield', 'fcf_yield', True),
        ):
            values = [prior[metric] for prior in window if prior[metric] is not None]
            eligible = values + ([row[metric]] if row[metric] is not None else [])
            row[f'{prefix}_hist_percentile_5y'] = percentile(eligible, row[metric], higher) if len(eligible) >= minimum else None
            med = median(values) if values else None
            row[f'{prefix}_vs_5y_median'] = safe_ratio(row[metric], med) - 1 if row[metric] is not None and med not in (None, 0) else None
            row[f'{prefix}_hist_z'] = robust_z(eligible, row[metric]) if len(eligible) >= minimum else None
        row['history_observation_count'] = len(window)+1
        history.append(row)


def _peer_scores(rows, request):
    weights = request.value_weights.model_dump()
    metrics = list(weights)
    for day in sorted(set(row['date'] for row in rows)):
        population = [row for row in rows if row['date'] == day]
        for metric in metrics:
            values = [row[metric] for row in population if row[metric] is not None]
            for row in population:
                row[f'_{metric}_z'] = robust_z(values, row[metric])
        for row in population:
            parts = [(row[f'_{metric}_z'], weight) for metric, weight in weights.items()
                     if weight > 0 and row[f'_{metric}_z'] is not None]
            row['value_factor_score'] = (sum(value*weight for value, weight in parts)/sum(weight for _, weight in parts)) if parts else None
            if row['value_factor_score'] is not None and row['distress_trap_flag']:
                row['value_factor_score'] -= 1
            row['quality_adjusted_value'] = (row['value_factor_score'] + (row.get('fundamental_quality_score')-50)/25
                                             if row.get('fundamental_quality_score') is not None and row['value_factor_score'] is not None else None)
        valid_scores = [row['value_factor_score'] for row in population if row['value_factor_score'] is not None]
        for row in population:
            row['value_percentile'] = percentile(valid_scores, row['value_factor_score'])
            for label, field in (('sector', 'sector'), ('industry', 'industry'), ('size_peer', 'size_bucket')):
                group = [peer for peer in population if row[field] and peer[field] == row[field] and peer['value_factor_score'] is not None]
                row[f'{label}_value_percentile'] = (percentile([peer['value_factor_score'] for peer in group], row['value_factor_score'])
                                                    if len(group) >= request.minimum_peer_count else None)
            sector_yields = [peer['earnings_yield'] for peer in population if row['sector'] and peer['sector'] == row['sector'] and peer['earnings_yield'] is not None]
            row['sector_neutral_value_z'] = (robust_z(sector_yields, row['earnings_yield'])
                                             if len(sector_yields) >= request.minimum_peer_count else None)
            row['valuation_state'] = ('INSUFFICIENT_DATA' if row['value_percentile'] is None else
                                      'CHEAP' if row['value_percentile'] >= 80 else
                                      'EXPENSIVE' if row['value_percentile'] <= 20 else 'FAIR')
            for metric in metrics:
                row.pop(f'_{metric}_z', None)


def calculate_valuations(request: ValuationRequest):
    source = { (item.instrument_key, item.date): item for item in request.observations }
    rows = [_base(source[key], request.stale_after_days) for key in sorted(source, key=lambda value: (value[1], value[0]))]
    # Preserve quality inputs for explainable interaction scores.
    for row in rows:
        original = source[(row['instrument_key'], date.fromisoformat(row['date']))]
        row['fundamental_quality_score'] = original.fundamental_quality_score
        row['financial_strength_score'] = original.financial_strength_score
    _history(rows, request.minimum_history)
    _peer_scores(rows, request)
    return dict(version=VERSION, snapshot_id=request.snapshot_id, as_of=request.as_of.isoformat(), rows=rows)
