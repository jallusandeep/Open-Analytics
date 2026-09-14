# Open Analytics — Step 17: Market Breadth Engine

## Purpose

The **Market Breadth Engine** measures how broadly market moves are being supported across stocks, sectors, industries, and market-cap groups.

An index can rise even when only a small number of heavyweight stocks are strong.

Breadth answers:

- How many stocks are actually participating?
- Are advances broad or narrow?
- Are more stocks making new highs or new lows?
- How many stocks are above key moving averages?
- Is participation strengthening or weakening?
- Is index strength confirmed by the broader market?
- Is breadth improving before price?
- Is breadth deteriorating while the index still rises?
- Which sectors are leading or weakening?
- Is the market in broad accumulation, narrow leadership, or broad distribution?

Breadth outputs feed directly into:

- Market Regime Engine
- Alpha / Signal Engine
- Risk overlays
- Sector rotation
- Portfolio exposure
- Market timing research
- Machine learning features

---

# 17.1 Core Principle

Market breadth should describe:

```text
Participation
Direction
Strength
Persistence
Leadership
Deterioration
Divergence
Concentration
```

Do not judge the market only from the index return.

---

# 17.2 Required Inputs

Minimum:

```text
date
universe_id

instrument_key
return_1d

adjusted_close

sma20
sma50
sma100
sma200

high_252d
low_252d
```

Preferred:

```text
sector
industry
market_cap_bucket

volume
liquidity eligibility
trend state
momentum state

index return
index price
```

Optional:

```text
advance volume
decline volume
new-high/new-low history
equal-weighted index
```

---

# 17.3 Historical Universe Requirement

Breadth must use the universe valid on each historical date.

Example:

```text
NIFTY_500 breadth on 2019-01-02
```

must use members eligible on that date.

Do not use today's NIFTY 500 constituents for historical breadth.

---

# 17.4 Eligible Breadth Universe

Possible universes:

```text
NIFTY_50
NIFTY_100
NIFTY_200
NIFTY_500
ALL_LIQUID_NSE
FNO_UNIVERSE
LARGE_CAP
MID_CAP
SMALL_CAP
```

Breadth must always identify which universe it describes.

---

# 17.5 Advancing Stocks

Count stocks where:

```text
return_1d > 0
```

Store:

```text
advancers
```

---

# 17.6 Declining Stocks

Count:

```text
return_1d < 0
```

Store:

```text
decliners
```

---

# 17.7 Unchanged Stocks

Count:

```text
return_1d == 0
```

Store:

```text
unchanged
```

Use tolerance if necessary for floating-point calculations.

---

# 17.8 Advance-Decline Difference

```text
ad_difference =
advancers - decliners
```

Store:

```text
ad_difference
```

---

# 17.9 Advance-Decline Ratio

```text
ad_ratio =
advancers / decliners
```

Handle zero decliners safely.

Store:

```text
ad_ratio
```

---

# 17.10 Advance Percentage

```text
advance_pct =
advancers / valid_stock_count
```

Store:

```text
advance_pct
decline_pct
```

---

# 17.11 Advance-Decline Line

Cumulative:

```text
AD_line_t =
AD_line_(t-1)
+
advancers
-
decliners
```

Store:

```text
advance_decline_line
```

This is one of the most important breadth series.

---

# 17.12 AD Line Slope

Calculate:

```text
ad_line_slope_20d
ad_line_slope_60d
```

This helps identify improving/deteriorating participation.

---

# 17.13 AD Line New High

Store:

```text
ad_line_new_high_252d
```

Useful for confirmation/divergence analysis.

---

# 17.14 Equal-Weighted Market Return

Calculate:

```text
equal_weight_return =
mean(stock returns in valid universe)
```

Store:

```text
equal_weight_return_1d
equal_weight_return_5d
equal_weight_return_21d
```

This reduces index-weight concentration effects.

---

# 17.15 Cap-Weighted vs Equal-Weighted Spread

```text
breadth_return_spread =
equal_weight_return
-
cap_weighted_index_return
```

Interpretation:

```text
positive
→ broader stocks outperforming index

negative
→ large-cap/index concentration
```

---

# 17.16 Percentage Above SMA20

```text
pct_above_sma20 =
count(close > sma20)
/
valid_count
```

Store:

```text
pct_above_sma20
```

---

# 17.17 Percentage Above SMA50

```text
pct_above_sma50
```

---

# 17.18 Percentage Above SMA100

```text
pct_above_sma100
```

---

# 17.19 Percentage Above SMA200

```text
pct_above_sma200
```

This is a major long-term breadth measure.

---

# 17.20 Percentage Above EMA

Optional:

```text
pct_above_ema20
pct_above_ema50
pct_above_ema200
```

---

# 17.21 Breadth by Trend State

Using Step 7:

```text
pct_strong_uptrend
pct_uptrend
pct_sideways
pct_downtrend
pct_strong_downtrend
```

This gives richer structure than MA percentages alone.

---

# 17.22 Breadth by Momentum State

Using Step 8:

```text
pct_strong_positive_momentum
pct_positive_momentum
pct_negative_momentum
```

---

# 17.23 New 20-Day Highs

Count:

```text
close >= prior_20d_high
```

Store:

```text
new_highs_20d
```

---

# 17.24 New 20-Day Lows

Store:

```text
new_lows_20d
```

---

# 17.25 New 52-Week Highs

Count:

```text
new_highs_252d
```

---

# 17.26 New 52-Week Lows

Count:

```text
new_lows_252d
```

---

# 17.27 High-Low Difference

```text
high_low_difference =
new_highs_252d - new_lows_252d
```

---

# 17.28 High-Low Ratio

```text
high_low_ratio =
new_highs_252d / new_lows_252d
```

Handle zero safely.

---

# 17.29 High-Low Index

Possible:

```text
high_low_index =
new_highs
/
(new_highs + new_lows)
```

Range:

```text
0 to 1
```

---

# 17.30 High-Low Line

Cumulative:

```text
high_low_line_t =
high_low_line_(t-1)
+
new_highs
-
new_lows
```

---

# 17.31 New-High Participation Percentage

```text
new_high_pct =
new_highs / valid_count
```

Similarly:

```text
new_low_pct
```

---

# 17.32 Breadth Thrust

Breadth thrust attempts to detect a rapid shift from weak to strong participation.

Possible input:

```text
advance_pct
```

smoothed over several sessions.

Store:

```text
breadth_thrust_score
```

Any exact named breadth-thrust formula should only be used if implemented precisely.

---

# 17.33 McClellan-Style Oscillator

Possible future breadth oscillator using smoothed net advances.

Concept:

```text
short EMA of net advances
-
long EMA of net advances
```

Store:

```text
mcclellan_style_oscillator
```

Only label it exact McClellan Oscillator if methodology matches the published definition.

---

# 17.34 Breadth Momentum

Measure change in participation.

Examples:

```text
pct_above_sma50_change_5d
pct_above_sma200_change_21d

advance_pct_change_5d
```

Store:

```text
breadth_momentum_score
```

---

# 17.35 Breadth Acceleration

Second-order improvement:

```text
breadth_acceleration
```

Possible from:

```text
breadth momentum today
-
breadth momentum prior period
```

---

# 17.36 Breadth Persistence

Measure how long breadth remains strong or weak.

Possible:

```text
days_pct_above_sma50_gt_60
days_advance_pct_gt_60
```

Output:

```text
breadth_persistence_score
```

---

# 17.37 Up Volume

Aggregate volume for advancing stocks:

```text
up_volume =
sum(volume where return > 0)
```

---

# 17.38 Down Volume

```text
down_volume =
sum(volume where return < 0)
```

---

# 17.39 Up/Down Volume Ratio

```text
up_down_volume_ratio =
up_volume / down_volume
```

---

# 17.40 Up-Volume Percentage

```text
up_volume_pct =
up_volume
/
(up_volume + down_volume)
```

---

# 17.41 Traded-Value Breadth

Use rupee traded value instead of shares.

```text
up_traded_value
down_traded_value
```

Then:

```text
up_down_value_ratio
```

This may be more meaningful across securities with different prices.

---

# 17.42 Volume Breadth Confirmation

Possible state:

```text
price breadth positive
+
up-volume dominance
```

Store:

```text
volume_breadth_confirmation
```

---

# 17.43 Sector Breadth

For every sector:

```text
sector_advancers
sector_decliners
sector_advance_pct

sector_pct_above_sma50
sector_pct_above_sma200

sector_new_highs
sector_new_lows
```

---

# 17.44 Sector Breadth Rank

Rank sectors by:

```text
advance_pct
pct_above_sma50
pct_above_sma200
new-high participation
```

Store:

```text
sector_breadth_score
sector_breadth_rank
```

---

# 17.45 Industry Breadth

Similarly:

```text
industry_breadth_score
```

where industry peer count is sufficient.

---

# 17.46 Large-Cap Breadth

Store:

```text
large_cap_advance_pct
large_cap_pct_above_sma50
```

---

# 17.47 Mid-Cap Breadth

Store:

```text
mid_cap_advance_pct
mid_cap_pct_above_sma50
```

---

# 17.48 Small-Cap Breadth

Store:

```text
small_cap_advance_pct
small_cap_pct_above_sma50
```

This can reveal risk appetite.

---

# 17.49 Size Breadth Divergence

Example:

```text
large caps strong
small caps weak
```

Store:

```text
size_breadth_divergence
```

---

# 17.50 Index-Breadth Divergence

Possible bearish divergence:

```text
index makes new high
AD line does not
```

Possible bullish divergence:

```text
index makes new low
breadth improves
```

Store deterministic flags:

```text
bearish_breadth_divergence
bullish_breadth_divergence
```

---

# 17.51 SMA Breadth Divergence

Example:

```text
index rising
pct_above_sma50 falling
```

Store:

```text
sma50_breadth_divergence
```

---

# 17.52 New-High Divergence

Example:

```text
index near record high
new 52W highs declining
```

Store:

```text
new_high_divergence
```

---

# 17.53 Breadth Confirmation

Possible:

```text
index uptrend
+
AD line uptrend
+
pct_above_sma200 high
```

Store:

```text
breadth_confirmation_score
```

---

# 17.54 Market Participation Score

Possible components:

```text
advance_pct
AD line slope
pct above SMA50
pct above SMA200
new-high/new-low balance
up-volume ratio
```

Output:

```text
market_participation_score
```

---

# 17.55 Breadth Score

Composite:

```text
breadth_score
```

Possible range:

```text
0 to 100
```

Recommended interpretation:

```text
0   = extremely weak breadth
100 = extremely strong breadth
```

Keep components visible.

---

# 17.56 Breadth Regime

Possible:

```text
VERY_STRONG
STRONG
NEUTRAL
WEAK
VERY_WEAK
```

Store:

```text
breadth_regime
```

---

# 17.57 Narrow Leadership State

Possible when:

```text
index positive
equal-weight weak
pct above SMA50 weak
few new highs
```

Store:

```text
narrow_leadership_flag
```

---

# 17.58 Broad Participation State

Possible when:

```text
index positive
equal-weight strong
advance_pct high
new highs expanding
```

Store:

```text
broad_participation_flag
```

---

# 17.59 Broad Distribution State

Possible when:

```text
decliners dominate
down-volume dominates
new lows expand
pct above MAs declines
```

Store:

```text
broad_distribution_flag
```

---

# 17.60 Capitulation Breadth

Potential:

```text
extreme decline_pct
extreme down-volume
extreme new lows
```

Store:

```text
breadth_capitulation_flag
```

This is contextual, not a guaranteed bottom.

---

# 17.61 Breadth Recovery

Possible when:

```text
market still near lows
but advance_pct / AD line / SMA breadth improve
```

Store:

```text
breadth_recovery_flag
```

---

# 17.62 Breadth and Volatility

Combine with risk:

```text
weak breadth + rising VIX
```

can indicate stressed regime.

Store:

```text
breadth_volatility_state
```

---

# 17.63 Breadth and Institutional Flow

Combine with Step 15:

```text
FII buying + broad breadth
FII buying + narrow breadth
```

Store:

```text
flow_breadth_state
```

---

# 17.64 Breadth and Derivatives

Combine with Step 16:

```text
strong breadth + futures long buildup
```

or:

```text
weak breadth + high put skew
```

This belongs later in Market Regime Engine.

---

# 17.65 Breadth Dispersion

Measure variation across sectors or stocks.

Possible:

```text
sector_breadth_dispersion
```

High dispersion may indicate rotation rather than broad market trend.

---

# 17.66 Breadth Concentration

Measure how much of index performance comes from few names.

Possible:

```text
top_5_contribution_share
top_10_contribution_share
```

Requires index weights and constituent returns.

Store:

```text
index_concentration_score
```

---

# 17.67 Contribution Breadth

Count how many stocks contribute positively to index return.

Possible:

```text
positive_index_contributors
```

---

# 17.68 Equal-Weight Relative Strength

Track:

```text
equal_weight_index / cap_weight_index
```

Slope:

```text
equal_weight_relative_slope
```

This can identify broadening or narrowing participation.

---

# 17.69 Breadth Historical Percentile

Compare current breadth with own history:

```text
breadth_percentile_252d
```

Possible for:

```text
advance_pct
pct_above_sma50
pct_above_sma200
```

---

# 17.70 Breadth Z-Score

Store:

```text
advance_pct_z
sma50_breadth_z
sma200_breadth_z
```

---

# 17.71 Breadth Shock

Detect sudden collapse/improvement.

Possible:

```text
breadth_change_1d
breadth_change_5d
```

Store:

```text
breadth_shock_flag
```

---

# 17.72 Historical Breadth Snapshot

Recommended per date:

```text
date
universe_id

valid_stock_count

advancers
decliners
unchanged

advance_pct
decline_pct

ad_difference
ad_ratio
advance_decline_line

equal_weight_return

pct_above_sma20
pct_above_sma50
pct_above_sma100
pct_above_sma200

new_highs_20d
new_lows_20d
new_highs_252d
new_lows_252d

high_low_difference

up_volume
down_volume
up_volume_pct

breadth_score
breadth_regime

breadth_confirmation_score
breadth_percentile_252d

breadth_quality_status
```

---

# 17.73 Sector Breadth Record

```text
date
sector_id

valid_count

advance_pct
pct_above_sma50
pct_above_sma200

new_high_pct
new_low_pct

sector_breadth_score
sector_breadth_rank
```

---

# 17.74 Initial Production Metrics

Recommended first production set:

```text
advancers
decliners
unchanged

advance_pct
decline_pct

ad_difference
ad_ratio
advance_decline_line

equal_weight_return_1d
breadth_return_spread

pct_above_sma20
pct_above_sma50
pct_above_sma200

new_highs_20d
new_lows_20d

new_highs_252d
new_lows_252d

high_low_difference

up_volume
down_volume
up_down_volume_ratio

sector_advance_pct
sector_pct_above_sma50

breadth_confirmation_score
breadth_score
breadth_regime

narrow_leadership_flag
broad_participation_flag

breadth_quality_status
```

Then expand into:

```text
advanced breadth thrust
contribution breadth
index concentration
industry breadth
intraday breadth
```

---

# 17.75 Breadth Engine Processing Flow

Recommended:

```text
POINT-IN-TIME UNIVERSE
        ↓
VALID DAILY STOCK DATA
        ↓
ADVANCERS / DECLINERS
        ↓
AD RATIO / AD LINE
        ↓
EQUAL-WEIGHT RETURN
        ↓
% ABOVE MOVING AVERAGES
        ↓
NEW HIGHS / NEW LOWS
        ↓
UP / DOWN VOLUME
        ↓
SECTOR / SIZE BREADTH
        ↓
BREADTH MOMENTUM
        ↓
INDEX-BREADTH DIVERGENCE
        ↓
CONCENTRATION / LEADERSHIP
        ↓
BREADTH SCORE
        ↓
BREADTH REGIME
        ↓
QUALITY FLAGS
```

---

# 17.76 Point-in-Time Rule

At date T, breadth may only use:

```text
universe membership at T
prices through T
moving averages through T
sector mapping at T
```

No future information.

---

# 17.77 Missing Data

Only valid, eligible stocks should enter denominator.

Track:

```text
eligible_count
valid_count
missing_count
```

Breadth quality can deteriorate when too many members are missing.

---

# 17.78 Minimum Coverage

Possible rule:

```text
breadth_valid =
valid_count / eligible_count >= threshold
```

Store:

```text
breadth_coverage_pct
```

---

# 17.79 Suspensions and Stale Stocks

Do not treat stale/no-trade stocks as unchanged by default.

Consume:

```text
trading_status
stale_price_flag
```

Exclude or handle explicitly.

---

# 17.80 Corporate Actions

Breadth should use adjusted price-based trend metrics to avoid false breakdowns.

---

# 17.81 Universe Changes

When stocks enter/leave an index/universe:

```text
AD line methodology
```

should remain internally consistent.

Track constituent changes.

---

# 17.82 Breadth Data Quality Status

Possible:

```text
VALID
LOW_COVERAGE
STALE_COMPONENTS
UNIVERSE_MAPPING_ISSUE
MISSING_VOLUME
INVALID
```

---

# 17.83 Research Diagnostics

Test breadth against:

```text
future index returns
future volatility
drawdowns
market regime changes
sector rotation
```

---

# 17.84 Breadth Predictive Tests

Examples:

```text
future return after extreme breadth weakness
future return after breadth thrust
future drawdown after bearish divergence
```

These are research diagnostics, not direct live rules.

---

# 17.85 Breadth Regime Transition

Track transitions:

```text
WEAK → NEUTRAL
NEUTRAL → STRONG
STRONG → WEAK
```

Store:

```text
breadth_regime_change
```

---

# 17.86 Important Quant Rules

## Rule 1 — Index Return Is Not Breadth

A few heavyweight stocks can move the index.

## Rule 2 — Universe Definition Matters

Breadth is meaningless without a clearly defined universe.

## Rule 3 — Use Historical Constituents

Avoid survivorship bias.

## Rule 4 — Denominators Must Use Valid Stocks

Missing/stale names should not silently distort percentages.

## Rule 5 — Breadth Must Be Multi-Dimensional

Use advances, MA breadth, highs/lows, and volume.

## Rule 6 — Equal-Weight Comparison Is Valuable

It helps reveal narrow leadership.

## Rule 7 — Divergence Needs Deterministic Rules

Avoid subjective chart interpretation.

## Rule 8 — Broad Participation and Narrow Leadership Are Different Regimes

Preserve that distinction.

## Rule 9 — Breadth Can Lead or Lag

Backtest the relationship rather than assuming predictive power.

## Rule 10 — Keep Components Visible

Do not rely only on one breadth score.

---

# 17.87 Completion Criteria

Step 17 is complete when Open Analytics can answer:

1. How many stocks advanced?
2. How many declined?
3. What is the advance percentage?
4. What is the advance-decline ratio?
5. What is the AD line doing?
6. Is equal-weight performance stronger or weaker than the cap-weighted index?
7. What percentage of stocks are above SMA20?
8. What percentage are above SMA50?
9. What percentage are above SMA200?
10. How many stocks are making new 20D highs/lows?
11. How many are making new 52W highs/lows?
12. Is up-volume or down-volume dominant?
13. Which sectors have the strongest breadth?
14. Are large caps, mid caps, and small caps participating equally?
15. Is the index being driven by only a few stocks?
16. Is breadth confirming the index trend?
17. Is there bearish or bullish breadth divergence?
18. Is participation broadening or narrowing?
19. What is the current breadth score/regime?
20. Is breadth data sufficiently complete and point-in-time correct?

Once these are reliable, the Market Breadth Engine is ready to feed:

```text
Step 18 — Market Regime Engine
```

---

# Step 17 Final Output

The Market Breadth Engine transforms:

```text
Point-in-Time Universe
+
Stock Returns
+
Trend States
+
Volume
```

into:

```text
Advance/Decline Statistics
Advance-Decline Line
Equal-Weight Market Return
Moving-Average Breadth
New High/New Low Breadth
Up/Down Volume Breadth
Sector Breadth
Size Breadth
Breadth Momentum
Breadth Divergence
Leadership Concentration
Breadth Confirmation
Breadth Score
Breadth Regime
Breadth Quality Flags
```

This becomes the market-participation layer for Open Analytics.
