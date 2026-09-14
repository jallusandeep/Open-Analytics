# Open Analytics — Step 27: ML Dataset Engine

## Purpose

The **ML Dataset Engine** converts the entire Open Analytics research stack into clean, point-in-time, leakage-safe datasets for machine learning and statistical modeling.

This engine should answer:

- What is one training row?
- What timestamp does that row represent?
- Which features were actually known at that timestamp?
- What target is the model trying to predict?
- Which securities are eligible?
- How are missing values handled?
- How are categorical features encoded?
- How are numerical features normalized?
- How are train, validation, and test periods separated?
- How are overlapping forward-return labels handled?
- How do we prevent future data from leaking into features?
- How do we preserve historical universe membership?
- How do we version datasets for reproducibility?
- How do we create the same features in research and production?

The output feeds directly into:

- Step 28 — ML / Forecasting Engine
- Statistical modeling
- Cross-sectional return prediction
- Classification models
- Ranking models
- Regime models
- Risk forecasting
- Signal research
- Feature importance analysis

---

# 27.1 Core Principle

A machine-learning dataset is not just:

```text
SELECT *
FROM features
JOIN future_returns
```

A valid quant ML dataset must preserve:

```text
Point-in-Time Availability
Historical Universe Membership
Feature/Label Separation
Timestamp Alignment
No Look-Ahead
No Survivorship Bias
Stable Feature Definitions
Reproducible Dataset Versions
```

---

# 27.2 Row Definition

The first design decision is defining one row.

Recommended base key:

```text
as_of_date
instrument_key
```

For intraday models:

```text
as_of_timestamp
instrument_key
```

Every row represents:

```text
what Open Analytics knew
about one security
at one specific historical time
```

---

# 27.3 Observation Timestamp

Store:

```text
as_of_timestamp
```

This is the model decision timestamp.

All features must satisfy:

```text
feature_available_at <= as_of_timestamp
```

---

# 27.4 Label Timestamp

Store:

```text
label_start_timestamp
label_end_timestamp
```

This makes target horizons explicit.

---

# 27.5 Dataset Grain

Possible grains:

```text
DAILY_SECURITY
WEEKLY_SECURITY
MONTHLY_SECURITY
EVENT_SECURITY
INTRADAY_SECURITY
MARKET_DAY
SECTOR_DAY
```

Initial recommended production grain:

```text
DAILY_SECURITY
```

---

# 27.6 Daily Security Dataset

Primary key:

```text
as_of_date
instrument_key
dataset_version
```

---

# 27.7 Universe Eligibility

Every row should include:

```text
universe_id
universe_eligible
```

Only securities eligible at that historical date should enter model training unless explicitly researching a broader universe.

---

# 27.8 Historical Universe Membership

Use:

```text
point-in-time universe membership
```

Never today's surviving securities only.

---

# 27.9 Security Metadata

Recommended:

```text
instrument_key
company_id
ISIN
exchange
sector
industry
market_cap_bucket
```

Use historical mappings where required.

---

# 27.10 Feature Sources

The ML dataset can consume features from:

```text
Step 4  Returns
Step 5  Risk
Step 6  Liquidity
Step 7  Trend
Step 8  Momentum
Step 9  Volume / Participation
Step 10 Cross-Sectional Ranking
Step 11 Fundamentals
Step 12 Valuation
Step 13 Factors
Step 14 News / Events
Step 15 Institutional Flow
Step 16 Derivatives
Step 17 Market Breadth
Step 18 Market Regime
Step 19 Alpha / Signals
Step 20 Confidence
```

Portfolio/execution outputs should usually not be used as predictors for stock-return models unless the research question specifically requires them.

---

# 27.11 Feature Registry

Maintain a registry:

```text
feature_name
feature_version
feature_family

data_type
description

source_engine
source_table

availability_rule
lookback_window

normalization
missing_value_policy

higher_is_better
active
```

---

# 27.12 Feature Versioning

Every feature formula change requires:

```text
new feature_version
```

Do not silently overwrite historical feature definitions.

---

# 27.13 Feature Availability Timestamp

Each underlying source should expose:

```text
available_at
```

Examples:

```text
price close available after session close
financial results available after announcement
news available at publication time
flow data available when published
```

---

# 27.14 Feature Event Time vs Availability Time

Important distinction:

```text
event_time
```

and:

```text
available_at
```

may differ.

Use:

```text
available_at
```

for ML joins.

---

# 27.15 Point-in-Time Join

Feature join rule:

```text
latest valid feature record
with available_at <= as_of_timestamp
```

Do not join by period date alone.

---

# 27.16 As-Of Join

For slow-moving features:

```text
fundamentals
macro
ownership
```

use an as-of join.

Concept:

```text
feature_date <= observation_date
AND
available_at <= observation_timestamp
```

---

# 27.17 Feature Age

Store:

```text
feature_age_days
```

for stale-sensitive inputs.

Examples:

```text
fundamental_age_days
news_age_hours
flow_age_days
```

---

# 27.18 Feature Freshness Flags

Possible:

```text
fundamental_stale_flag
news_stale_flag
derivative_stale_flag
```

These may themselves become model features.

---

# 27.19 Price Features

Possible:

```text
return_1d
return_5d
return_21d

log_return_1d

gap_return

distance_to_52w_high
```

Never include future returns as predictors.

---

# 27.20 Momentum Features

Possible:

```text
momentum_21d
momentum_63d
momentum_126d
momentum_252d
momentum_12_1

relative_momentum
momentum_percentile
```

---

# 27.21 Trend Features

Possible:

```text
price_vs_sma20
price_vs_sma50
price_vs_sma200

trend_slope
trend_r2
ADX

breakout_strength
```

---

# 27.22 Risk Features

Possible:

```text
volatility_21d
volatility_63d
downside_volatility

beta
drawdown
CVaR

idiosyncratic_volatility
```

---

# 27.23 Liquidity Features

Possible:

```text
ADV
turnover
spread
Amihud
trading_frequency
days_to_liquidate
```

---

# 27.24 Volume / Participation Features

Possible:

```text
RVOL
volume_z
OBV slope
CMF
MFI
delivery_pct
participation_score
```

---

# 27.25 Fundamental Features

Possible:

```text
revenue_growth
EPS_growth
ROE
ROIC
margin
FCF_margin
debt_to_equity
cash_conversion
accruals
```

---

# 27.26 Valuation Features

Possible:

```text
earnings_yield
book_to_price
FCF_yield
EV_EBITDA
value_percentile
```

---

# 27.27 Factor Features

Possible:

```text
momentum_factor
value_factor
quality_factor
growth_factor
low_vol_factor
liquidity_factor
```

---

# 27.28 News Features

Possible:

```text
news_sentiment_24h
news_sentiment_7d
event_intensity
novelty
event_risk
positive_catalyst
negative_catalyst
```

---

# 27.29 Institutional Flow Features

Market-level:

```text
fii_flow_z
dii_flow_z
institutional_flow_score
```

Sector/stock-level where reliable.

---

# 27.30 Derivatives Features

Possible:

```text
basis_pct
OI_change
futures_position_state
ATM_IV
IV_percentile
PCR
put_skew
expected_move
```

---

# 27.31 Breadth Features

Market-level:

```text
advance_pct
pct_above_sma50
pct_above_sma200
breadth_score
```

---

# 27.32 Regime Features

Possible:

```text
regime_label
trend_regime_score
volatility_regime_score
market_stress_score
bull_probability
bear_probability
```

---

# 27.33 Cross-Sectional Features

Prefer normalized versions for many stock-selection models:

```text
rank
percentile
z-score
sector-relative percentile
```

---

# 27.34 Raw vs Normalized Features

Store both where practical:

```text
raw_metric
normalized_metric
```

This supports model flexibility.

---

# 27.35 Target / Label Families

Possible labels:

```text
FORWARD_RETURN
EXCESS_RETURN
RELATIVE_RETURN
UP_DOWN
OUTPERFORM
RANK
VOLATILITY
DRAWDOWN
EVENT_RESPONSE
```

---

# 27.36 Forward Return Label

Example:

```text
target_return_5d =
price_(t+5) / price_t - 1
```

Use adjusted prices consistently.

---

# 27.37 Recommended Return Horizons

```text
1D
2D
5D
10D
21D
63D
```

Do not create unnecessary horizons without research purpose.

---

# 27.38 Excess Return Label

Possible:

```text
stock_forward_return
-
benchmark_forward_return
```

Store:

```text
target_excess_return_21d
```

---

# 27.39 Sector-Relative Return Label

Possible:

```text
stock return
-
sector return
```

---

# 27.40 Cross-Sectional Rank Label

At each date:

```text
rank forward returns across universe
```

Store:

```text
target_return_rank_21d
```

Useful for ranking models.

---

# 27.41 Binary Direction Label

Possible:

```text
target_up_5d =
1 if forward_return_5d > 0
else 0
```

---

# 27.42 Outperformance Label

Possible:

```text
1 if stock_return > benchmark_return
```

---

# 27.43 Quantile Classification Label

Possible:

```text
TOP_DECILE
MIDDLE
BOTTOM_DECILE
```

Useful for classification but loses continuous information.

---

# 27.44 Volatility Target

Possible:

```text
future_realized_volatility_21d
```

for risk forecasting.

---

# 27.45 Drawdown Target

Possible:

```text
future_max_drawdown_21d
```

---

# 27.46 Event Response Label

For event ML:

```text
abnormal_return_1d
abnormal_return_5d
```

after event publication.

---

# 27.47 Label Leakage Rule

Target fields must never appear in the feature matrix.

Maintain separate logical groups:

```text
X = features
y = labels
```

---

# 27.48 Label Availability

Training row may be created at T but label only becomes known at:

```text
T + horizon
```

Store:

```text
label_available_at
```

---

# 27.49 Overlapping Labels

Forward 21D returns overlap heavily across adjacent daily observations.

This causes:

```text
serial dependence
train-test leakage
```

if splitting is naive.

---

# 27.50 Purging

When labels overlap across train/test boundaries, remove training samples whose label window overlaps the validation/test period.

---

# 27.51 Embargo

Apply a time gap after test samples where appropriate.

Store:

```text
embargo_sessions
```

---

# 27.52 Feature Lookback Overlap

Feature windows may overlap, which is normal.

The key issue is:

```text
future information crossing split boundaries
```

---

# 27.53 Train / Validation / Test Split

For financial time series use chronological splits.

Recommended:

```text
TRAIN
VALIDATION
TEST
```

Never random-shuffle time series by default.

---

# 27.54 Example Split

Conceptual:

```text
Train:      older history
Validation: later period
Test:       newest untouched period
```

---

# 27.55 Walk-Forward Dataset

Recommended:

```text
Train Window 1 → Test Period 1
Train Window 2 → Test Period 2
...
```

---

# 27.56 Expanding Window

Use all history before each test period.

---

# 27.57 Rolling Window

Use only last N years/sessions.

---

# 27.58 Cross-Sectional Sampling

At each date, include:

```text
all valid eligible securities
```

or a clearly defined subsample.

---

# 27.59 Class Imbalance

For classification targets:

```text
up/down
top/bottom quantile
```

monitor:

```text
class_distribution
```

---

# 27.60 Rebalancing Classes

Possible:

```text
class weights
undersampling
oversampling
```

But avoid methods that distort time structure.

---

# 27.61 Missing Values

Possible policies:

```text
DROP_ROW
DROP_FEATURE
MEDIAN_IMPUTE
SECTOR_MEDIAN
FORWARD_ASOF
MISSING_INDICATOR
MODEL_NATIVE_MISSING
```

Feature-specific rules are preferable.

---

# 27.62 Unknown Is Not Zero

Never replace missing with zero unless zero is economically correct.

---

# 27.63 Missing Indicator

For many features create:

```text
feature_missing_flag
```

when missingness itself may carry information.

---

# 27.64 Fundamental Missingness

A young company may have less history.

Use:

```text
history_length
fundamental_available_flag
```

rather than arbitrary zeros.

---

# 27.65 Winsorization

Possible:

```text
cross-sectional percentile clipping
```

e.g.:

```text
1st–99th percentile
```

Exact thresholds must be versioned.

---

# 27.66 Outlier Handling

Options:

```text
winsorize
clip
robust scaling
keep + outlier flag
```

---

# 27.67 Standardization

Possible:

```text
z-score
robust z-score
rank transform
percentile
```

For cross-sectional equity models, date-wise normalization is often useful.

---

# 27.68 Cross-Sectional Z-Score

At each date:

```text
z_i,t =
(x_i,t - mean_t) / std_t
```

---

# 27.69 Sector-Neutral Z-Score

Calculate within sector.

---

# 27.70 Robust Z-Score

Use:

```text
median
MAD
```

where distributions have heavy tails.

---

# 27.71 Rank Transform

Convert values into:

```text
rank
percentile
```

Useful for robust tree/ranking models.

---

# 27.72 Gaussian Rank Transform

Optional:

```text
rank → normal quantile
```

---

# 27.73 Scaling Leakage

Scalers must be fitted only on:

```text
training data
```

Never fit normalization parameters on test data.

---

# 27.74 Cross-Sectional Daily Scaling

For date-wise ranking/z-score features, calculation can use same-date eligible universe because it is observable at that date.

---

# 27.75 Time-Series Scaling

Rolling normalization must use only prior/current observations.

---

# 27.76 Categorical Features

Examples:

```text
sector
industry
market_cap_bucket
regime
```

Possible encodings:

```text
one-hot
ordinal
target encoding
embedding
```

---

# 27.77 Target Encoding Leakage

If target encoding is used:

```text
fit only on training folds
```

with leakage-safe cross-validation.

---

# 27.78 Entity Identifiers

Do not blindly use:

```text
instrument_key
symbol
```

as model predictors unless deliberately modeling entity effects.

---

# 27.79 Date Features

Possible:

```text
day_of_week
month
quarter
expiry_week
```

Use only if economically justified.

---

# 27.80 Age Features

Possible:

```text
days_since_listing
days_since_event
days_since_filing
```

---

# 27.81 Interaction Features

Possible:

```text
momentum × regime
value × quality
news × volume
flow × breadth
```

Start simple; avoid uncontrolled feature explosion.

---

# 27.82 Feature Redundancy

Track correlation between features.

Possible:

```text
feature_correlation_matrix
```

---

# 27.83 Multicollinearity

Important for linear models.

Possible diagnostics:

```text
VIF
correlation thresholds
```

---

# 27.84 Feature Clustering

Group highly correlated features.

---

# 27.85 Feature Selection

Possible methods:

```text
economic preselection
IC filtering
stability filtering
regularization
tree importance
permutation importance
```

Never select features using final test set.

---

# 27.86 Feature IC

For each candidate feature:

```text
rank_IC(feature_t, forward_return_t+h)
```

---

# 27.87 Feature IC Stability

Store:

```text
mean_IC
IC_std
IC_IR
positive_IC_ratio
```

---

# 27.88 Feature Coverage

Store:

```text
feature_non_null_pct
```

---

# 27.89 Feature Turnover

For ranking features:

```text
rank_autocorrelation
```

---

# 27.90 Feature Decay

Evaluate predictive power over:

```text
1D
5D
21D
63D
```

---

# 27.91 Feature Regime Stability

Evaluate IC by:

```text
bull
bear
high vol
low vol
```

---

# 27.92 Feature Sector Stability

Evaluate by sector.

---

# 27.93 Feature Size Stability

Evaluate by market-cap bucket.

---

# 27.94 Feature Quality Score

Possible combination:

```text
coverage
stability
IC
regime robustness
```

Output:

```text
feature_quality_score
```

---

# 27.95 Dataset Row Quality

Each row may have:

```text
row_quality_score
```

Inputs:

```text
feature coverage
stale inputs
data quality flags
```

---

# 27.96 Row Exclusion Rules

Possible:

```text
critical bad price
insufficient history
not universe eligible
suspended
missing target
```

---

# 27.97 Training Eligibility

Store:

```text
training_eligible
```

---

# 27.98 Inference Eligibility

Store separately:

```text
inference_eligible
```

A row can be inference-eligible even though future label is not yet known.

---

# 27.99 Label Completeness

Near dataset end:

```text
future labels unavailable
```

These rows can be used for inference but not training.

---

# 27.100 Right-Censoring

Handle rows where label horizon extends beyond available data.

Do not assign partial target silently.

---

# 27.101 Delisting Labels

If stock delists during label window, target methodology must define outcome.

Do not simply drop losing securities.

---

# 27.102 Suspension Labels

Handle untradable periods explicitly.

---

# 27.103 Corporate Actions

Targets should use correctly adjusted return series.

---

# 27.104 Benchmark Alignment

Excess-return labels require same-period benchmark return.

---

# 27.105 Sector Benchmark Alignment

Sector-relative targets use historical sector mapping.

---

# 27.106 Sample Weighting

Possible sample weights:

```text
equal
liquidity weighted
confidence weighted
recency weighted
```

Use only if model objective requires it.

---

# 27.107 Recency Weighting

Possible:

```text
newer observations receive more weight
```

but this changes model objective and must be validated.

---

# 27.108 Liquidity Weighting

Can reduce influence of economically untradeable microcaps.

Better alternative may be:

```text
universe eligibility filter
```

rather than weighting.

---

# 27.109 Label Winsorization

Forward returns can have extreme tails.

Possible:

```text
winsorize labels
```

for some models, but retain raw label too.

---

# 27.110 Raw Label Preservation

Store:

```text
target_return_raw
target_return_winsorized
```

separately.

---

# 27.111 Cross-Sectional Demeaned Label

Possible:

```text
stock_return - cross_section_mean_return
```

---

# 27.112 Market-Neutral Label

Possible:

```text
residual return after market beta
```

---

# 27.113 Residual Return Label

Estimate:

```text
stock return
-
expected factor return
```

Useful for idiosyncratic alpha modeling.

---

# 27.114 Ranking Dataset

For learning-to-rank models:

```text
group_id = date
```

Rows within each date form a ranking group.

---

# 27.115 Pairwise Ranking Labels

Optional later.

---

# 27.116 Event Dataset

For event models, row key:

```text
event_id
instrument_key
as_of_timestamp
```

Features must represent information known immediately after event availability.

---

# 27.117 Market Dataset

For market-regime ML, one row may be:

```text
date
market_id
```

---

# 27.118 Sector Dataset

Possible:

```text
date
sector_id
```

---

# 27.119 Multi-Task Dataset

Could contain multiple targets:

```text
return_5d
return_21d
vol_21d
drawdown_21d
```

but training architecture should decide which targets to use.

---

# 27.120 Feature Store vs ML Dataset

Separate concepts:

```text
Feature Store
→ reusable point-in-time features

ML Dataset
→ selected features + labels + split metadata
```

---

# 27.121 Feature Store Table

Possible wide daily table:

```text
security_daily_features
```

---

# 27.122 Long Feature Table

Alternative:

```text
date
instrument_key
feature_name
feature_value
feature_version
```

Useful for registry-driven systems.

---

# 27.123 ML Dataset Manifest

Every dataset build should store:

```text
dataset_id
dataset_version

created_at

start_date
end_date

universe_id

feature_set_version
label_set_version

split_definition
normalization_version

row_count
feature_count

code_commit
config_hash
```

---

# 27.124 Dataset Hash

Create:

```text
dataset_hash
```

from:

```text
config
feature versions
label versions
source snapshot IDs
```

---

# 27.125 Source Snapshot IDs

Where practical, record:

```text
source_table_snapshot
```

or source data version.

---

# 27.126 Reproducibility

The exact same manifest should rebuild:

```text
same rows
same features
same labels
same splits
```

---

# 27.127 Dataset Split Metadata

Each row should carry:

```text
split
```

Possible:

```text
TRAIN
VALIDATION
TEST
LIVE_INFERENCE
```

---

# 27.128 Fold Metadata

For walk-forward CV:

```text
fold_id
```

---

# 27.129 Purge Metadata

Store:

```text
purged_flag
```

---

# 27.130 Embargo Metadata

Store:

```text
embargo_flag
```

---

# 27.131 Dataset Quality Report

For every build report:

```text
row count
date coverage
security count
feature coverage
missingness
label distribution
class balance
outliers
split sizes
```

---

# 27.132 Leakage Audit

Automated checks should test:

```text
feature_available_at > as_of_timestamp
forward-return feature accidentally included
future constituent mapping
future fundamental revision
future news update
```

---

# 27.133 Feature-Label Name Guard

Any feature with names like:

```text
forward
future
target
label
```

should trigger explicit validation.

---

# 27.134 Correlation Leakage Check

If a feature correlates almost perfectly with target:

```text
investigate
```

It may be legitimate, but often signals leakage.

---

# 27.135 Timestamp Leakage Check

Check max source timestamp per row.

---

# 27.136 Revision Leakage Check

For fundamentals/macro:

```text
ensure original vintage
```

where available.

---

# 27.137 Post-Event Leakage

For event models, ensure no post-event price reaction is used as a feature before the prediction timestamp unless explicitly intended.

---

# 27.138 Same-Day Close Leakage

If model predicts next-day return using EOD data:

```text
features may use today's close
```

but execution should be after that close.

Dataset semantics must match production execution.

---

# 27.139 Dataset Timing Contract

Every dataset should declare:

```text
feature cutoff
decision time
earliest execution time
label start time
```

---

# 27.140 Example Daily Timing Contract

Conceptual:

```text
Feature cutoff:      market close T
Decision time:       after close T
Earliest execution:  next session T+1
Label start:         T+1 execution reference
```

---

# 27.141 Feature Selection Pipeline

Recommended:

```text
candidate features
        ↓
quality filter
        ↓
coverage filter
        ↓
redundancy analysis
        ↓
economic review
        ↓
training-only selection
        ↓
final feature set
```

---

# 27.142 Initial Feature Set

V1 should use stable interpretable features from:

```text
returns
trend
momentum
risk
liquidity
volume
fundamentals
valuation
factors
breadth
regime
```

Add:

```text
news
flow
derivatives
```

once those data sources are reliable.

---

# 27.143 Avoid Feature Explosion

Do not create thousands of arbitrary technical indicators immediately.

Prefer:

```text
economically justified
non-redundant
stable
```

features.

---

# 27.144 Feature Family Limits

Track feature counts by family to prevent one family dominating by sheer dimensionality.

---

# 27.145 Feature Family Metadata

Example:

```text
MOMENTUM
RISK
FUNDAMENTAL
VALUATION
NEWS
FLOW
```

---

# 27.146 Dataset for Regression

Target:

```text
continuous forward return
```

---

# 27.147 Dataset for Classification

Target:

```text
up/down
outperform/not
top-decile/not
```

---

# 27.148 Dataset for Ranking

Target:

```text
cross-sectional forward-return rank
```

---

# 27.149 Dataset for Volatility Forecasting

Target:

```text
future realized volatility
```

---

# 27.150 Dataset for Risk Forecasting

Targets:

```text
future drawdown
future tail loss
```

---

# 27.151 Dataset for Event Modeling

Targets:

```text
post-event abnormal return
IV change
volume response
```

---

# 27.152 Dataset for Regime Modeling

Features:

```text
market-level trend
volatility
breadth
flow
derivatives
```

Targets may be:

```text
latent / clustering
future risk state
```

depending on model.

---

# 27.153 Training Dataset Row

Recommended:

```text
dataset_id
dataset_version

as_of_date
as_of_timestamp

instrument_key
company_id

universe_id

sector
industry
market_cap_bucket

feature columns...

target_return_1d
target_return_5d
target_return_21d
target_excess_return_21d
target_rank_21d

training_eligible
inference_eligible

row_quality_score

split
fold_id
```

---

# 27.154 Feature Metadata Table

```text
feature_name
feature_version
feature_family
description

source_engine
source_table

data_type
lookback

availability_rule

normalization
missing_policy

active
```

---

# 27.155 Label Metadata Table

```text
label_name
label_version

horizon
definition

price_reference
benchmark

winsorization

label_start_rule
label_end_rule
```

---

# 27.156 Dataset Build Record

```text
dataset_id
dataset_version

created_at

universe_id
start_date
end_date

feature_set_version
label_set_version

split_config
purge_config
embargo_config

row_count
column_count

dataset_hash

build_status
quality_status
```

---

# 27.157 Initial Production Dataset

Recommended first ML dataset:

```text
Daily NSE equity cross-sectional dataset
```

with:

```text
point-in-time eligible equities
```

Features from:

```text
returns
risk
liquidity
trend
momentum
volume
fundamentals
valuation
factor ranks
market regime
breadth
```

Target:

```text
21D forward sector-relative return
```

plus:

```text
5D
63D
```

for research comparison.

---

# 27.158 Why Sector-Relative Return Is Useful

It reduces some broad sector beta and asks:

```text
which stocks outperform peers?
```

But retain absolute and benchmark-relative labels too.

---

# 27.159 Recommended V1 Split

Use chronological:

```text
TRAIN
VALIDATION
TEST
```

with purging for overlapping labels.

Then later move to:

```text
walk-forward folds
```

---

# 27.160 Recommended V1 Normalization

Prefer existing cross-sectional:

```text
percentiles
z-scores
```

from Step 10.

This reduces need for leakage-prone global scaling.

---

# 27.161 Recommended V1 Missing Strategy

Use:

```text
feature-specific null handling
+
missing flags
```

Do not use universal zero-fill.

---

# 27.162 Recommended V1 Models Compatibility

Dataset should support:

```text
linear regression
logistic regression
gradient boosting
random forest
learning-to-rank
neural networks later
```

---

# 27.163 Dataset Processing Flow

Recommended:

```text
POINT-IN-TIME UNIVERSE
        ↓
FEATURE REGISTRY
        ↓
SOURCE FEATURES
        ↓
AVAILABILITY-TIME CHECK
        ↓
AS-OF JOINS
        ↓
ROW QUALITY CHECK
        ↓
MISSING / OUTLIER HANDLING
        ↓
NORMALIZATION
        ↓
LABEL GENERATION
        ↓
LABEL AVAILABILITY CHECK
        ↓
TRAIN / VALID / TEST SPLITS
        ↓
PURGE / EMBARGO
        ↓
LEAKAGE AUDIT
        ↓
DATASET MANIFEST
        ↓
VERSIONED ML DATASET
```

---

# 27.164 Point-in-Time Rule

For every row:

```text
max(feature_available_at)
<=
as_of_timestamp
```

This should be machine-validated.

---

# 27.165 Historical Fundamental Rule

Use:

```text
filing available date
```

not:

```text
financial period end date
```

---

# 27.166 Historical News Rule

Use the article/event version known at the observation time.

Do not use later corrected sentiment retrospectively.

---

# 27.167 Historical Universe Rule

Use membership as known on that date.

---

# 27.168 Historical Sector Rule

Use point-in-time sector classification where feasible.

---

# 27.169 Historical Market Cap

Calculate using contemporaneous:

```text
price
shares outstanding known at T
```

---

# 27.170 Label Isolation Rule

Labels should be built after feature matrix is frozen logically.

This helps prevent accidental use in transformations.

---

# 27.171 Test Set Isolation

The final test set must remain untouched until model selection is complete.

---

# 27.172 Validation Set Purpose

Use for:

```text
hyperparameters
feature selection
early stopping
```

not final performance claims.

---

# 27.173 Test Set Purpose

Use only for:

```text
final unbiased evaluation
```

---

# 27.174 Walk-Forward Production Simulation

Best later standard:

```text
at each historical model date:
    train on prior history
    fit preprocessing
    fit model
    predict next period
```

---

# 27.175 Research Dataset vs Production Dataset

Keep:

```text
RESEARCH dataset
```

and:

```text
PRODUCTION feature view
```

aligned by the same feature definitions.

---

# 27.176 Training-Serving Skew

Avoid differences between:

```text
offline feature calculation
```

and:

```text
live feature calculation
```

---

# 27.177 Feature Parity Check

For overlapping dates compare:

```text
research feature
vs
production-calculated feature
```

Store mismatch rate.

---

# 27.178 Numerical Tolerance

Define tolerance for parity checks.

---

# 27.179 Dataset Drift

Compare live feature distributions with training distribution.

---

# 27.180 Population Stability Index

Possible drift metric:

```text
PSI
```

---

# 27.181 KS Statistic

Possible for continuous feature drift.

---

# 27.182 Feature Missingness Drift

Track whether missing rates change live.

---

# 27.183 Universe Drift

Track changes in:

```text
market cap distribution
sector distribution
liquidity distribution
```

---

# 27.184 Label Drift

Track changes in future return distribution during research updates.

---

# 27.185 Dataset Quality Status

Possible:

```text
VALID
LOW_COVERAGE
LEAKAGE_WARNING
SURVIVORSHIP_WARNING
SPLIT_WARNING
LABEL_INCOMPLETE
SOURCE_VERSION_MISSING
INVALID
```

---

# 27.186 Automated Dataset Tests

Required tests:

```text
unique primary key
no duplicate rows

feature timestamps valid
label timestamps future

split chronology valid
purge rules respected

historical universe valid
target non-null for training rows

no target fields in feature list
```

---

# 27.187 Duplicate Row Check

Ensure one row per:

```text
dataset_version
as_of_timestamp
instrument_key
```

---

# 27.188 Coverage Report

Report by:

```text
date
feature
sector
market cap bucket
```

---

# 27.189 Label Distribution Report

Report:

```text
mean
median
std
percentiles
skew
kurtosis
```

---

# 27.190 Split Distribution Check

Ensure:

```text
train
validation
test
```

have comparable but naturally time-varying distributions.

Do not force them to match artificially.

---

# 27.191 Feature Correlation Report

Generate only on training data for model-selection use.

---

# 27.192 Target Correlation Report

Feature-target IC/correlation should be computed separately by split.

---

# 27.193 Out-of-Sample IC

Track feature IC in validation/test.

---

# 27.194 Dataset Lineage

Every dataset column should trace to:

```text
source table
source feature
source engine
feature version
```

---

# 27.195 Storage Format

Possible:

```text
DuckDB tables
Parquet
```

Parquet is useful for large ML training datasets.

DuckDB is excellent for:

```text
point-in-time assembly
querying
validation
```

---

# 27.196 Partitioning

For Parquet:

```text
year
date
```

or dataset version depending workload.

---

# 27.197 Wide vs Long ML Table

Training often prefers:

```text
wide matrix
```

Feature registry may remain long metadata.

---

# 27.198 Memory Efficiency

Use appropriate types:

```text
float32 where acceptable
categoricals
integers
booleans
```

Validate precision needs.

---

# 27.199 Dataset Export

Support:

```text
Parquet
CSV for inspection only
Pandas
Polars
NumPy
PyTorch tensors later
```

---

# 27.200 Dataset Sampling for Development

Allow:

```text
small date range
small universe
```

for fast model development.

But final validation must use full intended dataset.

---

# 27.201 Rebuild Modes

Possible:

```text
FULL_REBUILD
INCREMENTAL_BUILD
REPAIR_RANGE
```

---

# 27.202 Incremental Build

Add rows for new dates while preserving historical versions.

---

# 27.203 Backfill

Historical feature backfills must retain version lineage.

---

# 27.204 Dataset Freeze

For model training, freeze:

```text
dataset_version
```

Do not let underlying live tables silently change the model's training data.

---

# 27.205 Model-to-Dataset Link

Every model should store:

```text
training_dataset_id
training_dataset_version
```

---

# 27.206 Experiment Tracking

Later model experiments should store:

```text
dataset version
feature set
label
hyperparameters
metrics
```

---

# 27.207 Important Quant Rules

## Rule 1 — Availability Time Beats Reference Date

A financial result from Q1 is not known until published.

## Rule 2 — Never Random-Shuffle Financial Time Series by Default

Use chronological validation.

## Rule 3 — Forward Returns Are Labels Only

Never predictors.

## Rule 4 — Historical Universe Membership Is Mandatory

Prevent survivorship bias.

## Rule 5 — Purge Overlapping Labels

Especially for 21D/63D forward returns.

## Rule 6 — Fit Preprocessing on Training Data Only

Prevent subtle leakage.

## Rule 7 — Unknown Is Not Zero

Use explicit missing-value rules.

## Rule 8 — Dataset Versions Must Be Immutable

A trained model must always trace to the exact dataset.

## Rule 9 — Training and Production Features Must Match

Prevent training-serving skew.

## Rule 10 — Test Set Must Remain Untouched

Do not repeatedly tune against final test performance.

## Rule 11 — Feature Explosion Is Not Intelligence

Prefer economically meaningful features.

## Rule 12 — Every Row Must Be Reproducible

Given dataset version and timestamp, the same row should rebuild exactly.

---

# 27.208 Completion Criteria

Step 27 is complete when Open Analytics can answer:

1. What exactly does one ML row represent?
2. What was the observation timestamp?
3. Was every feature known at that timestamp?
4. Which historical universe was used?
5. Which feature versions were used?
6. Which target definition was used?
7. What is the label horizon?
8. Are feature and label windows separated correctly?
9. Are overlapping labels purged near split boundaries?
10. Are train/validation/test splits chronological?
11. Was preprocessing fitted only on training data?
12. How are missing values handled per feature?
13. How are outliers handled?
14. How are categorical features encoded?
15. What is feature coverage?
16. What is label distribution?
17. Are delisted/suspended securities handled correctly?
18. Are historical fundamentals/news point-in-time safe?
19. Is there any leakage warning?
20. Is there any survivorship warning?
21. Can research and production feature values be compared for parity?
22. What dataset version trained a given model?
23. Can the exact ML dataset be rebuilt later?
24. Is the dataset ready for walk-forward model training?

Once these are reliable, the ML Dataset Engine is ready to feed:

```text
Step 28 — ML / Forecasting Engine
```

---

# Step 27 Final Output

The ML Dataset Engine transforms:

```text
Point-in-Time Universe
+
Versioned Features
+
Historical Metadata
+
Future Labels
```

into:

```text
Leakage-Safe Training Rows
Feature Matrix
Label Matrix
Historical Universe Alignment
Point-in-Time As-Of Joins
Missing-Value Metadata
Normalized Features
Chronological Splits
Purged / Embargoed Folds
Dataset Manifests
Dataset Hashes
Feature Lineage
Reproducible ML Datasets
```

This becomes the machine-learning data foundation for Open Analytics.
