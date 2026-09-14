# Open Analytics — Step 9: Volume & Participation Engine

## Purpose

The **Volume & Participation Engine** measures how strongly market participants are supporting, confirming, rejecting, or distributing a price move.

Price tells us where the market moved.

Volume and participation help answer:

- How much participation was behind the move?
- Was the move broadly supported or thin?
- Is demand increasing or fading?
- Is selling pressure increasing or easing?
- Is a breakout confirmed by stronger participation?
- Is price rising while participation weakens?
- Is there evidence of accumulation or distribution?
- Is current activity unusual relative to the stock's own history?
- Does participation agree with trend and momentum?

This engine should not duplicate Step 6.

Step 6 — Liquidity & Tradability focuses on:

```text
Can we trade this stock efficiently?
```

Step 9 — Volume & Participation focuses on:

```text
What does trading activity tell us about current market behavior?
```

Outputs feed directly into:

- Momentum confirmation
- Trend confirmation
- Breakout analysis
- Alpha signals
- Event detection
- Accumulation/distribution research
- Market breadth
- Machine learning features

---

# 9.1 Core Principle

Volume should not be treated as one number.

Open Analytics should separate:

```text
Absolute Volume
Relative Volume
Traded Value
Participation Change
Volume Trend
Price-Volume Agreement
Accumulation / Distribution
Money Flow
Breakout Confirmation
Volume Divergence
Event Volume
```

Do not assume:

```text
high volume = bullish
```

High volume can represent buying, selling, rebalancing, forced liquidation, event activity, or two-sided disagreement.

Context matters.

---

# 9.2 Required Inputs

Minimum:

```text
instrument_key
date

open
high
low
close
volume
```

Preferred:

```text
adjusted_open
adjusted_high
adjusted_low
adjusted_close
adjusted_volume

daily_traded_value

return_1d
trend metrics
momentum metrics
liquidity metrics

delivery_quantity
delivery_percentage

number_of_trades

benchmark volume / breadth where useful
```

Optional advanced:

```text
intraday bars
tick data
buy/sell initiated volume
order-flow data
market depth
block/bulk deal data
```

---

# 9.3 Daily Volume

Store:

```text
daily_volume
```

This is the base raw participation measure.

Do not compare daily volume across stocks without normalization.

---

# 9.4 Daily Traded Value

Store:

```text
daily_traded_value
```

Prefer actual exchange turnover where available.

Otherwise:

```text
daily_traded_value ≈ close × volume
```

Traded value is useful for comparing participation across differently priced stocks.

---

# 9.5 Rolling Average Volume

Recommended:

```text
avg_volume_5d
avg_volume_10d
avg_volume_20d
avg_volume_60d
avg_volume_126d
avg_volume_252d
```

These establish local participation baselines.

---

# 9.6 Rolling Median Volume

Also calculate:

```text
median_volume_20d
median_volume_60d
median_volume_252d
```

Median is more robust when one event day creates an extreme spike.

---

# 9.7 Rolling Average Traded Value

Recommended:

```text
avg_traded_value_5d
avg_traded_value_20d
avg_traded_value_60d
avg_traded_value_252d
```

This overlaps with Step 6, but Step 9 uses these values mainly as behavior/participation context.

---

# 9.8 Relative Volume

Relative Volume:

```text
rvol_20d =
current_volume / avg_volume_20d
```

Recommended:

```text
rvol_5d
rvol_20d
rvol_60d
```

Example:

```text
Current volume     = 5,000,000
20D average volume = 1,000,000

RVOL = 5.0
```

This indicates participation is five times the recent norm.

---

# 9.9 Relative Traded Value

Analogous:

```text
rtv_20d =
current_traded_value / avg_traded_value_20d
```

Store:

```text
rtv_20d
rtv_60d
```

This can be more robust than raw RVOL for very low-priced securities.

---

# 9.10 Volume Z-Score

Standardize current activity:

```text
volume_z_20d =
(current_volume - avg_volume_20d)
/
std_volume_20d
```

Likewise:

```text
traded_value_z_20d
```

Outputs:

```text
volume_z_20d
volume_z_60d

traded_value_z_20d
traded_value_z_60d
```

---

# 9.11 Volume Percentile

Historical percentile relative to own history:

```text
volume_historical_percentile_252d
```

Cross-sectional percentile:

```text
volume_universe_percentile
```

These answer different questions.

---

# 9.12 Volume Trend

Measure whether participation itself is rising or falling.

Possible:

```text
volume_slope_20d
volume_slope_60d

traded_value_slope_20d
traded_value_slope_60d
```

Normalize where needed.

---

# 9.13 Volume Acceleration

Compare short and long volume baselines:

```text
volume_acceleration =
avg_volume_5d / avg_volume_20d
```

or:

```text
avg_volume_20d / avg_volume_60d
```

Store:

```text
volume_accel_5_20
volume_accel_20_60
```

---

# 9.14 Participation Regime

Classify current activity:

```text
VERY_LOW
LOW
NORMAL
HIGH
EXTREME
```

Inputs:

```text
RVOL
volume z-score
historical percentile
traded value
```

Output:

```text
participation_regime
```

---

# 9.15 Price-Volume Direction Matrix

Basic behavior map:

```text
Price ↑ + Volume ↑
→ rising price with stronger participation

Price ↑ + Volume ↓
→ rising price with weaker participation

Price ↓ + Volume ↑
→ falling price with stronger selling / disagreement

Price ↓ + Volume ↓
→ decline with fading participation
```

Store a normalized state:

```text
price_volume_state
```

Possible:

```text
UP_VOLUME_EXPANDING
UP_VOLUME_CONTRACTING
DOWN_VOLUME_EXPANDING
DOWN_VOLUME_CONTRACTING
FLAT_MIXED
```

Do not interpret these states as deterministic buy/sell signals.

---

# 9.16 Volume Confirmation of Trend

Consume Step 7 trend state.

Example:

```text
trend = STRONG_UPTREND
volume trend = RISING
```

Possible:

```text
trend_volume_confirmation = STRONG
```

Other states:

```text
CONFIRMED
PARTIAL
DIVERGENT
```

---

# 9.17 Volume Confirmation of Momentum

Consume Step 8 momentum.

Possible logic:

```text
high positive momentum
+
high RVOL
+
rising traded value
```

Store:

```text
momentum_volume_confirmation
```

---

# 9.18 Breakout Volume Confirmation

A breakout should be evaluated against normal participation.

Example:

```text
breakout_20d_high = true
rvol_20d >= threshold
```

Store:

```text
breakout_volume_confirmation
```

Possible states:

```text
STRONG
MODERATE
WEAK
NONE
```

Thresholds should be configurable and researched.

---

# 9.19 Breakdown Volume Confirmation

Similarly:

```text
breakdown_20d_low = true
```

combined with:

```text
high volume
```

can indicate stronger downside participation.

Store:

```text
breakdown_volume_confirmation
```

---

# 9.20 OBV — On-Balance Volume

Concept:

```text
if close_today > close_yesterday:
    OBV += volume

if close_today < close_yesterday:
    OBV -= volume
```

Store:

```text
obv
```

Then derive:

```text
obv_slope_20d
obv_slope_60d
```

OBV should be treated as a cumulative participation proxy.

---

# 9.21 OBV Divergence

Possible:

```text
price making new high
but OBV not making new high
```

or:

```text
price making new low
but OBV not making new low
```

Store:

```text
obv_bullish_divergence
obv_bearish_divergence
```

Divergence rules must be deterministic to avoid subjective chart interpretation.

---

# 9.22 Accumulation / Distribution Line

Typical concept uses close location inside daily range combined with volume.

Money Flow Multiplier:

```text
((close - low) - (high - close))
/
(high - low)
```

Then:

```text
money_flow_volume =
multiplier × volume
```

Cumulative:

```text
ad_line
```

Store:

```text
ad_line
ad_slope_20d
ad_slope_60d
```

Handle:

```text
high == low
```

safely.

---

# 9.23 Chaikin Money Flow

CMF aggregates money-flow volume over a window.

Recommended:

```text
cmf_20
```

Optional:

```text
cmf_10
cmf_60
```

Positive values indicate more closes near the upper part of ranges weighted by volume; negative values indicate the opposite.

---

# 9.24 Money Flow Index

MFI combines price and volume.

Recommended:

```text
mfi_14
```

This is a volume-weighted oscillator.

Treat it as an auxiliary measure, not the primary institutional-flow metric.

---

# 9.25 Volume Price Trend

VPT concept:

```text
VPT_t =
VPT_(t-1)
+
volume_t × return_t
```

Store:

```text
vpt
vpt_slope_20d
vpt_slope_60d
```

---

# 9.26 VWAP

For intraday data:

```text
VWAP =
sum(price × volume)
/
sum(volume)
```

Daily-bar data cannot recreate true intraday VWAP precisely.

If intraday data exists, store:

```text
session_vwap
```

and:

```text
close_vs_vwap_pct
```

---

# 9.27 Rolling VWAP-Like Measure

Using daily bars, Open Analytics may optionally calculate a rolling volume-weighted average price:

```text
rolling_vwap_20d =
sum(typical_price × volume)
/
sum(volume)
```

where:

```text
typical_price =
(high + low + close) / 3
```

Store:

```text
rolling_vwap_20d
distance_rolling_vwap_20d
```

Clearly distinguish this from true intraday session VWAP.

---

# 9.28 Anchored VWAP

Later, with adequate data, calculate AVWAP anchored to:

```text
earnings date
breakout date
52-week low
IPO date
major event date
calendar year start
```

Possible:

```text
avwap_event
distance_avwap_event
```

This is a later-stage feature.

---

# 9.29 Volume-Weighted Return

Possible feature:

```text
volume_weighted_return
```

where higher-volume sessions contribute more heavily to the measure.

This can be useful for assessing whether strong returns occurred on meaningful participation.

---

# 9.30 Up-Volume and Down-Volume

Classify volume by daily return sign:

```text
up_volume
down_volume
```

Rolling sums:

```text
up_volume_20d
down_volume_20d
```

Ratio:

```text
up_down_volume_ratio_20d
```

---

# 9.31 Up-Value and Down-Value

Similarly with traded value:

```text
up_traded_value_20d
down_traded_value_20d
```

This can be more informative for cross-stock comparisons.

---

# 9.32 Positive Return Volume Share

Calculate:

```text
positive_volume_share =
volume on positive-return days
/
total volume
```

Recommended:

```text
positive_volume_share_20d
positive_volume_share_60d
```

---

# 9.33 Negative Return Volume Share

Similarly:

```text
negative_volume_share_20d
negative_volume_share_60d
```

---

# 9.34 Participation Balance

Possible metric:

```text
participation_balance =
positive_volume_share - negative_volume_share
```

or use traded value.

Store:

```text
participation_balance_20d
```

---

# 9.35 Delivery Percentage

Where available:

```text
delivery_pct =
delivery_quantity / traded_quantity
```

Store:

```text
delivery_pct
avg_delivery_pct_20d
avg_delivery_pct_60d
```

Delivery behavior can provide additional context on holding-oriented participation.

Do not interpret high delivery percentage as automatically bullish.

---

# 9.36 Delivery Z-Score

```text
delivery_z_20d
```

This identifies unusual delivery behavior.

---

# 9.37 Delivery-Price Agreement

Possible states:

```text
price up + delivery rising
price down + delivery rising
```

Store:

```text
delivery_price_state
```

Again, this is contextual evidence, not a deterministic signal.

---

# 9.38 Number of Trades

If available:

```text
trade_count
```

Rolling:

```text
avg_trade_count_20d
```

This can help distinguish:

```text
many small trades
vs
few large prints
```

---

# 9.39 Average Trade Size

```text
avg_trade_size =
volume / trade_count
```

Value:

```text
avg_trade_value =
traded_value / trade_count
```

Track:

```text
avg_trade_size
avg_trade_value
```

---

# 9.40 Trade Count Z-Score

```text
trade_count_z_20d
```

Unusually high trade count can indicate increased attention or participation.

---

# 9.41 Block / Bulk Deal Context

Where available:

```text
block_deal_value
bulk_deal_value
```

Create:

```text
block_bulk_activity_flag
```

This helps explain abnormal volume spikes.

---

# 9.42 Event Volume

Identify volume spikes around:

```text
earnings
corporate actions
news
index rebalance
large deals
regulatory events
```

Store:

```text
event_volume_flag
event_volume_type
```

Do not classify unexplained spikes automatically.

---

# 9.43 Abnormal Volume

Flag:

```text
volume_z_20d >= threshold
```

or:

```text
rvol_20d >= threshold
```

Store:

```text
abnormal_volume_flag
```

---

# 9.44 Volume Spike Magnitude

Continuous metric:

```text
volume_spike_score
```

Possible inputs:

```text
RVOL
z-score
historical percentile
```

---

# 9.45 Volume Persistence

One isolated high-volume day differs from sustained activity.

Calculate:

```text
high_volume_days_20d
high_volume_days_60d
```

where high-volume threshold may be based on historical percentile or RVOL.

Store:

```text
volume_persistence_score
```

---

# 9.46 Participation Expansion

Possible state when:

```text
volume rising
traded value rising
trade count rising
```

Store:

```text
participation_expansion_flag
```

---

# 9.47 Participation Contraction

Opposite:

```text
participation_contraction_flag
```

Useful for weakening-trend detection.

---

# 9.48 Price-Volume Correlation

Calculate rolling correlation between:

```text
return
volume change
```

or:

```text
absolute return
volume
```

Examples:

```text
return_volume_corr_20d
abs_return_volume_corr_20d
```

Interpret carefully because relationships are nonlinear and regime-dependent.

---

# 9.49 Volume Surprise

Model current volume relative to an expected baseline.

Simple:

```text
volume_surprise =
current_volume / expected_volume - 1
```

Expected volume may initially be:

```text
avg_volume_20d
```

Later it may account for day-of-week and intraday seasonality.

---

# 9.50 Intraday Volume Curve

If intraday bars are available, model expected cumulative volume by time of day.

Example:

```text
expected_volume_by_10_30
expected_volume_by_12_00
expected_volume_by_14_00
```

Then:

```text
intraday_volume_surprise
```

This is useful for real-time scanners.

Not required for daily first production.

---

# 9.51 Buy/Sell Initiated Volume

With tick or quote data, classify trades using methods such as:

```text
trade price vs midpoint
tick rule
```

Then estimate:

```text
buy_initiated_volume
sell_initiated_volume
```

and:

```text
order_flow_imbalance
```

This belongs to a more advanced microstructure layer.

---

# 9.52 Order Flow Imbalance

If available:

```text
OFI =
buy_pressure - sell_pressure
```

Store:

```text
order_flow_imbalance
```

Useful for intraday/short-horizon signals.

---

# 9.53 Cumulative Volume Delta

With aggressor-side data:

```text
CVD =
cumulative(buy_volume - sell_volume)
```

Possible:

```text
cvd
cvd_slope
```

Not possible reliably from daily OHLCV alone.

---

# 9.54 Price-Volume Divergence

Possible examples:

```text
price rising
volume trend falling
```

or:

```text
price falling
OBV rising
```

Store deterministic divergence states:

```text
price_volume_bullish_divergence
price_volume_bearish_divergence
```

Avoid subjective chart pattern rules.

---

# 9.55 Participation Quality Score

Possible components:

```text
RVOL
traded value trend
volume persistence
delivery behavior
trade count
price-volume agreement
```

Output:

```text
participation_quality_score
```

Do not combine advanced components unless corresponding data exists.

---

# 9.56 Volume Factor Score

Eventually derive:

```text
volume_factor_score
```

Potential components:

```text
relative volume
traded value acceleration
positive volume share
OBV slope
CMF
volume confirmation
```

Weights should be researched.

---

# 9.57 Volume Percentile

Final cross-sectional measure:

```text
volume_factor_percentile
```

This should indicate stronger participation characteristics relative to eligible peers.

---

# 9.58 Participation State

Possible simplified state:

```text
STRONG_ACCUMULATION
ACCUMULATION
NEUTRAL
DISTRIBUTION
STRONG_DISTRIBUTION
```

This should be treated cautiously.

Daily OHLCV alone cannot reveal exact buyer/seller identity.

Use the label only as a statistical state derived from observable behavior.

---

# 9.59 Trend + Volume Matrix

Example composite context:

```text
Strong uptrend + expanding volume
Strong uptrend + contracting volume

Downtrend + expanding volume
Downtrend + contracting volume
```

Store:

```text
trend_volume_state
```

This is useful for signal generation later.

---

# 9.60 Momentum + Volume Matrix

Similarly:

```text
Strong momentum + strong participation
Strong momentum + weak participation
Weak momentum + strong selling participation
```

Store:

```text
momentum_volume_state
```

---

# 9.61 Breakout Confirmation Score

Potential score inputs:

```text
breakout strength
RVOL
traded value z-score
OBV slope
close location within range
```

Output:

```text
breakout_confirmation_score
```

This belongs at the boundary between Trend and Volume engines.

---

# 9.62 Close Location Value

Useful daily feature:

```text
CLV =
((close - low) - (high - close))
/
(high - low)
```

Range:

```text
-1 to +1
```

High positive values indicate close near daily high; negative values indicate close near daily low.

Store:

```text
close_location_value
```

---

# 9.63 Volume-Weighted Close Location

Multiply:

```text
CLV × volume
```

This forms the basis of accumulation/distribution style measures.

---

# 9.64 Volume Around Highs

Possible research features:

```text
avg_volume_near_20d_high
avg_volume_near_52w_high
```

This can help evaluate whether leadership is supported by participation.

Not required for first production.

---

# 9.65 Volume Around Lows

Similarly:

```text
avg_volume_near_20d_low
avg_volume_near_52w_low
```

Useful for capitulation/reversal studies.

---

# 9.66 Capitulation Volume

Potential state:

```text
large negative return
+
extreme volume percentile
+
close near low
```

Store:

```text
capitulation_volume_flag
```

This is contextual, not a guaranteed bottom.

---

# 9.67 Climax Volume

Possible:

```text
large positive return
+
extreme volume
+
extended trend
```

Store:

```text
climax_volume_flag
```

Again, not a deterministic reversal signal.

---

# 9.68 Quiet Accumulation

Potential pattern:

```text
price slowly rising
volume stable/moderate
positive volume share high
OBV rising
```

Could later form:

```text
quiet_accumulation_score
```

This is advanced and should be empirically validated.

---

# 9.69 Volume Compression

Track when volume falls significantly below normal:

```text
volume_compression_flag
```

Potential setup context for future expansion.

---

# 9.70 Volume Expansion After Compression

Store:

```text
compression_breakout_volume_flag
```

This can be useful in breakout models.

---

# 9.71 Sector Participation Comparison

Compare stock participation with sector peers:

```text
sector_volume_percentile
sector_rvol_percentile
```

This can identify unusually active stocks within an otherwise quiet sector.

---

# 9.72 Market Participation Comparison

Compare to broad universe:

```text
universe_volume_percentile
universe_traded_value_percentile
```

Use point-in-time universe membership.

---

# 9.73 Historical Participation Snapshot

All calculations must be point-in-time.

At date T:

```text
avg_volume_20d
```

must use only data through T.

Do not use future volume.

---

# 9.74 Survivorship Bias Protection

Stocks that later delisted or became illiquid must remain in historical participation calculations if they were eligible at that time.

---

# 9.75 Corporate Action Handling

Volume may need adjustment after:

```text
stock splits
bonus issues
```

Use adjusted volume where appropriate for historical comparability.

Keep raw exchange-reported volume separately.

---

# 9.76 Stale / No-Trade Sessions

Do not interpret:

```text
volume = missing
```

as:

```text
volume = 0
```

unless the source explicitly indicates a valid no-trade session.

Distinguish:

```text
zero volume
missing data
suspension
holiday
```

---

# 9.77 Missing Data

For unavailable inputs:

```text
metric = null
metric_valid = false
```

Do not fabricate volume or delivery data.

---

# 9.78 Data Quality Flags

Recommended:

```text
volume_valid
volume_quality_status

volume_missing_flag
volume_outlier_flag
trade_count_valid
delivery_data_valid

volume_invalid_reason
```

---

# 9.79 Recommended Daily Volume & Participation Record

A daily record could include:

```text
instrument_key
date


# RAW ACTIVITY

daily_volume
daily_traded_value
trade_count

delivery_quantity
delivery_pct


# BASELINES

avg_volume_5d
avg_volume_20d
avg_volume_60d
avg_volume_252d

median_volume_20d
median_volume_60d

avg_traded_value_20d
avg_traded_value_60d


# RELATIVE ACTIVITY

rvol_5d
rvol_20d
rvol_60d

rtv_20d

volume_z_20d
volume_z_60d

traded_value_z_20d

volume_historical_percentile_252d


# PARTICIPATION TREND

volume_slope_20d
volume_slope_60d

volume_accel_5_20
volume_accel_20_60

participation_regime


# PRICE / VOLUME

price_volume_state

positive_volume_share_20d
negative_volume_share_20d

up_down_volume_ratio_20d
participation_balance_20d


# CUMULATIVE INDICATORS

obv
obv_slope_20d
obv_slope_60d

ad_line
ad_slope_20d

cmf_20
mfi_14

vpt
vpt_slope_20d


# VWAP-RELATED

rolling_vwap_20d
distance_rolling_vwap_20d

session_vwap
close_vs_vwap_pct


# DELIVERY / TRADES

avg_delivery_pct_20d
delivery_z_20d

avg_trade_size
avg_trade_value
trade_count_z_20d


# CONFIRMATION

trend_volume_confirmation
momentum_volume_confirmation

breakout_volume_confirmation
breakdown_volume_confirmation

trend_volume_state
momentum_volume_state


# DIVERGENCE / EVENTS

obv_bullish_divergence
obv_bearish_divergence

price_volume_bullish_divergence
price_volume_bearish_divergence

abnormal_volume_flag
event_volume_flag

capitulation_volume_flag
climax_volume_flag


# FINAL

participation_quality_score
volume_factor_score
volume_factor_percentile
participation_state


# QUALITY

volume_valid
volume_quality_status
volume_invalid_reason
```

---

# 9.80 Initial Production Metrics

The first production version should focus on metrics possible from clean daily OHLCV.

Recommended:

```text
daily_volume
daily_traded_value

avg_volume_5d
avg_volume_20d
avg_volume_60d

median_volume_20d
median_volume_60d

rvol_20d
rvol_60d

volume_z_20d
traded_value_z_20d

volume_slope_20d
volume_accel_5_20

price_volume_state

positive_volume_share_20d
negative_volume_share_20d
up_down_volume_ratio_20d

obv
obv_slope_20d

ad_line
ad_slope_20d

cmf_20
mfi_14

vpt
vpt_slope_20d

rolling_vwap_20d
distance_rolling_vwap_20d

trend_volume_confirmation
momentum_volume_confirmation

breakout_volume_confirmation

abnormal_volume_flag

participation_quality_score
volume_factor_percentile

volume_quality_status
```

When delivery, trade-count, intraday, order-flow, or depth data becomes available, extend the engine.

---

# 9.81 Volume & Participation Engine Processing Flow

Recommended:

```text
VALID OHLCV
        ↓
ADJUSTED VOLUME WHERE REQUIRED
        ↓
ROLLING VOLUME / TRADED VALUE
        ↓
RELATIVE VOLUME / Z-SCORES
        ↓
VOLUME TREND / ACCELERATION
        ↓
PRICE-VOLUME STATE
        ↓
UP / DOWN VOLUME
        ↓
OBV
        ↓
ACCUMULATION / DISTRIBUTION
        ↓
CMF / MFI / VPT
        ↓
VWAP-RELATED FEATURES
        ↓
TREND / MOMENTUM CONFIRMATION
        ↓
BREAKOUT CONFIRMATION
        ↓
DIVERGENCE / EVENT VOLUME
        ↓
CROSS-SECTIONAL RANKING
        ↓
PARTICIPATION SCORE
        ↓
QUALITY FLAGS
```

---

# 9.82 Important Quant Rules

## Rule 1 — High Volume Is Not Automatically Bullish

Direction and context matter.

---

## Rule 2 — Relative Volume Is More Useful Than Raw Volume Alone

A 10 million share day means different things for different stocks.

---

## Rule 3 — Traded Value Matters

Volume without price context is incomplete.

---

## Rule 4 — Separate Liquidity from Participation

Liquidity answers whether we can trade.

Participation answers what current activity may imply.

---

## Rule 5 — Use Medians as Well as Means

Event spikes can distort averages.

---

## Rule 6 — Confirmation Must Be Continuous

Store strength scores where possible instead of only Boolean rules.

---

## Rule 7 — Divergence Rules Must Be Deterministic

Avoid subjective chart-reading logic.

---

## Rule 8 — Do Not Invent Buyer/Seller Identity

Daily OHLCV cannot tell us exactly who bought or sold.

---

## Rule 9 — Adjust Historical Volume for Structural Share Changes

Splits and bonuses can distort historical comparisons.

---

## Rule 10 — Use Point-in-Time Baselines

Historical volume ranks must not use future activity.

---

## Rule 11 — Preserve Raw Metrics

Do not expose only one participation score.

---

## Rule 12 — Volume Quality Matters

Missing/stale/irregular volume data must invalidate dependent features where necessary.

---

# 9.83 Completion Criteria

Step 9 is complete when Open Analytics can answer:

1. What is today's volume and traded value?
2. How does it compare with the stock's normal volume?
3. Is current participation unusually high or low?
4. Is volume expanding or contracting?
5. Is traded value expanding or contracting?
6. Does volume support the current price direction?
7. Is trend confirmed by participation?
8. Is momentum confirmed by participation?
9. Is a breakout occurring on strong or weak participation?
10. Is OBV rising or falling?
11. Is accumulation/distribution behavior improving or weakening?
12. What do CMF/MFI/VPT indicate?
13. Is there a deterministic price-volume divergence?
14. Is the stock showing abnormal/event-driven volume?
15. What share of recent volume occurred on positive vs negative return days?
16. Is participation persistent or driven by one event?
17. How does current participation rank versus peers?
18. What is the participation quality score?
19. Is the underlying volume data reliable?
20. Which participation metrics are unavailable and why?

Once these are reliable, the Volume & Participation Engine is ready to feed:

```text
Step 10 — Cross-Sectional Ranking Engine
```

---

# Step 9 Final Output

The Volume & Participation Engine transforms:

```text
OHLCV + Trend + Momentum + Liquidity Context
```

into:

```text
Relative Volume
Traded Value Surprise
Volume Trends
Participation Regimes
Price-Volume States
Up/Down Volume
OBV
Accumulation/Distribution
CMF
MFI
VPT
VWAP-Related Features
Breakout Confirmation
Trend/Momentum Confirmation
Volume Divergence
Event Volume Flags
Participation Quality
Volume Factor Percentiles
Volume Quality Flags
```

This becomes the participation-confirmation layer for Open Analytics.
