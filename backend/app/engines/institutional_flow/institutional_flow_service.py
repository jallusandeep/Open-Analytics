"""Point-in-time institutional cash flow, positioning and flow proxies."""
from collections import defaultdict
from math import tanh
from statistics import fmean, pstdev

from app.engines.institutional_flow.institutional_flow_schema import InstitutionalFlowRequest

VERSION = '1'


def _sum(rows, field, window):
    if len(rows) < window:
        return None
    values = [row[field] for row in rows[-window:] if row.get(field) is not None]
    return sum(values) if len(values) == window else None


def _mean(rows, field, window):
    value = _sum(rows, field, window)
    return value/window if value is not None else None


def _z(rows, field, window):
    values = [row[field] for row in rows[-window:] if row.get(field) is not None]
    if len(values) < 2:
        return None
    deviation = pstdev(values)
    return (values[-1]-fmean(values))/deviation if deviation else 0.0


def _percentile(rows, field, window):
    values = [row[field] for row in rows[-window:] if row.get(field) is not None]
    if len(values) < 2:
        return None
    value = values[-1]
    below, tied = sum(item < value for item in values), sum(item == value for item in values)
    return 100*(below+(tied-1)/2)/(len(values)-1)


def _corr(rows, left, right, window):
    pairs = [(row.get(left), row.get(right)) for row in rows[-window:]]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if len(pairs) < 2:
        return None
    xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
    xm, ym = fmean(xs), fmean(ys)
    denominator = (sum((x-xm)**2 for x in xs)*sum((y-ym)**2 for y in ys))**.5
    return sum((x-xm)*(y-ym) for x, y in pairs)/denominator if denominator else None


def _net(row, prefix):
    supplied = getattr(row, f'{prefix}_net')
    if supplied is not None:
        return supplied
    buy, sell = getattr(row, f'{prefix}_gross_buy'), getattr(row, f'{prefix}_gross_sell')
    return buy-sell if buy is not None and sell is not None else None


def _sign_state(fii, dii):
    if fii is None or dii is None:
        return 'PARTIAL'
    if fii == 0 and dii == 0:
        return 'MIXED_LOW_INTENSITY'
    return f"FII_{'BUY' if fii > 0 else 'SELL'}_DII_{'BUY' if dii > 0 else 'SELL'}"


def _regime(z, rolling):
    if z is None or rolling is None:
        return 'INSUFFICIENT_HISTORY'
    if z >= 1.5 and rolling > 0: return 'STRONG_FOREIGN_ACCUMULATION'
    if z >= .5 and rolling > 0: return 'FOREIGN_ACCUMULATION'
    if z <= -1.5 and rolling < 0: return 'STRONG_FOREIGN_DISTRIBUTION'
    if z <= -.5 and rolling < 0: return 'FOREIGN_DISTRIBUTION'
    return 'NEUTRAL'


def _score(z, momentum, scale, clip):
    if z is None:
        return None
    momentum_component = max(-1, min(1, momentum/scale)) if momentum is not None and scale else 0
    return max(0, min(100, 50+15*max(-clip, min(clip, z))+10*momentum_component))


def _market_rows(request):
    output = []
    for evaluation in request.evaluations:
        versions = {}
        for item in request.market_observations:
            if item.source_date <= evaluation.date and item.data_available_at <= evaluation.evaluated_at:
                current = versions.get(item.source_date)
                if current is None or (item.data_available_at, item.revision) > (current.data_available_at, current.revision):
                    versions[item.source_date] = item
        history = []
        for source_date in sorted(versions):
            item = versions[source_date]
            fii, dii = _net(item, 'fii'), _net(item, 'dii')
            index_futures = (item.fii_index_futures_long-item.fii_index_futures_short
                             if item.fii_index_futures_long is not None and item.fii_index_futures_short is not None else None)
            stock_futures = (item.fii_stock_futures_long-item.fii_stock_futures_short
                             if item.fii_stock_futures_long is not None and item.fii_stock_futures_short is not None else None)
            history.append(dict(date=source_date.isoformat(), fii_net=fii, dii_net=dii,
                                institutional_net=fii+dii if fii is not None and dii is not None else None,
                                market_return=item.market_return, index_futures=index_futures,
                                stock_futures=stock_futures, source=item))
        current = next((row for row in reversed(history) if row['date'] == evaluation.date.isoformat()), None)
        if current is None:
            output.append(dict(date=evaluation.date.isoformat(), evaluated_at=evaluation.evaluated_at.isoformat(),
                               flow_valid=False, flow_quality_status='SOURCE_MISSING', flow_invalid_reason='No published market flow observation'))
            continue
        item = current['source']
        position = history.index(current)+1
        known = history[:position]
        row = dict(date=current['date'], evaluated_at=evaluation.evaluated_at.isoformat(),
            source_date=item.source_date.isoformat(), published_at=item.published_at.isoformat(),
            data_available_at=item.data_available_at.isoformat(), source_name=item.source_name,
            source_reference=item.source_reference, revision=item.revision, currency=item.currency,
            fii_gross_buy=item.fii_gross_buy, fii_gross_sell=item.fii_gross_sell, fii_net=current['fii_net'],
            dii_gross_buy=item.dii_gross_buy, dii_gross_sell=item.dii_gross_sell, dii_net=current['dii_net'],
            institutional_net=current['institutional_net'], market_turnover=item.market_turnover,
            market_return=item.market_return, market_breadth=item.market_breadth, india_vix=item.india_vix,
            fii_index_futures_net=current['index_futures'], fii_stock_futures_net=current['stock_futures'])
        for prefix in ('fii', 'dii', 'institutional'):
            field = f'{prefix}_net'
            for window in (5, 20, 60): row[f'{field}_{window}d'] = _sum(known, field, window)
            row[f'{prefix}_flow_z_60d'] = _z(known, field, 60)
            row[f'{prefix}_flow_percentile_252d'] = _percentile(known, field, 252)
            avg5, avg20 = _mean(known, field, 5), _mean(known, field, 20)
            row[f'{prefix}_flow_momentum'] = avg5-avg20 if avg5 is not None and avg20 is not None else None
        for prefix in ('fii', 'dii'):
            momentum = row[f'{prefix}_flow_momentum']
            prior_avg5 = _mean(known[:-1], f'{prefix}_net', 5)
            prior_avg20 = _mean(known[:-1], f'{prefix}_net', 20)
            prior_momentum = prior_avg5-prior_avg20 if prior_avg5 is not None and prior_avg20 is not None else None
            row[f'{prefix}_flow_acceleration'] = momentum-prior_momentum if momentum is not None and prior_momentum is not None else None
            last20 = known[-20:]
            field = f'{prefix}_net'
            valid = [value[field] for value in last20 if value[field] is not None]
            row[f'{prefix}_positive_day_ratio_20d'] = sum(value > 0 for value in valid)/len(valid) if valid else None
            row[f'{prefix}_negative_day_ratio_20d'] = sum(value < 0 for value in valid)/len(valid) if valid else None
            row[f'{prefix}_flow_volatility_20d'] = pstdev(valid) if len(valid) >= 2 else None
        row['fii_flow_pct_turnover'] = row['fii_net']/item.market_turnover if row['fii_net'] is not None and item.market_turnover else None
        row['dii_flow_pct_turnover'] = row['dii_net']/item.market_turnover if row['dii_net'] is not None and item.market_turnover else None
        row['institutional_flow_state'] = _sign_state(row['fii_net'], row['dii_net'])
        row['flow_price_state'] = ('MISSING' if item.market_return is None or row['fii_net'] is None else
                                   f"MARKET_{'UP' if item.market_return >= 0 else 'DOWN'}_FII_{'BUYING' if row['fii_net'] >= 0 else 'SELLING'}")
        row['flow_breadth_confirmation'] = ('MISSING' if item.market_breadth is None or row['fii_net'] is None else
                                            'CONFIRMED' if item.market_breadth*row['fii_net'] >= 0 else 'DIVERGENT')
        row['flow_volatility_state'] = ('MISSING' if item.india_vix is None or row['fii_net'] is None else
                                        f"FII_{'BUYING' if row['fii_net'] >= 0 else 'SELLING'}_VIX_{'HIGH' if item.india_vix >= 20 else 'LOW'}")
        futures = current['index_futures']
        prior_source = known[-2] if len(known) >= 2 else None
        row['fii_index_futures_net_change'] = (futures-prior_source['index_futures']
                                                if futures is not None and prior_source and prior_source['index_futures'] is not None else None)
        row['fii_stock_futures_net_change'] = (current['stock_futures']-prior_source['stock_futures']
                                                if current['stock_futures'] is not None and prior_source and prior_source['stock_futures'] is not None else None)
        row['cash_futures_alignment'] = ('MISSING_DERIVATIVES' if futures is None or row['fii_net'] is None else
            f"CASH_{'BUY' if row['fii_net'] >= 0 else 'SELL'}_FUTURES_{'LONG' if futures >= 0 else 'SHORT'}")
        row['fii_market_return_corr_20d'] = _corr(known, 'fii_net', 'market_return', 20)
        row['fii_market_return_corr_60d'] = _corr(known, 'fii_net', 'market_return', 60)
        row['flow_regime'] = _regime(row['fii_flow_z_60d'], row['fii_net_20d'])
        positive_ratio = row['fii_positive_day_ratio_20d']
        row['flow_regime_persistence'] = (None if positive_ratio is None else 100*abs(positive_ratio-.5)*2)
        scale = row['fii_flow_volatility_20d']
        row['foreign_flow_score'] = _score(row['fii_flow_z_60d'], row['fii_flow_momentum'], scale, request.score_z_clip)
        dii_scale = row['dii_flow_volatility_20d']
        row['domestic_flow_score'] = _score(row['dii_flow_z_60d'], row['dii_flow_momentum'], dii_scale, request.score_z_clip)
        scores = [value for value in (row['foreign_flow_score'], row['domestic_flow_score']) if value is not None]
        row['institutional_flow_score'] = fmean(scores) if scores else None
        required = [row['fii_net'], row['dii_net'], item.market_return, item.market_breadth, current['index_futures']]
        row['flow_confidence'] = 100*sum(value is not None for value in required)/len(required)
        row['flow_valid'] = row['fii_net'] is not None and row['dii_net'] is not None
        row['flow_quality_status'] = ('VALID' if row['flow_confidence'] == 100 else
                                      'MISSING_DERIVATIVES' if current['index_futures'] is None else 'PARTIAL')
        row['flow_invalid_reason'] = None if row['flow_valid'] else 'Missing FII or DII cash flow'
        output.append(row)
    return output


def _sector_rows(request):
    output = []
    for evaluation in request.evaluations:
        known = [item for item in request.sector_observations if item.date <= evaluation.date and item.data_available_at <= evaluation.evaluated_at]
        versions = {}
        for item in sorted(known, key=lambda value: value.data_available_at):
            versions[(item.date, item.sector_id)] = item
        latest = {sector: item for (day, sector), item in versions.items() if day == evaluation.date}
        values = [item.flow_value for item in latest.values()]
        for sector, item in sorted(latest.items()):
            history = [value for (day, name), value in sorted(versions.items()) if name == sector and day <= evaluation.date]
            flow_values = [value.flow_value for value in history]
            flow_5d = sum(flow_values[-5:]) if len(flow_values) >= 5 else None
            flow_20d = sum(flow_values[-20:]) if len(flow_values) >= 20 else None
            recent = flow_values[-60:]
            deviation = pstdev(recent) if len(recent) >= 2 else None
            flow_z = ((recent[-1]-fmean(recent))/deviation if deviation else (0.0 if len(recent) >= 2 else None))
            below = sum(value < item.flow_value for value in values)
            tied = sum(value == item.flow_value for value in values)
            percentile = 100*(below+(tied-1)/2)/(len(values)-1) if len(values) > 1 else None
            output.append(dict(date=evaluation.date.isoformat(), evaluated_at=evaluation.evaluated_at.isoformat(),
                sector_id=sector, sector_flow=item.flow_value, sector_flow_5d=flow_5d, sector_flow_20d=flow_20d,
                sector_flow_z=flow_z, sector_flow_rank=sum(value > item.flow_value for value in values)+(tied+1)/2,
                sector_flow_percentile=percentile, sector_flow_score=percentile,
                flow_quality_status='VALID' if item.direct_observation else 'PROXY_ONLY', source_name=item.source_name))
    return output


def _stock_rows(request):
    output = []
    for evaluation in request.evaluations:
        rows = [item for item in request.stock_observations if item.date == evaluation.date and item.data_available_at <= evaluation.evaluated_at]
        for item in rows:
            direct_net = (item.institutional_buy_value-item.institutional_sell_value
                          if item.institutional_buy_value is not None and item.institutional_sell_value is not None else None)
            components = []
            if direct_net is not None:
                gross = item.institutional_buy_value+item.institutional_sell_value
                components.append(direct_net/gross if gross else 0)
            components.extend(tanh(value/1e9) for value in (item.bulk_deal_net, item.block_deal_net) if value is not None)
            components.extend(max(-1, min(1, value)) for value in (item.fpi_holding_change, item.mf_holding_change) if value is not None)
            proxy = item.delivery_z
            if proxy is not None: components.append(max(-1, min(1, proxy/3)))
            score = 50+50*fmean(components) if components else None
            quality = 'VALID' if item.direct_observation and direct_net is not None else ('PROXY_ONLY' if proxy is not None else 'PARTIAL')
            output.append(dict(date=evaluation.date.isoformat(), evaluated_at=evaluation.evaluated_at.isoformat(),
                instrument_key=item.instrument_key, institutional_buy_value=item.institutional_buy_value,
                institutional_sell_value=item.institutional_sell_value, institutional_net_value=direct_net,
                bulk_deal_net=item.bulk_deal_net, block_deal_net=item.block_deal_net,
                fpi_holding_change=item.fpi_holding_change, mf_holding_change=item.mf_holding_change,
                delivery_pct=item.delivery_pct, delivery_z=item.delivery_z,
                stock_flow_score=max(0, min(100, score)) if score is not None else None,
                score_components=components,
                stock_flow_confidence=90 if quality == 'VALID' else (35 if quality == 'PROXY_ONLY' else 50),
                flow_quality_status=quality, delivery_is_institutional_flow=False, source_name=item.source_name))
    return output


def calculate_institutional_flows(request: InstitutionalFlowRequest):
    return dict(version=VERSION, snapshot_id=request.snapshot_id, as_of=request.as_of.isoformat(),
                market_rows=_market_rows(request), sector_rows=_sector_rows(request), stock_rows=_stock_rows(request))
