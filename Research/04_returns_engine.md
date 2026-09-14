# Open Analytics — Step 4: Returns Engine

## Purpose

The **Returns Engine** converts adjusted market prices into return series that become the mathematical foundation for almost every later quantitative calculation in Open Analytics.

Returns feed directly into:

- Risk
- Volatility
- Beta
- Correlation
- Drawdown
- Momentum
- Relative strength
- Factor models
- Alpha models
- Portfolio construction
- Backtesting
- Performance attribution
- Machine learning targets

The Returns Engine must be point-in-time correct, corporate-action aware, benchmark aware, sector aware, and consistent across all securities.

---

# 4.1 Core Principle

Returns must be calculated from the correct price series.

The engine should support at least:

```text
Raw price return
Adjusted price return
Total return
Benchmark-relative return
Sector-relative return
Residual / risk-adjusted return
```

Do not use raw prices for long-horizon return calculations when corporate actions have materially changed the price series.

---

# 4.2 Required Input Data

Minimum input:

```text
instrument_key
date

open
high
low
close
volume
```

Preferred adjusted input:

```text
adjusted_open
adjusted_high
adjusted_low
adjusted_close
adjusted_volume
```

Additional data:

```text
total_return_close

benchmark_id
benchmark_close

sector_id
sector_index_close

trading_calendar
corporate_action_flags
data_quality_flags
```

---

# 4.3 Daily Close-to-Close Return

The standard simple return:

```text
return_1d = current_close / previous_close - 1
```

Formula:

R_t = P_t / P_(t-1) - 1

Example:

```text
Previous close = 100
Current close  = 103

return_1d = 3%
```

Preferred price source:

```text
adjusted_close
```

for historically comparable returns.

---

# 4.4 Log Return

Log return:

```text
log_return_1d = ln(current_close / previous_close)
```

Formula:

r_t = ln(P_t / P_(t-1))

Useful for:

```text
statistical modeling
volatility estimation
time-series aggregation
risk models
machine learning features
```

Simple return and log return should both be stored.

They are not interchangeable for every use case.

---

# 4.5 Intraday Return

Measures open-to-close movement.

```text
intraday_return =
adjusted_close / adjusted_open - 1
```

Useful for:

```text
intraday direction
session momentum
open-to-close strategies
market behavior analysis
```

---

# 4.6 Overnight Return

Measures previous close to current open.

```text
overnight_return =
adjusted_open_today / adjusted_close_previous_session - 1
```

This separates overnight information from regular trading-session movement.

Useful for:

```text
earnings reactions
global-market effects
overnight gap behavior
news-driven moves
```

---

# 4.7 High-Low Range Return

Optional diagnostic metrics:

```text
high_low_range_pct =
high / low - 1
```

Additional:

```text
open_to_high_return
open_to_low_return
close_to_high_distance
close_to_low_distance
```

These are useful later for volatility and intraday behavior models.

---

# 4.8 Multi-Period Returns

Calculate standard trading-session horizons.

Recommended:

```text
return_2d
return_3d
return_5d
return_10d

return_21d
return_42d
return_63d

return_126d
return_189d
return_252d

return_504d
return_756d
return_1260d
```

Approximate interpretation:

```text
5D    ≈ 1 trading week
21D   ≈ 1 trading month
63D   ≈ 3 months
126D  ≈ 6 months
252D  ≈ 1 year
504D  ≈ 2 years
756D  ≈ 3 years
1260D ≈ 5 years
```

Formula:

```text
return_Nd =
price_today / price_N_sessions_ago - 1
```

Do not use calendar-day offsets for trading-horizon returns.

Use exchange trading sessions.

---

# 4.9 Monthly, Quarterly and Annual Calendar Returns

In addition to fixed-session returns, calculate true calendar-period returns.

Examples:

```text
MTD return
QTD return
YTD return

previous_month_return
previous_quarter_return
previous_year_return
```

For MTD:

```text
MTD =
current_price / last_price_before_month_start - 1
```

For YTD:

```text
YTD =
current_price / last_price_before_year_start - 1
```

Use actual available trading dates rather than assuming January 1 or month-end was a trading day.

---

# 4.10 Cumulative Return

From a selected start date:

```text
cumulative_return =
current_value / start_value - 1
```

For daily return series:

```text
cumulative_return =
product(1 + daily_return) - 1
```

Useful for:

```text
equity curves
strategy NAV
stock performance comparison
benchmark comparison
```

---

# 4.11 Annualized Return

For periods longer than one year:

```text
annualized_return =
(ending_value / starting_value)^(1 / years) - 1
```

This is commonly referred to as CAGR when applied to compounded growth over multiple years.

Store:

```text
cagr_2y
cagr_3y
cagr_5y
```

only where sufficient history exists.

---

# 4.12 Price Return vs Total Return

These must remain separate.

## Price Return

Uses adjusted market price but excludes cash distributions from investor wealth.

```text
price_return
```

## Total Return

Includes reinvested distributions such as dividends where appropriate.

```text
total_return
```

Conceptually:

```text
total_return =
(price_change + distributions) / prior_value
```

For long-term investor performance, total return is usually more meaningful.

For some technical strategies, split-adjusted price return may be preferred.

---

# 4.13 Dividend Return Component

Where dividend data is available:

```text
dividend_return =
cash_dividend / reference_price
```

Then conceptually:

```text
total_return
≈
price_return + dividend_return
```

Exact handling depends on timing and reinvestment assumptions.

Store the components separately when possible.

---

# 4.14 Benchmark Return

Every security should have a relevant benchmark.

Examples:

```text
NIFTY 50
NIFTY 100
NIFTY 500
Broad NSE market index
```

Calculate benchmark returns over the same dates and horizons.

```text
benchmark_return_1d
benchmark_return_5d
benchmark_return_21d
benchmark_return_63d
benchmark_return_126d
benchmark_return_252d
```

Date alignment is mandatory.

---

# 4.15 Excess Return

Simple benchmark-relative return:

```text
excess_return =
stock_return - benchmark_return
```

Examples:

```text
excess_return_1d
excess_return_21d
excess_return_63d
excess_return_126d
excess_return_252d
```

Example:

```text
Stock 3M return = +18%
NIFTY 3M return = +7%

Excess return = +11%
```

This is much more informative than raw return alone.

---

# 4.16 Sector-Relative Return

Compare each stock against its sector benchmark.

```text
sector_relative_return =
stock_return - sector_return
```

Store:

```text
sector_relative_return_5d
sector_relative_return_21d
sector_relative_return_63d
sector_relative_return_126d
sector_relative_return_252d
```

Example:

```text
Stock 6M return   = +25%
Sector 6M return  = +17%

Sector-relative return = +8%
```

This helps distinguish company-specific strength from sector-wide strength.

---

# 4.17 Industry-Relative Return

If industry indices or industry portfolios are available:

```text
industry_relative_return =
stock_return - industry_return
```

This allows finer peer comparisons than broad sector classifications.

---

# 4.18 Relative Strength

Relative strength should be treated as a family of metrics rather than one indicator.

Possible calculations:

```text
market_relative_21d
market_relative_63d
market_relative_126d
market_relative_252d

sector_relative_21d
sector_relative_63d
sector_relative_126d
sector_relative_252d
```

Later these can be ranked across the universe.

---

# 4.19 Return Percentile Ranking

For every date and universe:

```text
return_percentile_5d
return_percentile_21d
return_percentile_63d
return_percentile_126d
return_percentile_252d
```

Example:

```text
return_percentile_63d = 94
```

means the stock outperformed approximately 94% of eligible universe members over the same horizon.

This is more useful for cross-sectional research than raw return alone.

---

# 4.20 Return Z-Score

Calculate standardized cross-sectional returns:

```text
return_zscore_Nd =
(stock_return_Nd - universe_mean_return_Nd)
/
universe_std_return_Nd
```

Possible outputs:

```text
return_z_5d
return_z_21d
return_z_63d
return_z_126d
return_z_252d
```

Prefer robust preprocessing before z-scoring when extreme outliers exist.

---

# 4.21 Winsorized Return

Extreme values can dominate universe statistics.

Maintain both:

```text
raw_return
winsorized_return
```

Possible cross-sectional preprocessing:

```text
1st percentile floor
99th percentile cap
```

or another configurable robust method.

Never overwrite the original return value.

---

# 4.22 Sector-Neutral Return Rank

A stock should optionally be compared only with sector peers.

Calculate:

```text
sector_return_percentile
sector_return_zscore
```

This becomes useful later for sector-neutral momentum factors.

---

# 4.23 Return Consistency

A quant cares not only about total return but how consistently it was generated.

Possible metrics derived later from return series:

```text
positive_day_ratio
positive_week_ratio
positive_month_ratio

return_hit_rate
up_capture
down_capture
```

These belong near the boundary between Returns and Performance/Risk engines.

The Returns Engine should provide clean underlying return series required for them.

---

# 4.24 Positive and Negative Return Flags

For each session:

```text
is_positive_return
is_negative_return
is_zero_return
```

Useful for:

```text
hit-rate calculations
streak calculations
breadth statistics
behavioral analysis
```

---

# 4.25 Return Streaks

Optional derived features:

```text
positive_streak_days
negative_streak_days

max_positive_streak
max_negative_streak
```

These may later feed momentum and behavioral models.

---

# 4.26 Gap Return

Explicitly store gap return:

```text
gap_return =
open_today / close_previous_session - 1
```

Classify:

```text
gap_up
gap_down
no_material_gap
```

Possible threshold should be configurable.

---

# 4.27 Gap-Adjusted Intraday Behavior

Useful decomposition:

```text
daily_return
=
overnight effect
+
intraday effect
+
interaction
```

Store the underlying components rather than relying on one daily number.

---

# 4.28 Open-to-Open Return

For strategies executed at market open:

```text
open_to_open_return =
open_today / open_previous_session - 1
```

This can be more appropriate than close-to-close return for some backtests.

---

# 4.29 Close-to-Next-Open Forward Return

For predictive research:

```text
forward_overnight_return_1d
```

Similarly:

```text
forward_intraday_return_1d
forward_close_return_1d
```

Forward returns are targets, not features.

They must never leak into same-date model inputs.

---

# 4.30 Forward Returns for ML and Signal Research

Recommended target horizons:

```text
forward_return_1d
forward_return_2d
forward_return_5d
forward_return_10d
forward_return_21d
forward_return_63d
```

Formula:

```text
forward_return_Nd =
future_price_N_sessions / current_price - 1
```

Critical rule:

```text
Forward returns are only labels / targets.
They must never be available to the prediction timestamp.
```

---

# 4.31 Risk-Free Excess Return

For Sharpe-like later calculations:

```text
risk_free_excess_return =
asset_return - risk_free_return
```

Risk-free data should be frequency aligned.

This output may be generated in the Risk engine, but the Returns Engine should support the required alignment.

---

# 4.32 Residual Return

More advanced models should separate market-driven return from unexplained return.

Conceptually:

```text
stock_return =
alpha
+ beta_market × market_return
+ beta_sector × sector_return
+ residual
```

Then:

```text
residual_return
```

becomes useful for:

```text
idiosyncratic momentum
event studies
statistical arbitrage
alpha research
```

The full residual model belongs in later factor/risk layers, but Returns should supply aligned inputs.

---

# 4.33 Trading Calendar Alignment

Never calculate return merely by subtracting calendar dates.

Use official trading sessions.

Example:

```text
Friday close
→ Monday close
```

is a one-session return even though three calendar days passed.

Requirements:

```text
exchange_calendar
session_date
previous_valid_session
next_valid_session
```

---

# 4.34 Missing Data Handling

Do not silently forward-fill missing stock prices for normal return calculation.

If required price observations are missing:

```text
return = null
return_valid = false
```

Store:

```text
return_invalid_reason
```

Possible reasons:

```text
MISSING_CURRENT_PRICE
MISSING_PRIOR_PRICE
INSUFFICIENT_HISTORY
DATA_QUALITY_FAILURE
CORPORATE_ACTION_UNRESOLVED
```

---

# 4.35 Suspensions and No-Trade Sessions

A no-trade day is not necessarily a true 0% market return.

Distinguish:

```text
valid zero movement
no trading
missing data
suspended security
```

Do not automatically turn absent observations into zero returns.

---

# 4.36 Corporate Action Protection

Before calculating returns:

```text
if unresolved_corporate_action:
    do not trust raw return
```

Store:

```text
corporate_action_adjusted
corporate_action_validated
```

The Returns Engine should consume the output of Step 3.

---

# 4.37 IPO Handling

For newly listed stocks:

```text
return_1d may become available quickly
return_21d requires enough sessions
return_252d remains unavailable until enough history exists
```

Do not fill unavailable long-horizon returns with zero.

Use:

```text
null
eligible = false
```

---

# 4.38 Delisting Handling

Historical return data must remain available after a stock leaves the current universe.

For delisting or terminal events, preserve:

```text
last_valid_return
last_trade_date
terminal_status
```

Backtesting must not silently remove securities before the actual historical exit date.

---

# 4.39 Extreme Return Detection

Returns Engine should flag unusually large moves.

Examples:

```text
abs(return_1d) > configured threshold
return_zscore extremely high
price ratio inconsistent with corporate actions
```

Store:

```text
return_outlier_flag
return_outlier_reason
```

Do not automatically delete extreme market moves.

A 20% genuine move can be valid information.

---

# 4.40 Return Quality Flags

Recommended:

```text
return_valid
return_quality_status

price_source
adjustment_source

corporate_action_adjusted
benchmark_aligned
sector_aligned

outlier_flag
missing_input_flag
```

---

# 4.41 Recommended Daily Returns Record

A daily record may include:

```text
instrument_key
date

# PRICES

adjusted_open
adjusted_close
total_return_close


# DAILY RETURNS

return_1d
log_return_1d

intraday_return
overnight_return
open_to_open_return

high_low_range_pct


# MULTI-PERIOD RETURNS

return_2d
return_5d
return_10d
return_21d
return_42d
return_63d
return_126d
return_189d
return_252d


# CALENDAR RETURNS

mtd_return
qtd_return
ytd_return


# LONG HORIZON

return_504d
return_756d
return_1260d

cagr_2y
cagr_3y
cagr_5y


# BENCHMARK RELATIVE

benchmark_return_1d
benchmark_return_21d
benchmark_return_63d
benchmark_return_126d
benchmark_return_252d

excess_return_1d
excess_return_21d
excess_return_63d
excess_return_126d
excess_return_252d


# SECTOR RELATIVE

sector_return_21d
sector_return_63d
sector_return_126d
sector_return_252d

sector_relative_return_21d
sector_relative_return_63d
sector_relative_return_126d
sector_relative_return_252d


# CROSS SECTION

return_percentile_5d
return_percentile_21d
return_percentile_63d
return_percentile_126d
return_percentile_252d

return_z_5d
return_z_21d
return_z_63d
return_z_126d
return_z_252d


# FORWARD TARGETS

forward_return_1d
forward_return_5d
forward_return_10d
forward_return_21d
forward_return_63d


# QUALITY

return_valid
return_quality_status

corporate_action_adjusted
outlier_flag

invalid_reason
```

---

# 4.42 Separate Raw, Derived and Target Tables

Recommended architecture:

```text
ADJUSTED MARKET DATA
        ↓
DAILY RETURN SERIES
        ↓
MULTI-HORIZON RETURNS
        ↓
RELATIVE RETURNS
        ↓
CROSS-SECTIONAL RETURN FEATURES
        ↓
FORWARD RETURN TARGETS
```

Do not mix future target data casually into normal feature-serving tables.

A safer structure is:

```text
historical_returns
return_features
forward_return_labels
```

---

# 4.43 Point-in-Time Rule

Every value must use information actually known by that date.

For date T:

```text
return feature at T
```

may use current and historical prices through T.

It must not use:

```text
T+1
T+5
future index membership
future corporate actions not yet known
future sector classification changes
```

Forward returns belong exclusively in research labels.

---

# 4.44 Universe-Aware Ranking

Cross-sectional ranks must use the correct historical universe.

For example:

```text
NIFTY_500 return percentile on 2019-06-01
```

must use the NIFTY 500 membership valid on that historical date, not today's members.

This directly depends on Step 1 historical universe snapshots.

---

# 4.45 Benchmark Mapping

Each security may need multiple reference benchmarks:

```text
primary_market_benchmark
broad_market_benchmark
sector_benchmark
industry_benchmark
```

Example:

```text
Stock
→ NIFTY 500
→ Sector Index
→ Industry Peer Basket
```

Store benchmark mappings point-in-time where mappings can change.

---

# 4.46 Return Frequency Support

The engine should ultimately support:

```text
daily
weekly
monthly
quarterly
annual
```

Potential future support:

```text
intraday
5-minute
15-minute
hourly
```

Keep frequency explicitly stored.

---

# 4.47 Weekly Return

Use consistent week boundaries.

Recommended:

```text
last valid trading close of previous week
to
last valid trading close of current week
```

Do not assume Friday always exists due to holidays.

---

# 4.48 Monthly Return

Use:

```text
last valid trading close of previous month
to
last valid trading close of current month
```

This is preferable to simply using 21-session return when actual calendar-month performance is needed.

---

# 4.49 Return Aggregation

For simple returns:

```text
multi_period_return =
product(1 + daily_return) - 1
```

For log returns:

```text
multi_period_log_return =
sum(daily_log_return)
```

This is one reason log returns are convenient for statistical analysis.

---

# 4.50 Ranking Outputs

For every important horizon, eventually expose:

```text
raw_return
universe_rank
universe_percentile
sector_rank
sector_percentile
z_score
```

Example:

```text
63D Return             +18.4%
NIFTY 500 Rank         27 / 500
Universe Percentile    94.6
Sector Rank            2 / 31
Sector Percentile      93.5
Return Z-Score         +1.42
```

This is the format a quant screener can use effectively.

---

# 4.51 Return Decomposition

Later research can decompose:

```text
Total stock return
├── Market component
├── Sector component
├── Industry component
└── Idiosyncratic component
```

This helps identify whether a stock actually generated unique strength.

---

# 4.52 Required Eligibility Inputs

Returns Engine must consume history eligibility from Step 1.

Example:

```text
eligible_5d
eligible_21d
eligible_63d
eligible_126d
eligible_252d
```

The Returns Engine should not independently invent inconsistent history thresholds.

---

# 4.53 Recommended Initial Production Metrics

Do not implement every possible return metric on day one.

The first production version should prioritize:

```text
return_1d
log_return_1d

intraday_return
overnight_return

return_5d
return_21d
return_63d
return_126d
return_252d

mtd_return
ytd_return

cumulative_return

benchmark_return_21d
benchmark_return_63d
benchmark_return_126d
benchmark_return_252d

excess_return_21d
excess_return_63d
excess_return_126d
excess_return_252d

sector_relative_return_21d
sector_relative_return_63d
sector_relative_return_126d
sector_relative_return_252d

return_percentile_21d
return_percentile_63d
return_percentile_126d
return_percentile_252d

return_z_21d
return_z_63d
return_z_126d
return_z_252d
```

Then expand into more advanced calculations.

---

# 4.54 Returns Engine Processing Flow

Recommended processing sequence:

```text
UNIVERSE ELIGIBILITY
        ↓
DATA QUALITY VALIDATION
        ↓
CORPORATE ACTION ADJUSTED PRICES
        ↓
TRADING CALENDAR ALIGNMENT
        ↓
1D SIMPLE RETURNS
        ↓
LOG RETURNS
        ↓
INTRADAY / OVERNIGHT RETURNS
        ↓
MULTI-HORIZON RETURNS
        ↓
CALENDAR-PERIOD RETURNS
        ↓
BENCHMARK RETURNS
        ↓
EXCESS RETURNS
        ↓
SECTOR / INDUSTRY RELATIVE RETURNS
        ↓
CROSS-SECTIONAL RANKS
        ↓
Z-SCORES / ROBUST NORMALIZATION
        ↓
FORWARD RETURN LABELS
        ↓
QUALITY FLAGS
```

---

# 4.55 Important Quant Rules

## Rule 1 — Use Adjusted Prices

Do not allow splits and bonuses to generate artificial returns.

---

## Rule 2 — Keep Price Return and Total Return Separate

They answer different questions.

---

## Rule 3 — Use Trading Sessions

Do not calculate standard horizons with raw calendar-day offsets.

---

## Rule 4 — Never Fill Missing Returns with Zero

Missing data and zero performance are different states.

---

## Rule 5 — Preserve Raw Returns

Winsorization and normalization must create additional columns rather than overwrite originals.

---

## Rule 6 — Benchmark Dates Must Match

Stock and benchmark returns must use the same valid observation window.

---

## Rule 7 — Relative Performance Matters

A +10% return in a +15% market is not the same as +10% in a -5% market.

---

## Rule 8 — Use Historical Universe Membership

Cross-sectional ranks must be calculated against the universe that existed at that time.

---

## Rule 9 — Forward Returns Are Labels

Never expose future returns to same-date feature calculations.

---

## Rule 10 — Return Eligibility Is Horizon-Specific

A stock can be eligible for a 21D return but not a 252D return.

---

# 4.56 Returns Engine Completion Criteria

Step 4 is complete when Open Analytics can reliably answer:

1. What was the stock's daily return?
2. What was its log return?
3. What happened overnight?
4. What happened intraday?
5. What were its 5D, 21D, 63D, 126D and 252D returns?
6. What is its MTD and YTD return?
7. What is its cumulative return?
8. What is its long-term CAGR where eligible?
9. What did the benchmark return over the same period?
10. How much did the stock outperform or underperform the benchmark?
11. How much did it outperform or underperform its sector?
12. Where does its return rank within its historical universe?
13. What is its cross-sectional return z-score?
14. Is the return based on valid adjusted data?
15. Was a corporate action involved?
16. Is the requested horizon actually eligible?
17. What future return should be used as a research target without leaking into features?

Once these are reliable, the Returns Engine is ready to feed:

```text
Step 5 — Risk Engine
```

---

# Step 4 Final Output

The Returns Engine should transform:

```text
Adjusted Prices
```

into:

```text
Daily Returns
Multi-Horizon Returns
Calendar Returns
Benchmark Returns
Excess Returns
Sector-Relative Returns
Cross-Sectional Rankings
Return Z-Scores
Forward Research Labels
Return Quality Flags
```

This becomes the core mathematical return layer for the rest of Open Analytics.
