# Open Analytics — Step 7: Trend Engine

## Purpose

The **Trend Engine** measures the direction, strength, persistence, maturity, and structural quality of price trends.

It should answer:

- Is the stock trending up, down, or sideways?
- How strong is that trend?
- Is the trend accelerating or weakening?
- Is price above or below important moving averages?
- Is the stock breaking out of a prior range?
- Is it near a 52-week high or low?
- Is the trend persistent or noisy?
- Is the trend confirmed across multiple horizons?
- How does trend strength compare with peers?
- Is the current trend state suitable for a strategy?

Trend metrics feed into:

- Momentum
- Alpha signals
- Regime detection
- Breakout strategies
- Risk controls
- Position sizing
- Stock screening
- Machine learning features

---

# 7.1 Core Principle

Trend is not one indicator.

Open Analytics should describe trend using multiple dimensions:

```text
Direction
Slope
Strength
Persistence
Breakout State
Distance from Trend
Trend Alignment
Trend Maturity
Trend Stability
```

Do not reduce trend to one rule such as:

```text
price > SMA200
```

That is only one feature.

---

# 7.2 Required Inputs

Minimum inputs:

```text
instrument_key
date

adjusted_open
adjusted_high
adjusted_low
adjusted_close
```

Preferred:

```text
volume
return_1d

market benchmark
sector benchmark

data_quality_status
corporate_action_adjusted
```

---

# 7.3 Simple Moving Averages

Recommended moving averages:

```text
sma_5
sma_10
sma_20
sma_50
sma_100
sma_200
```

Formula:

```text
SMA_N =
mean(close over previous N trading sessions)
```

Use adjusted closing prices.

---

# 7.4 Exponential Moving Averages

Recommended:

```text
ema_5
ema_10
ema_20
ema_50
ema_100
ema_200
```

EMA gives more weight to recent prices.

Use a consistent smoothing convention.

---

# 7.5 Price Relative to Moving Average

For each key average:

```text
price_above_sma20
price_above_sma50
price_above_sma100
price_above_sma200
```

Also calculate normalized distance:

```text
distance_sma20_pct =
close / sma20 - 1
```

Likewise:

```text
distance_sma50_pct
distance_sma100_pct
distance_sma200_pct
```

This is more informative than a Boolean alone.

---

# 7.6 Moving Average Alignment

Trend structure can be classified from ordering.

Example bullish alignment:

```text
close > sma20 > sma50 > sma200
```

Bearish alignment:

```text
close < sma20 < sma50 < sma200
```

Store:

```text
ma_alignment_state
```

Possible values:

```text
STRONG_BULLISH
BULLISH
MIXED
BEARISH
STRONG_BEARISH
```

---

# 7.7 Golden Cross / Death Cross

Track structural crossovers such as:

```text
sma50 crossing above sma200
sma50 crossing below sma200
```

Store:

```text
golden_cross_flag
death_cross_flag

days_since_golden_cross
days_since_death_cross
```

These are slower trend-state features, not standalone signals.

---

# 7.8 Moving Average Slope

A moving average can be above another average but flattening.

Calculate slope:

```text
sma20_slope
sma50_slope
sma200_slope
```

Simple version:

```text
slope =
MA_today - MA_N_days_ago
```

Normalized:

```text
normalized_slope =
(MA_today / MA_N_days_ago - 1)
```

Better regression slope can also be used.

---

# 7.9 Linear Regression Price Slope

Fit:

```text
price ~ time
```

over rolling windows.

Recommended:

```text
price_slope_20d
price_slope_63d
price_slope_126d
```

Normalize slope by:

```text
price level
ATR
volatility
```

Possible:

```text
normalized_price_slope
```

---

# 7.10 Regression R-Squared for Trend

A strong trend should often have a relatively clean directional path.

Store:

```text
trend_r2_20d
trend_r2_63d
trend_r2_126d
```

Interpretation:

```text
High slope + high R²
→ cleaner trend

High slope + low R²
→ noisy trend
```

---

# 7.11 Trend Strength Score

A composite trend-strength score may eventually use:

```text
price slope
moving-average alignment
ADX
distance from moving averages
breakout status
trend R²
```

Output:

```text
trend_strength_score
```

Keep underlying components visible.

---

# 7.12 ADX

Average Directional Index measures trend strength rather than direction.

Store:

```text
adx_14
```

Also:

```text
plus_di_14
minus_di_14
```

Interpretation conceptually:

```text
higher ADX
→ stronger trend

+DI > -DI
→ directional bias upward

-DI > +DI
→ directional bias downward
```

Do not treat fixed ADX thresholds as universal truth; use research and percentile context.

---

# 7.13 Aroon

Aroon measures recency of highs and lows.

Store:

```text
aroon_up_25
aroon_down_25
aroon_oscillator_25
```

Useful for identifying emerging or weakening trends.

---

# 7.14 Donchian Channels

Rolling highest high and lowest low.

Recommended:

```text
donchian_high_20
donchian_low_20

donchian_high_55
donchian_low_55
```

Breakout flags:

```text
breakout_20d_high
breakdown_20d_low

breakout_55d_high
breakdown_55d_low
```

---

# 7.15 Rolling High / Low Structure

Track:

```text
high_20d
low_20d

high_63d
low_63d

high_126d
low_126d

high_252d
low_252d
```

These provide structural support/resistance context.

---

# 7.16 52-Week High Distance

Very important for momentum/trend research.

```text
distance_52w_high =
close / high_252d - 1
```

Example:

```text
Current close = 980
52W high      = 1000

distance_52w_high = -2%
```

Store:

```text
distance_52w_high
distance_52w_low
```

---

# 7.17 52-Week Position

Normalize price inside its annual range:

```text
position_52w =
(close - low_252d)
/
(high_252d - low_252d)
```

Range:

```text
0 → near annual low
1 → near annual high
```

This is useful as a continuous feature.

---

# 7.18 Breakout Strength

A breakout should not be treated only as true/false.

Possible metric:

```text
breakout_strength =
(close - prior_range_high)
/
ATR
```

or relative percentage:

```text
(close / prior_high) - 1
```

Store:

```text
breakout_strength_20d
breakout_strength_55d
```

---

# 7.19 Breakout Age

Track:

```text
days_since_20d_breakout
days_since_55d_breakout
```

This helps distinguish a fresh breakout from a mature trend.

---

# 7.20 Failed Breakout

A prior breakout that quickly falls back below the breakout level can be flagged.

Possible fields:

```text
failed_breakout_flag
days_since_failed_breakout
```

Useful for reversal and risk logic.

---

# 7.21 Higher Highs / Higher Lows

Trend structure can include local swing relationships.

Possible classification:

```text
higher_high
higher_low
lower_high
lower_low
```

At a broader level:

```text
swing_structure_state
```

Possible values:

```text
UPTREND_STRUCTURE
DOWNTREND_STRUCTURE
MIXED_STRUCTURE
```

Swing detection methodology must be deterministic and documented.

---

# 7.22 Trend Persistence

A strong trend should persist across multiple observations.

Possible measures:

```text
fraction_days_above_sma20
fraction_days_above_sma50
fraction_positive_slope_days
```

Over rolling windows:

```text
trend_persistence_20d
trend_persistence_63d
```

---

# 7.23 Directional Consistency

Measure how consistently daily returns follow one direction.

Example:

```text
positive_day_ratio_20d
negative_day_ratio_20d
```

But do not confuse return hit rate with trend quality alone.

---

# 7.24 Path Efficiency

One useful concept:

```text
efficiency_ratio =
absolute(net price change)
/
sum(absolute daily price changes)
```

Range:

```text
0 to 1
```

Higher values imply a cleaner directional path.

Store:

```text
efficiency_ratio_10d
efficiency_ratio_20d
efficiency_ratio_63d
```

---

# 7.25 Choppiness / Noise

Complementary metrics can measure sideways behavior.

Possible:

```text
choppiness_index
```

or derived from:

```text
low efficiency ratio
frequent MA crosses
low trend R²
```

Output:

```text
trend_noise_score
```

---

# 7.26 Trend Acceleration

Measure whether slope itself is increasing.

Possible:

```text
trend_acceleration =
short_term_slope - long_term_slope
```

Examples:

```text
price_slope_20d - price_slope_63d
sma20_slope - sma50_slope
```

Store:

```text
trend_acceleration_score
```

---

# 7.27 Trend Deceleration

Likewise detect weakening:

```text
positive long-term slope
+
falling short-term slope
```

Possible flag:

```text
trend_weakening_flag
```

---

# 7.28 Multi-Horizon Trend State

Trend should be measured at multiple horizons.

Recommended:

```text
trend_short
trend_medium
trend_long
```

Example:

```text
short  = BULLISH
medium = BULLISH
long   = BEARISH
```

This gives more context than one signal.

---

# 7.29 Trend Alignment Across Horizons

Create:

```text
multi_horizon_trend_alignment
```

Possible values:

```text
FULL_BULLISH
MOSTLY_BULLISH
MIXED
MOSTLY_BEARISH
FULL_BEARISH
```

---

# 7.30 Trend Regime State

Possible simplified state model:

```text
STRONG_UPTREND
WEAK_UPTREND
SIDEWAYS
WEAK_DOWNTREND
STRONG_DOWNTREND
```

Inputs could include:

```text
slope
ADX
MA alignment
price position
R²
```

Thresholds should be researched and configurable.

---

# 7.31 Trend Maturity

A trend can be:

```text
EARLY
DEVELOPING
MATURE
EXHAUSTED
```

Potential inputs:

```text
days since breakout
distance from long-term average
slope
trend persistence
volatility
momentum deceleration
```

This is a later composite feature, not required for first production.

---

# 7.32 Distance from Trend

A price can be in an uptrend but excessively extended.

Track:

```text
distance_sma20_pct
distance_sma50_pct
distance_sma200_pct

distance_ema20_pct
distance_ema50_pct
```

Standardize by ATR:

```text
distance_sma20_atr =
(close - sma20) / ATR
```

This helps detect overextension.

---

# 7.33 Trend Pullback State

Possible classification:

```text
UPTREND_PULLBACK
DOWNTREND_RALLY
TREND_CONTINUATION
NO_CLEAR_PULLBACK
```

Inputs:

```text
long-term trend direction
short-term price relative to MA
recent retracement
```

Useful for entry-timing models later.

---

# 7.34 Relative Trend vs Benchmark

Compare trend with market.

Possible features:

```text
relative_price_line =
stock_price / benchmark_price
```

Then calculate:

```text
relative_trend_slope_20d
relative_trend_slope_63d
```

This is closely related to relative momentum but useful structurally.

---

# 7.35 Relative Trend vs Sector

Similarly:

```text
stock_price / sector_index
```

Calculate:

```text
sector_relative_trend_slope
```

This helps identify stock-specific leadership.

---

# 7.36 Benchmark Trend Context

Store benchmark trend state alongside stock trend.

Example:

```text
stock_trend = STRONG_UPTREND
market_trend = DOWNTREND
```

This may represent unusually strong relative behavior.

---

# 7.37 Trend Percentile

Cross-sectional ranking:

```text
trend_strength_percentile
```

Also:

```text
slope_percentile
breakout_strength_percentile
```

Point-in-time universe rules apply.

---

# 7.38 Trend Z-Score

Possible standardized features:

```text
trend_strength_z
slope_z
distance_52w_high_z
```

These later feed factor and alpha models.

---

# 7.39 Trend Quality Score

Separate direction from quality.

Possible components:

```text
R²
efficiency ratio
persistence
few whipsaws
stable slope
```

Output:

```text
trend_quality_score
```

A stock can have positive slope but poor trend quality.

---

# 7.40 Whipsaw Detection

Frequent moving-average crossings imply unstable trend.

Track:

```text
sma20_cross_count_63d
sma50_cross_count_126d
```

Higher cross count can indicate choppiness.

---

# 7.41 Trend Reversal Detection

Potential early reversal features:

```text
slope sign change
MA crossover
new low after uptrend
breakdown below trend average
ADX weakening
relative strength deterioration
```

Output:

```text
trend_reversal_warning
```

Do not interpret as a guaranteed reversal.

---

# 7.42 Trend Confirmation by Volume

Trend Engine may consume outputs from Step 6.

Examples:

```text
breakout + high RVOL
uptrend + improving ADV
downtrend + heavy volume
```

Store:

```text
volume_confirmed_trend_flag
```

The detailed participation calculations remain in the Liquidity/Volume layers.

---

# 7.43 Trend Confirmation by Breadth

Later, market breadth can confirm or weaken trend confidence.

Example:

```text
stock bullish
sector breadth strong
market breadth strong
```

This integration belongs in later signal/regime stages.

---

# 7.44 Data Quality Requirements

Trend calculations require clean adjusted prices.

Potential invalid reasons:

```text
INSUFFICIENT_HISTORY
MISSING_PRICE_DATA
CORPORATE_ACTION_UNRESOLVED
STALE_PRICE
TOO_MANY_GAPS
```

Each metric should have a validity state.

---

# 7.45 IPO Handling

New listings should receive only valid short-history trend metrics.

Example:

```text
30 sessions available

sma20              available
sma50              unavailable
sma200             unavailable
distance_52w_high  unavailable as full 252-day metric
```

Do not fill unavailable values with zeros.

---

# 7.46 Suspended / Illiquid Stocks

Stale prices can create false flat trends.

Trend Engine must consume:

```text
stale_price_flag
trading_frequency
liquidity_quality
```

and lower confidence or invalidate metrics when needed.

---

# 7.47 Corporate Actions

All historical trend metrics should use adjusted price series.

Otherwise splits and bonuses can create:

```text
fake breakdowns
fake slopes
fake moving-average crosses
fake 52-week highs/lows
```

---

# 7.48 Point-in-Time Rule

At date T, calculate trend using only prices through T.

Do not use:

```text
future highs
future lows
future confirmed swings
future index membership
```

If swing-point detection requires future bars for confirmation, explicitly lag its availability.

---

# 7.49 Historical Universe Ranking

Cross-sectional trend percentiles must use the universe valid on that historical date.

This dependency comes from Step 1.

---

# 7.50 Recommended Daily Trend Record

A daily record could include:

```text
instrument_key
date


# MOVING AVERAGES

sma_5
sma_10
sma_20
sma_50
sma_100
sma_200

ema_5
ema_10
ema_20
ema_50
ema_100
ema_200


# PRICE RELATIVE TO TREND

distance_sma20_pct
distance_sma50_pct
distance_sma100_pct
distance_sma200_pct

price_above_sma20
price_above_sma50
price_above_sma100
price_above_sma200

ma_alignment_state


# SLOPE

sma20_slope
sma50_slope
sma200_slope

price_slope_20d
price_slope_63d
price_slope_126d

trend_r2_20d
trend_r2_63d


# TREND STRENGTH

adx_14
plus_di_14
minus_di_14

aroon_up_25
aroon_down_25
aroon_oscillator_25


# HIGH / LOW STRUCTURE

high_20d
low_20d

high_63d
low_63d

high_252d
low_252d

distance_52w_high
distance_52w_low
position_52w


# BREAKOUT

breakout_20d_high
breakdown_20d_low

breakout_55d_high
breakdown_55d_low

breakout_strength_20d
breakout_strength_55d

days_since_20d_breakout
days_since_55d_breakout


# PERSISTENCE / QUALITY

efficiency_ratio_20d
efficiency_ratio_63d

trend_persistence_20d
trend_persistence_63d

trend_quality_score
trend_noise_score

sma20_cross_count_63d


# STATE

trend_short
trend_medium
trend_long

multi_horizon_trend_alignment
trend_regime_state

trend_acceleration_score
trend_weakening_flag


# CROSS SECTION

trend_strength_percentile
slope_percentile

trend_strength_z


# QUALITY

trend_valid
trend_quality_status
trend_invalid_reason
```

---

# 7.51 Initial Production Metrics

First production version should prioritize:

```text
sma_20
sma_50
sma_100
sma_200

ema_20
ema_50
ema_200

price_above_sma20
price_above_sma50
price_above_sma200

distance_sma20_pct
distance_sma50_pct
distance_sma200_pct

ma_alignment_state

sma20_slope
sma50_slope
sma200_slope

price_slope_20d
price_slope_63d

trend_r2_20d
trend_r2_63d

adx_14
plus_di_14
minus_di_14

high_20d
low_20d
high_252d
low_252d

distance_52w_high
distance_52w_low
position_52w

breakout_20d_high
breakdown_20d_low

breakout_55d_high
breakdown_55d_low

efficiency_ratio_20d
efficiency_ratio_63d

trend_strength_percentile
trend_regime_state

trend_quality_status
```

Then add more advanced structure and reversal features.

---

# 7.52 Trend Engine Processing Flow

Recommended processing:

```text
VALID ADJUSTED PRICE SERIES
        ↓
HISTORY ELIGIBILITY
        ↓
MOVING AVERAGES
        ↓
PRICE / MA DISTANCES
        ↓
MA ALIGNMENT
        ↓
SLOPES
        ↓
REGRESSION TREND / R²
        ↓
ADX / DIRECTIONAL STRENGTH
        ↓
ROLLING HIGHS / LOWS
        ↓
52-WEEK POSITION
        ↓
BREAKOUT / BREAKDOWN
        ↓
PERSISTENCE / EFFICIENCY
        ↓
MULTI-HORIZON TREND STATE
        ↓
CROSS-SECTIONAL RANKS
        ↓
TREND SCORE / QUALITY
        ↓
QUALITY FLAGS
```

---

# 7.53 Important Quant Rules

## Rule 1 — Trend Is Multi-Dimensional

Do not reduce trend to one moving-average rule.

---

## Rule 2 — Use Adjusted Prices

Corporate actions must not generate fake trend breaks.

---

## Rule 3 — Direction and Strength Are Different

ADX may show strong trend strength without telling you whether the direction is up or down.

---

## Rule 4 — Use Multiple Horizons

Short, medium, and long trend states may disagree.

---

## Rule 5 — Measure Distance, Not Only Boolean State

Price 0.1% above SMA200 and 40% above SMA200 are very different conditions.

---

## Rule 6 — Clean Trends Matter

Slope plus R² / efficiency can distinguish orderly trends from noisy movement.

---

## Rule 7 — Breakouts Need Context

A breakout on strong participation differs from one on weak liquidity.

---

## Rule 8 — Avoid Future Confirmation Leakage

Swing and reversal logic must not use future bars unless availability is explicitly lagged.

---

## Rule 9 — Ranks Must Be Point-in-Time

Historical trend percentiles must use the correct historical universe.

---

## Rule 10 — Preserve Components

Do not expose only one trend score.

Store the moving averages, slopes, ranges, breakout state, and quality metrics too.

---

# 7.54 Completion Criteria

Step 7 is complete when Open Analytics can answer:

1. Is the stock above or below its major moving averages?
2. Are the moving averages bullishly or bearishly aligned?
3. Are those moving averages rising or falling?
4. What is the short-term price slope?
5. What is the medium-term price slope?
6. How clean is the trend statistically?
7. How strong is the trend according to directional measures?
8. Is the stock near a 20-day, 55-day, or 52-week high?
9. Is it breaking out or breaking down?
10. How strong is the breakout?
11. How far is price from its 52-week high?
12. Where is price positioned within the 52-week range?
13. Is the trend persistent or choppy?
14. Is the trend accelerating or weakening?
15. Do short-, medium-, and long-term trends agree?
16. How does trend strength rank against peers?
17. Is the observed trend based on sufficient clean data?
18. Is the trend state usable by the next-stage Momentum Engine?

Once these are reliable, the Trend Engine is ready to feed:

```text
Step 8 — Momentum Engine
```

---

# Step 7 Final Output

The Trend Engine transforms:

```text
Adjusted Price History
```

into:

```text
Moving Averages
Moving-Average Alignment
Price-to-Trend Distances
Trend Slopes
Trend R-Squared
ADX / Directional Measures
Rolling Highs and Lows
52-Week Position
Breakout / Breakdown State
Trend Persistence
Path Efficiency
Multi-Horizon Trend State
Trend Rankings
Trend Quality Flags
```

This becomes the structural price-direction layer for Open Analytics.
