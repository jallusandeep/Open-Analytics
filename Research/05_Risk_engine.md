# Open Analytics — Step 5: Risk Engine

## Purpose

The **Risk Engine** converts return series into quantitative measures of uncertainty, loss potential, drawdown behavior, market sensitivity, tail exposure, and diversification risk.

The Risk Engine should answer:

- How volatile is this stock?
- How much downside volatility does it have?
- How large have historical drawdowns been?
- How sensitive is the stock to the market?
- How correlated is it with its sector, benchmark, and other securities?
- What losses are plausible under normal and stressed conditions?
- Is risk increasing or decreasing?
- Is the stock's risk mostly market-driven or idiosyncratic?
- How does its risk compare with the rest of the universe?
- Is the stock suitable for the strategy's risk limits?

Risk metrics become inputs to:

- Stock selection
- Factor construction
- Position sizing
- Portfolio construction
- Hedging
- Signal confidence
- Backtesting
- Performance attribution
- Risk controls
- Machine learning features

---

# 5.1 Core Principle

Risk is not one number.

Open Analytics should treat risk as a collection of dimensions:

```text
Volatility Risk
Downside Risk
Drawdown Risk
Market Risk
Sector Risk
Correlation Risk
Tail Risk
Liquidity Risk
Gap Risk
Event Risk
Concentration Risk
Portfolio Contribution Risk
```

The first production Risk Engine should focus on market-price and return-based risk.

Liquidity, event, derivatives, and portfolio-specific risk can then extend it.

---

# 5.2 Required Inputs

Minimum inputs from Step 4:

```text
instrument_key
date

return_1d
log_return_1d

benchmark_return_1d
sector_return_1d
```

Preferred additional inputs:

```text
adjusted_close
high
low
open

intraday_return
overnight_return

return_quality_status
corporate_action_adjusted

universe_id
sector_id
industry_id
```

Later:

```text
market_cap
liquidity metrics
risk_free_rate
futures data
options data
```

---

# 5.3 Historical Volatility

Historical volatility measures dispersion of returns.

Basic daily volatility:

```text
volatility_Nd =
standard_deviation(daily_returns over N sessions)
```

Annualized:

```text
annualized_volatility_Nd =
daily_volatility_Nd × sqrt(252)
```

Recommended windows:

```text
vol_5d
vol_10d
vol_21d
vol_42d
vol_63d
vol_126d
vol_252d
```

Annualized versions:

```text
ann_vol_21d
ann_vol_63d
ann_vol_126d
ann_vol_252d
```

---

# 5.4 Log-Return Volatility

For statistical modeling, volatility may also be calculated from log returns.

```text
log_vol_21d
log_vol_63d
log_vol_126d
log_vol_252d
```

Use a consistent methodology across the platform.

---

# 5.5 Upside and Downside Volatility

Separate positive and negative return variability.

```text
upside_volatility
downside_volatility
```

Downside volatility:

```text
standard deviation of negative / below-target returns
```

Recommended:

```text
downside_vol_21d
downside_vol_63d
downside_vol_126d
downside_vol_252d
```

This is useful because investors generally care more about downside variation than upside variation.

---

# 5.6 Semideviation

Downside semideviation can be defined relative to:

```text
0% return
risk-free rate
minimum acceptable return
benchmark return
```

Store the target definition explicitly.

Example:

```text
downside_semidev_63d
downside_target_type = ZERO
```

---

# 5.7 Volatility Change

Risk direction matters.

Calculate:

```text
vol_change_5d
vol_change_21d
vol_ratio_short_long
```

Example:

```text
vol_ratio_21_252 =
ann_vol_21d / ann_vol_252d
```

Interpretation:

```text
> 1 → short-term volatility above long-term norm
< 1 → short-term volatility below long-term norm
```

---

# 5.8 Volatility Percentile

Rank current volatility against:

1. Cross-sectional universe.
2. The stock's own history.

Store both.

```text
volatility_universe_percentile
volatility_historical_percentile
```

Example:

```text
ann_vol_21d = 42%
universe_percentile = 85
historical_percentile = 91
```

This means the stock is volatile relative both to peers and to its own history.

---

# 5.9 Volatility Z-Score

Cross-sectional:

```text
volatility_zscore =
(stock_vol - universe_mean_vol)
/
universe_std_vol
```

Historical:

```text
historical_vol_zscore =
(current_vol - own_history_mean)
/
own_history_std
```

Do not mix these two concepts.

---

# 5.10 EWMA Volatility

Exponentially Weighted Moving Average volatility gives more weight to recent observations.

Conceptually:

```text
variance_t =
lambda × variance_(t-1)
+
(1-lambda) × return_(t-1)^2
```

Then:

```text
ewma_volatility = sqrt(variance)
```

Possible outputs:

```text
ewma_vol_21d
ewma_vol_63d
```

Lambda should be configurable.

---

# 5.11 Parkinson Volatility

Uses high-low prices.

Conceptually:

```text
Parkinson variance
∝
mean(ln(high / low)^2)
```

Useful where intraday ranges contain additional information beyond closing returns.

Outputs:

```text
parkinson_vol_21d
parkinson_vol_63d
```

---

# 5.12 Garman-Klass Volatility

Uses:

```text
Open
High
Low
Close
```

and can be more efficient than close-to-close volatility under certain assumptions.

Outputs:

```text
garman_klass_vol_21d
garman_klass_vol_63d
```

---

# 5.13 Rogers-Satchell / Yang-Zhang Volatility

Advanced range-based estimators may later be included.

Possible outputs:

```text
rogers_satchell_vol
yang_zhang_vol
```

Yang-Zhang can be useful because it incorporates overnight gaps and intraday price ranges.

These are advanced metrics; not required for initial production.

---

# 5.14 ATR Risk

Average True Range is useful for absolute trading range risk.

True Range:

```text
max(
    high - low,
    abs(high - previous_close),
    abs(low - previous_close)
)
```

Then:

```text
ATR_N = average(True Range)
```

Recommended:

```text
atr_14
atr_21
```

Normalize:

```text
atr_pct =
ATR / close
```

Store:

```text
atr_pct_14
atr_pct_21
```

ATR percentage is more comparable across differently priced stocks.

---

# 5.15 Gap Risk

Use overnight returns from Step 4.

Calculate:

```text
overnight_volatility
gap_up_frequency
gap_down_frequency

large_gap_frequency
max_positive_gap
max_negative_gap
```

Recommended windows:

```text
gap_risk_21d
gap_risk_63d
gap_risk_252d
```

---

# 5.16 Drawdown

Drawdown measures decline from previous peak.

Running peak:

```text
running_peak_t =
max(price_1 ... price_t)
```

Drawdown:

```text
drawdown_t =
price_t / running_peak_t - 1
```

Example:

```text
Peak price     = 1000
Current price  = 800

Current drawdown = -20%
```

---

# 5.17 Current Drawdown

Store:

```text
current_drawdown
```

This tells how far the stock currently sits below its historical or selected-window high.

---

# 5.18 Maximum Drawdown

Maximum drawdown:

```text
max_drawdown =
minimum(drawdown series)
```

Recommended windows:

```text
max_drawdown_63d
max_drawdown_126d
max_drawdown_252d
max_drawdown_3y
max_drawdown_5y
max_drawdown_all
```

---

# 5.19 Drawdown Duration

Measure time spent below a previous peak.

Store:

```text
current_drawdown_duration
max_drawdown_duration
average_drawdown_duration
```

Duration can be measured in trading sessions.

---

# 5.20 Time to Recovery

Measure how long it takes after a trough to regain the previous peak.

Store:

```text
last_recovery_days
average_recovery_days
max_recovery_days
```

For unresolved drawdowns:

```text
recovered = false
```

Do not fabricate recovery duration.

---

# 5.21 Ulcer Index

Ulcer Index measures severity and persistence of drawdowns.

Conceptually:

```text
sqrt(mean(drawdown_pct^2))
```

Outputs:

```text
ulcer_index_63d
ulcer_index_252d
```

Useful because it focuses specifically on downside drawdown behavior.

---

# 5.22 Beta

Beta measures sensitivity to benchmark returns.

Formula:

```text
beta =
Cov(stock_return, benchmark_return)
/
Var(benchmark_return)
```

Recommended:

```text
beta_21d
beta_63d
beta_126d
beta_252d
beta_3y
```

Use overlapping valid observations only.

---

# 5.23 Rolling Beta

Beta should be time-varying.

Store rolling beta per date.

Example:

```text
date
instrument_key
beta_63d
beta_252d
```

This allows detection of changing market sensitivity.

---

# 5.24 Sector Beta

Also calculate sensitivity to sector returns.

```text
sector_beta_63d
sector_beta_126d
sector_beta_252d
```

This can help distinguish broad-market exposure from sector exposure.

---

# 5.25 Alpha

A basic CAPM-style alpha:

```text
stock_excess_return =
alpha
+
beta × market_excess_return
+
error
```

Outputs:

```text
alpha_63d
alpha_126d
alpha_252d
```

Annualization methodology must be documented.

Alpha estimation belongs partly in performance/factor models, but basic regression alpha can live with beta calculations.

---

# 5.26 R-Squared

Store regression fit:

```text
r_squared_63d
r_squared_126d
r_squared_252d
```

Interpretation:

```text
High R² → market explains a large portion of return variance
Low R²  → more idiosyncratic behavior
```

---

# 5.27 Residual / Idiosyncratic Volatility

From regression residuals:

```text
idiosyncratic_volatility =
std(residual_returns)
```

Store:

```text
idio_vol_63d
idio_vol_126d
idio_vol_252d
```

This is important for later factor models.

---

# 5.28 Correlation

Calculate correlation with:

```text
Broad benchmark
Primary benchmark
Sector benchmark
Industry benchmark
Other securities
Portfolio
```

Recommended benchmark correlation windows:

```text
market_corr_21d
market_corr_63d
market_corr_126d
market_corr_252d

sector_corr_21d
sector_corr_63d
sector_corr_126d
sector_corr_252d
```

---

# 5.29 Rolling Correlation

Correlation changes over time.

Store:

```text
rolling_market_corr_63d
rolling_sector_corr_63d
```

Risk models should not assume correlation is constant.

---

# 5.30 Covariance

Covariance is required for portfolio risk.

Store or calculate on demand:

```text
covariance(stock_i, stock_j)
```

A full covariance matrix becomes important later in the Portfolio Engine.

For large universes, do not blindly store every pair daily unless justified by performance/storage design.

Possible approaches:

```text
on-demand calculation
factor covariance model
scheduled covariance snapshots
```

---

# 5.31 Value at Risk — Historical VaR

Historical VaR estimates a loss quantile from observed returns.

Example 95% VaR:

```text
VaR_95 =
negative 5th percentile return
```

Recommended:

```text
var_95_21d
var_95_63d
var_95_252d

var_99_63d
var_99_252d
```

Sign convention must be standardized.

Recommended display:

```text
VaR as positive expected loss magnitude
```

Example:

```text
VaR 95% = 3.2%
```

meaning:

> Based on the model/window, a one-period loss worse than approximately 3.2% falls in the worst 5% of observations.

---

# 5.32 Parametric VaR

Assuming a return distribution:

```text
VaR =
mean_return - z × volatility
```

Possible outputs:

```text
parametric_var_95
parametric_var_99
```

Do not treat parametric VaR as absolute truth because real returns exhibit skew and fat tails.

---

# 5.33 Conditional VaR / Expected Shortfall

CVaR asks:

> When losses exceed VaR, how bad are they on average?

Store:

```text
cvar_95
cvar_99
```

Also known as:

```text
Expected Shortfall
```

This is generally more informative for tail loss than VaR alone.

---

# 5.34 Tail Loss Metrics

Additional tail metrics:

```text
worst_1d_return
worst_5d_return
worst_21d_return

best_1d_return
best_5d_return

left_tail_mean
right_tail_mean
```

Recommended windows:

```text
63d
252d
3y
5y
```

---

# 5.35 Skewness

Skewness measures asymmetry of returns.

Store:

```text
skew_21d
skew_63d
skew_126d
skew_252d
```

Negative skew can indicate stronger downside-tail behavior.

---

# 5.36 Kurtosis

Kurtosis measures tail heaviness relative to a normal distribution.

Store:

```text
kurtosis_21d
kurtosis_63d
kurtosis_126d
kurtosis_252d
```

Use excess kurtosis or raw kurtosis consistently and document the choice.

---

# 5.37 Downside Capture

Compare performance during benchmark down periods.

Conceptually:

```text
down_capture =
stock return during market-down periods
/
benchmark return during market-down periods
```

Also:

```text
up_capture
```

Useful later for defensive stock analysis.

---

# 5.38 Worst Drawdown Context

Do not store only maximum drawdown.

Also record:

```text
max_drawdown_start_date
max_drawdown_trough_date
max_drawdown_recovery_date
```

This enables event and regime analysis.

---

# 5.39 Risk-Adjusted Return Inputs

The Risk Engine should provide inputs needed later for:

```text
Sharpe Ratio
Sortino Ratio
Calmar Ratio
Treynor Ratio
Information Ratio
Omega Ratio
```

The actual ratios may be calculated in a later Risk-Adjusted Performance layer, but foundational metrics come from here.

---

# 5.40 Tracking Error

Tracking error measures volatility of active returns.

```text
active_return =
stock_return - benchmark_return
```

Then:

```text
tracking_error =
std(active_return)
```

Recommended:

```text
tracking_error_63d
tracking_error_126d
tracking_error_252d
```

Annualized versions should also be available.

---

# 5.41 Information Ratio Inputs

Information Ratio:

```text
mean(active_return)
/
tracking_error
```

The Risk Engine should provide:

```text
active_return_series
tracking_error
```

---

# 5.42 Risk Concentration Flags

At single-stock level, flag unusual concentration of risk:

```text
high_beta_flag
high_volatility_flag
high_downside_vol_flag
high_gap_risk_flag
high_tail_risk_flag
deep_drawdown_flag
```

Thresholds should be configurable or percentile-based.

---

# 5.43 Cross-Sectional Risk Ranking

For each date and universe, rank:

```text
volatility
downside_volatility
beta
max_drawdown
VaR
CVaR
idiosyncratic_volatility
```

Outputs:

```text
volatility_rank
volatility_percentile

downside_risk_rank
beta_rank
tail_risk_rank
drawdown_rank
```

---

# 5.44 Risk Z-Scores

Standardized risk metrics:

```text
volatility_z
downside_vol_z
beta_z
drawdown_z
var_z
cvar_z
```

Use robust handling for extreme outliers.

---

# 5.45 Composite Risk Score

Eventually create a composite risk score.

Example conceptual inputs:

```text
Volatility
Downside volatility
Drawdown
Beta
Tail risk
Gap risk
Liquidity risk
```

Do not hard-code arbitrary production weights without research.

Conceptually:

```text
risk_score = 0 to 100
```

Recommended interpretation:

```text
0   → low measured risk
100 → high measured risk
```

Also store:

```text
risk_percentile
risk_bucket
```

Possible buckets:

```text
LOW
MEDIUM
HIGH
EXTREME
```

---

# 5.46 Risk Regime Detection

For each stock, detect whether current risk is elevated relative to its own history.

Possible states:

```text
LOW_VOL
NORMAL_VOL
HIGH_VOL
EXTREME_VOL
```

Inputs:

```text
historical volatility percentile
volatility ratio
gap activity
drawdown state
```

This should remain separate from overall market regime detection.

---

# 5.47 Risk Trend

Calculate whether risk is rising or falling.

Possible metrics:

```text
vol_slope
beta_change
correlation_change
drawdown_change
tail_risk_change
```

Example:

```text
risk_trend = RISING
```

or:

```text
risk_trend = FALLING
```

---

# 5.48 Data Quality Requirements

Risk calculations must not proceed blindly when returns are invalid.

Each metric should include eligibility and quality status.

Example:

```text
vol_252d_valid
beta_252d_valid
var_252d_valid
```

Possible invalid reasons:

```text
INSUFFICIENT_HISTORY
INSUFFICIENT_OVERLAP
BAD_RETURN_DATA
CORPORATE_ACTION_UNRESOLVED
TOO_MANY_MISSING_OBSERVATIONS
BENCHMARK_MISSING
```

---

# 5.49 Minimum Observation Rules

Different risk metrics need different sample sizes.

Examples:

```text
21D volatility → approximately 21 valid returns
63D beta       → enough overlapping stock and benchmark observations
252D VaR       → preferably substantial observation count
```

Do not calculate unstable tail metrics from trivially small samples.

The minimum sample count should be configurable by metric.

---

# 5.50 IPO Handling

New listings should receive only metrics supported by available history.

Example:

```text
45 valid daily returns

vol_21d      = available
vol_63d      = unavailable
beta_252d    = unavailable
max_dd_21d   = available
var_252d     = unavailable
```

Do not substitute zeros.

---

# 5.51 Suspensions and Illiquid Stocks

Risk metrics based on stale prices can be misleading.

Example:

```text
zero returns for 10 days
```

may appear as low volatility even though the security simply did not trade.

Therefore Risk Engine should consume:

```text
trading_status
liquidity_status
stale_price_flag
```

and flag unreliable volatility estimates.

---

# 5.52 Corporate Actions

Risk must use corporate-action-adjusted return series.

Otherwise splits and bonuses can create:

```text
fake volatility
fake drawdown
fake VaR
fake tail events
```

This dependency must be explicit.

---

# 5.53 Benchmark Alignment

For beta/correlation:

```text
stock_return_date == benchmark_return_date
```

Use only overlapping valid observations.

Track:

```text
beta_observation_count
correlation_observation_count
```

This makes reliability visible.

---

# 5.54 Risk-Free Rate

For later risk-adjusted ratios, maintain point-in-time risk-free data.

Possible sources/representations:

```text
Treasury bill yield
short-term government rate
strategy-configured risk-free series
```

Do not hard-code a permanent risk-free rate.

---

# 5.55 Recommended Daily Risk Record

A daily risk-feature record could include:

```text
instrument_key
date

# VOLATILITY

vol_5d
vol_10d
vol_21d
vol_63d
vol_126d
vol_252d

ann_vol_21d
ann_vol_63d
ann_vol_126d
ann_vol_252d

downside_vol_21d
downside_vol_63d
downside_vol_126d
downside_vol_252d

ewma_vol_21d
ewma_vol_63d

atr_14
atr_pct_14

parkinson_vol_21d
garman_klass_vol_21d


# DRAWDOWN

current_drawdown

max_drawdown_63d
max_drawdown_126d
max_drawdown_252d

current_drawdown_duration
max_drawdown_duration

ulcer_index_63d
ulcer_index_252d


# MARKET RISK

beta_21d
beta_63d
beta_126d
beta_252d

market_corr_21d
market_corr_63d
market_corr_126d
market_corr_252d

sector_beta_63d
sector_beta_252d

sector_corr_63d
sector_corr_252d

r_squared_63d
r_squared_252d

idio_vol_63d
idio_vol_252d


# TAIL RISK

var_95_63d
var_95_252d

var_99_252d

cvar_95_63d
cvar_95_252d

cvar_99_252d

skew_63d
skew_252d

kurtosis_63d
kurtosis_252d

worst_1d_return_252d


# ACTIVE RISK

tracking_error_63d
tracking_error_252d


# RANKING

volatility_percentile
downside_risk_percentile
beta_percentile
drawdown_percentile
tail_risk_percentile

volatility_z
beta_z

risk_score
risk_percentile
risk_bucket
risk_trend


# QUALITY

risk_valid
risk_quality_status

vol_observation_count
beta_observation_count

risk_invalid_reason
```

---

# 5.56 Initial Production Metrics

Do not implement every advanced estimator immediately.

Recommended first production set:

```text
vol_21d
vol_63d
vol_126d
vol_252d

ann_vol_21d
ann_vol_63d
ann_vol_252d

downside_vol_63d
downside_vol_252d

atr_14
atr_pct_14

current_drawdown
max_drawdown_63d
max_drawdown_252d

beta_63d
beta_252d

market_corr_63d
market_corr_252d

sector_corr_63d
sector_corr_252d

idiosyncratic_volatility_252d

var_95_252d
cvar_95_252d

skew_252d
kurtosis_252d

tracking_error_252d

volatility_percentile
beta_percentile
drawdown_percentile

risk_score
risk_quality_status
```

Then expand into advanced estimators.

---

# 5.57 Risk Engine Processing Flow

Recommended processing:

```text
VALID RETURN SERIES
        ↓
HISTORY / QUALITY ELIGIBILITY
        ↓
ROLLING VOLATILITY
        ↓
DOWNSIDE VOLATILITY
        ↓
ATR / RANGE-BASED VOLATILITY
        ↓
DRAWDOWN SERIES
        ↓
MAX DRAWDOWN / DURATION
        ↓
BENCHMARK ALIGNMENT
        ↓
BETA / CORRELATION / R²
        ↓
IDIOSYNCRATIC RISK
        ↓
VaR / CVaR
        ↓
SKEW / KURTOSIS / TAIL METRICS
        ↓
ACTIVE RISK / TRACKING ERROR
        ↓
CROSS-SECTIONAL RANKING
        ↓
COMPOSITE RISK SCORE
        ↓
QUALITY FLAGS
```

---

# 5.58 Important Quant Rules

## Rule 1 — Risk Must Use Clean Returns

Never calculate risk directly from unvalidated raw price changes.

---

## Rule 2 — Low Volatility Can Be Fake

Illiquid or stale stocks may appear artificially safe.

Always combine volatility with trading-status and liquidity checks.

---

## Rule 3 — Use Multiple Horizons

21D risk and 252D risk answer different questions.

---

## Rule 4 — Downside Risk Matters Separately

Two stocks with the same total volatility may have very different downside characteristics.

---

## Rule 5 — Drawdown Is Not Volatility

A stock can have moderate volatility but severe persistent drawdowns.

---

## Rule 6 — Beta Is Time-Varying

Do not treat beta as a permanent company property.

---

## Rule 7 — Correlation Changes

Diversification based only on long-term static correlation can fail during stressed periods.

---

## Rule 8 — VaR Is Not Maximum Loss

VaR is a statistical threshold, not a worst-case guarantee.

---

## Rule 9 — CVaR Complements VaR

Expected Shortfall helps describe the severity of losses beyond VaR.

---

## Rule 10 — Tail Metrics Need Enough Data

Do not calculate confident tail statistics from tiny samples.

---

## Rule 11 — Preserve Component Metrics

Do not expose only a single risk score.

The underlying volatility, drawdown, beta, and tail metrics must remain available.

---

## Rule 12 — Ranking Must Be Point-in-Time

Risk percentiles must use the historical universe valid on that date.

---

# 5.59 Risk Engine Completion Criteria

Step 5 is complete when Open Analytics can reliably answer:

1. What is the stock's short-term volatility?
2. What is its long-term volatility?
3. Is volatility rising or falling?
4. How does current volatility compare with its own history?
5. How does volatility compare with the rest of the universe?
6. What is its downside volatility?
7. What is its current drawdown?
8. What is its maximum historical drawdown?
9. How long has the drawdown lasted?
10. What is its market beta?
11. What is its sector beta?
12. How correlated is it with the market?
13. How correlated is it with its sector?
14. How much risk is idiosyncratic?
15. What is its 95% VaR?
16. What is its Expected Shortfall / CVaR?
17. Does it exhibit negative skew or fat tails?
18. What is its tracking error versus benchmark?
19. Is its apparent low risk caused by stale or illiquid trading?
20. Is each metric based on enough valid observations?
21. How does its total measured risk rank against peers?
22. What is its composite risk score?
23. Why is any risk metric unavailable or invalid?

Once these are reliable, the Risk Engine is ready to feed:

```text
Step 6 — Liquidity & Tradability Engine
```

---

# Step 5 Final Output

The Risk Engine transforms:

```text
Clean Return Series
```

into:

```text
Volatility
Downside Risk
ATR / Range Risk
Drawdown
Drawdown Duration
Beta
Correlation
R-Squared
Idiosyncratic Risk
VaR
CVaR / Expected Shortfall
Skewness
Kurtosis
Tracking Error
Cross-Sectional Risk Rankings
Composite Risk Score
Risk Quality Flags
```

This becomes the main price-risk layer used throughout Open Analytics.
