"""Historical-universe breadth, participation, leadership and divergence."""
from collections import defaultdict
from statistics import fmean, pstdev

from app.engines.market_breadth.market_breadth_schema import MarketBreadthRequest

VERSION = '1'


def _ratio(numerator, denominator): return numerator/denominator if denominator else None
def _pct(rows, predicate): return 100*sum(predicate(row) for row in rows)/len(rows) if rows else None


def _slope(values):
    if len(values) < 2: return None
    xm=(len(values)-1)/2; ym=fmean(values)
    denominator=sum((index-xm)**2 for index in range(len(values)))
    return sum((index-xm)*(value-ym) for index,value in enumerate(values))/denominator if denominator else None


def _ema(previous, value, span):
    alpha=2/(span+1)
    return value if previous is None else alpha*value+(1-alpha)*previous


def _percentile(values, value):
    if len(values)<2:return None
    below=sum(item<value for item in values); tied=sum(item==value for item in values)
    return 100*(below+(tied-1)/2)/(len(values)-1)


def _z(values, value):
    if len(values)<2:return None
    deviation=pstdev(values)
    return (value-fmean(values))/deviation if deviation else 0.0


def _score(row):
    components=[]
    for name in ('advance_pct','pct_above_sma50','pct_above_sma200','up_volume_pct'):
        if row.get(name) is not None: components.append(row[name]*100 if row[name] <= 1 else row[name])
    if row.get('high_low_index') is not None: components.append(row['high_low_index']*100)
    return fmean(components) if components else None, components


def _aggregate(day, universe, population, index_row, request):
    eligible=[row for row in population if row.eligible]
    active=[row for row in eligible if row.quality_valid and not row.stale_price_flag and row.trading_status=='ACTIVE']
    valid=[row for row in active if row.return_1d is not None and row.adjusted_close is not None]
    tolerance=request.unchanged_tolerance
    advancers=sum(row.return_1d>tolerance for row in valid); decliners=sum(row.return_1d < -tolerance for row in valid)
    unchanged=len(valid)-advancers-decliners
    up_volume=sum(row.volume or 0 for row in valid if row.return_1d>tolerance)
    down_volume=sum(row.volume or 0 for row in valid if row.return_1d < -tolerance)
    up_value=sum(row.traded_value or 0 for row in valid if row.return_1d>tolerance)
    down_value=sum(row.traded_value or 0 for row in valid if row.return_1d < -tolerance)
    def ma_pct(field):
        rows=[row for row in active if row.adjusted_close is not None and getattr(row,field) is not None]
        return _ratio(sum(row.adjusted_close>getattr(row,field) for row in rows),len(rows))
    def extremes(high_field,low_field):
        rows=[row for row in active if row.adjusted_close is not None and getattr(row,high_field) is not None and getattr(row,low_field) is not None]
        return sum(row.adjusted_close>=getattr(row,high_field) for row in rows),sum(row.adjusted_close<=getattr(row,low_field) for row in rows)
    highs20,lows20=extremes('prior_high_20d','prior_low_20d'); highs252,lows252=extremes('prior_high_252d','prior_low_252d')
    coverage=_ratio(len(valid),len(eligible)) or 0
    missing_volume=any(row.volume is None for row in valid)
    quality=('LOW_COVERAGE' if coverage<request.minimum_coverage else 'STALE_COMPONENTS' if any(row.stale_price_flag for row in eligible) else 'MISSING_VOLUME' if missing_volume else 'VALID')
    size_metrics={}
    for bucket in ('LARGE','MID','SMALL'):
        members=[row for row in valid if (row.market_cap_bucket or '').upper().startswith(bucket)]
        size_metrics[f'{bucket.lower()}_cap_advance_pct']=_ratio(sum(row.return_1d>tolerance for row in members),len(members))
        eligible_ma=[row for row in members if row.sma50 is not None]
        size_metrics[f'{bucket.lower()}_cap_pct_above_sma50']=_ratio(sum(row.adjusted_close>row.sma50 for row in eligible_ma),len(eligible_ma))
    trend_states={state:_ratio(sum((row.trend_state or '').upper()==state for row in valid),len(valid)) for state in ('STRONG_UPTREND','UPTREND','SIDEWAYS','DOWNTREND','STRONG_DOWNTREND')}
    momentum_states={state:_ratio(sum((row.momentum_state or '').upper()==state for row in valid),len(valid)) for state in ('STRONG_POSITIVE','POSITIVE','NEGATIVE')}
    return dict(date=day,universe_id=universe,eligible_count=len(eligible),valid_stock_count=len(valid),
        missing_count=len(eligible)-len(valid),breadth_coverage_pct=coverage,advancers=advancers,decliners=decliners,
        unchanged=unchanged,advance_pct=_ratio(advancers,len(valid)),decline_pct=_ratio(decliners,len(valid)),
        ad_difference=advancers-decliners,ad_ratio=_ratio(advancers,decliners),
        equal_weight_return_1d=fmean([row.return_1d for row in valid]) if valid else None,
        cap_weighted_index_return=index_row.index_return_1d if index_row else None,
        pct_above_sma20=ma_pct('sma20'),pct_above_sma50=ma_pct('sma50'),
        pct_above_sma100=ma_pct('sma100'),pct_above_sma200=ma_pct('sma200'),
        new_highs_20d=highs20,new_lows_20d=lows20,new_highs_252d=highs252,new_lows_252d=lows252,
        high_low_difference=highs252-lows252,high_low_ratio=_ratio(highs252,lows252),
        high_low_index=_ratio(highs252,highs252+lows252),new_high_pct=_ratio(highs252,len(valid)),new_low_pct=_ratio(lows252,len(valid)),
        up_volume=up_volume,down_volume=down_volume,up_down_volume_ratio=_ratio(up_volume,down_volume),
        up_volume_pct=_ratio(up_volume,up_volume+down_volume),up_traded_value=up_value,down_traded_value=down_value,
        up_down_value_ratio=_ratio(up_value,down_value),index_price=index_row.index_price if index_row else None,
        breadth_valid=coverage>=request.minimum_coverage,breadth_quality_status=quality,
        **size_metrics,**{f'pct_{key.lower()}':value for key,value in trend_states.items()},
        **{f'pct_{key.lower()}_momentum':value for key,value in momentum_states.items()})


def _sector_rows(day,universe,population,request):
    groups=defaultdict(list)
    for row in population:
        if row.eligible and row.sector and row.quality_valid and not row.stale_price_flag and row.trading_status=='ACTIVE' and row.return_1d is not None and row.adjusted_close is not None:
            groups[row.sector].append(row)
    output=[]
    for sector,rows in sorted(groups.items()):
        if len(rows)<request.minimum_sector_count:continue
        advance=_pct(rows,lambda row:row.return_1d>request.unchanged_tolerance)/100
        sma50=[row for row in rows if row.sma50 is not None]; sma200=[row for row in rows if row.sma200 is not None]
        high=sum(row.prior_high_252d is not None and row.adjusted_close>=row.prior_high_252d for row in rows)
        low=sum(row.prior_low_252d is not None and row.adjusted_close<=row.prior_low_252d for row in rows)
        above50=_ratio(sum(row.adjusted_close>row.sma50 for row in sma50),len(sma50)); above200=_ratio(sum(row.adjusted_close>row.sma200 for row in sma200),len(sma200))
        components=[value for value in (advance,above50,above200,_ratio(high,len(rows))) if value is not None]
        output.append(dict(date=day,universe_id=universe,sector_id=sector,valid_count=len(rows),advance_pct=advance,
            pct_above_sma50=above50,pct_above_sma200=above200,new_high_pct=_ratio(high,len(rows)),new_low_pct=_ratio(low,len(rows)),
            sector_breadth_score=100*fmean(components) if components else None,sector_breadth_rank=None))
    values=[row['sector_breadth_score'] for row in output if row['sector_breadth_score'] is not None]
    for row in output:
        row['sector_breadth_rank']=sum(value>row['sector_breadth_score'] for value in values)+1 if row['sector_breadth_score'] is not None else None
        row['sector_breadth_percentile']=_percentile(values,row['sector_breadth_score']) if row['sector_breadth_score'] is not None else None
    return output


def calculate_market_breadth(request:MarketBreadthRequest):
    groups=defaultdict(list)
    for row in request.observations:groups[(row.date.isoformat(),row.universe_id)].append(row)
    indexes={(row.date.isoformat(),row.universe_id):row for row in request.index_observations}
    rows=[];sectors=[];history=defaultdict(list);ema_state=defaultdict(lambda:[None,None])
    for key in sorted(groups):
        row=_aggregate(key[0],key[1],groups[key],indexes.get(key),request); prior=history[key[1]]
        row['advance_decline_line']=(prior[-1]['advance_decline_line'] if prior else 0)+row['ad_difference']
        row['high_low_line']=(prior[-1]['high_low_line'] if prior else 0)+row['high_low_difference']
        ad_values=[item['advance_decline_line'] for item in prior]+[row['advance_decline_line']]
        row['ad_line_slope_20d']=_slope(ad_values[-20:]);row['ad_line_slope_60d']=_slope(ad_values[-60:])
        row['ad_line_new_high_252d']=row['advance_decline_line']>=max(ad_values[-252:])
        returns=[item['equal_weight_return_1d'] for item in prior if item['equal_weight_return_1d'] is not None]+([row['equal_weight_return_1d']] if row['equal_weight_return_1d'] is not None else [])
        for window in (5,21):row[f'equal_weight_return_{window}d']=(__import__('math').prod(1+value for value in returns[-window:])-1 if len(returns)>=window else None)
        row['breadth_return_spread']=(row['equal_weight_return_1d']-row['cap_weighted_index_return'] if row['equal_weight_return_1d'] is not None and row['cap_weighted_index_return'] is not None else None)
        short,long=ema_state[key[1]];short=_ema(short,row['ad_difference'],19);long=_ema(long,row['ad_difference'],39);ema_state[key[1]]=[short,long]
        row['mcclellan_style_oscillator']=short-long
        for field,lag in (('advance_pct',5),('pct_above_sma50',5),('pct_above_sma200',21)):
            previous=prior[-lag].get(field) if len(prior)>=lag else None
            row[f'{field}_change_{lag}d']=row[field]-previous if row.get(field) is not None and previous is not None else None
        momentum_values=[row.get('advance_pct_change_5d'),row.get('pct_above_sma50_change_5d'),row.get('pct_above_sma200_change_21d')]
        momentum_values=[value for value in momentum_values if value is not None];row['breadth_momentum_score']=fmean(momentum_values)*100 if momentum_values else None
        prior_momentum=prior[-1].get('breadth_momentum_score') if prior else None
        row['breadth_acceleration']=row['breadth_momentum_score']-prior_momentum if row['breadth_momentum_score'] is not None and prior_momentum is not None else None
        row['volume_breadth_confirmation']='CONFIRMED' if row['advance_pct'] is not None and row['up_volume_pct'] is not None and (row['advance_pct']-.5)*(row['up_volume_pct']-.5)>=0 else 'DIVERGENT'
        score,components=_score(row);row['breadth_score']=score;row['breadth_score_components']=components
        row['market_participation_score']=score;row['breadth_confirmation_score']=score
        row['breadth_regime']='INVALID' if score is None else 'VERY_STRONG' if score>=80 else 'STRONG' if score>=60 else 'NEUTRAL' if score>=40 else 'WEAK' if score>=20 else 'VERY_WEAK'
        previous_regime=prior[-1]['breadth_regime'] if prior else None;row['breadth_regime_change']=f'{previous_regime}_TO_{row["breadth_regime"]}' if previous_regime and previous_regime!=row['breadth_regime'] else None
        score_history=[item['breadth_score'] for item in prior[-251:] if item['breadth_score'] is not None]+([score] if score is not None else [])
        row['breadth_percentile_252d']=_percentile(score_history,score) if score is not None else None;row['breadth_z_252d']=_z(score_history,score) if score is not None else None
        index_returns=[item['cap_weighted_index_return'] for item in prior[-19:] if item['cap_weighted_index_return'] is not None]+([row['cap_weighted_index_return']] if row['cap_weighted_index_return'] is not None else [])
        index_trend=sum(index_returns) if index_returns else None;ad_slope=row['ad_line_slope_20d']
        row['bearish_breadth_divergence']=bool(index_trend is not None and index_trend>0 and ad_slope is not None and ad_slope<0)
        row['bullish_breadth_divergence']=bool(index_trend is not None and index_trend<0 and ad_slope is not None and ad_slope>0)
        row['sma50_breadth_divergence']=bool(index_trend is not None and row.get('pct_above_sma50_change_5d') is not None and index_trend*row['pct_above_sma50_change_5d']<0)
        row['narrow_leadership_flag']=bool(row['cap_weighted_index_return'] is not None and row['cap_weighted_index_return']>0 and (row['breadth_return_spread'] or 0)<0 and (row['pct_above_sma50'] or 0)<.5)
        row['broad_participation_flag']=bool(row['cap_weighted_index_return'] is not None and row['cap_weighted_index_return']>0 and (row['advance_pct'] or 0)>=.6 and (row['pct_above_sma50'] or 0)>=.6)
        row['broad_distribution_flag']=bool((row['decline_pct'] or 0)>=.6 and (row['up_volume_pct'] or 1)<=.4)
        row['breadth_shock_flag']=bool((row['decline_pct'] or 0)>=.8 and (row['up_volume_pct'] or 1)<=.2)
        strong_days=sum((item.get('advance_pct') or 0)>=.6 and (item.get('pct_above_sma50') or 0)>=.6 for item in prior[-19:])
        strong_days+=int((row.get('advance_pct') or 0)>=.6 and (row.get('pct_above_sma50') or 0)>=.6)
        row['breadth_persistence_score']=100*strong_days/min(20,len(prior)+1)
        large=row.get('large_cap_advance_pct');small=row.get('small_cap_advance_pct')
        row['size_breadth_divergence']=(large-small if large is not None and small is not None else None)
        prior_highs=fmean([item['new_high_pct'] for item in prior[-20:] if item.get('new_high_pct') is not None]) if any(item.get('new_high_pct') is not None for item in prior[-20:]) else None
        row['new_high_divergence']=bool(index_trend is not None and index_trend>0 and prior_highs is not None and row.get('new_high_pct') is not None and row['new_high_pct']<prior_highs)
        rows.append(row);history[key[1]].append(row);sectors.extend(_sector_rows(key[0],key[1],groups[key],request))
    return dict(version=VERSION,snapshot_id=request.snapshot_id,as_of=request.as_of.isoformat(),rows=rows,sector_rows=sectors)
