# Open Analytics — Step 13: Factor Engine

## Purpose

The **Factor Engine** converts standardized raw metrics from earlier engines into coherent, researchable, explainable quantitative factors.

A factor is not just one indicator.

A professional factor typically combines several related measurements into a normalized score that can be:

- ranked across a universe,
- backtested,
- compared across regimes,
- neutralized for unwanted exposures,
- combined with other factors,
- used in portfolio construction,
- and monitored for decay or crowding.

The Factor Engine should answer:

- How strong is this stock on Momentum?
- How attractive is it on Value?
- How high is its business Quality?
- How strong is its Growth profile?
- How low is its measured Risk?
- How liquid is it?
- How large or small is it?
- Are the factor scores sector-neutral?
- Are factors correlated or redundant?
- Which factors are currently predictive?
- How stable are factor ranks?
- How quickly do signals decay?
- What turnover would the factor create?
- Does the factor survive transaction costs?
- Does the factor work consistently across time and regimes?

Factor outputs feed directly into:

- Alpha / Signal Engine
- Stock Search / Screener
- Portfolio Construction
- Risk Exposure Management
- Backtesting
- Attribution
- Machine Learning

---

# 13.1 Core Principle

A factor should be:

```text
Economically motivated
Precisely defined
Point-in-time correct
Cross-sectionally comparable
Robust to outliers
Neutralized where appropriate
Backtestable
Explainable
Versioned
```

Do not build factor scores by arbitrarily adding unrelated raw indicators.

---

# 13.2 Required Inputs

The Factor Engine consumes outputs from prior steps.

Examples:

## Returns / Momentum

```text
mom_63d
mom_126d
mom_12_1
market_rel_mom_126d
sector_rel_mom_126d
```

## Risk

```text
ann_vol_63d
ann_vol_252d
downside_vol_252d
beta_252d
max_drawdown_252d
cvar_95_252d
```

## Liquidity

```text
avg_traded_value_20d
amihud_20d
liquidity_score
```

## Trend

```text
price_slope_63d
trend_strength_score
distance_52w_high
```

## Volume / Participation

```text
rvol_20d
obv_slope_20d
participation_quality_score
```

## Fundamentals

```text
roe_ttm
roic_ttm
fcf_margin
debt_to_equity
revenue_growth_yoy
eps_growth_yoy
```

## Valuation

```text
earnings_yield
book_to_price
ebit_to_ev
fcf_yield
```

## Cross-Sectional Ranking

```text
percentiles
robust z-scores
sector-neutral z-scores
size-neutral z-scores
```

---

# 13.3 Factor Families

Recommended initial factor families:

```text
Momentum
Value
Quality
Growth
Low Volatility
Liquidity
Size
Trend
Participation
```

Later:

```text
Earnings Revision
News
Institutional Flow
Carry
Residual Momentum
Profitability
Investment
Defensive
Crowding
```

---

# 13.4 Momentum Factor

Possible components:

```text
12-1 momentum
6-1 momentum
3M momentum
market-relative momentum
sector-relative momentum
momentum persistence
risk-adjusted momentum
```

Prefer standardized inputs:

```text
z_mom_12_1
z_mom_6_1
z_sector_rel_mom
```

Conceptually:

```text
momentum_factor =
weighted_average(
    z_mom_12_1,
    z_mom_6_1,
    z_sector_rel_mom,
    z_momentum_quality
)
```

Weights should be researched, not guessed.

---

# 13.5 Value Factor

Possible components:

```text
earnings_yield
book_to_price
ebit_to_ev
fcf_yield
sales_yield
```

Prefer sector-aware normalization.

Conceptually:

```text
value_factor =
average(
    sector_neutral_z_earnings_yield,
    sector_neutral_z_book_to_price,
    sector_neutral_z_ebit_to_ev,
    sector_neutral_z_fcf_yield
)
```

---

# 13.6 Quality Factor

Possible components:

```text
ROIC
ROE
FCF margin
cash conversion
earnings stability
margin stability
low accruals
low leverage
```

Conceptually:

```text
quality_factor =
positive profitability
+
positive cash quality
+
positive stability
+
balance-sheet strength
```

---

# 13.7 Growth Factor

Possible components:

```text
revenue growth
EPS growth
EBITDA growth
FCF growth
growth acceleration
margin expansion
```

Prefer sector-relative scoring where appropriate.

---

# 13.8 Low Volatility Factor

Possible components:

```text
low realized volatility
low downside volatility
low beta
low drawdown
low tail risk
```

Direction adjustment is required because lower raw risk is better.

Example:

```text
low_vol_factor =
average(
    -z_volatility,
    -z_downside_vol,
    -z_beta,
    -z_drawdown_risk
)
```

---

# 13.9 Liquidity Factor

Possible components:

```text
ADV
trading frequency
spread
Amihud illiquidity
market depth
price impact
```

Direction-adjusted standardized metrics:

```text
high ADV = positive
low spread = positive
low Amihud = positive
high depth = positive
```

---

# 13.10 Size Factor

Usually based on:

```text
market_cap
free_float_market_cap
```

Common transform:

```text
log_market_cap
```

Depending on model, a small-size factor may use:

```text
-size_z
```

while a large-size preference uses:

```text
+size_z
```

Direction depends on research objective.

---

# 13.11 Trend Factor

Possible components:

```text
price slope
MA alignment
trend R²
ADX
distance from 52-week high
breakout strength
```

Trend and Momentum should remain distinct even if related.

---

# 13.12 Participation Factor

Possible components:

```text
relative volume
volume z-score
OBV slope
CMF
participation quality
breakout volume confirmation
```

This can measure strength of market participation rather than pure liquidity.

---

# 13.13 Profitability Factor

Could be separated from broader Quality.

Possible:

```text
ROE
ROA
ROIC
gross profitability
EBIT margin
FCF margin
```

This separation can be useful for academic-style factor research.

---

# 13.14 Investment Factor

Later factor family:

```text
asset growth
capex growth
working capital growth
share issuance
```

Some factor models treat conservative vs aggressive investment as distinct from value or quality.

---

# 13.15 Earnings Revision Factor

If analyst estimates exist:

```text
EPS revision 1M
EPS revision 3M
upgrade count
downgrade count
estimate dispersion
```

Output:

```text
revision_factor
```

---

# 13.16 News Factor

Later:

```text
news sentiment
news surprise
news novelty
news velocity
event severity
```

Output:

```text
news_factor
```

---

# 13.17 Flow Factor

Later institutional-flow inputs:

```text
FII/DII activity
futures OI
delivery flow
fund flow
```

Output:

```text
flow_factor
```

---

# 13.18 Raw Factor Input Rules

Every input should specify:

```text
source_engine
metric_name
direction
transform
winsorization
normalization
peer_group
weight
availability_rule
```

This belongs in a Factor Registry.

---

# 13.19 Factor Registry

Recommended metadata:

```text
factor_name
factor_version
description

component_metric
component_weight

normalization_method
neutralization_method

minimum_component_count
missing_value_rule

rebalance_frequency
holding_horizon

active
```

---

# 13.20 Factor Versioning

Never silently change factor formula.

Store:

```text
factor_version
```

Example:

```text
MOMENTUM_V1
MOMENTUM_V2
```

This allows reproducible backtests.

---

# 13.21 Component Normalization

Before combining components, use comparable scale:

```text
robust z-score
percentile
rank-normalized score
```

Do not combine raw:

```text
ROE + P/E + volatility
```

directly.

---

# 13.22 Direction Adjustment

Convert all factor inputs so:

```text
higher normalized score = more desirable
```

Examples:

```text
higher momentum → positive
higher ROIC → positive
higher FCF yield → positive

higher volatility → negative
higher leverage → negative
higher spread → negative
```

---

# 13.23 Winsorization

Apply component-level clipping before combining.

Example:

```text
P01 / P99
```

or robust MAD-based limits.

Preserve raw values.

---

# 13.24 Missing Components

Do not automatically assign zero.

Possible rules:

```text
REQUIRE_ALL
REQUIRE_MINIMUM_COUNT
RENORMALIZE_AVAILABLE_WEIGHTS
IMPUTE_PEER_MEDIAN
```

Each factor must define its own rule.

Recommended default:

```text
minimum component count
+
renormalize available weights
```

with explicit quality flag.

---

# 13.25 Factor Quality Status

Possible:

```text
VALID
PARTIAL_COMPONENTS
LOW_DATA_QUALITY
LOW_PEER_COUNT
STALE_FUNDAMENTALS
INSUFFICIENT_HISTORY
INVALID
```

Store:

```text
factor_quality_status
```

---

# 13.26 Sector Neutralization

Many factors need sector neutralization.

Example:

```text
value
quality
growth
```

Possible methods:

```text
within-sector z-score
demeaning by sector
regression residualization
```

Store both:

```text
raw_factor_score
sector_neutral_factor_score
```

---

# 13.27 Industry Neutralization

For finer peer effects:

```text
industry_neutral_factor
```

Useful where sector buckets remain too broad.

---

# 13.28 Size Neutralization

Some factors correlate strongly with size.

Example:

```text
liquidity
quality
volatility
```

Possible:

```text
factor ~ log_market_cap
```

Use residual.

---

# 13.29 Beta Neutralization

For alpha research:

```text
factor ~ beta
```

Then use residual to reduce unintended market-risk exposure.

---

# 13.30 Multi-Exposure Neutralization

Advanced regression:

```text
factor
~
sector
+
log_market_cap
+
beta
+
liquidity
```

Residual becomes:

```text
neutralized_factor
```

---

# 13.31 Factor Percentile

Expose:

```text
factor_percentile = 0 to 100
```

Recommended convention:

```text
100 = strongest
0 = weakest
```

---

# 13.32 Factor Rank

Store:

```text
factor_rank
```

Point-in-time universe rules apply.

---

# 13.33 Factor Deciles

Store:

```text
factor_decile
```

Convention:

```text
10 = strongest
1 = weakest
```

---

# 13.34 Composite Factor Score

Example:

```text
factor_score = weighted sum of standardized components
```

Then optionally map to:

```text
0–100
```

for UI.

Keep raw z-score as well.

---

# 13.35 Factor Exposure Matrix

Create matrix:

```text
stock × factor
```

Example:

```text
             Momentum  Value  Quality  Growth  LowVol
Stock A        +1.2    -0.4    +0.8    +0.5   +0.3
Stock B        -0.8    +1.1    +0.2    -0.1   -0.5
```

This becomes core input to portfolio construction.

---

# 13.36 Factor Correlation

Calculate cross-sectional factor correlations.

Examples:

```text
Momentum vs Value
Quality vs LowVol
Size vs Liquidity
```

Store research diagnostics.

Highly correlated factors may be redundant.

---

# 13.37 Factor Orthogonalization

Advanced option:

```text
factor_A_residual =
factor_A - exposure explained by factor_B
```

Example:

```text
Quality orthogonalized to Size
```

Use cautiously because interpretation changes.

---

# 13.38 Information Coefficient

A core factor diagnostic.

IC:

```text
correlation(
    factor_score_t,
    forward_return_t+h
)
```

Common:

```text
Pearson IC
Spearman Rank IC
```

Rank IC is often especially useful.

---

# 13.39 IC by Horizon

Calculate:

```text
ic_1d
ic_5d
ic_21d
ic_63d
```

Factor usefulness may vary by horizon.

---

# 13.40 IC Time Series

Store per date:

```text
date
factor
forward_horizon
IC
```

This allows stability analysis.

---

# 13.41 Mean IC

Calculate:

```text
mean_ic
```

over a research period.

---

# 13.42 IC Information Ratio

Common:

```text
IC_IR =
mean(IC)
/
std(IC)
```

Useful for factor stability.

---

# 13.43 Positive IC Frequency

```text
positive_ic_ratio =
count(IC > 0)
/
total_periods
```

This indicates consistency.

---

# 13.44 Quantile Return Test

Sort stocks by factor into:

```text
deciles
quintiles
```

Then measure future returns.

Example:

```text
Top decile return
Bottom decile return
```

---

# 13.45 Long-Short Factor Spread

Concept:

```text
factor_return =
top_quantile_return
-
bottom_quantile_return
```

Store:

```text
long_short_spread
```

This is one of the most important factor diagnostics.

---

# 13.46 Monotonicity

A strong factor should often show orderly returns across quantiles.

Example:

```text
Decile 10 > 9 > 8 ... > 1
```

Measure:

```text
quantile_monotonicity_score
```

---

# 13.47 Factor Hit Rate

Possible:

```text
top_quantile_outperforms_rate
```

or:

```text
long_short_positive_period_ratio
```

---

# 13.48 Factor Decay

Measure how predictive power changes with holding horizon.

Example:

```text
IC 1D
IC 5D
IC 21D
IC 63D
```

Output:

```text
factor_decay_curve
```

---

# 13.49 Half-Life

Estimate approximate factor half-life.

Useful for:

```text
rebalance frequency
holding period
turnover expectations
```

---

# 13.50 Rank Autocorrelation

Calculate:

```text
corr(
    factor_rank_t,
    factor_rank_t+1
)
```

High autocorrelation means stable ranks.

Low autocorrelation implies high turnover.

---

# 13.51 Factor Turnover

Measure changes in selected names or weights.

Examples:

```text
top_decile_turnover
rank_turnover
portfolio_turnover
```

---

# 13.52 Transaction Cost Sensitivity

A factor may look strong gross but weak net.

Evaluate:

```text
gross factor spread
- spread
- slippage
- impact
- taxes/fees
=
net factor spread
```

Step 6 supplies execution inputs.

---

# 13.53 Capacity

Factor capacity depends on:

```text
stock liquidity
position concentration
turnover
market impact
```

A high-turnover microcap factor may have low real-world capacity.

---

# 13.54 Factor Crowding

Later indicators may include:

```text
factor valuation extremes
factor ownership
factor correlation spikes
factor dispersion
short interest / derivatives positioning
```

This is advanced.

---

# 13.55 Regime Analysis

Evaluate factor performance under:

```text
Bull markets
Bear markets
High volatility
Low volatility
High rates
Low rates
Strong breadth
Weak breadth
```

Store:

```text
factor_regime_performance
```

---

# 13.56 Sector Regime Analysis

Momentum may work differently in:

```text
IT
Banks
Metals
Pharma
```

Evaluate factor IC/spreads by sector.

---

# 13.57 Market-Cap Regime Analysis

Factor performance may differ in:

```text
Large cap
Mid cap
Small cap
```

Track separately.

---

# 13.58 Factor Dispersion

Calculate spread of factor scores:

```text
std factor score
p90 - p10
```

High dispersion means stronger cross-sectional differentiation.

---

# 13.59 Factor Breadth

Example:

```text
percentage of universe with positive factor score
```

or:

```text
top-quintile count
```

Useful for regime context.

---

# 13.60 Factor Concentration

Check whether top factor scores cluster in one:

```text
sector
industry
theme
size bucket
```

High concentration may create hidden risk.

---

# 13.61 Exposure Diagnostics

For each factor portfolio, measure exposure to:

```text
Beta
Size
Sector
Liquidity
Volatility
Value
Momentum
```

This helps identify unintended bets.

---

# 13.62 Factor Purity

Concept:

```text
how much the constructed factor reflects intended exposure
vs unintended exposures
```

Can be measured via regressions.

---

# 13.63 Factor Redundancy

If two factors are highly correlated and have similar IC, combining them may add little value.

Research outputs:

```text
factor_corr_matrix
factor_cluster
```

---

# 13.64 Composite Multi-Factor Score

Later combine:

```text
Momentum
Value
Quality
Growth
LowVol
Liquidity
```

Example conceptual:

```text
multi_factor_score =
wM * Momentum
+
wV * Value
+
wQ * Quality
+
wG * Growth
+
wL * LowVol
```

Do not set production weights without backtesting.

---

# 13.65 Equal Weight Composite

Baseline:

```text
equal_weight_factor_score =
mean(selected factor z-scores)
```

Useful as a simple research benchmark.

---

# 13.66 Research-Weighted Composite

Weights may be based on:

```text
historical IC
IC stability
regime
turnover
transaction costs
```

---

# 13.67 Dynamic Factor Weights

Advanced:

```text
factor weights change by market regime
```

Example:

```text
high volatility regime
→ increase quality / low-vol weight
```

Must be backtested carefully to avoid overfitting.

---

# 13.68 Machine-Learned Factor Combination

Later:

```text
features = factor scores
target = forward return / rank
```

Model can learn nonlinear combinations.

But raw factor infrastructure should remain independently usable.

---

# 13.69 Factor Score Confidence

Possible inputs:

```text
component availability
data quality
factor IC stability
rank stability
regime fit
```

Output:

```text
factor_confidence
```

---

# 13.70 Factor Explainability

For every stock, Open Analytics should expose:

```text
factor score
component scores
component weights
peer percentile
neutralization applied
quality flags
```

Example:

```text
Momentum Factor = 82/100

12-1 Momentum        91st percentile
6-1 Momentum         87th percentile
Sector Relative      79th percentile
Momentum Quality     71st percentile
```

---

# 13.71 Point-in-Time Rule

At date T, factor score may only use:

```text
metrics known at T
universe membership at T
sector mapping at T
fundamentals available at T
```

No future information.

---

# 13.72 Survivorship Bias Protection

Factor backtests must retain stocks that later:

```text
failed
delisted
merged
left the index
became illiquid
```

if they were eligible at the time.

---

# 13.73 Corporate Action Dependency

Price-based factor components must use adjusted prices.

Fundamental ratios must use correctly adjusted per-share data.

---

# 13.74 Factor Rebalance Frequency

Each factor should define:

```text
DAILY
WEEKLY
MONTHLY
QUARTERLY
```

Examples:

```text
Momentum → daily/weekly
Value → daily with quarterly fundamentals
Quality → quarterly with daily ranking possible
```

---

# 13.75 Factor Holding Horizon

Define intended horizon:

```text
SHORT
MEDIUM
LONG
```

or explicit:

```text
5D
21D
63D
126D
```

This helps align validation metrics.

---

# 13.76 Factor Refresh vs Rebalance

Important distinction:

```text
refresh factor values daily
```

does not necessarily mean:

```text
rebalance portfolio daily
```

Keep these separate.

---

# 13.77 Factor Storage Model

Recommended daily factor record:

```text
date
universe_id
instrument_key

factor_name
factor_version

raw_factor_z
neutralized_factor_z

factor_rank
factor_percentile
factor_decile

factor_quality_status
factor_confidence
```

---

# 13.78 Wide Production Factor Table

For fast scanning:

```text
instrument_key
date

momentum_factor
value_factor
quality_factor
growth_factor
low_vol_factor
liquidity_factor
size_factor
trend_factor
participation_factor

multi_factor_score
```

---

# 13.79 Research Diagnostics Table

Separate:

```text
date
factor_name
forward_horizon

IC
rank_IC
long_short_spread
turnover
dispersion
breadth
```

This prevents mixing per-stock features with research analytics.

---

# 13.80 Recommended Initial Factor Definitions

## Momentum V1

```text
mom_12_1
mom_6_1
sector_rel_mom_126d
momentum_persistence
```

## Value V1

```text
earnings_yield
book_to_price
ebit_to_ev
fcf_yield
```

## Quality V1

```text
roic_ttm
roe_ttm
fcf_margin
cash_conversion
low leverage
```

## Growth V1

```text
revenue_growth_yoy
eps_growth_yoy
revenue_cagr_3y
eps_cagr_3y
```

## Low Vol V1

```text
ann_vol_252d
downside_vol_252d
beta_252d
max_drawdown_252d
```

## Liquidity V1

```text
ADV
trading frequency
Amihud
spread if available
```

These should first be equal-weighted standardized components as a research baseline.

---

# 13.81 Recommended Initial Research Tests

For every factor:

```text
Rank IC
Mean IC
IC IR

Top vs bottom quintile return
Top vs bottom decile return

Monotonicity
Turnover

Gross return
Net return after costs

Large-cap performance
Mid-cap performance
Small-cap performance

Sector-neutral performance
Regime performance
```

---

# 13.82 Factor Engine Processing Flow

Recommended:

```text
STANDARDIZED INPUT METRICS
        ↓
FACTOR REGISTRY
        ↓
COMPONENT VALIDATION
        ↓
DIRECTION ADJUSTMENT
        ↓
WINSORIZATION
        ↓
NORMALIZATION
        ↓
SECTOR / SIZE NEUTRALIZATION
        ↓
COMPONENT WEIGHTING
        ↓
RAW FACTOR SCORE
        ↓
FACTOR RANK / PERCENTILE
        ↓
FACTOR QUALITY / CONFIDENCE
        ↓
IC TESTING
        ↓
QUANTILE RETURN TESTING
        ↓
DECAY / TURNOVER
        ↓
TRANSACTION COST TESTING
        ↓
REGIME DIAGNOSTICS
        ↓
MULTI-FACTOR COMBINATION
```

---

# 13.83 Important Quant Rules

## Rule 1 — Factor ≠ Indicator

A factor is a systematic, cross-sectional, testable signal family.

---

## Rule 2 — Normalize Before Combining

Raw metrics on different scales must not be directly added.

---

## Rule 3 — Direction Must Be Consistent

After adjustment:

```text
higher factor score = stronger desired exposure
```

---

## Rule 4 — Neutralization Must Be Explicit

Sector and size effects should not disappear silently.

---

## Rule 5 — Backtest Every Factor Separately

Know whether each factor actually contributes before combining them.

---

## Rule 6 — Use Point-in-Time Inputs

No future fundamentals, memberships, or classifications.

---

## Rule 7 — Test Net of Costs

High-turnover factors can disappear after transaction costs.

---

## Rule 8 — Measure Decay

Factor horizon matters.

---

## Rule 9 — Avoid Redundant Factors

Highly correlated factors may add little incremental information.

---

## Rule 10 — Preserve Component Explainability

Every factor score should be decomposable.

---

## Rule 11 — Version Factor Definitions

Any formula change requires a new version.

---

## Rule 12 — Avoid Overfitting

Simple robust factor definitions should be the baseline before complex weighting.

---

# 13.84 Completion Criteria

Step 13 is complete when Open Analytics can answer:

1. What is each stock's Momentum factor score?
2. What is its Value factor score?
3. What is its Quality factor score?
4. What is its Growth factor score?
5. What is its Low-Volatility factor score?
6. What is its Liquidity factor score?
7. What inputs created each score?
8. Were those inputs normalized correctly?
9. Were sector/size effects neutralized where required?
10. Where does the stock rank for each factor?
11. What factor decile does it belong to?
12. How stable are factor ranks?
13. What is the factor's historical IC?
14. What is its IC IR?
15. Do top factor quantiles outperform bottom quantiles?
16. Is performance monotonic across quantiles?
17. How quickly does the factor decay?
18. What turnover does it create?
19. Does it survive transaction costs?
20. Does it work across market regimes?
21. Does it work across size buckets and sectors?
22. Is the factor redundant with another factor?
23. What is the factor's quality/confidence status?
24. Can the exact historical factor value be reproduced?
25. Can multiple factors be combined without hiding their individual contributions?

Once these are reliable, the Factor Engine is ready to feed:

```text
Step 14 — News & Event Engine
```

---

# Step 13 Final Output

The Factor Engine transforms:

```text
Standardized Quant Metrics
+
Point-in-Time Peer Context
```

into:

```text
Momentum Factor
Value Factor
Quality Factor
Growth Factor
Low-Volatility Factor
Liquidity Factor
Size Factor
Trend Factor
Participation Factor
Factor Ranks
Factor Percentiles
Factor Deciles
Sector/Size-Neutral Scores
Factor Confidence
Factor Exposure Matrix
IC / Rank-IC Diagnostics
Quantile Return Spreads
Factor Decay
Factor Turnover
Transaction-Cost-Adjusted Performance
Multi-Factor Scores
```

This becomes the core systematic stock-selection layer for Open Analytics.
