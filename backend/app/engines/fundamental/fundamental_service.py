"""Deterministic point-in-time fundamental metrics from normalized statements."""
from collections import defaultdict
from statistics import fmean, pstdev

from app.engines.fundamental.fundamental_schema import FundamentalRequest

VERSION = '1'
FLOW_FIELDS = ('revenue', 'gross_profit', 'ebitda', 'ebit', 'net_income', 'eps',
               'operating_cash_flow', 'capital_expenditure', 'free_cash_flow',
               'interest_expense', 'tax_expense', 'profit_before_tax')


def ratio(numerator, denominator, *, positive_denominator=False):
    if numerator is None or denominator is None or denominator == 0:
        return None
    if positive_denominator and denominator <= 0:
        return None
    return numerator / denominator


def total(values):
    return sum(values) if values and all(value is not None for value in values) else None


def growth(current, previous):
    # Percentage growth is not meaningful across zero or a sign change.
    if current is None or previous is None or previous == 0 or current * previous <= 0:
        return None
    return current / previous - 1


def cagr(current, previous, years):
    if current is None or previous is None or current <= 0 or previous <= 0:
        return None
    return (current / previous) ** (1 / years) - 1


def average(a, b):
    return (a + b) / 2 if a is not None and b is not None else (a if a is not None else b)


def trend(current, previous, tolerance):
    if current is None or previous is None:
        return 'INSUFFICIENT_DATA'
    scale = max(abs(previous), 1e-12)
    change = (current - previous) / scale
    return 'IMPROVING' if change > tolerance else ('DETERIORATING' if change < -tolerance else 'STABLE')


def lower_is_better_trend(current, previous, tolerance):
    value = trend(current, previous, tolerance)
    return {'IMPROVING': 'DETERIORATING', 'DETERIORATING': 'IMPROVING'}.get(value, value)


def clip_score(value):
    return None if value is None else max(0.0, min(100.0, value))


def mean_present(values):
    present = [value for value in values if value is not None]
    return fmean(present) if present else None


def standardized_score(components):
    # Component values are already mapped to an interpretable 0..100 scale.
    return clip_score(mean_present(components))


def _percentile(values, value, lower_is_better=False):
    if value is None or len(values) < 2:
        return None
    ordered = sorted(values, reverse=lower_is_better)
    below = sum(candidate < value for candidate in ordered)
    tied = sum(candidate == value for candidate in ordered)
    percentile = 100 * (below + (tied-1)/2) / (len(ordered)-1)
    return 100-percentile if lower_is_better else percentile


def _latest_versions(rows):
    versions = {}
    for row in sorted(rows, key=lambda item: (item.data_available_date, item.revision)):
        key = (row.period_end_date, row.period_type)
        versions[key] = row
    return list(versions.values())


def _ttm(quarters):
    latest = sorted(quarters, key=lambda row: row.period_end_date, reverse=True)[:4]
    if len(latest) < 4:
        return None, {}
    # Four quarters must cover roughly one year; this rejects gaps and mixed frequencies.
    if (latest[0].period_end_date - latest[-1].period_end_date).days not in range(250, 331):
        return None, {}
    return latest[0], {field: total([getattr(row, field) for row in latest]) for field in FLOW_FIELDS}


def _period_metrics(flow, balance, prior_balance=None):
    revenue, ebitda, ebit, net_income = (flow.get(name) for name in ('revenue', 'ebitda', 'ebit', 'net_income'))
    ocf, capex = flow.get('operating_cash_flow'), flow.get('capital_expenditure')
    fcf = flow.get('free_cash_flow')
    if fcf is None and ocf is not None and capex is not None:
        # Capex is accepted in either common convention (positive spend or negative outflow).
        fcf = ocf - abs(capex)
    assets = balance.total_assets
    equity = balance.shareholders_equity
    debt = balance.total_debt
    cash = balance.cash
    net_debt = debt - cash if debt is not None and cash is not None else None
    average_assets = average(assets, prior_balance.total_assets if prior_balance else None)
    average_equity = average(equity, prior_balance.shareholders_equity if prior_balance else None)
    capital_employed = assets - balance.current_liabilities if assets is not None and balance.current_liabilities is not None else None
    tax_rate = ratio(flow.get('tax_expense'), flow.get('profit_before_tax'), positive_denominator=True)
    tax_rate = max(0, min(1, tax_rate)) if tax_rate is not None else None
    nopat = ebit * (1-tax_rate) if ebit is not None and tax_rate is not None else None
    invested_capital = equity + debt - cash if equity is not None and debt is not None and cash is not None else None
    accruals = net_income - ocf if net_income is not None and ocf is not None else None
    return dict(
        **flow, free_cash_flow_ttm=fcf, net_debt=net_debt,
        ebitda_margin=ratio(ebitda, revenue), ebit_margin=ratio(ebit, revenue),
        net_margin=ratio(net_income, revenue), gross_margin=ratio(flow.get('gross_profit'), revenue),
        roe_ttm=ratio(net_income, average_equity, positive_denominator=True),
        roa_ttm=ratio(net_income, average_assets, positive_denominator=True),
        roce_ttm=ratio(ebit, capital_employed, positive_denominator=True),
        roic_ttm=ratio(nopat, invested_capital, positive_denominator=True),
        asset_turnover=ratio(revenue, average_assets, positive_denominator=True),
        debt_to_equity=ratio(debt, equity, positive_denominator=True),
        debt_to_assets=ratio(debt, assets, positive_denominator=True),
        net_debt_to_ebitda=ratio(net_debt, ebitda, positive_denominator=True),
        interest_coverage=ratio(ebit, flow.get('interest_expense'), positive_denominator=True),
        current_ratio=ratio(balance.current_assets, balance.current_liabilities, positive_denominator=True),
        quick_ratio=ratio((balance.current_assets-balance.inventory) if balance.current_assets is not None and balance.inventory is not None else None,
                          balance.current_liabilities, positive_denominator=True),
        cash_ratio=ratio(cash, balance.current_liabilities, positive_denominator=True),
        fcf_margin=ratio(fcf, revenue), cash_conversion_ratio=ratio(ocf, net_income, positive_denominator=True),
        fcf_conversion=ratio(fcf, net_income, positive_denominator=True),
        accrual_ratio=ratio(accruals, average_assets, positive_denominator=True),
    )


def _annual_metric(rows, field):
    return getattr(rows[0], field) if rows and getattr(rows[0], field) is not None else None


def _calculate_company(instrument_key, source_rows, request):
    rows = _latest_versions(source_rows)
    quarters = sorted((r for r in rows if r.period_type == 'QUARTERLY'), key=lambda r: r.period_end_date, reverse=True)
    annual = sorted((r for r in rows if r.period_type == 'ANNUAL'), key=lambda r: r.period_end_date, reverse=True)
    latest_balance, flow = _ttm(quarters)
    period_basis = 'TTM'
    if latest_balance is None and annual:
        latest_balance, flow, period_basis = annual[0], {field: getattr(annual[0], field) for field in FLOW_FIELDS}, 'ANNUAL'
    if latest_balance is None:
        latest = max(rows, key=lambda r: r.period_end_date)
        return dict(instrument_key=instrument_key, company_id=latest.company_id, as_of=request.as_of.isoformat(),
                    fundamental_valid=False, fundamental_quality_status='INSUFFICIENT_PERIODS',
                    fundamental_invalid_reason='Four complete quarters or one annual statement are required')

    prior_balance = next((r for r in rows
                          if (latest_balance.period_end_date-r.period_end_date).days >= 300), None)
    metrics = _period_metrics(flow, latest_balance, prior_balance)
    prior_flow = None
    if period_basis == 'TTM' and len(quarters) >= 8:
        _, prior_flow = _ttm(quarters[4:8])
    elif len(annual) >= 2:
        prior_flow = {field: getattr(annual[1], field) for field in FLOW_FIELDS}
    prior_metrics = _period_metrics(prior_flow, prior_balance or latest_balance) if prior_flow else {}
    for field in ('revenue', 'ebitda', 'net_income', 'eps'):
        metrics[f'{field}_growth_yoy'] = growth(metrics.get(field), prior_flow.get(field) if prior_flow else None)
    metrics['revenue_cagr_3y'] = cagr(_annual_metric(annual, 'revenue'), getattr(annual[3], 'revenue') if len(annual) > 3 else None, 3)
    metrics['eps_cagr_3y'] = cagr(_annual_metric(annual, 'eps'), getattr(annual[3], 'eps') if len(annual) > 3 else None, 3)
    for field in ('ebitda_margin', 'ebit_margin', 'net_margin'):
        metrics[f'{field}_delta'] = (metrics[field] - prior_metrics[field]) if metrics.get(field) is not None and prior_metrics.get(field) is not None else None
    tolerance = request.trend_tolerance
    metrics['profitability_trend'] = trend(mean_present([metrics.get('roe_ttm'), metrics.get('roic_ttm'), metrics.get('roce_ttm')]),
                                             mean_present([prior_metrics.get('roe_ttm'), prior_metrics.get('roic_ttm'), prior_metrics.get('roce_ttm')]), tolerance)
    metrics['margin_trend'] = trend(mean_present([metrics.get('ebitda_margin'), metrics.get('net_margin')]),
                                     mean_present([prior_metrics.get('ebitda_margin'), prior_metrics.get('net_margin')]), tolerance)
    metrics['leverage_trend'] = lower_is_better_trend(metrics.get('debt_to_equity'), prior_metrics.get('debt_to_equity'), tolerance)
    metrics['cash_flow_trend'] = trend(metrics.get('operating_cash_flow'), prior_metrics.get('operating_cash_flow'), tolerance)
    metrics['capital_efficiency_trend'] = trend(mean_present([metrics.get('roic_ttm'), metrics.get('roce_ttm')]),
                                                 mean_present([prior_metrics.get('roic_ttm'), prior_metrics.get('roce_ttm')]), tolerance)
    annual_margins = [ratio(r.net_income, r.revenue) for r in annual[:4]]
    metrics['margin_volatility_3y'] = pstdev([v for v in annual_margins if v is not None]) if len([v for v in annual_margins if v is not None]) >= 3 else None
    annual_eps = [r.eps for r in annual[:4] if r.eps is not None]
    metrics['eps_volatility_3y'] = pstdev(annual_eps) if len(annual_eps) >= 3 else None
    profitability = standardized_score([clip_score(50+200*(metrics.get(k) or 0)) if metrics.get(k) is not None else None for k in ('roe_ttm', 'roic_ttm', 'roce_ttm')])
    cash_quality = standardized_score([clip_score(50+25*(metrics.get('cash_conversion_ratio') or 0)),
                                       clip_score(50-500*(metrics.get('accrual_ratio') or 0))] if metrics.get('cash_conversion_ratio') is not None else [])
    balance_score = standardized_score([clip_score(100-25*(metrics.get('debt_to_equity') or 0)) if metrics.get('debt_to_equity') is not None else None,
                                        clip_score(25*(metrics.get('current_ratio') or 0)) if metrics.get('current_ratio') is not None else None,
                                        clip_score(10*(metrics.get('interest_coverage') or 0)) if metrics.get('interest_coverage') is not None else None])
    growth_score = standardized_score([clip_score(50+100*(metrics.get(k) or 0)) if metrics.get(k) is not None else None for k in ('revenue_growth_yoy', 'ebitda_growth_yoy', 'eps_growth_yoy')])
    stability = clip_score(100-1000*metrics['margin_volatility_3y']) if metrics['margin_volatility_3y'] is not None else None
    weights = request.score_weights.model_dump()
    score_parts = {'profitability': profitability, 'cash_quality': cash_quality,
                   'balance_sheet': balance_score, 'stability': stability}
    active = [(score_parts[name], weight) for name, weight in weights.items() if score_parts[name] is not None and weight > 0]
    quality_score = sum(value*weight for value, weight in active)/sum(weight for _, weight in active) if active else None
    age = (request.as_of-latest_balance.data_available_date).days
    missing_core = [name for name in ('revenue', 'net_income', 'total_assets', 'shareholders_equity')
                    if (metrics.get(name) if name in metrics else getattr(latest_balance, name)) is None]
    stale = age > request.stale_after_days
    status = 'STALE' if stale else ('PARTIAL' if missing_core else 'VALID')
    metrics.update(revenue_ttm=metrics.pop('revenue', None), ebitda_ttm=metrics.pop('ebitda', None),
                   ebit_ttm=metrics.pop('ebit', None), net_income_ttm=metrics.pop('net_income', None),
                   eps_ttm=metrics.pop('eps', None), operating_cash_flow_ttm=metrics.pop('operating_cash_flow', None),
                   fundamental_quality_score=quality_score, fundamental_growth_score=growth_score,
                   financial_strength_score=balance_score, earnings_quality_score=cash_quality,
                   fundamental_score=mean_present([quality_score, growth_score, balance_score, cash_quality]))
    return dict(instrument_key=instrument_key, company_id=latest_balance.company_id,
                sector=latest_balance.sector, industry=latest_balance.industry,
                as_of=request.as_of.isoformat(), period_end_date=latest_balance.period_end_date.isoformat(),
                data_available_date=latest_balance.data_available_date.isoformat(), period_type=period_basis,
                source_revision=latest_balance.revision, currency=latest_balance.currency,
                fundamental_age_days=age, fundamental_staleness_flag=stale,
                fundamental_valid=not stale and not missing_core, fundamental_quality_status=status,
                fundamental_invalid_reason=', '.join(missing_core) if missing_core else None, **metrics)


def calculate_fundamentals(request: FundamentalRequest):
    grouped = defaultdict(list)
    for row in request.statements:
        grouped[row.instrument_key].append(row)
    rows = [_calculate_company(key, grouped[key], request) for key in sorted(grouped)]
    ranking_fields = {
        'roe_ttm': 'roe_percentile', 'roic_ttm': 'roic_percentile',
        'revenue_growth_yoy': 'revenue_growth_percentile',
        'eps_growth_yoy': 'eps_growth_percentile', 'fcf_margin': 'fcf_margin_percentile',
        'debt_to_equity': 'debt_quality_percentile',
    }
    for row in rows:
        peers = [peer for peer in rows if peer.get('fundamental_valid') and
                 (peer.get('sector') == row.get('sector') if row.get('sector') else True)]
        for metric, output in ranking_fields.items():
            values = [peer.get(metric) for peer in peers if peer.get(metric) is not None]
            row[output] = _percentile(values, row.get(metric), lower_is_better=metric == 'debt_to_equity')
            row[f'sector_{output}'] = row[output] if row.get('sector') else None
    return dict(version=VERSION, snapshot_id=request.snapshot_id, as_of=request.as_of.isoformat(), rows=rows)
