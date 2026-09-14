# Open Analytics — Step 19: Alpha / Signal Engine

## Purpose

The **Alpha / Signal Engine** converts validated quantitative features and factor scores into explicit, testable forecasts or trade-selection signals.

This is the layer where Open Analytics moves from:

```text
describing stocks
```

to:

```text
estimating relative opportunity
```

The engine should answer:

- Which stocks have the strongest expected return?
- Which signals are long, short, neutral, or avoid?
- How strong is each signal?
- How confident are we?
- Which factors are driving the signal?
- Does the market regime support or weaken the signal?
- Is the signal fresh or stale?
- Is the signal supported by momentum, fundamentals, flow, news, and participation?
- What is the expected holding horizon?
- What is the expected alpha after risk and transaction costs?
- How stable is the signal?
- Is the signal too crowded or too correlated with other positions?
- Has the signal historically worked in similar regimes?

The output feeds directly into:

- Confidence Engine
- Portfolio Construction
- Position Sizing
- Risk Controls
- Execution
- Backtesting
- Performance Attribution
- ML models
- Stock Search / Screener

---

# 19.1 Core Principle

A **signal** is not the same as a factor.

A factor says:

```text
This stock has strong momentum
```

A signal says:

```text
Given all available information,
this stock has positive expected alpha
over a defined horizon.
```

Signals should be:

```text
Point-in-time
Explainable
Versioned
Backtestable
Cost-aware
Regime-aware
Risk-aware
Horizon-specific
```

---

# 19.2 Required Inputs

The Signal Engine can consume:

## Factor Engine

```text
momentum_factor
value_factor
quality_factor
growth_factor
low_vol_factor
liquidity_factor
trend_factor
participation_factor
```

## News / Events

```text
news_factor_score
positive_catalyst_score
negative_catalyst_score
event_risk_score
```

## Institutional Flow

```text
foreign_flow_score
domestic_flow_score
institutional_flow_score
```

## Derivatives

```text
futures_positioning_score
options_positioning_score
derivatives_sentiment_score
derivatives_risk_score
```

## Market Regime

```text
regime_label
bull_probability
bear_probability
market_stress_score
```

## Risk

```text
volatility
beta
drawdown
tail risk
```

## Liquidity

```text
liquidity_score
execution_eligibility
```

---

# 19.3 Signal Types

Recommended categories:

```text
CROSS_SECTIONAL
TIME_SERIES
EVENT_DRIVEN
MEAN_REVERSION
TREND_FOLLOWING
BREAKOUT
FUNDAMENTAL
MULTI_FACTOR
REGIME_CONDITIONAL
MACHINE_LEARNED
```

Each signal should have a clear family.

---

# 19.4 Long / Short / Neutral

Basic output:

```text
LONG
SHORT
NEUTRAL
AVOID
```

For long-only use:

```text
BUY_CANDIDATE
HOLD
AVOID
```

Keep internal continuous score as primary.

---

# 19.5 Raw Alpha Score

Construct:

```text
raw_alpha_score
```

Possible scale:

```text
-3 to +3
```

or:

```text
-1 to +1
```

This is before cost/risk adjustments.

---

# 19.6 Expected Return Forecast

Where possible, map signal to:

```text
expected_return
```

for a specified horizon.

Example:

```text
expected_return_21d
```

This requires calibration from historical data.

---

# 19.7 Horizon-Specific Signals

Do not use one signal for all horizons.

Recommended:

```text
alpha_1d
alpha_5d
alpha_21d
alpha_63d
```

or strategy-specific horizon.

---

# 19.8 Cross-Sectional Alpha

Predict relative performance across stocks.

Output:

```text
cross_sectional_alpha_score
```

Used for ranking.

---

# 19.9 Time-Series Alpha

Predict direction for one asset relative to its own history.

Output:

```text
time_series_alpha_score
```

---

# 19.10 Multi-Factor Alpha

Combine:

```text
Momentum
Value
Quality
Growth
Low Vol
Trend
Participation
```

Conceptually:

```text
alpha =
w1 * Momentum
+
w2 * Value
+
w3 * Quality
+
w4 * Growth
+
...
```

Weights must be validated.

---

# 19.11 Regime-Conditioned Alpha

Adjust factor influence by regime.

Example:

```text
BULL_LOW_VOL:
    more weight to Momentum

BEAR_HIGH_VOL:
    more weight to Quality / LowVol
```

Only after out-of-sample validation.

---

# 19.12 Event Alpha

Use:

```text
earnings surprise
guidance change
order win
news novelty
materiality
event drift
```

Output:

```text
event_alpha_score
```

---

# 19.13 Flow Alpha

Use:

```text
institutional flow
sector flow
stock-level institutional evidence
```

Output:

```text
flow_alpha_score
```

---

# 19.14 Derivatives Alpha

Potential:

```text
basis
OI state
skew
IV
PCR
positioning
```

Output:

```text
derivatives_alpha_score
```

---

# 19.15 Breakout Alpha

Potential inputs:

```text
breakout strength
trend quality
RVOL
breadth
flow
```

Output:

```text
breakout_alpha_score
```

---

# 19.16 Mean-Reversion Alpha

Potential:

```text
short-term reversal
extreme z-score
oversold state
liquidity
event absence
```

Output:

```text
mean_reversion_alpha_score
```

Keep separate from trend signals.

---

# 19.17 Signal Ensemble

Combine multiple independent signals.

Example:

```text
final_alpha =
weighted average of:
momentum alpha
value alpha
event alpha
flow alpha
derivatives alpha
```

---

# 19.18 Ensemble Weighting

Possible:

```text
equal weight
historical IC weight
regime weight
confidence weight
ML-learned weight
```

Start with simple methods.

---

# 19.19 IC-Weighted Signal

Possible:

```text
weight_i =
historical_IC_i
/
sum(abs(IC))
```

Use rolling and out-of-sample estimates only.

---

# 19.20 Confidence-Weighted Signal

Possible:

```text
weighted_alpha =
signal_score × signal_confidence
```

Do not hide raw signal.

---

# 19.21 Regime-Weighted Signal

Possible:

```text
alpha_adjusted =
raw_alpha × regime_multiplier
```

Keep:

```text
raw_alpha
regime_adjusted_alpha
```

separate.

---

# 19.22 Risk-Adjusted Alpha

Possible:

```text
risk_adjusted_alpha =
expected_return / expected_volatility
```

or use more advanced optimization later.

---

# 19.23 Cost-Adjusted Alpha

Estimate:

```text
net_alpha =
gross_alpha
-
expected_transaction_cost
```

This is essential.

---

# 19.24 Liquidity-Adjusted Alpha

Downweight signals in stocks with:

```text
low ADV
wide spread
high price impact
```

Output:

```text
liquidity_adjusted_alpha
```

---

# 19.25 Alpha After Slippage

Store:

```text
expected_alpha_after_slippage
```

This is more realistic than raw forecast.

---

# 19.26 Alpha Rank

Cross-sectional:

```text
alpha_rank
```

---

# 19.27 Alpha Percentile

```text
alpha_percentile
```

Recommended:

```text
100 = strongest long opportunity
0 = strongest short / weakest
```

---

# 19.28 Signal Thresholds

Possible:

```text
LONG if alpha_percentile >= 90
SHORT if alpha_percentile <= 10
```

Thresholds must be configurable.

---

# 19.29 Dynamic Thresholds

Thresholds can adapt to:

```text
regime
signal dispersion
market stress
liquidity
```

But should be backtested carefully.

---

# 19.30 Signal Dispersion

Measure cross-sectional spread:

```text
alpha_dispersion
```

High dispersion may mean stronger stock-selection opportunity.

---

# 19.31 Signal Breadth

Count:

```text
positive_alpha_count
negative_alpha_count
```

Useful for portfolio opportunity.

---

# 19.32 Signal Stability

Measure:

```text
alpha_change_1d
alpha_change_5d
```

Output:

```text
signal_stability_score
```

---

# 19.33 Signal Persistence

Track:

```text
days_signal_positive
days_signal_negative
```

---

# 19.34 Signal Decay

Estimate how fast predictive power declines.

Store:

```text
signal_half_life
```

---

# 19.35 Signal Age

```text
days_since_signal_generated
```

or for event signals:

```text
time_since_event
```

---

# 19.36 Signal Freshness

Possible:

```text
FRESH
ACTIVE
AGING
STALE
```

Store:

```text
signal_freshness
```

---

# 19.37 Signal Confirmation

Potential confirmations:

```text
trend
momentum
volume
flow
news
derivatives
breadth
```

Store:

```text
confirmation_count
confirmation_score
```

---

# 19.38 Signal Conflict

Example:

```text
Momentum bullish
Value bullish
News negative
Flow negative
```

Store:

```text
signal_conflict_score
```

---

# 19.39 Signal Agreement State

Possible:

```text
STRONG_AGREEMENT
MODERATE_AGREEMENT
MIXED
STRONG_CONFLICT
```

---

# 19.40 Signal Confidence Inputs

Potential:

```text
factor quality
data quality
historical IC
regime fit
signal stability
confirmation
liquidity
```

Output:

```text
signal_confidence
```

---

# 19.41 Explainability

For every signal expose:

```text
top_positive_drivers
top_negative_drivers
```

Example:

```text
+ Momentum
+ Quality
+ Sector-relative strength
- Expensive valuation
- Weak foreign flow
```

---

# 19.42 Contribution Decomposition

Store per component:

```text
component_score
component_weight
component_contribution
```

This is critical for auditability.

---

# 19.43 Signal Reason Codes

Example:

```text
MOMENTUM_STRONG
VALUE_ATTRACTIVE
QUALITY_HIGH
NEWS_NEGATIVE
FLOW_WEAK
LIQUIDITY_LOW
```

---

# 19.44 Hard Exclusion Rules

Some conditions may override alpha:

```text
not tradable
suspended
very low liquidity
critical data issue
major unresolved corporate event
```

Output:

```text
signal_eligible = false
```

---

# 19.45 Soft Penalties

Instead of exclusion:

```text
low confidence
high volatility
moderate liquidity
```

can reduce score.

---

# 19.46 Avoid Signal

Use:

```text
AVOID
```

when:

```text
alpha attractive
but risk/data/liquidity unacceptable
```

---

# 19.47 Signal Versioning

Store:

```text
signal_name
signal_version
```

Any formula change requires version change.

---

# 19.48 Signal Registry

Recommended metadata:

```text
signal_name
signal_version

signal_family
horizon

components
weights

neutralization
thresholds

rebalance_frequency
decay_model

active
```

---

# 19.49 Point-in-Time Rule

At date T, only use:

```text
features known at T
factors known at T
news known at T
flow known at T
regime known at T
```

No future information.

---

# 19.50 Forward Returns Are Labels Only

Never use:

```text
forward_return_5d
forward_return_21d
```

as signal inputs.

They are only for:

```text
training
validation
evaluation
```

---

# 19.51 Survivorship Bias Protection

Use historical eligible universe.

Keep securities that later:

```text
delisted
failed
merged
left index
```

---

# 19.52 Signal Neutralization

Optional:

```text
sector-neutral alpha
beta-neutral alpha
size-neutral alpha
```

Store separately from raw alpha.

---

# 19.53 Sector-Neutral Alpha

Possible:

```text
alpha - sector_mean_alpha
```

or regression residual.

---

# 19.54 Beta-Neutral Alpha

Remove beta exposure.

Useful when signal should represent stock-specific alpha.

---

# 19.55 Size-Neutral Alpha

Remove unintended market-cap bias.

---

# 19.56 Alpha Residualization

Advanced:

```text
alpha
~
sector
+
size
+
beta
+
liquidity
```

Use residual.

---

# 19.57 Signal IC

Evaluate:

```text
corr(signal_t, forward_return_t+h)
```

Prefer:

```text
Rank IC
```

for cross-sectional signals.

---

# 19.58 Mean IC

Store:

```text
mean_signal_ic
```

---

# 19.59 IC IR

```text
signal_ic_ir =
mean(IC) / std(IC)
```

---

# 19.60 Hit Rate

Possible:

```text
positive_forward_return_ratio
```

for long signals.

---

# 19.61 Long-Short Spread

```text
top_decile_return
-
bottom_decile_return
```

---

# 19.62 Signal Monotonicity

Check return ordering across quantiles.

---

# 19.63 Signal Turnover

Measure:

```text
rank turnover
selection turnover
portfolio turnover
```

---

# 19.64 Net Signal Performance

Subtract:

```text
spread
slippage
impact
fees
taxes
```

---

# 19.65 Signal Capacity

Estimate max deployable capital before alpha erodes.

Inputs:

```text
ADV
position size
participation rate
turnover
```

---

# 19.66 Signal Crowding

Potential later inputs:

```text
factor crowding
ownership concentration
short interest
derivatives concentration
```

Output:

```text
crowding_risk_score
```

---

# 19.67 Signal Regime Performance

Track:

```text
IC by regime
hit rate by regime
return by regime
drawdown by regime
```

---

# 19.68 Signal Sector Performance

Track by sector.

---

# 19.69 Signal Size-Bucket Performance

Track:

```text
large cap
mid cap
small cap
```

---

# 19.70 Signal Horizon Performance

Evaluate:

```text
1D
5D
21D
63D
```

---

# 19.71 Signal Calibration

Map score to expected return.

Example:

```text
alpha percentile 90-100
→ average future return historically X
```

Use rolling out-of-sample calibration.

---

# 19.72 Probability of Positive Return

Possible:

```text
prob_positive_return_21d
```

This is different from expected return.

---

# 19.73 Probability of Outperformance

Possible:

```text
prob_outperform_benchmark_21d
```

---

# 19.74 Expected Alpha Distribution

Advanced:

```text
expected_alpha_mean
expected_alpha_std
```

Useful for probabilistic portfolio construction.

---

# 19.75 Signal Uncertainty

Store:

```text
signal_uncertainty
```

High when:

```text
few observations
conflicting factors
unstable regime
low data quality
```

---

# 19.76 Signal Confidence vs Signal Strength

Important distinction:

```text
Signal Strength
→ size of expected opportunity

Signal Confidence
→ reliability of that estimate
```

Do not combine them conceptually.

---

# 19.77 Rule-Based Signal

Initial production may use transparent weighted rules.

Example:

```text
Momentum score
+ Quality score
+ Value score
+ Trend confirmation
```

This is a good baseline.

---

# 19.78 Statistical Signal

Later use:

```text
linear regression
logistic regression
rank models
```

---

# 19.79 Machine-Learned Signal

Later:

```text
gradient boosting
random forest
neural network
```

But only after robust feature/label design.

---

# 19.80 Ensemble Signal

Combine:

```text
rule-based
factor-based
statistical
ML
```

only if out-of-sample evidence supports it.

---

# 19.81 Recommended Daily Signal Record

```text
date
instrument_key
signal_name
signal_version


# RAW

raw_alpha_score
expected_return

alpha_rank
alpha_percentile


# ADJUSTMENTS

regime_adjusted_alpha
risk_adjusted_alpha
liquidity_adjusted_alpha
cost_adjusted_alpha


# COMPONENTS

momentum_contribution
value_contribution
quality_contribution
growth_contribution
trend_contribution
news_contribution
flow_contribution
derivatives_contribution


# AGREEMENT

confirmation_count
confirmation_score
signal_conflict_score
signal_agreement_state


# STATE

signal_direction
signal_strength
signal_freshness

signal_confidence
signal_uncertainty


# ELIGIBILITY

signal_eligible
avoid_flag
exclusion_reason


# FINAL

final_alpha_score
final_alpha_percentile

prob_positive_return
prob_outperform_benchmark

quality_status
```

---

# 19.82 Initial Production Signal

A simple V1 should be explainable.

Example components:

```text
Momentum
Quality
Value
Trend
Participation
```

Possible:

```text
alpha_v1 =
equal-weight normalized combination
```

Then:

```text
regime adjustment
liquidity filter
cost adjustment
```

Do not start with complex ML.

---

# 19.83 Initial Production Outputs

Recommended:

```text
raw_alpha_score
alpha_percentile

signal_direction
signal_strength

confirmation_score
signal_conflict_score

regime_adjusted_alpha
risk_adjusted_alpha
cost_adjusted_alpha

signal_confidence
signal_freshness

signal_eligible
avoid_flag

final_alpha_score
final_alpha_percentile

signal_quality_status
```

---

# 19.84 Alpha / Signal Engine Processing Flow

Recommended:

```text
POINT-IN-TIME FEATURES
        ↓
FACTOR SCORES
        ↓
EVENT / FLOW / DERIVATIVES FEATURES
        ↓
REGIME CONTEXT
        ↓
SIGNAL REGISTRY
        ↓
COMPONENT NORMALIZATION
        ↓
RAW ALPHA
        ↓
NEUTRALIZATION
        ↓
REGIME ADJUSTMENT
        ↓
RISK ADJUSTMENT
        ↓
LIQUIDITY / COST ADJUSTMENT
        ↓
CONFIRMATION / CONFLICT
        ↓
SIGNAL CONFIDENCE
        ↓
ELIGIBILITY FILTERS
        ↓
FINAL ALPHA SCORE
        ↓
RANK / PERCENTILE
        ↓
VALIDATION / IC / TURNOVER
```

---

# 19.85 Important Quant Rules

## Rule 1 — Signal Is Not Factor

Factors describe characteristics; signals estimate opportunity.

## Rule 2 — Signals Must Be Horizon-Specific

A 1-day and 3-month signal are different models.

## Rule 3 — Raw Alpha Must Be Preserved

Do not overwrite it with adjusted scores.

## Rule 4 — Risk and Cost Matter

Gross alpha is not enough.

## Rule 5 — Regime Conditioning Must Be Validated

Do not dynamically weight factors without evidence.

## Rule 6 — Confidence and Strength Are Different

Keep them separate.

## Rule 7 — Forward Returns Are Labels Only

Never leak future returns into live features.

## Rule 8 — Hard Exclusions and Soft Penalties Are Different

Do not treat them the same.

## Rule 9 — Explainability Is Mandatory

Every final signal should show its drivers.

## Rule 10 — Version Every Signal

Backtests must remain reproducible.

## Rule 11 — Test Net of Costs

High-turnover alpha may disappear in practice.

## Rule 12 — Avoid Overfitting

Start simple, then increase complexity only when justified.

---

# 19.86 Completion Criteria

Step 19 is complete when Open Analytics can answer:

1. What is the raw alpha score?
2. What is the expected return horizon?
3. Is the signal long, short, neutral, or avoid?
4. What factors are driving the signal?
5. What events or flows support it?
6. Does the market regime support it?
7. How strong is the signal?
8. How confident is the signal?
9. Are there conflicting indicators?
10. What is the risk-adjusted alpha?
11. What is the liquidity-adjusted alpha?
12. What is the expected transaction-cost-adjusted alpha?
13. Where does the stock rank across the universe?
14. What is its alpha percentile?
15. Is the signal fresh or stale?
16. Is the stock eligible to trade?
17. What is the signal's historical IC?
18. What is its hit rate?
19. Does it survive transaction costs?
20. What is the expected capacity?
21. How does the signal perform by regime?
22. Can the exact historical signal be reproduced?
23. Can the final signal be fully explained from its components?

Once these are reliable, the Alpha / Signal Engine is ready to feed:

```text
Step 20 — Confidence Engine
```

---

# Step 19 Final Output

The Alpha / Signal Engine transforms:

```text
Factors
+
Trend
+
Momentum
+
Fundamentals
+
Valuation
+
News
+
Institutional Flow
+
Derivatives
+
Market Regime
+
Risk
+
Liquidity
```

into:

```text
Raw Alpha
Expected Return
Signal Direction
Signal Strength
Signal Confirmation
Signal Conflict
Regime-Adjusted Alpha
Risk-Adjusted Alpha
Liquidity-Adjusted Alpha
Cost-Adjusted Alpha
Alpha Rank
Alpha Percentile
Signal Freshness
Signal Confidence Inputs
Signal Eligibility
Final Alpha Score
```

This becomes the actual opportunity-ranking layer for Open Analytics.
