# Open Analytics — Step 29: Stock Search / Screener Engine

## Purpose

The **Stock Search / Screener Engine** converts the entire Open Analytics research stack into an interactive discovery and filtering layer for finding securities that satisfy specific quantitative, fundamental, technical, risk, liquidity, event, factor, and ML conditions.

This engine should answer:

- Which stocks match a user-defined research condition?
- Which stocks are strongest on a chosen factor or signal?
- Which securities satisfy multiple conditions simultaneously?
- Can users screen by trend, momentum, valuation, quality, liquidity, news, flow, derivatives, risk, regime, or ML forecast?
- Can a screen be saved and rerun later?
- Can filters be combined with AND / OR / NOT?
- Can results be ranked independently from filters?
- Can screens be evaluated historically without survivorship bias?
- Can a screener explain exactly why each stock passed or failed?
- Can screening rules be converted into research universes or strategy candidates?
- Can users search securities by symbol, name, ISIN, sector, industry, or factor state?
- Can stock discovery remain point-in-time correct for backtests?

Outputs feed directly into:

- Research workflows
- Alpha / Signal Engine
- Portfolio candidate selection
- Strategy prototyping
- Watchlists
- Backtesting
- ML feature inspection
- Final Research Decision Layer

---

# 29.1 Core Principle

The screener should not be a disconnected UI filter over random columns.

It should be a structured query layer over the Open Analytics feature system.

The engine should support:

```text
Universe Selection
Filters
Boolean Logic
Ranking
Scoring
Sorting
Grouping
Explanations
Saved Screens
Point-in-Time Replay
```

A user should be able to go from:

```text
idea
```

to:

```text
reproducible stock set
```

---

# 29.2 Required Inputs

The Screener Engine can consume outputs from:

```text
Universe Definition
Returns
Risk
Liquidity
Trend
Momentum
Volume / Participation
Cross-Sectional Ranking
Fundamentals
Valuation
Factors
News / Events
Institutional Flow
Derivatives
Market Breadth
Market Regime
Alpha / Signal
Confidence
ML Forecasts
```

It also needs:

```text
security master
sector / industry mapping
point-in-time universe membership
feature registry
metric metadata
```

---

# 29.3 Search Modes

Recommended modes:

```text
SECURITY_SEARCH
FILTER_SCREEN
RANKING_SCREEN
COMPOSITE_SCREEN
POINT_IN_TIME_SCREEN
STRATEGY_CANDIDATE_SCREEN
```

---

# 29.4 Security Search

Basic lookup by:

```text
trading symbol
company name
ISIN
instrument key
sector
industry
```

Possible fuzzy search for:

```text
partial symbol
partial company name
```

---

# 29.5 Universe Selection

Before filters, choose a base universe.

Examples:

```text
ALL_NSE_EQUITY
NIFTY_50
NIFTY_100
NIFTY_200
NIFTY_500
FNO_UNIVERSE
LARGE_CAP
MID_CAP
SMALL_CAP
CUSTOM_UNIVERSE
```

Store:

```text
universe_id
```

---

# 29.6 Research vs Trading Universe

Support distinction between:

```text
research_eligible
```

and:

```text
trading_eligible
```

A user may want to research a stock that is not currently tradeable.

---

# 29.7 Filter Condition

General structure:

```text
metric
operator
value
```

Example:

```text
momentum_63d > 10%
```

---

# 29.8 Supported Operators

Recommended:

```text
>
>=
<
<=
=
!=
BETWEEN
IN
NOT_IN
IS_NULL
IS_NOT_NULL
```

For text:

```text
CONTAINS
STARTS_WITH
ENDS_WITH
```

For categorical states:

```text
IN
NOT_IN
```

---

# 29.9 Boolean Logic

Support:

```text
AND
OR
NOT
```

Nested conditions should be supported.

Example:

```text
(
    momentum_63d > 10%
    AND
    quality_factor >= 80
)
OR
(
    positive_catalyst_score >= 90
)
```

---

# 29.10 Filter Groups

Represent nested logic as groups.

Example:

```text
group_id
logical_operator
children
```

---

# 29.11 Filter Registry

Each filterable metric should have metadata:

```text
metric_name
display_name
feature_family
data_type
unit
allowed_operators
description
```

---

# 29.12 Metric Categories

Recommended:

```text
PRICE
RETURN
TREND
MOMENTUM
RISK
LIQUIDITY
VOLUME
FUNDAMENTAL
VALUATION
FACTOR
NEWS
FLOW
DERIVATIVES
BREADTH
REGIME
ALPHA
CONFIDENCE
ML
REFERENCE
```

---

# 29.13 Numeric Filters

Examples:

```text
market_cap > ₹5,000 crore
ROE > 15%
debt_to_equity < 0.5
momentum_126d > 20%
```

---

# 29.14 Percentile Filters

Examples:

```text
momentum_percentile >= 90
quality_percentile >= 80
value_percentile >= 75
```

Percentiles are often easier for cross-sectional screening.

---

# 29.15 Z-Score Filters

Examples:

```text
volume_z >= 2
flow_z <= -2
```

---

# 29.16 Categorical Filters

Examples:

```text
trend_regime IN [UPTREND, STRONG_UPTREND]
```

---

# 29.17 Boolean Filters

Examples:

```text
signal_eligible = true
broad_participation_flag = true
```

---

# 29.18 Date Filters

Possible:

```text
earnings_date within next N days
days_since_event <= N
```

Point-in-time correctness required.

---

# 29.19 Range Filters

Examples:

```text
PE between 10 and 20
beta between 0.8 and 1.2
```

---

# 29.20 Null Handling

Users should be able to specify:

```text
exclude missing
include missing
only missing
```

Do not silently treat null as zero.

---

# 29.21 Filter Order

Logical output should not depend on order.

Execution planner may reorder filters for performance.

---

# 29.22 Ranking

After filtering, allow ranking by:

```text
single metric
composite score
alpha
confidence-adjusted alpha
ML prediction
```

---

# 29.23 Ranking Direction

Support:

```text
ASC
DESC
```

Metric metadata can define default preference.

---

# 29.24 Multi-Key Sorting

Example:

```text
1. alpha_percentile DESC
2. confidence_score DESC
3. liquidity_score DESC
```

---

# 29.25 Composite Ranking

Allow combining metrics:

```text
0.4 momentum
+
0.3 quality
+
0.2 value
+
0.1 news
```

---

# 29.26 Composite Weight Validation

Weights should:

```text
sum to 1
```

or be normalized.

---

# 29.27 Direction Adjustment

If:

```text
lower is better
```

for risk or valuation metrics, adjust before composite scoring.

---

# 29.28 Rank-Based Composite

Recommended robust method:

```text
weighted average of percentiles
```

---

# 29.29 Z-Score Composite

Alternative:

```text
weighted normalized z-scores
```

---

# 29.30 Screen Score

Output:

```text
screen_score
```

This should be separate from Alpha Engine score unless intentionally mapped.

---

# 29.31 Screen Pass State

For every security:

```text
PASS
FAIL
EXCLUDED
MISSING_DATA
```

---

# 29.32 Screen Explanation

For each result expose:

```text
which conditions passed
which conditions failed
```

---

# 29.33 Reason Codes

Examples:

```text
HIGH_MOMENTUM
STRONG_QUALITY
LOW_LIQUIDITY
VALUATION_TOO_HIGH
NEWS_RISK
```

---

# 29.34 Explainability Record

Possible:

```text
instrument_key
screen_id
condition_id
metric_value
operator
threshold
pass_flag
```

---

# 29.35 Saved Screens

Users should be able to save:

```text
screen_name
screen_description
universe
filters
ranking
columns
```

---

# 29.36 Screen Versioning

If saved screen logic changes:

```text
screen_version
```

should increment.

---

# 29.37 Screen Ownership

Store:

```text
created_by
```

where user-level persistence exists.

---

# 29.38 Shared Screens

Optional:

```text
private
shared
system
```

---

# 29.39 System Screens

Open Analytics can ship standard screens.

Examples:

```text
High Quality Momentum
Deep Value
Low Volatility Leaders
Strong Breakout
Positive Earnings Catalyst
Institutional Accumulation
```

---

# 29.40 High Quality Momentum Screen

Example conceptual rules:

```text
momentum_percentile >= 80
quality_percentile >= 70
trend_state in uptrend
liquidity_score >= threshold
```

---

# 29.41 Value + Quality Screen

Example:

```text
value_percentile >= 80
quality_percentile >= 70
financial_strength high
```

---

# 29.42 Breakout Screen

Example:

```text
breakout_strength high
RVOL > threshold
trend strong
```

---

# 29.43 Mean-Reversion Screen

Example:

```text
short-term reversal extreme
long-term quality acceptable
liquidity sufficient
```

---

# 29.44 News Catalyst Screen

Example:

```text
positive_catalyst_score high
novelty high
materiality high
```

---

# 29.45 Institutional Accumulation Screen

Example:

```text
flow_score high
volume confirmation
trend positive
```

---

# 29.46 Derivatives Screen

Examples:

```text
long buildup
high IV percentile
put skew extreme
```

---

# 29.47 Low-Risk Screen

Possible:

```text
low volatility
low beta
strong quality
high liquidity
```

---

# 29.48 ML Forecast Screen

Possible:

```text
ml_percentile >= 90
ml_confidence >= threshold
```

---

# 29.49 Alpha Screen

Possible:

```text
final_alpha_percentile >= 90
confidence_score >= 70
signal_eligible = true
```

---

# 29.50 Negative Risk Screen

Possible:

```text
event_risk_score high
drawdown high
liquidity weak
```

Useful for exclusions/watchlists.

---

# 29.51 Custom Columns

Users can select output columns.

Examples:

```text
symbol
price
momentum
quality
value
alpha
confidence
sector
```

---

# 29.52 Column Registry

Each displayable column should have:

```text
column_id
display_name
source_metric
format
unit
```

---

# 29.53 Grouping

Possible:

```text
group by sector
group by industry
group by market-cap bucket
```

---

# 29.54 Aggregation

Within groups show:

```text
count
mean score
median score
pass rate
```

---

# 29.55 Top N

Allow:

```text
top 10
top 50
top 100
```

---

# 29.56 Bottom N

Allow for short/avoid research.

---

# 29.57 Watchlist Output

A screen result can be saved as:

```text
watchlist
```

---

# 29.58 Dynamic Watchlist

Saved screen reruns automatically on latest data.

---

# 29.59 Static Watchlist

Snapshot of selected securities.

---

# 29.60 Screen Snapshot

Store:

```text
screen_id
run_timestamp
result_count
result_instruments
```

---

# 29.61 Historical Screen Replay

User should be able to run:

```text
screen as of historical date T
```

This is essential for research.

---

# 29.62 Point-in-Time Screen

At T, use only features available by T.

---

# 29.63 Screen Backtest

Possible workflow:

```text
run screen monthly
hold passing stocks
measure forward returns
```

This bridges screening and strategy research.

---

# 29.64 Screen Hit Rate

Track:

```text
future positive-return ratio
```

for historical screen snapshots.

---

# 29.65 Screen Forward Returns

Possible:

```text
1D
5D
21D
63D
```

for research only.

---

# 29.66 Screen IC

If screen score is continuous:

```text
Rank IC
```

against future returns.

---

# 29.67 Screen Turnover

Track how much membership changes between runs.

---

# 29.68 Screen Stability

Store:

```text
membership_stability
rank_stability
```

---

# 29.69 Screen Breadth

How many stocks pass?

```text
screen_pass_count
```

---

# 29.70 Screen Selectivity

```text
pass_count / universe_count
```

---

# 29.71 Over-Restrictive Screen

If no stocks pass frequently:

```text
screen_too_restrictive_flag
```

---

# 29.72 Over-Broad Screen

If nearly all pass:

```text
screen_too_broad_flag
```

---

# 29.73 Filter Selectivity

Track how many rows each filter eliminates.

---

# 29.74 Query Planner

For performance, apply selective indexed filters early.

---

# 29.75 Precomputed Feature Tables

Screener should query:

```text
daily feature snapshots
```

not recompute all engines interactively.

---

# 29.76 Materialized Screener View

Recommended:

```text
security_daily_research_snapshot
```

wide table with commonly screened metrics.

---

# 29.77 Screener Snapshot Fields

Possible:

```text
date
instrument_key
symbol
company_name
sector
industry

price
market_cap

return_21d
momentum_percentile
trend_state

volatility
beta

ADV
liquidity_score

quality_factor
value_factor
growth_factor

news_score
flow_score
derivatives_score

alpha_score
alpha_percentile
confidence_score

ml_score
ml_percentile

signal_eligible
```

---

# 29.78 Search Indexes

Useful indexes/organization by:

```text
date
instrument_key
symbol
sector
industry
```

In DuckDB, optimize query layout appropriately rather than assuming traditional OLTP indexes.

---

# 29.79 Query Grammar

Optional structured grammar:

```text
momentum > 80
AND quality > 70
AND sector != "Financial Services"
```

Can be parsed into safe filter objects.

---

# 29.80 Natural Language Screener

Later optional feature:

```text
"show me liquid mid-cap stocks with strong momentum,
high quality, and positive news"
```

Translate into explicit filter rules.

Always show interpreted conditions before execution.

---

# 29.81 Query Safety

Never execute arbitrary SQL supplied through screener UI.

Use:

```text
validated metric registry
validated operators
parameterized values
```

---

# 29.82 Filter Validation

Reject:

```text
unknown metric
invalid operator
invalid data type
```

---

# 29.83 Unit Awareness

Examples:

```text
market cap
percentage
ratio
currency
days
```

UI should display units correctly.

---

# 29.84 Percentage Semantics

Clearly define whether internal value is:

```text
0.15
```

or:

```text
15
```

for 15%.

Use one internal standard.

---

# 29.85 Currency Semantics

Store base values consistently, display:

```text
₹ crore
```

as presentation only.

---

# 29.86 Market Cap Filters

Support:

```text
minimum market cap
maximum market cap
market-cap bucket
```

---

# 29.87 Liquidity Filters

Support:

```text
ADV
turnover
spread
liquidity_score
days_to_liquidate
```

---

# 29.88 Risk Filters

Support:

```text
volatility
beta
drawdown
CVaR
risk_bucket
```

---

# 29.89 Trend Filters

Support:

```text
price above SMA
trend state
ADX
trend strength
breakout
```

---

# 29.90 Momentum Filters

Support:

```text
21D
63D
126D
252D
12-1
percentile
factor score
```

---

# 29.91 Fundamental Filters

Support:

```text
revenue growth
EPS growth
ROE
ROIC
margins
cash flow
leverage
```

---

# 29.92 Valuation Filters

Support:

```text
P/E
P/B
EV/EBITDA
earnings yield
FCF yield
value percentile
```

---

# 29.93 Factor Filters

Support all production factor scores.

---

# 29.94 News Filters

Support:

```text
sentiment
catalyst
event risk
novelty
materiality
news velocity
```

---

# 29.95 Flow Filters

Support:

```text
institutional flow score
flow z-score
flow regime
```

---

# 29.96 Derivatives Filters

Support:

```text
basis
OI state
IV percentile
PCR
skew
expected move
```

---

# 29.97 Regime Filters

Possible at market or sector level.

Example:

```text
only show candidates when market regime = BULL_LOW_VOL
```

---

# 29.98 Alpha Filters

Support:

```text
raw alpha
final alpha
alpha percentile
signal direction
```

---

# 29.99 Confidence Filters

Support:

```text
confidence score
confidence bucket
```

---

# 29.100 ML Filters

Support:

```text
predicted return
outperformance probability
ML percentile
model health
```

---

# 29.101 Data Quality Filters

Support:

```text
only valid
exclude stale
exclude low coverage
```

---

# 29.102 Eligibility Filters

Support:

```text
research eligible
trading eligible
short eligible
F&O eligible
```

---

# 29.103 Event Calendar Filters

Possible:

```text
earnings within N days
corporate action upcoming
```

only with point-in-time calendar data.

---

# 29.104 Historical Filing Availability

When screening historically, fundamentals must respect announcement time.

---

# 29.105 Historical News Availability

Use only events available by screen timestamp.

---

# 29.106 Historical Derivatives Availability

Use chain data available then.

---

# 29.107 Historical ML Prediction

If replaying a historical ML screen, use the model version that was valid then or clearly mark it as retrospective research.

---

# 29.108 Live Screen

Use:

```text
latest available feature snapshot
```

---

# 29.109 Intraday Screen

Optional later.

Requires:

```text
intraday feature pipeline
```

Do not pretend daily features are real-time.

---

# 29.110 Screen Refresh

Possible:

```text
on demand
daily
scheduled
intraday
```

depending on feature family.

---

# 29.111 Scheduled Screen

Users may schedule screen runs in future versions.

Store screen snapshots for monitoring.

---

# 29.112 Screen Change Detection

Compare current vs previous run:

```text
new entrants
exits
rank movers
```

---

# 29.113 New Entrants

Store:

```text
entered_screen_flag
```

---

# 29.114 Screen Exits

Store.

---

# 29.115 Rank Movers

Track:

```text
rank_change
```

---

# 29.116 Screen Alerting

Optional:

```text
notify when stock enters screen
```

This belongs in monitoring/automation layer rather than core calculation.

---

# 29.117 Candidate Funnel

Recommended pipeline:

```text
Universe
    ↓
Eligibility
    ↓
Hard Filters
    ↓
Soft Filters
    ↓
Ranking
    ↓
Top Candidates
    ↓
Signal / Portfolio Review
```

---

# 29.118 Hard Filters

Examples:

```text
tradable
minimum liquidity
minimum data quality
```

---

# 29.119 Soft Filters

Examples:

```text
quality > threshold
momentum > threshold
```

These may influence score rather than exclude.

---

# 29.120 Ranking vs Filtering

Important distinction:

```text
Filter:
must satisfy condition

Ranking:
preference among survivors
```

Do not convert every preference into a hard cutoff.

---

# 29.121 Candidate Count Control

Possible:

```text
minimum candidates
maximum candidates
```

---

# 29.122 Diversified Candidate List

Optional:

```text
top N per sector
```

to avoid one-sector domination.

---

# 29.123 Sector Quotas

Possible:

```text
max candidates per sector
```

---

# 29.124 Market-Cap Quotas

Possible.

---

# 29.125 Rank Neutralization

If desired, rank within:

```text
sector
industry
size bucket
```

---

# 29.126 Peer-Based Screener

Example:

```text
top 10% momentum within sector
```

---

# 29.127 Relative Filters

Examples:

```text
P/E below sector median
ROE above sector median
```

---

# 29.128 Dynamic Thresholds

Possible:

```text
top 20 percentile
```

rather than fixed numeric threshold.

More robust across changing distributions.

---

# 29.129 Historical Percentile Filters

Example:

```text
current valuation below own 20th percentile
```

---

# 29.130 Cross-Sectional Percentile Filters

Example:

```text
current quality in top decile of universe
```

---

# 29.131 Screen Scoring Explainability

For composite screen, expose:

```text
component
raw value
percentile
weight
contribution
```

---

# 29.132 Screen Confidence

Optional:

```text
screen_confidence
```

can aggregate data quality and metric availability.

---

# 29.133 Missing-Metric Penalty

If composite score lacks one component:

```text
penalize
```

or:

```text
exclude
```

according to saved screen policy.

---

# 29.134 Screen Quality Status

Possible:

```text
VALID
PARTIAL_DATA
LOW_COVERAGE
STALE_DATA
POINT_IN_TIME_WARNING
INVALID
```

---

# 29.135 Screener Run Record

Recommended:

```text
screen_run_id
screen_id
screen_version

run_timestamp
as_of_timestamp

universe_id

result_count
eligible_count

sort_metric
sort_direction

quality_status
```

---

# 29.136 Screener Definition Record

```text
screen_id
screen_name
screen_version

description

universe_id

filter_definition_json
ranking_definition_json

column_definition_json

created_by
created_at
updated_at

active
```

---

# 29.137 Screener Result Record

```text
screen_run_id
instrument_key

rank
screen_score

pass_state

alpha_score
confidence_score

reason_codes

snapshot_reference
```

---

# 29.138 Filter Evaluation Record

```text
screen_run_id
instrument_key
condition_id

metric_name
metric_value
operator
threshold

pass_flag
```

---

# 29.139 Screen Snapshot Reproducibility

Store enough metadata to rerun exactly:

```text
feature_snapshot_date
feature versions
screen version
universe version
```

---

# 29.140 Initial Production Screener

Recommended V1 functionality:

```text
1. Select point-in-time universe.
2. Filter by reference/security metadata.
3. Filter by liquidity.
4. Filter by trend.
5. Filter by momentum.
6. Filter by risk.
7. Filter by fundamentals.
8. Filter by valuation.
9. Filter by factor scores.
10. Filter by alpha/confidence.
11. Rank results.
12. Save screen.
13. Re-run latest screen.
14. Run historical as-of screen.
```

---

# 29.141 Initial Production System Screens

Recommended:

```text
High Quality Momentum
Value + Quality
Strong Trend Breakout
Low Volatility Quality
High Alpha High Confidence
Positive News Catalyst
Institutional Flow Leaders
```

---

# 29.142 High Alpha High Confidence

Conceptual:

```text
final_alpha_percentile >= 90
confidence_score >= 70
liquidity_score >= threshold
signal_eligible = true
```

---

# 29.143 Strong Trend Breakout

Conceptual:

```text
trend_state = STRONG_UPTREND
breakout_strength high
RVOL elevated
liquidity valid
```

---

# 29.144 Low Volatility Quality

Conceptual:

```text
low_vol_factor high
quality_factor high
drawdown moderate
```

---

# 29.145 Initial Production Output Columns

Recommended:

```text
Symbol
Company
Sector

Price
Market Cap

Trend
Momentum

Volatility
Liquidity

Quality
Value
Growth

News
Flow

Alpha
Confidence

ML Forecast
```

---

# 29.146 Screener Processing Flow

Recommended:

```text
POINT-IN-TIME UNIVERSE
        ↓
FEATURE SNAPSHOT
        ↓
FILTER REGISTRY
        ↓
VALIDATE SCREEN DEFINITION
        ↓
EVALUATE HARD FILTERS
        ↓
EVALUATE SOFT FILTERS
        ↓
COMPOSITE SCORE
        ↓
RANK
        ↓
GROUP / LIMIT
        ↓
EXPLANATIONS
        ↓
SCREEN RESULTS
        ↓
SAVE SNAPSHOT
        ↓
HISTORICAL / BACKTEST LINK
```

---

# 29.147 Point-in-Time Rule

At historical timestamp T, screen may only use:

```text
features available at T
universe membership at T
sector mapping at T
model outputs valid at T
```

---

# 29.148 Retrospective Research Mode

If using today's model on historical data, label clearly:

```text
RETROSPECTIVE_RESEARCH
```

Do not confuse with what would actually have been known historically.

---

# 29.149 Production Screen Mode

Use:

```text
current valid feature/model versions
```

---

# 29.150 Screen Backtest Integration

A screen can generate a historical candidate universe for Step 24.

Store:

```text
screen_run_id
```

with backtest positions.

---

# 29.151 Screen Performance Evaluation

For saved screens, track:

```text
future median return
hit rate
top-decile spread
turnover
```

---

# 29.152 Screen Decay

A screen that worked historically may weaken.

Track:

```text
rolling screen IC
rolling hit rate
```

---

# 29.153 Screen Health Status

Possible:

```text
HEALTHY
WATCH
DEGRADED
```

---

# 29.154 Query Performance

Target interactive latency by relying on precomputed snapshots.

Do not compute full fundamental/factor pipelines per user click.

---

# 29.155 Pagination

For large result sets, support:

```text
page
page_size
```

---

# 29.156 Stable Sorting

Use deterministic tie-breakers.

Example:

```text
rank metric
then instrument_key
```

---

# 29.157 Export

Possible:

```text
CSV
Parquet
watchlist
```

Later UI can expose downloads.

---

# 29.158 API Design Concept

Possible operations:

```text
search securities
validate screen
run screen
save screen
list screens
load screen
run historical screen
```

---

# 29.159 Security Master Search

Search fields:

```text
symbol
company_name
ISIN
```

---

# 29.160 Fuzzy Search Score

Possible:

```text
search_relevance_score
```

---

# 29.161 Search Result Ranking

Prioritize:

```text
exact symbol
exact company
prefix match
fuzzy match
```

---

# 29.162 Recent Searches

Optional user convenience.

---

# 29.163 Screen Templates

System templates can be cloned and customized.

---

# 29.164 Screen Sharing

Optional later.

---

# 29.165 Screen Audit Trail

Store changes:

```text
who
when
what changed
```

---

# 29.166 Validation Errors

Examples:

```text
unknown metric
invalid threshold
unsupported operator
empty group
```

---

# 29.167 Filter Conflicts

Detect logically impossible screens.

Example:

```text
PE < 10
AND
PE > 30
```

Warn user.

---

# 29.168 Empty Screen Diagnostics

If zero results, report most restrictive filters.

---

# 29.169 Filter Impact Analysis

For each filter:

```text
input count
output count
elimination rate
```

---

# 29.170 Screen Optimization

Suggesting changes can be a future UI feature, but core engine should only report objective filter impact.

---

# 29.171 Important Quant Rules

## Rule 1 — Screening Is Not Alpha by Itself

A screen generates candidates, not guaranteed returns.

## Rule 2 — Filter and Rank Are Different

Do not overuse hard thresholds.

## Rule 3 — Use Point-in-Time Data for Historical Screens

Avoid survivorship and look-ahead bias.

## Rule 4 — Unknown Is Not Zero

Null handling must be explicit.

## Rule 5 — Composite Scores Must Be Explainable

Show components and weights.

## Rule 6 — Saved Screens Must Be Versioned

Historical results must remain reproducible.

## Rule 7 — Precompute Expensive Features

Interactive filtering should be fast.

## Rule 8 — Screen Backtests Need Real Execution Rules

Do not evaluate screens only with raw forward returns.

## Rule 9 — Historical Screens Need Historical Universe Membership

Mandatory.

## Rule 10 — ML Predictions Must Carry Model Version

Especially in historical replay.

## Rule 11 — Query Inputs Must Be Validated

Never expose arbitrary SQL execution.

## Rule 12 — Screener Results Should Trace to Feature Snapshots

Every result should be auditable.

---

# 29.172 Completion Criteria

Step 29 is complete when Open Analytics can answer:

1. Can a user search a stock by symbol, company, or ISIN?
2. Can a base universe be selected?
3. Can users filter on returns, risk, liquidity, trend, momentum, fundamentals, valuation, factors, news, flow, derivatives, alpha, confidence, and ML?
4. Can filters use AND / OR / NOT?
5. Can nested filter groups be created?
6. Can null handling be controlled?
7. Can results be ranked separately from filters?
8. Can multi-factor composite rankings be created?
9. Can the engine explain why each stock passed?
10. Can saved screens be versioned?
11. Can a screen be rerun on the latest data?
12. Can a screen be replayed historically as of date T?
13. Does historical screening use historical universe membership?
14. Are model outputs versioned in historical screens?
15. Can screen results be saved as watchlists?
16. Can screen membership changes be tracked?
17. Can screen turnover and historical efficacy be measured?
18. Can screens feed directly into backtests?
19. Are screen snapshots reproducible?
20. Are queries safe and registry-driven?
21. Are filter-impact diagnostics available?
22. Can the exact result set be recreated later from screen version + feature snapshot?

Once these are reliable, the Stock Search / Screener Engine is ready to feed:

```text
Step 30 — Final Research Decision Layer
```

---

# Step 29 Final Output

The Stock Search / Screener Engine transforms:

```text
Point-in-Time Research Features
+
Security Master
+
User Filter Logic
+
Ranking Rules
```

into:

```text
Search Results
Filtered Candidate Sets
Ranked Stock Lists
Composite Screen Scores
Saved Screens
Historical Screen Snapshots
Watchlists
Filter Explanations
Reason Codes
Screen Performance Diagnostics
Reproducible Research Candidate Universes
```

This becomes the stock-discovery and research-query layer for Open Analytics.
