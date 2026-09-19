"""Futures basis, option-chain volatility, positioning and quality metrics."""
from collections import defaultdict
from math import erf, exp, log, pi, sqrt
from statistics import fmean, pstdev

from app.engines.derivatives.derivatives_schema import DerivativesRequest

VERSION = '1'


def _cdf(value): return .5*(1+erf(value/sqrt(2)))
def _pdf(value): return exp(-value*value/2)/sqrt(2*pi)


def _option_price(spot, strike, years, rate, dividend, volatility, option_type):
    if years <= 0 or volatility <= 0: return max(0, spot-strike) if option_type == 'CALL' else max(0, strike-spot)
    d1 = (log(spot/strike)+(rate-dividend+.5*volatility**2)*years)/(volatility*sqrt(years))
    d2 = d1-volatility*sqrt(years)
    if option_type == 'CALL':
        return spot*exp(-dividend*years)*_cdf(d1)-strike*exp(-rate*years)*_cdf(d2)
    return strike*exp(-rate*years)*_cdf(-d2)-spot*exp(-dividend*years)*_cdf(-d1)


def _implied_volatility(price, spot, strike, years, rate, dividend, option_type):
    intrinsic = max(0, spot-strike) if option_type == 'CALL' else max(0, strike-spot)
    if price is None or price < intrinsic or years <= 0: return None
    low, high = 1e-4, 5.0
    if _option_price(spot, strike, years, rate, dividend, high, option_type) < price: return None
    for _ in range(80):
        middle = (low+high)/2
        if _option_price(spot, strike, years, rate, dividend, middle, option_type) < price: low = middle
        else: high = middle
    return (low+high)/2


def _greeks(spot, strike, years, rate, dividend, volatility, option_type):
    if years <= 0 or not volatility: return {}
    root = sqrt(years)
    d1 = (log(spot/strike)+(rate-dividend+.5*volatility**2)*years)/(volatility*root)
    d2 = d1-volatility*root
    discount_q, discount_r = exp(-dividend*years), exp(-rate*years)
    delta = discount_q*_cdf(d1) if option_type == 'CALL' else discount_q*(_cdf(d1)-1)
    gamma = discount_q*_pdf(d1)/(spot*volatility*root)
    vega = spot*discount_q*_pdf(d1)*root/100
    common = -spot*discount_q*_pdf(d1)*volatility/(2*root)
    if option_type == 'CALL':
        theta = (common-rate*strike*discount_r*_cdf(d2)+dividend*spot*discount_q*_cdf(d1))/365
        rho = strike*years*discount_r*_cdf(d2)/100
    else:
        theta = (common+rate*strike*discount_r*_cdf(-d2)-dividend*spot*discount_q*_cdf(-d1))/365
        rho = -strike*years*discount_r*_cdf(-d2)/100
    return dict(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)


def _z(values, value):
    if len(values) < 2: return None
    deviation = pstdev(values)
    return (value-fmean(values))/deviation if deviation else 0.0


def _percentile(values, value):
    if len(values) < 2: return None
    below, tied = sum(item < value for item in values), sum(item == value for item in values)
    return 100*(below+(tied-1)/2)/(len(values)-1)


def _futures_rows(request):
    histories = defaultdict(list)
    by_curve = defaultdict(list)
    output = []
    for quote in sorted(request.futures, key=lambda row: (row.date, row.underlying_key, row.expiry)):
        years = max(0, (quote.expiry-quote.date).days/365.25)
        basis = quote.futures_price-quote.spot_price
        basis_pct = quote.futures_price/quote.spot_price-1
        theoretical = quote.spot_price*exp((quote.risk_free_rate-quote.dividend_yield)*years)
        history = histories[(quote.instrument_key, quote.expiry)]
        previous = history[-1] if history else None
        price_change = quote.futures_price-previous.futures_price if previous else None
        oi_change = quote.open_interest-previous.open_interest if previous else None
        oi_change_pct = oi_change/previous.open_interest if oi_change is not None and previous.open_interest else None
        state = None
        if price_change is not None and oi_change is not None:
            state = ('LONG_BUILDUP' if price_change >= 0 and oi_change >= 0 else
                     'SHORT_BUILDUP' if price_change < 0 <= oi_change else
                     'SHORT_COVERING' if price_change >= 0 > oi_change else 'LONG_UNWINDING')
        past_oi = [row.open_interest for row in history[-59:]]+[quote.open_interest]
        past_volume = [row.volume for row in history[-19:]]+[quote.volume]
        spread = quote.ask-quote.bid if quote.ask is not None and quote.bid is not None else None
        spread_pct = spread/((quote.ask+quote.bid)/2) if spread is not None and quote.ask+quote.bid else None
        quote_age = max(0, (quote.available_at-quote.quote_timestamp).total_seconds())
        stale = quote_age > request.max_quote_age_seconds
        quality = ('STALE_QUOTES' if stale else 'WIDE_SPREAD' if spread_pct is not None and spread_pct > request.max_spread_pct else
                   'LOW_LIQUIDITY' if quote.volume <= 0 else 'VALID')
        row = dict(instrument_key=quote.instrument_key, underlying_key=quote.underlying_key,
            date=quote.date.isoformat(), expiry=quote.expiry.isoformat(), quote_timestamp=quote.quote_timestamp.isoformat(),
            available_at=quote.available_at.isoformat(), spot_price=quote.spot_price, futures_price=quote.futures_price,
            futures_basis=basis, basis_pct=basis_pct,
            annualized_basis=basis_pct/years if years > 0 else None,
            theoretical_futures_price=theoretical, fair_value_basis=theoretical-quote.spot_price,
            basis_deviation=quote.futures_price-theoretical,
            basis_state='PREMIUM' if basis_pct > request.fair_basis_tolerance else ('DISCOUNT' if basis_pct < -request.fair_basis_tolerance else 'FAIR'),
            open_interest=quote.open_interest, oi_change=oi_change, oi_change_pct=oi_change_pct,
            oi_z_60d=_z(past_oi, quote.open_interest), oi_percentile_252d=_percentile([r.open_interest for r in history[-251:]]+[quote.open_interest], quote.open_interest),
            futures_volume=quote.volume, avg_futures_volume_20d=fmean(past_volume),
            futures_volume_z_20d=_z(past_volume, quote.volume), oi_volume_ratio=quote.open_interest/quote.volume if quote.volume else None,
            futures_position_state=state, oi_price_state=state, bid_ask_spread=spread,
            bid_ask_spread_pct=spread_pct, quote_age_seconds=quote_age, stale_quote_flag=stale,
            futures_liquidity_score=max(0, min(100, 100-(spread_pct or 0)*500)) if quote.volume > 0 else 0,
            days_to_expiry=(quote.expiry-quote.date).days, adjustment_version=quote.adjustment_version,
            futures_positioning_score=None, derivatives_quality_status=quality)
        history.append(quote); output.append(row); by_curve[(quote.date, quote.underlying_key)].append(row)
    for rows in by_curve.values():
        rows.sort(key=lambda row: row['expiry'])
        curve = 'FLAT'
        if len(rows) >= 2:
            curve = 'CONTANGO' if rows[-1]['futures_price'] > rows[0]['futures_price'] else 'BACKWARDATION'
        total_near = sum(row['open_interest'] for row in rows[:2])
        rollover = rows[1]['open_interest']/total_near if len(rows) >= 2 and total_near else None
        roll_cost = rows[1]['futures_price']-rows[0]['futures_price'] if len(rows) >= 2 else None
        slope = rows[-1]['futures_basis']-rows[0]['futures_basis'] if len(rows) >= 2 else None
        for row in rows:
            row.update(futures_term_structure=curve, rollover_ratio=rollover,
                       rollover_cost=roll_cost, rollover_cost_pct=roll_cost/rows[0]['futures_price'] if roll_cost is not None else None,
                       futures_curve_slope=slope)
            basis_component = max(-1, min(1, row['basis_pct']*100))
            oi_component = 0 if row['oi_change_pct'] is None else max(-1, min(1, row['oi_change_pct']))
            row['futures_positioning_score'] = 50+25*basis_component+25*oi_component
    return output


def _option_contracts(request):
    output = []
    for quote in sorted(request.options, key=lambda row: (row.date, row.underlying_key, row.expiry, row.strike, row.option_type)):
        days = (quote.expiry-quote.date).days
        years = days/365.25
        mid = ((quote.bid+quote.ask)/2 if quote.bid is not None and quote.ask is not None else quote.last_price)
        spread_pct = ((quote.ask-quote.bid)/mid if quote.bid is not None and quote.ask is not None and mid else None)
        quote_age = max(0, (quote.available_at-quote.quote_timestamp).total_seconds())
        stale = quote_age > request.max_quote_age_seconds
        liquid = (quote.open_interest or 0) >= request.minimum_option_oi and (spread_pct is None or spread_pct <= request.max_spread_pct) and not stale
        iv = quote.implied_volatility
        iv_source = 'SUPPLIED' if iv is not None else None
        if iv is None and quote.exercise_style == 'EUROPEAN' and liquid:
            iv = _implied_volatility(mid, quote.spot_price, quote.strike, years, quote.risk_free_rate, quote.dividend_yield, quote.option_type)
            iv_source = 'BLACK_SCHOLES_SOLVED' if iv is not None else None
        calculated = _greeks(quote.spot_price, quote.strike, years, quote.risk_free_rate, quote.dividend_yield, iv, quote.option_type)
        greek_values = {name: getattr(quote, name) if getattr(quote, name) is not None else calculated.get(name)
                        for name in ('delta', 'gamma', 'theta', 'vega', 'rho')}
        ratio = quote.strike/quote.spot_price
        tolerance = .01
        moneyness = ('ATM' if abs(ratio-1) <= tolerance else
                     'ITM' if (quote.option_type == 'CALL' and ratio < 1) or (quote.option_type == 'PUT' and ratio > 1) else 'OTM')
        reasons = []
        if stale: reasons.append('STALE_QUOTES')
        if spread_pct is not None and spread_pct > request.max_spread_pct: reasons.append('WIDE_SPREAD')
        if (quote.open_interest or 0) < request.minimum_option_oi: reasons.append('LOW_LIQUIDITY')
        if iv is None: reasons.append('MISSING_IV')
        if any(value is None for value in greek_values.values()): reasons.append('MISSING_GREEKS')
        output.append(dict(contract_key=quote.contract_key, underlying_key=quote.underlying_key,
            date=quote.date.isoformat(), expiry=quote.expiry.isoformat(), strike=quote.strike,
            option_type=quote.option_type, quote_timestamp=quote.quote_timestamp.isoformat(),
            available_at=quote.available_at.isoformat(), spot_price=quote.spot_price,
            bid=quote.bid, ask=quote.ask, last_price=quote.last_price, mark_price=mid,
            bid_ask_spread_pct=spread_pct, volume=quote.volume, open_interest=quote.open_interest,
            implied_volatility=iv, iv_source=iv_source, pricing_model='BLACK_SCHOLES' if iv_source == 'BLACK_SCHOLES_SOLVED' else None,
            risk_free_rate=quote.risk_free_rate, dividend_yield=quote.dividend_yield,
            exercise_style=quote.exercise_style, moneyness=ratio, moneyness_state=moneyness,
            days_to_expiry=days, time_to_expiry_years=years, quote_age_seconds=quote_age, stale_quote_flag=stale,
            liquid_for_summary=liquid and iv is not None, quality_status=reasons[0] if reasons else 'VALID',
            quality_reasons=reasons, contract_multiplier=quote.contract_multiplier, **greek_values))
    return output


def _max_pain(contracts):
    strikes = sorted(set(row['strike'] for row in contracts))
    if not strikes: return None
    payouts = {}
    for settlement in strikes:
        payouts[settlement] = sum((max(0, settlement-row['strike']) if row['option_type'] == 'CALL' else max(0, row['strike']-settlement))*(row['open_interest'] or 0) for row in contracts)
    return min(strikes, key=lambda strike: payouts[strike])


def _option_summaries(request, contracts):
    groups = defaultdict(list)
    for row in contracts: groups[(row['date'], row['underlying_key'], row['expiry'])].append(row)
    atm_history = defaultdict(list); output = []
    for key in sorted(groups):
        rows = groups[key]; spot = fmean([row['spot_price'] for row in rows])
        strikes = sorted(set(row['strike'] for row in rows)); atm_strike = min(strikes, key=lambda strike: abs(strike-spot))
        atm = [row for row in rows if row['strike'] == atm_strike and row['liquid_for_summary']]
        atm_iv = fmean([row['implied_volatility'] for row in atm]) if atm else None
        days_to_expiry = rows[0]['days_to_expiry']
        tenor_bucket = 'NEAR' if days_to_expiry <= 45 else ('NEXT' if days_to_expiry <= 90 else 'FAR')
        history = atm_history[(key[1], tenor_bucket)]
        iv_values = [value for _, value in history[-251:] if value is not None]+([atm_iv] if atm_iv is not None else [])
        calls, puts = [row for row in rows if row['option_type'] == 'CALL'], [row for row in rows if row['option_type'] == 'PUT']
        call_oi, put_oi = sum(row['open_interest'] or 0 for row in calls), sum(row['open_interest'] or 0 for row in puts)
        call_volume, put_volume = sum(row['volume'] or 0 for row in calls), sum(row['volume'] or 0 for row in puts)
        atm_call = next((row for row in calls if row['strike'] == atm_strike), None)
        atm_put = next((row for row in puts if row['strike'] == atm_strike), None)
        straddle = ((atm_call['mark_price'] or 0)+(atm_put['mark_price'] or 0)) if atm_call and atm_put else None
        otm_put_ivs = [row['implied_volatility'] for row in puts if row['strike'] < spot and row['liquid_for_summary']]
        put_skew = fmean(otm_put_ivs)-atm_iv if otm_put_ivs and atm_iv is not None else None
        realized = request.realized_volatility.get(key[1])
        gex = sum((1 if row['option_type'] == 'CALL' else -1)*(row['gamma'] or 0)*(row['open_interest'] or 0)*row['contract_multiplier']*spot**2 for row in rows)
        completeness = 100*sum(row['liquid_for_summary'] for row in rows)/len(rows)
        pcr_oi = put_oi/call_oi if call_oi else None; pcr_volume = put_volume/call_volume if call_volume else None
        iv_percentile = _percentile(iv_values, atm_iv) if atm_iv is not None else None
        iv_rank = ((atm_iv-min(iv_values))/(max(iv_values)-min(iv_values))*100
                   if atm_iv is not None and len(iv_values) >= 2 and max(iv_values) != min(iv_values) else None)
        option_score = 50
        components = {}
        if pcr_oi is not None: components['pcr_oi'] = max(-1, min(1, pcr_oi-1))
        if put_skew is not None: components['put_skew'] = max(-1, min(1, -put_skew*5))
        if components: option_score = 50+25*fmean(components.values())
        risk_components = []
        if iv_percentile is not None: risk_components.append(iv_percentile)
        if completeness < 50: risk_components.append(100-completeness)
        risk_score = fmean(risk_components) if risk_components else None
        output.append(dict(date=key[0], underlying_key=key[1], expiry=key[2], spot_price=spot,
            atm_strike=atm_strike, atm_iv=atm_iv, iv_percentile_252d=iv_percentile, iv_rank_252d=iv_rank,
            iv_history_tenor_bucket=tenor_bucket,
            realized_volatility=realized, iv_rv_spread=atm_iv-realized if atm_iv is not None and realized is not None else None,
            volatility_risk_premium=atm_iv-realized if atm_iv is not None and realized is not None else None,
            pcr_oi=pcr_oi, pcr_volume=pcr_volume, put_skew=put_skew,
            max_call_oi_strike=max(calls, key=lambda row: row['open_interest'] or 0)['strike'] if calls else None,
            max_put_oi_strike=max(puts, key=lambda row: row['open_interest'] or 0)['strike'] if puts else None,
            max_pain_strike=_max_pain(rows), atm_call_price=atm_call['mark_price'] if atm_call else None,
            atm_put_price=atm_put['mark_price'] if atm_put else None, atm_straddle_price=straddle,
            straddle_expected_move=straddle, expected_move_pct=straddle/spot if straddle is not None else None,
            iv_expected_move=spot*atm_iv*sqrt(max(0, rows[0]['time_to_expiry_years'])) if atm_iv is not None else None,
            aggregate_gamma_exposure=gex, gamma_exposure_assumption='CALL_POSITIVE_PUT_NEGATIVE',
            chain_completeness_score=completeness, options_positioning_score=max(0, min(100, option_score)),
            derivatives_risk_score=risk_score, option_score_components=components,
            derivatives_confidence=completeness, derivatives_quality_status='VALID' if completeness >= 80 else 'PARTIAL_CHAIN'))
        history.append((key[0], atm_iv))
    term_groups = defaultdict(list)
    for row in output: term_groups[(row['date'], row['underlying_key'])].append(row)
    for rows in term_groups.values():
        rows.sort(key=lambda row: row['expiry'])
        valid = [row for row in rows if row['atm_iv'] is not None]
        slope = valid[-1]['atm_iv']-valid[0]['atm_iv'] if len(valid) >= 2 else None
        state = ('NORMAL' if slope is not None and slope > .005 else
                 'INVERTED' if slope is not None and slope < -.005 else 'FLAT' if slope is not None else 'INSUFFICIENT_EXPIRIES')
        for row in rows:
            row['iv_term_structure_slope'] = slope
            row['iv_term_structure_state'] = state
    return output


def calculate_derivatives(request: DerivativesRequest):
    futures = _futures_rows(request)
    contracts = _option_contracts(request)
    summaries = _option_summaries(request, contracts)
    futures_lookup = defaultdict(list)
    for row in futures: futures_lookup[(row['date'], row['underlying_key'])].append(row)
    for summary in summaries:
        candidates = futures_lookup.get((summary['date'], summary['underlying_key']), [])
        nearest = min(candidates, key=lambda row: row['expiry']) if candidates else None
        scores = [summary['options_positioning_score']]
        if nearest and nearest['futures_positioning_score'] is not None: scores.append(nearest['futures_positioning_score'])
        summary['futures_positioning_score'] = nearest['futures_positioning_score'] if nearest else None
        summary['derivatives_sentiment_score'] = fmean(scores)
        summary['volatility_regime_score'] = summary['derivatives_risk_score']
        summary['derivatives_score'] = fmean(scores)
        summary['derivatives_score_components'] = {
            'options_positioning': summary['options_positioning_score'],
            'futures_positioning': summary['futures_positioning_score'],
        }
    return dict(version=VERSION, snapshot_id=request.snapshot_id, as_of=request.as_of.isoformat(),
                futures=futures, option_contracts=contracts, option_summaries=summaries)
