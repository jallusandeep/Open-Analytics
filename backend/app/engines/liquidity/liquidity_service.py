"""Daily closing snapshots; no future observations or current master-data joins."""
from collections import defaultdict
from math import floor, isclose, isfinite, sqrt
from statistics import fmean, median, pstdev

VERSION = 'liquidity-1.1.0'

DAILY_NULL_FIELDS = (
    'daily_volume daily_traded_value traded_value_source daily_return amihud '
    'turnover_ratio free_float_turnover trade_count avg_trade_size avg_trade_value '
    'spread_abs spread_pct effective_spread effective_spread_pct quote_timestamp quote_age '
    'bid_depth_value ask_depth_value total_depth_value depth_imbalance '
    'slippage slippage_bps delivery_quantity delivery_percentage block_deal_value bulk_deal_value '
    'bid_depth_l1 ask_depth_l1 bid_depth_l5 ask_depth_l5 total_bid_depth total_ask_depth'
).split()


def divide(a, b):
    return a / b if a is not None and b is not None and b > 0 else None


def daily(observation, previous, options):
    o = observation
    if o is None or not o.quality_valid:
        return {**dict.fromkeys(DAILY_NULL_FIELDS), 'daily_volume': None, 'daily_traded_value': None, 'spread_pct': None,
                'total_depth_value': None, 'amihud': None, 'turnover_ratio': None,
                'delivery_percentage': None, 'trade_count': None, 'daily_return': None,
                'spread_available': False, 'depth_available': False,
                'quote_stale_flag': None, 'volume_valid': False, 'traded_value_valid': False,
                'spread_valid': False, 'depth_valid': False}
    value = o.traded_value if o.traded_value is not None else o.close*o.volume
    consistent = not ((o.volume == 0 and value > 0) or (o.volume > 0 and value == 0))
    value = value if consistent else None
    age = (o.observation_timestamp-o.quote_timestamp).total_seconds() if o.observation_timestamp and o.quote_timestamp else None
    fresh = age is not None and 0 <= age <= options.max_quote_age_seconds
    spread_ok = bool(fresh and o.bid_price and o.ask_price and o.ask_price >= o.bid_price)
    mid = (o.bid_price+o.ask_price)/2 if spread_ok else None
    spread = o.ask_price-o.bid_price if spread_ok else None
    bids = [(l.price, l.size) for l in o.bids] or ([(o.bid_price, o.bid_size)] if o.bid_price and o.bid_size is not None else [])
    asks = [(l.price, l.size) for l in o.asks] or ([(o.ask_price, o.ask_size)] if o.ask_price and o.ask_size is not None else [])
    depth_ok = bool(spread_ok and bids and asks and
                    all(bids[i][0] > bids[i+1][0] for i in range(len(bids)-1)) and
                    all(asks[i][0] < asks[i+1][0] for i in range(len(asks)-1)) and
                    bids[0][0] == o.bid_price and asks[0][0] == o.ask_price)
    bid_value = sum(p*s for p, s in bids) if depth_ok else None
    ask_value = sum(p*s for p, s in asks) if depth_ok else None
    ret = o.adjusted_close/previous.adjusted_close-1 if (previous and previous.quality_valid and
        previous.adjustment_valid and o.adjustment_valid and previous.adjusted_close and o.adjusted_close) else None
    result = dict(daily_volume=o.volume, daily_traded_value=value,
        traded_value_source='EXCHANGE' if o.traded_value is not None else 'CLOSE_TIMES_VOLUME',
        daily_return=ret, amihud=divide(abs(ret) if ret is not None else None, value),
        turnover_ratio=divide(value, o.market_cap), free_float_turnover=divide(value, o.free_float_market_cap),
        trade_count=o.trade_count, avg_trade_size=divide(o.volume, o.trade_count), avg_trade_value=divide(value, o.trade_count),
        spread_abs=spread, spread_pct=divide(spread, mid), spread_available=spread_ok, spread_valid=spread_ok,
        effective_spread=2*abs(o.trade_price-mid) if mid and o.trade_price else None,
        effective_spread_pct=2*abs(o.trade_price-mid)/mid if mid and o.trade_price else None,
        quote_timestamp=o.quote_timestamp.isoformat() if o.quote_timestamp else None,
        quote_age=age, quote_stale_flag=not fresh if o.quote_timestamp else None,
        bid_depth_value=bid_value, ask_depth_value=ask_value,
        total_depth_value=bid_value+ask_value if depth_ok else None,
        depth_imbalance=divide(bid_value-ask_value, bid_value+ask_value) if depth_ok else None,
        depth_available=depth_ok, depth_valid=depth_ok, volume_valid=True, traded_value_valid=consistent,
        slippage=(o.execution_price-o.reference_price)*(1 if o.side == 'BUY' else -1)
            if o.execution_price and o.reference_price else None,
        slippage_bps=(o.execution_price-o.reference_price)/o.reference_price*10000*(1 if o.side == 'BUY' else -1)
            if o.execution_price and o.reference_price else None,
        delivery_quantity=o.delivery_quantity, delivery_percentage=o.delivery_percentage,
        block_deal_value=o.block_deal_value, bulk_deal_value=o.bulk_deal_value)
    for side, levels in [('bid', bids), ('ask', asks)]:
        result[f'{side}_depth_l1'] = levels[0][1] if depth_ok else None
        result[f'{side}_depth_l5'] = sum(s for _, s in levels[:5]) if depth_ok and len(levels) >= 5 else None
        result[f'total_{side}_depth'] = sum(s for _, s in levels) if depth_ok else None
    return result


def rolling(rows, metric, window):
    values = [r.get(metric) for r in rows[-window:]]
    return values if len(values) == window and all(v is not None for v in values) else None


def calculate_liquidity(request):
    options = request.options
    inputs = {(o.instrument_key, o.date): o for o in request.observations if o.available_on <= o.date}
    membership = {(m.instrument_key, m.date): m for m in request.memberships if m.available_on <= m.date}
    result = []
    for key in request.instrument_keys:
        history, previous = [], None
        for day in request.sessions:
            if day > request.as_of:
                break
            o = inputs.get((key, day))
            member = membership.get((key, day))
            row = daily(o, previous, options)
            row.update(instrument_key=key, date=day.isoformat(), universe_id=member.universe_id if member else None,
                       sector_id=member.sector_id if member else None, size_bucket=member.size_bucket if member else None,
                       trading_status=o.trading_status if o else 'UNKNOWN')
            history.append(row)
            for metric, stem, windows in [('daily_volume', 'volume', (5, 10, 20, 60, 126, 252)),
                    ('daily_traded_value', 'traded_value', (5, 20, 60, 126, 252)),
                    ('spread_pct', 'spread_pct', (5, 20)), ('trade_count', 'trade_count', (20,)),
                    ('delivery_percentage', 'delivery_pct', (20,))]:
                for w in windows:
                    values = rolling(history, metric, w)
                    row[f'avg_{stem}_{w}d'] = fmean(values) if values else None
                    if w in (20, 60, 252):
                        row[f'median_{stem}_{w}d'] = median(values) if values else None
                    if w == 20:
                        std = pstdev(values) if values else None
                        row[f'{stem}_std_20d'] = std
                        row[f'{stem}_cv_20d'] = divide(std, fmean(values)) if values else None
                        row[f'{stem}_zscore_20d'] = divide(values[-1]-fmean(values), std) if values else None
            for w in (20, 60, 126, 252):
                values = rolling(history, 'daily_volume', w)
                row[f'traded_days_{w}d'] = sum(v > 0 for v in values) if values else None
                row[f'trading_frequency_{w}d'] = row[f'traded_days_{w}d']/w if values else None
                row[f'zero_volume_days_{w}d'] = sum(v == 0 for v in values) if values else None
                amihud = rolling(history, 'amihud', w)
                row[f'amihud_{w}d'] = fmean(amihud) if amihud else None
                row[f'amihud_illiquidity_{w}d'] = row[f'amihud_{w}d']
            row['zero_volume_ratio'] = divide(row['zero_volume_days_20d'], 20)
            row['delivery_zscore'] = row['delivery_pct_zscore_20d']
            row['spread'] = row['spread_pct']
            row['trading_frequency'] = row['trading_frequency_20d']
            for w in (5, 20, 60):
                row[f'rvol_{w}d'] = divide(row['daily_volume'], row[f'avg_volume_{w}d'])
            for w in (20, 60):
                values = rolling(history, 'turnover_ratio', w)
                row[f'turnover_{w}d'] = fmean(values) if values else None
            values = rolling(history, 'daily_traded_value', 20)
            row['turnover_velocity'] = divide(sum(values), o.free_float_market_cap) if values and o else None
            row['volume_outlier_flag'] = row['volume_zscore_20d'] is not None and abs(row['volume_zscore_20d']) >= 3
            row['abnormal_volume_flag'] = row['volume_outlier_flag']
            row['adv'] = row['avg_traded_value_20d']
            row['max_daily_order_value'] = row['adv']*options.max_participation_rate if row['adv'] is not None else None
            for pct in (1, 5, 10):
                capacity = row['adv']*pct/100 if row['adv'] is not None else None
                row[f'max_order_value_{pct}pct_adv'] = capacity
                row[f'max_position_value_{pct}pct_adv'] = capacity
            row['max_position_shares'] = floor(row['max_daily_order_value']/o.close/o.lot_size)*o.lot_size if o and o.lot_size and row['max_daily_order_value'] is not None else None
            order_value = (o.order_shares*(o.order_price or o.close) if o.order_shares is not None else o.order_value) if o else None
            row['requested_order_value'] = order_value
            row['participation_rate'] = divide(order_value, row['adv'])
            row['days_to_liquidate'] = divide(o.position_value, row['max_daily_order_value']) if o else None
            returns = rolling(history, 'daily_return', 20)
            row['estimated_price_impact'] = options.impact_coefficient*pstdev(returns)*sqrt(row['participation_rate']) if options.impact_coefficient and returns and row['participation_rate'] is not None else None
            row['expected_slippage_bps'] = (row['spread_pct']/2+row['estimated_price_impact'])*10000 if row['spread_pct'] is not None and row['estimated_price_impact'] is not None else None
            row['impact_model'] = 'CONFIGURED_SQUARE_ROOT_PROXY' if row['estimated_price_impact'] is not None else None
            trends = []
            for name, metric, direction in [('adv', 'adv', 1), ('spread', 'avg_spread_pct_20d', -1), ('depth', 'total_depth_value', 1), ('amihud', 'amihud_20d', -1)]:
                old = history[-22].get(metric) if len(history) >= 22 else None
                ratio = divide(row.get(metric), old)
                change = ratio-1 if ratio is not None else None
                row[f'{name}_change_21d'] = change
                if change is not None:
                    trends.append(change*direction)
            row['liquidity_trend'] = None if not trends else 'IMPROVING' if fmean(trends) > options.trend_threshold else 'DETERIORATING' if fmean(trends) < -options.trend_threshold else 'STABLE'
            prior = history[-2] if len(history) > 1 else {}
            shocks = []
            for metric, direction in [('daily_volume', 1), ('adv', 1), ('spread_pct', -1), ('total_depth_value', 1), ('amihud', -1), ('estimated_price_impact', -1)]:
                ratio = divide(row.get(metric), prior.get(metric))
                if ratio is not None:
                    shocks.append(ratio < options.shock_ratio if direction == 1 else ratio > 1/options.shock_ratio)
            row['liquidity_shock_flag'] = any(shocks) if shocks else None
            assess(row, o, member, options)
            result.append(row)
            previous = o
    rank_rows(result, request)
    if any(isinstance(v, float) and not isfinite(v) for r in result for v in r.values()):
        raise ArithmeticError('Inputs exceed the numerical range supported by liquidity calculations')
    return dict(calculation_version=VERSION, snapshot_id=request.snapshot_id, currency='INR',
                amihud_units='absolute fractional return per INR', rows=result)


def assess(row, o, member, options):
    reasons = []
    if o is None:
        reasons.append('MISSING_OBSERVATION')
    elif not o.quality_valid or not row['traded_value_valid']:
        reasons.append('INVALID_DATA_QUALITY')
    row['research_eligible'] = bool(member and member.research_eligible and not reasons)
    if not member or not member.research_eligible:
        reasons.append('RESEARCH_INELIGIBLE')
    row['liquidity_valid'] = row['adv'] is not None and row['traded_value_valid']
    row['liquidity_invalid_reason'] = None if row['liquidity_valid'] else 'MISSING_INVALID_OR_INSUFFICIENT_HISTORY'
    if row['adv'] is None:
        reasons.append('INSUFFICIENT_HISTORY')
    elif row['adv'] < options.min_adv:
        reasons.append('LOW_ADV')
    if row['trading_frequency_20d'] is None or row['trading_frequency_20d'] < options.min_trading_frequency:
        reasons.append('LOW_TRADING_FREQUENCY')
    if row['spread_pct'] is not None and row['spread_pct'] > options.max_spread_pct:
        reasons.append('WIDE_SPREAD')
    row['liquidity_eligible'] = not reasons
    if not o or o.trading_status != 'ACTIVE':
        reasons.append('TRADING_STATUS_NOT_ACTIVE')
    if not row['spread_available']:
        reasons.append('MISSING_OR_STALE_SPREAD')
    if options.require_depth and (row['total_depth_value'] is None or row['total_depth_value'] <= options.min_depth_value):
        reasons.append('INSUFFICIENT_DEPTH')
    for metric, threshold, missing, exceeded in (
        ('estimated_price_impact', options.max_price_impact, 'UNKNOWN_PRICE_IMPACT', 'HIGH_PRICE_IMPACT'),
        ('expected_slippage_bps', options.max_expected_slippage_bps, 'UNKNOWN_SLIPPAGE', 'HIGH_SLIPPAGE'),
        ('volume_cv_20d', options.max_volume_cv, 'UNKNOWN_VOLUME_STABILITY', 'UNSTABLE_VOLUME')):
        if threshold is not None:
            if row[metric] is None:
                reasons.append(missing)
            elif row[metric] > threshold:
                reasons.append(exceeded)
    if options.require_stable_order_book and (not o or o.order_book_stable is not True):
        reasons.append('ORDER_BOOK_STABILITY_UNCONFIRMED')
    if options.require_derivatives and (not o or o.derivatives_available is not True):
        reasons.append('DERIVATIVES_UNAVAILABLE')
    for flag in ('auction_flag', 'settlement_issue_flag', 'special_series_flag', 'trade_to_trade_flag', 'corporate_event_restriction'):
        row[flag] = getattr(o, flag) if o else None
    if o:
        if o.volume == 0:
            reasons.append('NO_TRADING_ACTIVITY')
        if options.require_depth and (row.get('bid_depth_value') == 0 or row.get('ask_depth_value') == 0):
            reasons.append('EMPTY_BOOK_SIDE')
        if o.close < options.min_price:
            reasons.append('PRICE_INELIGIBLE')
        if o.lot_size is None or o.tick_size is None:
            reasons.append('MISSING_LOT_OR_TICK')
        if o.order_shares and o.lot_size and o.order_shares % o.lot_size:
            reasons.append('INVALID_LOT_SIZE')
        if o.order_price and o.tick_size and not isclose(o.order_price/o.tick_size, round(o.order_price/o.tick_size), abs_tol=1e-7, rel_tol=0):
            reasons.append('INVALID_TICK_SIZE')
        if row['requested_order_value'] is not None and (row['participation_rate'] is None or row['participation_rate'] > options.max_participation_rate):
            reasons.append('PARTICIPATION_LIMIT')
        if o.position_value is not None and (row['days_to_liquidate'] is None or row['days_to_liquidate'] > options.max_days_to_liquidate):
            reasons.append('EXIT_CAPACITY_LIMIT')
        for flag in ('auction_flag', 'settlement_issue_flag', 'special_series_flag', 'trade_to_trade_flag', 'corporate_event_restriction'):
            row[flag] = getattr(o, flag)
            if getattr(o, flag):
                reasons.append(flag.upper())
        if options.require_short_sale and o.short_sale_available is not True:
            reasons.append('SHORT_SALE_UNAVAILABLE')
    row['upper_circuit_price'] = o.upper_circuit_price if o else None
    row['lower_circuit_price'] = o.lower_circuit_price if o else None
    row['near_upper_circuit'] = o.close >= o.upper_circuit_price*(1-options.circuit_proximity) if o and o.upper_circuit_price else None
    row['near_lower_circuit'] = o.close <= o.lower_circuit_price*(1+options.circuit_proximity) if o and o.lower_circuit_price else None
    circuit_checks = ([o.high >= o.upper_circuit_price] if o and o.upper_circuit_price else []) + ([o.low <= o.lower_circuit_price] if o and o.lower_circuit_price else [])
    row['circuit_hit_flag'] = any(circuit_checks) if circuit_checks else None
    row['circuit_risk_flag'] = bool(row['near_upper_circuit'] or row['near_lower_circuit'] or row['circuit_hit_flag']) if circuit_checks else None
    if row['circuit_risk_flag']:
        reasons.append('CIRCUIT_RISK')
    row['microcap_liquidity_warning'] = o.market_cap < options.microcap_threshold if o and o.market_cap else None
    row['execution_eligible'] = not reasons
    row['liquidity_exclusion_code'] = reasons[0] if reasons else None
    row['liquidity_exclusion_detail'] = reasons
    row['liquidity_quality_score'] = (50+25*row['spread_available']+25*row['depth_available']) if row['liquidity_valid'] else 0
    row['liquidity_quality_status'] = 'INVALID' if not row['liquidity_valid'] else 'COMPLETE' if row['spread_available'] and row['depth_available'] else 'LIMITED'


def percentile(value, values):
    return 100*(sum(v < value for v in values)+(values.count(value)-1)/2)/(len(values)-1)


def rank_rows(rows, request):
    groups = defaultdict(list)
    expected = defaultdict(set)
    for m in request.memberships:
        if m.available_on <= m.date and m.research_eligible:
            expected[(m.date.isoformat(), m.universe_id)].add(m.instrument_key)
    for row in rows:
        groups[(row['date'], row['universe_id'])].append(row)
    for identity, population in groups.items():
        complete = bool(identity[1]) and expected[identity] <= {r['instrument_key'] for r in population if r['research_eligible']}
        for component, metric, reverse in [('adv', 'adv', False), ('frequency', 'trading_frequency_20d', False), ('spread', 'spread_pct', True), ('depth', 'total_depth_value', False), ('amihud', 'amihud_20d', True), ('impact', 'estimated_price_impact', True)]:
            values = [r[metric] for r in population if r['research_eligible'] and r[metric] is not None]
            enough = complete and len(values) >= request.options.minimum_rank_count
            for r in population:
                valid = enough and r['research_eligible'] and r[metric] is not None
                p = percentile(r[metric], values) if valid else None
                r[f'{component}_percentile'] = 100-p if reverse and p is not None else p
                r[f'{component}_zscore'] = (r[metric]-fmean(values))/pstdev(values) if valid and pstdev(values) > 0 else None
        for r in population:
            weights = request.options.composite_weights
            score = sum(r[f'{k}_percentile']*v for k, v in weights.items())/sum(weights.values()) if all(r[f'{k}_percentile'] is not None for k in weights) else None
            r['liquidity_score'] = score
            r['liquidity_bucket'] = None if score is None else ('VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')[min(4, int(score/20))]
            r['tradability_score'] = score if r['execution_eligible'] else 0
            r['ranking_invalid_reason'] = 'INCOMPLETE_UNIVERSE' if not complete else 'INSUFFICIENT_COMPONENT_PEERS' if score is None else None
        for r in population:
            for field, peer_field in [('universe_liquidity_percentile', None), ('sector_liquidity_percentile', 'sector_id'), ('size_bucket_liquidity_percentile', 'size_bucket')]:
                peers = [p['liquidity_score'] for p in population if p['liquidity_score'] is not None and (peer_field is None or r[peer_field] is not None and p[peer_field] == r[peer_field])]
                r[field] = percentile(r['liquidity_score'], peers) if r['liquidity_score'] is not None and len(peers) >= request.options.minimum_rank_count else None
            r['liquidity_percentile'] = r['universe_liquidity_percentile']
