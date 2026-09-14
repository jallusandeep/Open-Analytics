# Open Analytics — Step 8: Momentum Engine

## Purpose

The **Momentum Engine** measures the persistence, strength, acceleration, and relative leadership of price movement across multiple horizons.

Momentum is one of the most widely studied quantitative effects, but it should not be reduced to a single oscillator such as RSI.

The engine should answer:

- Is the stock outperforming over short, medium, and long horizons?
- Is the recent move accelerating or weakening?
- Is the stock stronger than the market?
- Is it stronger than its sector and industry peers?
- Is momentum broad and persistent or driven by one isolated jump?
- Is momentum unusually strong relative to the rest of the universe?
- Is the current momentum consistent with trend structure?
- Is the stock experiencing short-term reversal despite long-term momentum?
- Is the momentum signal robust enough to enter a factor or alpha model?

Momentum outputs feed directly into:

- Cross-sectional ranking
- Factor construction
- Alpha signals
- Stock screening
- Portfolio construction
- Market regime logic
- Machine learning features

---

# 8.1 Core Principle

Momentum is multi-horizon and relative.

Open Analytics should distinguish:

```text
Absolute Momentum
Relative Momentum
Cross-Sectional Momentum
Sector-Relative Momentum
Residual Momentum
Short-Term Reversal
Momentum Acceleration
Momentum Persistence
Momentum Quality
```

Do not rely on:

```text
RSI < 30
RSI > 70
```

as the main momentum framework.

RSI is only one auxiliary feature.

---

# 8.2 Required Inputs

Minimum inputs from Step 4:

```text
instrument_key
date

return_1d
return_5d
return_21d
return_63d
return_126d
return_252d
```

Preferred:

```text
adjusted_close

benchmark_return
sector_return
industry_return

trend metrics from Step 7

volume / liquidity metrics
risk metrics

data_quality_status
```

---

# 8.3 Absolute Momentum

Absolute momentum measures the stock’s own return over a selected horizon.

Recommended:

```text
mom_5d
mom_10d
mom_21d
mom_42d
mom_63d
mom_126d
mom_189d
mom_252d
```

These can simply map to corresponding total or price returns, but should be stored as momentum features where needed.

---

# 8.4 Standard Horizon Interpretation

Approximate:

```text
5D    → 1 week
21D   → 1 month
63D   → 3 months
126D  → 6 months
252D  → 12 months
```

Keep actual implementation based on trading sessions rather than calendar dates.

---

# 8.5 12-1 Momentum

A commonly used medium-term momentum concept excludes the most recent month.

Conceptually:

```text
mom_12_1 =
price_21_sessions_ago / price_252_sessions_ago - 1
```

Equivalent to roughly:

```text
12-month return excluding latest 1 month
```

Store:

```text
mom_12_1
```

This helps reduce contamination from short-term reversal effects.

---

# 8.6 6-1 Momentum

Similarly:

```text
mom_6_1 =
price_21_sessions_ago / price_126_sessions_ago - 1
```

Store:

```text
mom_6_1
```

---

# 8.7 3-1 Momentum

Optional:

```text
mom_3_1 =
price_21_sessions_ago / price_63_sessions_ago - 1
```

Useful for shorter medium-term research.

---

# 8.8 Short-Term Momentum

Recommended:

```text
mom_5d
mom_10d
mom_21d
```

Short-term momentum may behave differently from medium-term momentum and can also interact with mean reversion.

Do not automatically combine all horizons with the same sign.

---

# 8.9 Medium-Term Momentum

Recommended:

```text
mom_63d
mom_126d
mom_6_1
```

These are typically more central to classic cross-sectional momentum models.

---

# 8.10 Long-Term Momentum

Recommended:

```text
mom_252d
mom_12_1
```

Long-term momentum should be treated carefully around:

```text
corporate actions
large event jumps
IPO history limitations
```

---

# 8.11 Relative Momentum vs Benchmark

Calculate:

```text
relative_momentum_market_Nd =
stock_return_Nd - benchmark_return_Nd
```

Recommended:

```text
market_rel_mom_21d
market_rel_mom_63d
market_rel_mom_126d
market_rel_mom_252d
```

Example:

```text
Stock 6M return = +24%
Benchmark 6M    = +10%

market_rel_mom_126d = +14%
```

---

# 8.12 Relative Momentum vs Sector

Calculate:

```text
sector_rel_mom_Nd =
stock_return_Nd - sector_return_Nd
```

Recommended:

```text
sector_rel_mom_21d
sector_rel_mom_63d
sector_rel_mom_126d
sector_rel_mom_252d
```

This helps identify genuine stock-specific leadership.

---

# 8.13 Relative Momentum vs Industry

If industry benchmark data exists:

```text
industry_rel_mom_63d
industry_rel_mom_126d
industry_rel_mom_252d
```

This is a finer peer comparison than sector-relative performance.

---

# 8.14 Cross-Sectional Momentum Rank

For each date and universe:

```text
mom_rank_21d
mom_rank_63d
mom_rank_126d
mom_rank_252d
```

Also percentiles:

```text
mom_pct_21d
mom_pct_63d
mom_pct_126d
mom_pct_252d
```

Example:

```text
mom_pct_126d = 94
```

means the stock outperformed approximately 94% of eligible peers over the same horizon.

---

# 8.15 Sector Momentum Rank

Within sector:

```text
sector_mom_rank_63d
sector_mom_rank_126d

sector_mom_percentile
```

This is useful for sector-neutral stock selection.

---

# 8.16 Momentum Z-Score

Cross-sectional standardization:

```text
mom_z_21d
mom_z_63d
mom_z_126d
mom_z_252d
```

Conceptually:

```text
z =
(stock_momentum - universe_mean)
/
universe_std
```

Use robust preprocessing for extreme returns.

---

# 8.17 Winsorized Momentum

Preserve both:

```text
raw_momentum
winsorized_momentum
```

Do not overwrite original values.

This can prevent a few extreme event stocks from dominating factor normalization.

---

# 8.18 Momentum Acceleration

Momentum acceleration asks whether recent performance is improving relative to earlier performance.

Possible:

```text
mom_accel_21_63 =
mom_21d - mom_63d_scaled
```

Better comparisons should account for horizon length.

Alternative:

```text
recent monthly return
-
prior monthly return
```

Store:

```text
momentum_acceleration
momentum_deceleration
```

---

# 8.19 Sequential Momentum

Compare consecutive windows.

Example:

```text
latest_21d_return
prior_21d_return
prior_21d_return_2
```

Then classify:

```text
ACCELERATING
STABLE
DECELERATING
REVERSING
```

---

# 8.20 Momentum Persistence

Measure how consistently a stock has remained strong.

Possible metrics:

```text
fraction_positive_5d_windows
fraction_positive_21d_windows
fraction_top_quartile_periods
```

Outputs:

```text
momentum_persistence_63d
momentum_persistence_126d
```

---

# 8.21 Momentum Breadth Across Horizons

Measure whether multiple horizons agree.

Example:

```text
mom_21d > 0
mom_63d > 0
mom_126d > 0
mom_252d > 0
```

Create:

```text
momentum_alignment_count
```

and:

```text
momentum_alignment_state
```

Possible:

```text
FULL_POSITIVE
MOSTLY_POSITIVE
MIXED
MOSTLY_NEGATIVE
FULL_NEGATIVE
```

---

# 8.22 Momentum Quality

A stock with one huge gap and flat performance afterward differs from a steadily advancing stock.

Possible quality inputs:

```text
path efficiency
return consistency
trend R²
drawdown within momentum window
single-day contribution
volume confirmation
```

Output:

```text
momentum_quality_score
```

---

# 8.23 Single-Day Contribution

Measure how much of a multi-month return came from one or a few extreme sessions.

Example:

```text
largest_positive_day_contribution
```

If 70% of a 3-month return came from one event day, momentum quality may be lower for some strategies.

---

# 8.24 Positive Day Ratio

Store:

```text
positive_day_ratio_21d
positive_day_ratio_63d
positive_day_ratio_126d
```

Useful as a persistence measure, but not sufficient alone.

---

# 8.25 Positive Week Ratio

Aggregate to weekly returns:

```text
positive_week_ratio_3m
positive_week_ratio_6m
positive_week_ratio_12m
```

This helps identify stable medium-term momentum.

---

# 8.26 Return Consistency

Possible metric:

```text
consistency_score =
frequency of positive sub-period returns
```

For example:

```text
3M positive
6M positive
12M positive
```

plus rolling-window consistency.

---

# 8.27 Momentum Drawdown

Measure the largest drawdown during the momentum formation window.

Example:

```text
momentum_window_max_drawdown_126d
```

Strong total return with severe internal drawdown may indicate lower-quality momentum.

---

# 8.28 Risk-Adjusted Momentum

Normalize momentum by risk.

Possible:

```text
risk_adjusted_momentum =
return_Nd / volatility_Nd
```

or:

```text
momentum / downside_volatility
```

Outputs:

```text
risk_adj_mom_63d
risk_adj_mom_126d
risk_adj_mom_252d
```

This does not replace raw momentum; it complements it.

---

# 8.29 Volatility-Scaled Momentum

Another variant:

```text
vol_scaled_momentum =
return / annualized_volatility
```

Useful for comparing high-volatility and low-volatility securities.

---

# 8.30 Residual Momentum

Residual momentum attempts to remove broad market or factor-driven returns.

Conceptually:

```text
stock_return
-
expected_return_from_market_and_factors
```

Then calculate momentum of residual returns.

Possible:

```text
residual_mom_63d
residual_mom_126d
residual_mom_252d
```

This is an advanced factor feature.

---

# 8.31 Idiosyncratic Momentum

Related concept:

```text
momentum in residual/idiosyncratic returns
```

Useful in more advanced factor research.

Not required for first production.

---

# 8.32 Short-Term Reversal

Very short horizons can behave differently from medium-term momentum.

Possible metrics:

```text
reversal_1d
reversal_5d
reversal_10d
```

Conceptually:

```text
short_term_reversal_score = - recent_short_return
```

Do not combine this blindly with 12-1 momentum.

Keep short-term reversal as a separate factor/component.

---

# 8.33 RSI

Relative Strength Index can be retained as a technical momentum oscillator.

Recommended:

```text
rsi_14
```

Optional:

```text
rsi_7
rsi_21
```

Use adjusted prices.

Important:

```text
RSI != cross-sectional relative strength
```

They are different concepts.

---

# 8.34 Rate of Change

ROC:

```text
roc_N =
close / close_N_sessions_ago - 1
```

This overlaps mathematically with simple momentum returns, but may be retained for compatibility.

Recommended:

```text
roc_10
roc_21
roc_63
```

---

# 8.35 Stochastic Oscillator

Optional:

```text
stoch_k
stoch_d
```

Useful for short-horizon momentum/positioning.

Not a core institutional momentum factor.

---

# 8.36 MACD Momentum

MACD belongs partly to trend and partly to momentum.

Store if desired:

```text
macd_line
macd_signal
macd_histogram
```

Use as supporting features rather than standalone stock-selection logic.

---

# 8.37 Momentum Slope

Calculate slope of a relative-strength or cumulative-return series.

Possible:

```text
momentum_slope_21d
momentum_slope_63d
```

This helps measure direction of momentum itself.

---

# 8.38 Relative Strength Line

Create:

```text
relative_strength_line =
stock_adjusted_price / benchmark_price
```

Then calculate:

```text
rs_line_slope_20d
rs_line_slope_63d
rs_line_new_high_flag
```

This is useful for identifying stocks outperforming even when the overall market is weak.

---

# 8.39 Sector Relative Strength Line

Similarly:

```text
stock_price / sector_index
```

Outputs:

```text
sector_rs_slope_20d
sector_rs_slope_63d
```

---

# 8.40 Momentum vs Trend Agreement

Momentum Engine should consume Step 7 outputs.

Example:

```text
high momentum
+
strong bullish trend
```

is different from:

```text
high 3M return
+
price below SMA200
```

Store:

```text
momentum_trend_agreement
```

Possible values:

```text
CONFIRMED
PARTIAL
DIVERGENT
```

---

# 8.41 Momentum vs Volume Agreement

Use Step 6 metrics where useful.

Example:

```text
positive momentum
+
rising traded value
+
high RVOL
```

can indicate stronger participation.

Store:

```text
momentum_volume_confirmation
```

---

# 8.42 Momentum vs Risk

A high-return stock with extreme volatility may need a lower-quality classification.

Possible output:

```text
momentum_risk_quality
```

Do not replace the risk engine; use risk as contextual information.

---

# 8.43 Momentum Reversal Warning

Possible warning inputs:

```text
long-term momentum positive
short-term momentum negative
trend slope weakening
distance from high increasing
volume distribution
```

Output:

```text
momentum_reversal_warning
```

This is a probability/context feature, not a guaranteed reversal call.

---

# 8.44 Momentum Exhaustion

Possible state:

```text
EXTENDED / EXHAUSTION_RISK
```

Potential inputs:

```text
extreme distance from MA
extreme momentum percentile
falling acceleration
negative divergence
very high short-term volatility
```

Not required for first production.

---

# 8.45 Cross-Sectional Momentum Factor

Eventually build a factor score using several robust momentum components.

Example conceptual inputs:

```text
12-1 momentum
6-1 momentum
3M momentum
market-relative momentum
sector-relative momentum
momentum quality
```

Normalize each component before combining.

Output:

```text
momentum_factor_score
```

Do not hard-code production weights without research.

---

# 8.46 Example Composite Structure

Conceptually:

```text
Momentum Factor
=
w1 × z(12-1 momentum)
+
w2 × z(6-1 momentum)
+
w3 × z(3M relative momentum)
+
w4 × z(momentum quality)
```

Weights should later be derived from research, not guessed.

---

# 8.47 Momentum Percentile

Final user-facing percentile:

```text
momentum_percentile = 0 to 100
```

Interpretation:

```text
95
→ stronger momentum than approximately 95% of eligible peers
```

---

# 8.48 Momentum Score

Possible normalized score:

```text
momentum_score = 0 to 100
```

Keep:

```text
raw components
z-scores
percentiles
```

available alongside it.

---

# 8.49 Momentum State

Possible simplified state:

```text
STRONG_POSITIVE
POSITIVE
NEUTRAL
NEGATIVE
STRONG_NEGATIVE
```

This should be derived from continuous metrics rather than replace them.

---

# 8.50 Historical Momentum Snapshot

Every momentum metric must be stored point-in-time.

At date T:

```text
mom_126d
```

may only use prices through T.

Historical rankings must use historical universe membership from Step 1.

---

# 8.51 Look-Ahead Protection

Do not use:

```text
future price
future benchmark data
future index membership
future corporate-action-adjusted data not known correctly at T
```

in live feature calculations.

Forward returns belong only in labels.

---

# 8.52 Survivorship Bias Protection

Stocks that later delisted or failed must remain in historical momentum ranks if they were eligible at the time.

Otherwise past winners will be overrepresented.

---

# 8.53 IPO Handling

New stocks receive only the horizons they support.

Example:

```text
70 valid sessions

mom_21d  → available
mom_63d  → available
mom_126d → unavailable
mom_252d → unavailable
mom_12_1 → unavailable
```

Do not fill unavailable values with zero.

---

# 8.54 Corporate Action Handling

Momentum must use adjusted historical prices.

Otherwise:

```text
split
bonus
rights adjustment
```

can create fake momentum crashes or jumps.

---

# 8.55 Stale / Illiquid Stock Handling

Illiquid stocks can display misleading momentum due to stale prices or discrete jumps.

Momentum Engine should consume:

```text
liquidity_quality_status
trading_frequency
stale_price_flag
```

and expose:

```text
momentum_quality_status
```

---

# 8.56 Missing Data

If a required historical price is unavailable:

```text
momentum_metric = null
metric_valid = false
```

Do not interpolate long-horizon momentum casually.

---

# 8.57 Recommended Daily Momentum Record

A daily momentum record could include:

```text
instrument_key
date


# ABSOLUTE MOMENTUM

mom_5d
mom_10d
mom_21d
mom_42d
mom_63d
mom_126d
mom_252d

mom_3_1
mom_6_1
mom_12_1


# RELATIVE MOMENTUM

market_rel_mom_21d
market_rel_mom_63d
market_rel_mom_126d
market_rel_mom_252d

sector_rel_mom_21d
sector_rel_mom_63d
sector_rel_mom_126d
sector_rel_mom_252d


# CROSS-SECTION

mom_rank_21d
mom_rank_63d
mom_rank_126d
mom_rank_252d

mom_pct_21d
mom_pct_63d
mom_pct_126d
mom_pct_252d

mom_z_21d
mom_z_63d
mom_z_126d
mom_z_252d


# ACCELERATION / PERSISTENCE

momentum_acceleration
momentum_deceleration

momentum_persistence_63d
momentum_persistence_126d

momentum_alignment_count
momentum_alignment_state


# QUALITY

positive_day_ratio_21d
positive_day_ratio_63d

momentum_window_max_drawdown_126d

risk_adj_mom_63d
risk_adj_mom_126d

momentum_quality_score


# OSCILLATORS

rsi_14
roc_21
roc_63

macd_line
macd_signal
macd_histogram


# RELATIVE STRENGTH LINE

rs_line_slope_20d
rs_line_slope_63d

sector_rs_slope_20d
sector_rs_slope_63d


# CONTEXT

momentum_trend_agreement
momentum_volume_confirmation
momentum_reversal_warning


# FINAL

momentum_factor_score
momentum_percentile
momentum_score
momentum_state


# QUALITY FLAGS

momentum_valid
momentum_quality_status
momentum_invalid_reason
```

---

# 8.58 Initial Production Metrics

Recommended first production set:

```text
mom_5d
mom_21d
mom_63d
mom_126d
mom_252d

mom_6_1
mom_12_1

market_rel_mom_21d
market_rel_mom_63d
market_rel_mom_126d
market_rel_mom_252d

sector_rel_mom_63d
sector_rel_mom_126d
sector_rel_mom_252d

mom_pct_21d
mom_pct_63d
mom_pct_126d
mom_pct_252d

mom_z_63d
mom_z_126d
mom_z_252d

momentum_persistence_63d
momentum_alignment_state

risk_adj_mom_63d
risk_adj_mom_126d

rsi_14

rs_line_slope_20d
rs_line_slope_63d

momentum_trend_agreement

momentum_percentile
momentum_quality_status
```

Then expand into more advanced residual and quality features.

---

# 8.59 Momentum Engine Processing Flow

Recommended:

```text
VALID RETURN SERIES
        ↓
HISTORY ELIGIBILITY
        ↓
ABSOLUTE MOMENTUM
        ↓
12-1 / 6-1 MOMENTUM
        ↓
BENCHMARK-RELATIVE MOMENTUM
        ↓
SECTOR-RELATIVE MOMENTUM
        ↓
SHORT-TERM REVERSAL
        ↓
ACCELERATION / DECELERATION
        ↓
PERSISTENCE
        ↓
RISK-ADJUSTED MOMENTUM
        ↓
RSI / AUXILIARY OSCILLATORS
        ↓
RELATIVE-STRENGTH LINE
        ↓
TREND / VOLUME AGREEMENT
        ↓
CROSS-SECTIONAL RANKS
        ↓
Z-SCORES
        ↓
MOMENTUM FACTOR SCORE
        ↓
QUALITY FLAGS
```

---

# 8.60 Important Quant Rules

## Rule 1 — Momentum Is Not RSI

RSI is only one oscillator.

---

## Rule 2 — Use Multiple Horizons

Short-, medium-, and long-term momentum can behave differently.

---

## Rule 3 — Keep Short-Term Reversal Separate

Recent reversal effects should not be blended blindly into medium-term momentum.

---

## Rule 4 — Relative Momentum Matters

A stock gaining 10% in a market gaining 20% is not strong relative momentum.

---

## Rule 5 — Sector Context Matters

Sector-wide rallies can make weak stocks look strong on absolute return.

---

## Rule 6 — Use Point-in-Time Universe Ranks

Historical ranks must use eligible peers at that date.

---

## Rule 7 — Preserve Raw Momentum

Winsorization and normalization should create derived values, not overwrite raw returns.

---

## Rule 8 — Avoid Event-Dominated Momentum

Track whether one or two extreme sessions dominate the formation period.

---

## Rule 9 — Momentum Quality Matters

Two stocks with the same 6M return can have very different paths and risks.

---

## Rule 10 — Use Adjusted Prices

Corporate actions must not generate fake momentum.

---

## Rule 11 — Do Not Give New IPOs Fake Long-Horizon Values

Unavailable momentum should remain null.

---

## Rule 12 — Keep Factor Score Explainable

A momentum score should be decomposable into its underlying horizons and relative-strength measures.

---

# 8.61 Completion Criteria

Step 8 is complete when Open Analytics can answer:

1. What is the stock's 1-week momentum?
2. What is its 1-month momentum?
3. What is its 3-month momentum?
4. What is its 6-month momentum?
5. What is its 12-month momentum?
6. What is its 12-1 momentum?
7. How much has it outperformed the broad market?
8. How much has it outperformed its sector?
9. Where does its momentum rank within the historical universe?
10. What is its momentum z-score?
11. Is momentum accelerating or weakening?
12. Is momentum persistent across sub-periods?
13. Do multiple momentum horizons agree?
14. Is the return path clean or dominated by one event?
15. How strong is momentum after adjusting for volatility?
16. Is its relative-strength line improving?
17. Does momentum agree with the Trend Engine?
18. Does momentum have volume/liquidity confirmation?
19. Is short-term reversal contradicting medium-term momentum?
20. Is the metric based on sufficient valid history?
21. What is the final momentum percentile/score?
22. Why is any momentum metric unavailable?

Once these are reliable, the Momentum Engine is ready to feed:

```text
Step 9 — Volume & Participation Engine
```

---

# Step 8 Final Output

The Momentum Engine transforms:

```text
Returns + Benchmark Returns + Sector Returns + Trend Context
```

into:

```text
Absolute Momentum
12-1 / 6-1 Momentum
Market-Relative Momentum
Sector-Relative Momentum
Cross-Sectional Momentum Ranks
Momentum Z-Scores
Momentum Acceleration
Momentum Persistence
Risk-Adjusted Momentum
Relative Strength
Auxiliary Oscillators
Momentum Quality
Momentum Factor Score
Momentum State
Momentum Quality Flags
```

This becomes the primary price-persistence and relative-leadership layer for Open Analytics.
