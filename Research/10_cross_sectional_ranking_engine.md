# Open Analytics — Step 10: Cross-Sectional Ranking Engine

## Purpose

The **Cross-Sectional Ranking Engine** converts raw metrics from all prior engines into comparable peer-relative measures.

This is one of the most important layers in a professional quant platform.

A raw number such as:

```text
6M return = +18%
ROE = 22%
Volatility = 31%
P/E = 24
```

does not tell enough by itself.

A quant process usually asks:

- How does this value compare with all eligible stocks today?
- How does it compare with stocks in the same sector?
- How does it compare with stocks of similar size?
- Is it an extreme outlier?
- Is the ranking stable?
- Should the raw metric be transformed before ranking?
- Is the rank based on a historically correct universe?
- Does the metric need direction reversal because lower is better?

This engine transforms raw features into:

```text
Rank
Percentile
Z-Score
Robust Z-Score
Sector Rank
Industry Rank
Size-Peer Rank
Neutralized Score
Composite Standardized Feature
```

These outputs are used by:

- Factor Engine
- Alpha Engine
- Stock Screener
- Portfolio Construction
- Risk Controls
- Research Analysis
- Machine Learning

---

# 10.1 Core Principle

Quant models should compare like with like.

Examples:

```text
Momentum
→ compare across current eligible universe

Valuation
→ often compare within sector/industry

Liquidity
→ compare by market-cap bucket and universe

Risk
→ compare across universe and own history

Growth
→ compare against sector peers
```

The ranking engine must support multiple peer groups rather than one universal ranking.

---

# 10.2 Required Inputs

Inputs come from prior engines.

Examples:

```text
instrument_key
date
universe_id

sector
industry
sub_industry

market_cap_bucket
liquidity_bucket

raw_metric_name
raw_metric_value

metric_valid
metric_quality_status
```

Typical metrics include:

```text
return_21d
return_63d
mom_12_1
ann_vol_63d
beta_252d
current_drawdown
rvol_20d
trend_strength_score
liquidity_score
```

Later:

```text
ROE
ROIC
revenue_growth
P/E
FCF yield
news sentiment
flow score
```

---

# 10.3 Eligible Peer Set

Before ranking a metric, define the valid peer set.

Example:

```text
Universe = NIFTY_500
Date = T
Metric = mom_126d
```

Only include stocks that are:

```text
members of NIFTY_500 on date T
metric_valid = true
sufficient history = true
data quality acceptable
```

Do not rank null or invalid values.

---

# 10.4 Point-in-Time Universe Rule

Historical rankings must use historical universe membership.

Example:

```text
mom_percentile on 2019-06-03
```

must use the securities eligible on:

```text
2019-06-03
```

not today's universe.

This prevents survivorship bias.

---

# 10.5 Raw Rank

Basic rank:

```text
rank = 1, 2, 3, ...
```

Direction depends on metric meaning.

Example:

For momentum:

```text
higher is better
```

So:

```text
highest momentum → rank 1
```

For volatility:

```text
lower may be better
```

So for a low-volatility factor:

```text
lowest volatility → rank 1
```

The ranking direction must be explicit in metric metadata.

---

# 10.6 Percentile Rank

Percentile gives a normalized 0–100 relative position.

Example:

```text
momentum_percentile = 95
```

means the stock is stronger than approximately 95% of valid peers.

Recommended convention:

```text
0   → weakest
100 → strongest
```

Even when raw metric direction is reversed.

This creates a consistent user-facing interpretation.

---

# 10.7 Rank Direction Metadata

Each metric should define:

```text
HIGHER_IS_BETTER
LOWER_IS_BETTER
NEUTRAL / ABSOLUTE_DISTANCE
```

Examples:

```text
momentum                HIGHER_IS_BETTER
ROE                     HIGHER_IS_BETTER
FCF yield               HIGHER_IS_BETTER

P/E                     context dependent
volatility              LOWER_IS_BETTER
drawdown magnitude      LOWER_IS_BETTER
spread                  LOWER_IS_BETTER
Amihud illiquidity      LOWER_IS_BETTER
```

Do not hide this logic in scattered code.

---

# 10.8 Standard Z-Score

Formula:

```text
z =
(x - mean)
/
std
```

Interpretation:

```text
z = +2
```

means the value is two standard deviations above peer mean.

Store:

```text
z_score
```

---

# 10.9 Direction-Adjusted Z-Score

For metrics where lower is better:

```text
factor_z = -raw_z
```

This allows:

```text
positive = desirable
negative = undesirable
```

consistently across factor inputs.

Store both:

```text
raw_z
direction_adjusted_z
```

---

# 10.10 Robust Z-Score

Mean/std can be distorted by outliers.

A robust alternative:

```text
robust_z =
(x - median)
/
MAD_scaled
```

where MAD is Median Absolute Deviation.

Possible denominator:

```text
1.4826 × MAD
```

Store:

```text
robust_z
```

This can be preferable for:

```text
valuation ratios
growth
financial ratios
illiquidity
event returns
```

---

# 10.11 Winsorization

Extreme values may dominate normalization.

Common approach:

```text
lower bound = 1st percentile
upper bound = 99th percentile
```

Then clip outside values.

Possible alternatives:

```text
2.5% / 97.5%
5% / 95%
median ± k × MAD
```

Store:

```text
raw_value
winsorized_value
```

Never overwrite raw input.

---

# 10.12 Clipping Z-Scores

After normalization, cap extreme z-scores if required.

Example:

```text
z_clip_min = -3
z_clip_max = +3
```

This is often useful in composite factors.

Again, preserve original z-score.

---

# 10.13 Missing Value Handling

Do not convert missing metrics to zero by default.

Use:

```text
metric = null
rank = null
percentile = null
z = null
```

and:

```text
rank_valid = false
```

If factor construction later imputes missing values, that should be explicit and model-specific.

---

# 10.14 Minimum Peer Count

Do not calculate unstable peer ranks on tiny groups.

Example:

```text
minimum_peer_count = configurable
```

Possible:

```text
sector rank requires at least 5 valid stocks
industry rank requires at least 5 valid stocks
```

If insufficient:

```text
sector_rank = null
sector_rank_valid = false
```

---

# 10.15 Whole-Universe Ranking

Examples:

```text
universe_rank
universe_percentile
universe_z
```

Peer set:

```text
all valid stocks in selected universe
```

This is the default cross-sectional comparison.

---

# 10.16 Sector Ranking

Within sector:

```text
sector_rank
sector_percentile
sector_z
```

Important for:

```text
valuation
quality
growth
momentum
```

because sectors have structurally different characteristics.

---

# 10.17 Industry Ranking

Within industry:

```text
industry_rank
industry_percentile
industry_z
```

This provides finer peer comparison.

---

# 10.18 Sub-Industry Ranking

Where enough peer count exists:

```text
subindustry_rank
subindustry_percentile
```

Do not use when groups are too small.

---

# 10.19 Market-Cap Peer Ranking

Compare within:

```text
LARGE_CAP
MID_CAP
SMALL_CAP
MICRO_CAP
```

Store:

```text
size_rank
size_percentile
size_z
```

Useful for:

```text
liquidity
volatility
growth
valuation
```

---

# 10.20 Liquidity Peer Ranking

Optional peer grouping:

```text
HIGH_LIQUIDITY
MEDIUM_LIQUIDITY
LOW_LIQUIDITY
```

Useful when comparing execution-sensitive metrics.

---

# 10.21 Multi-Peer Ranking

A single metric may expose several views:

```text
universe_percentile
sector_percentile
industry_percentile
size_percentile
```

Example:

```text
ROE = 24%

Universe percentile = 82
Sector percentile   = 68
Industry percentile = 61
```

This gives better context.

---

# 10.22 Sector Neutralization

Sector neutralization removes systematic sector-level differences.

Simple method:

```text
neutralized_value =
stock_value - sector_mean
```

or:

```text
stock_value - sector_median
```

Then normalize.

Store:

```text
sector_neutral_value
sector_neutral_z
```

---

# 10.23 Industry Neutralization

Likewise:

```text
industry_neutral_value
industry_neutral_z
```

This may be better for metrics heavily influenced by industry structure.

---

# 10.24 Regression Neutralization

More advanced neutralization can regress metric exposure against:

```text
sector dummies
industry dummies
log market cap
beta
liquidity
```

Then use residual:

```text
neutralized_metric = regression_residual
```

This is useful in institutional-style factor models.

---

# 10.25 Size Neutralization

Many metrics correlate with company size.

Example regression:

```text
metric ~ log_market_cap
```

Then:

```text
size_neutral_metric = residual
```

Store:

```text
size_neutral_z
```

---

# 10.26 Sector + Size Neutralization

For more robust factor research:

```text
metric
~
sector effects
+
log market cap
```

Use residual as normalized feature.

Possible output:

```text
sector_size_neutral_z
```

---

# 10.27 Beta Neutralization

Some signals may simply capture high-beta exposure.

Possible:

```text
metric ~ beta
```

Then use residual.

More relevant later in alpha/factor research.

---

# 10.28 Liquidity Neutralization

A signal may be biased toward illiquid stocks.

Possible:

```text
signal ~ liquidity
```

Then:

```text
liquidity_neutral_signal
```

Useful for testing whether alpha survives after liquidity exposure is removed.

---

# 10.29 Rank Transformation

Some factor models prefer ranks rather than raw z-scores.

Possible normalized rank:

```text
rank_scaled =
2 × percentile - 1
```

Range:

```text
-1 to +1
```

or:

```text
0 to 1
```

Store:

```text
rank_scaled
```

---

# 10.30 Gaussian Rank Transform

Advanced option:

1. Compute percentile rank.
2. Map percentile through inverse normal CDF.

Output:

```text
gaussian_rank_z
```

This can stabilize distributions across highly non-normal metrics.

Not required for first production.

---

# 10.31 Quantile Buckets

Divide universe into buckets:

```text
decile
quintile
quartile
```

Store:

```text
decile
quintile
quartile
```

Example:

```text
momentum_decile = 10
```

could indicate top decile if convention is ascending strength.

Document the convention clearly.

---

# 10.32 Top/Bottom Flags

Convenient outputs:

```text
top_10pct_flag
top_20pct_flag
bottom_10pct_flag
bottom_20pct_flag
```

Useful for research and screens.

---

# 10.33 Rank Stability

A good factor can be more useful if ranks are not purely noisy.

Track:

```text
rank_change_1d
rank_change_5d
rank_change_21d
```

Possible:

```text
rank_stability_score
```

---

# 10.34 Percentile Change

Store:

```text
percentile_change_5d
percentile_change_21d
```

Useful for detecting improving or deteriorating relative position.

---

# 10.35 Rank Momentum

Example:

```text
current momentum percentile = 85
21 days ago = 62
```

Then:

```text
rank_momentum = +23
```

This can identify rapidly improving leadership.

---

# 10.36 Cross-Sectional Breadth

For any metric, calculate universe-level summaries:

```text
median
mean
std
percentiles
valid_count
```

Example:

```text
median_63d_return
top_decile_threshold
bottom_decile_threshold
```

These are useful for research diagnostics.

---

# 10.37 Distribution Statistics

Per metric/date/universe, store:

```text
count
mean
median
std
mad
min
max

p01
p05
p10
p25
p50
p75
p90
p95
p99
```

This supports transparent normalization.

---

# 10.38 Outlier Detection

Possible outlier flags:

```text
standard_z_outlier
robust_z_outlier
iqr_outlier
```

Store:

```text
outlier_flag
outlier_method
```

Do not automatically remove outliers without metric-specific logic.

---

# 10.39 Metric Transformations

Some raw metrics benefit from transformations before normalization.

Examples:

```text
log(market_cap)
log(ADV)
log(1 + volume)
```

For heavily skewed positive values.

Other possible transforms:

```text
signed log
Box-Cox
Yeo-Johnson
```

Advanced transformations should be explicit and reproducible.

---

# 10.40 Ratio Safety

Financial ratios can become unstable when denominators approach zero.

Examples:

```text
P/E with near-zero earnings
Debt/EBITDA with negative EBITDA
ROE with tiny equity base
```

Ranking Engine should consume already validated metrics and maintain:

```text
ratio_valid
```

Do not rank mathematically meaningless values.

---

# 10.41 Negative Fundamental Values

Do not assume negative numbers are always missing.

Examples:

```text
negative earnings
negative FCF
negative growth
```

These are valid economic observations but may require special treatment depending on the metric.

---

# 10.42 Nonlinear Preference Metrics

Some metrics are not strictly "higher is better" or "lower is better."

Example:

```text
beta near 1 may be preferred
```

or:

```text
valuation too low can indicate distress
```

Such metrics need:

```text
TARGET_RANGE
```

or custom transformation.

---

# 10.43 Distance-to-Target Ranking

For target-centered metrics:

```text
score =
-abs(value - target)
```

Then rank.

This is useful for custom strategy logic.

---

# 10.44 Quality Weighting

Ranks may optionally consider source/data quality.

Example:

```text
raw factor score
×
data quality confidence
```

But raw rank and quality-adjusted rank should remain separate.

---

# 10.45 Peer-Group Quality

Track:

```text
peer_count
peer_valid_count
peer_missing_count
```

A percentile based on 450 valid peers is more reliable than one based on 6.

---

# 10.46 Rank Confidence

Possible output:

```text
rank_confidence
```

Inputs:

```text
peer count
metric quality
outlier stability
missingness
rank stability
```

This is optional but useful later.

---

# 10.47 Cross-Sectional Correlation

For research, calculate correlations between ranked metrics.

Examples:

```text
momentum vs volatility
quality vs value
size vs liquidity
```

This helps identify redundant factors.

This belongs to research analytics rather than daily per-stock output.

---

# 10.48 Factor Exposure Matrix

Later, standardized features form:

```text
stock × factor matrix
```

Example:

```text
              Momentum  Value  Quality  LowVol
Stock A          1.2     -0.4    0.8     0.3
Stock B         -0.8      1.1    0.2    -0.5
```

Step 10 provides the standardized building blocks.

---

# 10.49 Historical Ranking Store

Recommended:

```text
date
universe_id
instrument_key
metric_name

raw_value
winsorized_value

rank
percentile

z_score
robust_z

sector_rank
sector_percentile

industry_rank
industry_percentile

size_rank
size_percentile

quality_status
```

---

# 10.50 Wide vs Long Storage

Two design options:

## Wide Table

```text
instrument_key
date
mom_pct_63d
vol_pct_63d
liquidity_pct
...
```

Pros:

```text
fast feature access
simple queries
```

Cons:

```text
many columns
schema expansion
```

## Long Table

```text
instrument_key
date
metric_name
raw_value
percentile
z_score
```

Pros:

```text
flexible
generic
```

Cons:

```text
more joins
larger row count
```

Open Analytics may use:

```text
long normalization store
+
wide production feature tables
```

for efficiency.

---

# 10.51 Metric Registry

Create a metadata registry for every rankable metric.

Fields:

```text
metric_name
source_engine
description

direction
transform
winsorization_method
normalization_method

default_peer_group
minimum_peer_count

allow_sector_neutralization
allow_size_neutralization

active
version
```

Example:

```text
metric_name = mom_126d
direction = HIGHER_IS_BETTER
transform = NONE
winsorization = P01_P99
normalization = ROBUST_Z
peer_group = UNIVERSE
```

This avoids duplicating rules in code.

---

# 10.52 Versioning

Normalization rules can change.

Store:

```text
normalization_version
metric_version
```

This is critical for reproducible backtests.

---

# 10.53 Point-in-Time Sector Mapping

If a company changes sector classification historically, use the mapping valid at that date.

Do not apply today's sector mapping retroactively unless intentionally doing a restated research view.

---

# 10.54 Point-in-Time Market Cap

Size-neutralization and size-bucket ranks must use historical market cap.

Never use today's market cap for a historical ranking.

---

# 10.55 Survivorship Bias Protection

Historical ranking must include securities that were eligible then but later:

```text
delisted
failed
merged
became illiquid
left the index
```

---

# 10.56 Look-Ahead Protection

At date T, use only:

```text
metrics available through T
classification known at T
universe membership at T
```

Never use future restatements or future membership without explicit point-in-time handling.

---

# 10.57 Tie Handling

Ranks may have ties.

Define one consistent method:

```text
average rank
dense rank
minimum rank
```

Recommended:

```text
average rank
```

for percentile calculations, unless research indicates otherwise.

Document the choice.

---

# 10.58 Percentile Convention

Choose one platform-wide convention.

Recommended:

```text
0 = weakest
100 = strongest
```

after direction adjustment.

This keeps all user-facing factor percentiles intuitive.

---

# 10.59 Decile Convention

Recommended:

```text
1  = weakest
10 = strongest
```

again after direction adjustment.

---

# 10.60 Composite Standardization

Before combining multiple factors, transform each input into a comparable scale.

Possible:

```text
robust z-score
rank-normalized score
percentile
```

Do not combine:

```text
P/E raw
+
ROE raw
+
momentum raw
```

directly.

---

# 10.61 Rank-Based Composite

Example:

```text
composite =
mean(
    momentum_percentile,
    quality_percentile,
    value_percentile
)
```

This is simple and robust.

More advanced weighting belongs in Factor Engine.

---

# 10.62 Z-Score Composite

Example:

```text
composite_z =
w1 * momentum_z
+
w2 * quality_z
+
w3 * value_z
```

Weights should be researched.

---

# 10.63 Neutralized Composite

Before combining:

```text
sector-neutral momentum
sector-neutral value
size-neutral quality
```

may be used.

This helps reduce unintended systematic exposures.

---

# 10.64 Ranking Quality Status

Possible:

```text
VALID
LOW_PEER_COUNT
HIGH_MISSINGNESS
OUTLIER_SENSITIVE
STALE_INPUT
INVALID_SOURCE_METRIC
```

Store:

```text
rank_quality_status
```

---

# 10.65 Recommended Ranking Record

A generic record:

```text
date
universe_id
instrument_key
metric_name


# INPUT

raw_value
input_valid
input_quality_status


# TRANSFORM

transformed_value
winsorized_value


# UNIVERSE COMPARISON

universe_rank
universe_percentile

raw_z
direction_adjusted_z
robust_z


# SECTOR

sector_rank
sector_percentile
sector_z

sector_neutral_value
sector_neutral_z


# INDUSTRY

industry_rank
industry_percentile
industry_z


# SIZE

size_rank
size_percentile
size_z

size_neutral_z


# BUCKETS

quartile
quintile
decile

top_10pct_flag
bottom_10pct_flag


# CHANGE

rank_change_1d
rank_change_5d
rank_change_21d

percentile_change_5d
percentile_change_21d


# PEER QUALITY

peer_count
sector_peer_count
industry_peer_count


# FINAL

rank_valid
rank_quality_status

normalization_version
```

---

# 10.66 Initial Production Metrics to Normalize

First production should standardize outputs from Steps 4–9.

## Returns

```text
return_21d
return_63d
return_126d
return_252d
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

## Momentum

```text
mom_63d
mom_126d
mom_12_1
market_rel_mom_126d
sector_rel_mom_126d
```

## Volume

```text
rvol_20d
volume_z_20d
obv_slope_20d
participation_quality_score
```

---

# 10.67 Initial Production Outputs

For each important metric:

```text
raw_value
universe_rank
universe_percentile
robust_z
sector_percentile
size_percentile
decile
rank_quality_status
```

This is enough to support the first Factor Engine.

---

# 10.68 Cross-Sectional Ranking Engine Processing Flow

Recommended:

```text
POINT-IN-TIME UNIVERSE
        ↓
VALID SOURCE METRICS
        ↓
METRIC REGISTRY RULES
        ↓
PEER-GROUP SELECTION
        ↓
RAW DISTRIBUTION CHECK
        ↓
TRANSFORMATION
        ↓
WINSORIZATION
        ↓
RANK
        ↓
PERCENTILE
        ↓
STANDARD Z-SCORE
        ↓
ROBUST Z-SCORE
        ↓
SECTOR / INDUSTRY RANK
        ↓
SIZE RANK
        ↓
NEUTRALIZATION
        ↓
QUANTILE BUCKETS
        ↓
RANK CHANGE / STABILITY
        ↓
QUALITY FLAGS
```

---

# 10.69 Important Quant Rules

## Rule 1 — Raw Metrics Are Not Comparable Across Scales

Normalize before combining factors.

---

## Rule 2 — Direction Must Be Explicit

Higher is not always better.

---

## Rule 3 — Use Robust Statistics

Financial data often contains extreme outliers.

---

## Rule 4 — Preserve Raw Values

Never destroy original metrics during winsorization or transformation.

---

## Rule 5 — Compare Like with Like

Sector and size peer groups matter.

---

## Rule 6 — Ranking Must Be Point-in-Time

Use the historical universe valid on each date.

---

## Rule 7 — Neutralization Should Be Explicit

Do not silently remove sector or size effects.

---

## Rule 8 — Missing Is Not Zero

Never rank missing data as average by default.

---

## Rule 9 — Peer Count Matters

Tiny groups create unstable rankings.

---

## Rule 10 — Historical Classifications Matter

Use historical sector and market-cap information where possible.

---

## Rule 11 — Standardize User-Facing Percentiles

Recommended convention:

```text
100 = strongest / most desirable
0 = weakest / least desirable
```

---

## Rule 12 — Version the Normalization Logic

Backtests must remain reproducible after methodology changes.

---

# 10.70 Completion Criteria

Step 10 is complete when Open Analytics can answer:

1. What is the stock's raw metric value?
2. Where does it rank in the eligible universe?
3. What is its percentile?
4. What is its standard z-score?
5. What is its robust z-score?
6. Was the metric winsorized?
7. How does it rank inside its sector?
8. How does it rank inside its industry?
9. How does it rank against similar-size companies?
10. What is the sector-neutral score?
11. What is the size-neutral score?
12. What decile/quintile does it belong to?
13. Is the rank improving or deteriorating?
14. Is the peer group large enough?
15. Is the input metric valid?
16. Which transformation and normalization rules were used?
17. Which historical universe was used?
18. Can the exact ranking be reproduced later?

Once these are reliable, the Cross-Sectional Ranking Engine is ready to feed:

```text
Step 11 — Fundamental Engine
```

---

# Step 10 Final Output

The Cross-Sectional Ranking Engine transforms:

```text
Raw Quant Metrics
+
Historical Universe
+
Peer Classifications
```

into:

```text
Ranks
Percentiles
Standard Z-Scores
Robust Z-Scores
Winsorized Features
Sector Ranks
Industry Ranks
Size-Peer Ranks
Sector-Neutral Features
Size-Neutral Features
Quantile Buckets
Rank Momentum
Rank Stability
Normalization Quality Flags
```

This becomes the standardization layer that allows Open Analytics to combine fundamentally different measurements into professional factor and alpha models.
