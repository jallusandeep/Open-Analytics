# Open Analytics — Step 20: Confidence Engine

## Purpose

The **Confidence Engine** estimates how much trust Open Analytics should place in a signal, forecast, factor score, or model output.

Signal strength and confidence are different.

A stock can have:

```text
very strong signal
but low confidence
```

because:

```text
data is incomplete
signal components disagree
historical IC is unstable
regime is unfavorable
liquidity is poor
event uncertainty is high
```

Likewise, a moderate signal can have high confidence when multiple independent components agree and historical behavior is stable.

The Confidence Engine should answer:

- How reliable is this signal?
- Is the underlying data complete and fresh?
- Do independent models agree?
- Has this signal historically worked?
- Does it work in the current regime?
- How stable is the signal?
- Is the forecast well calibrated?
- How uncertain is the estimate?
- Is the stock liquid enough for the signal to be actionable?
- Are news/event inputs confirmed?
- Is the model extrapolating outside normal conditions?
- Should portfolio sizing be reduced because confidence is weak?

Confidence outputs feed directly into:

- Portfolio Construction
- Position Sizing
- Risk Controls
- Signal Ranking
- Execution
- Backtesting
- Model Monitoring
- Machine Learning

---

# 20.1 Core Principle

Confidence is not:

```text
signal score
```

and not:

```text
probability stock goes up
```

Confidence is:

```text
estimated reliability of the information and model producing the signal
```

Keep separate:

```text
Signal Strength
Expected Return
Probability
Confidence
Uncertainty
```

---

# 20.2 Required Inputs

From Step 19:

```text
raw_alpha_score
final_alpha_score
signal_strength
signal_conflict_score
signal_stability_score
signal_freshness
```

From data-quality layers:

```text
data_quality_score
fundamental_quality_status
news_quality_status
flow_quality_status
derivatives_quality_status
```

From research diagnostics:

```text
historical_IC
IC_IR
hit_rate
regime_performance
sample_count
```

From market context:

```text
regime_confidence
market_stress_score
liquidity_score
```

Optional model inputs:

```text
prediction_interval
ensemble_dispersion
model_probability
out_of_distribution_score
```

---

# 20.3 Confidence Dimensions

Recommended dimensions:

```text
DATA_CONFIDENCE
SIGNAL_AGREEMENT
HISTORICAL_EFFICACY
REGIME_FIT
MODEL_STABILITY
LIQUIDITY_CONFIDENCE
EVENT_CONFIDENCE
CALIBRATION_CONFIDENCE
```

Each should be separately measurable.

---

# 20.4 Data Confidence

Possible inputs:

```text
price data coverage
fundamental freshness
news timestamp quality
flow data completeness
derivatives chain completeness
```

Output:

```text
data_confidence_score
```

---

# 20.5 Data Coverage Score

Possible:

```text
valid_required_features
/
total_required_features
```

Store:

```text
feature_coverage_pct
```

---

# 20.6 Data Freshness Score

Penalize stale inputs.

Examples:

```text
old fundamental filing
stale derivative quote
delayed news source
stale flow publication
```

Store:

```text
data_freshness_score
```

---

# 20.7 Signal Agreement

Measure how many independent components point in the same direction.

Possible components:

```text
momentum
trend
value
quality
news
flow
derivatives
```

Store:

```text
signal_agreement_score
```

---

# 20.8 Signal Conflict

Use Step 19:

```text
signal_conflict_score
```

Higher conflict should reduce confidence.

---

# 20.9 Independent Confirmation Count

Store:

```text
independent_confirmation_count
```

Avoid counting highly correlated signals as independent.

---

# 20.10 Historical IC Confidence

Use:

```text
mean_IC
IC_IR
positive_IC_ratio
sample_count
```

Output:

```text
historical_ic_confidence
```

---

# 20.11 Hit-Rate Confidence

Store:

```text
historical_hit_rate
```

but adjust for:

```text
sample size
class imbalance
regime dependence
```

---

# 20.12 Sample Size Confidence

A result from:

```text
30 observations
```

should carry lower confidence than one from:

```text
3,000 observations
```

Store:

```text
sample_size_score
```

---

# 20.13 Regime Fit

Measure how well the signal historically performs in the current market regime.

Store:

```text
regime_fit_score
```

---

# 20.14 Regime Confidence Interaction

A regime-conditioned signal should have lower confidence when:

```text
regime_confidence is low
```

Store:

```text
regime_adjusted_confidence
```

---

# 20.15 Model Stability

Possible inputs:

```text
score volatility
parameter stability
feature importance stability
rolling IC stability
```

Output:

```text
model_stability_score
```

---

# 20.16 Signal Stability

If alpha score jumps wildly every day:

```text
confidence should fall
```

Store:

```text
signal_stability_score
```

---

# 20.17 Rank Stability

Track:

```text
alpha_rank_change_1d
alpha_rank_change_5d
```

Possible:

```text
rank_stability_score
```

---

# 20.18 Ensemble Agreement

For multiple models:

```text
model_1 predicts positive
model_2 predicts positive
model_3 predicts negative
```

Measure:

```text
ensemble_agreement_score
```

---

# 20.19 Ensemble Dispersion

Compute variation between model forecasts:

```text
ensemble_prediction_std
```

High dispersion = higher uncertainty.

---

# 20.20 Prediction Uncertainty

Possible:

```text
prediction_std
prediction_interval_width
```

Store:

```text
forecast_uncertainty_score
```

---

# 20.21 Calibration

If model predicts:

```text
70% probability
```

events should occur roughly 70% of the time over large samples.

Track:

```text
calibration_error
```

---

# 20.22 Calibration Confidence

Output:

```text
calibration_confidence
```

---

# 20.23 Brier Score

For probabilistic classification:

```text
Brier Score
```

can assess calibration and accuracy.

Store in research diagnostics.

---

# 20.24 Reliability Curve

Compare:

```text
predicted probability
vs
observed frequency
```

Useful for probability calibration.

---

# 20.25 Out-of-Distribution Detection

A model may face market conditions unlike training data.

Possible:

```text
OOD_score
```

Inputs may include:

```text
feature distance
regime rarity
volatility extremes
```

High OOD should reduce confidence.

---

# 20.26 Feature Range Check

If current inputs are outside historical training range:

```text
feature_outlier_flag
```

---

# 20.27 Extreme Regime Penalty

Possible:

```text
market_stress_score very high
```

can reduce confidence in normal-regime models.

---

# 20.28 Liquidity Confidence

A strong signal in an illiquid stock is less actionable.

Possible:

```text
liquidity_confidence_score
```

Inputs:

```text
ADV
spread
impact
tradability
```

---

# 20.29 Execution Confidence

Estimate whether expected alpha can realistically be captured.

Store:

```text
execution_confidence
```

---

# 20.30 Event Confidence

Consume Step 14:

```text
event_confidence
source_quality
official_confirmation
novelty
```

---

# 20.31 News Confidence

Possible:

```text
news_confidence_score
```

---

# 20.32 Flow Confidence

Consume:

```text
flow_confidence
```

---

# 20.33 Derivatives Confidence

Consume:

```text
derivatives_confidence
```

---

# 20.34 Fundamental Confidence

Possible inputs:

```text
filing freshness
restatement status
source completeness
sector-specific applicability
```

Output:

```text
fundamental_confidence
```

---

# 20.35 Factor Confidence

Each factor can have:

```text
momentum_confidence
value_confidence
quality_confidence
growth_confidence
```

---

# 20.36 Confidence Weighting

Conceptually:

```text
final_confidence =
weighted combination of confidence dimensions
```

Do not hard-code production weights without validation.

---

# 20.37 Minimum Confidence Floor

Possible:

```text
confidence < threshold
→ signal not actionable
```

Output:

```text
confidence_eligible
```

---

# 20.38 Confidence Buckets

Possible:

```text
VERY_LOW
LOW
MEDIUM
HIGH
VERY_HIGH
```

Keep continuous score primary.

---

# 20.39 Confidence Score

Recommended:

```text
0 to 100
```

Interpretation:

```text
0   = very unreliable
100 = highly reliable
```

---

# 20.40 Confidence vs Expected Return

Keep separate:

```text
Expected Return = magnitude
Confidence = reliability
```

Example:

```text
Stock A:
expected alpha = 8%
confidence = 40

Stock B:
expected alpha = 4%
confidence = 85
```

Portfolio engine can decide how to balance them.

---

# 20.41 Confidence-Adjusted Alpha

Possible:

```text
confidence_adjusted_alpha =
alpha × confidence_normalized
```

Store separately from raw alpha.

---

# 20.42 Confidence-Adjusted Rank

Possible:

```text
confidence_adjusted_alpha_rank
```

Useful for final screening.

---

# 20.43 Confidence Decay

Confidence can decline as information ages.

Examples:

```text
event confidence decays
old analyst estimate confidence falls
stale fundamental confidence falls
```

Store:

```text
confidence_decay_rate
```

---

# 20.44 Confidence Half-Life

Possible:

```text
confidence_half_life
```

Signal-family specific.

---

# 20.45 Confidence Recovery

New confirming information can increase confidence.

Examples:

```text
earnings beat
+
volume confirmation
+
price breakout
```

---

# 20.46 Contradiction Penalty

New evidence against the signal should reduce confidence.

Store:

```text
contradiction_penalty
```

---

# 20.47 Correlated Evidence Penalty

Do not double-count:

```text
trend
momentum
MA alignment
```

as three fully independent confirmations.

Use:

```text
effective_confirmation_count
```

---

# 20.48 Model Diversity Score

For ensembles:

```text
model_diversity_score
```

High diversity + agreement is more meaningful than many identical models agreeing.

---

# 20.49 Research Stability

Track confidence across:

```text
time periods
regimes
sectors
size buckets
```

---

# 20.50 Cross-Regime Robustness

Possible:

```text
cross_regime_robustness_score
```

---

# 20.51 Cross-Sector Robustness

Possible:

```text
cross_sector_robustness_score
```

---

# 20.52 Temporal Robustness

Compare signal efficacy in:

```text
older sample
recent sample
```

Output:

```text
temporal_robustness_score
```

---

# 20.53 Parameter Sensitivity

A strategy whose result disappears with tiny threshold changes has low robustness.

Store:

```text
parameter_stability_score
```

---

# 20.54 Confidence Penalties

Possible penalties:

```text
missing data
stale data
low liquidity
weak historical IC
high model disagreement
regime mismatch
extreme OOD
high event uncertainty
```

---

# 20.55 Confidence Bonuses

Possible:

```text
strong data quality
independent confirmation
high historical IC stability
strong regime fit
low uncertainty
high liquidity
```

---

# 20.56 Hard Confidence Exclusions

Possible:

```text
critical data error
signal built on stale price
missing required feature
invalid model state
```

Then:

```text
confidence_valid = false
```

---

# 20.57 Confidence Reason Codes

Examples:

```text
HIGH_DATA_QUALITY
MULTI_FACTOR_CONFIRMATION
LOW_SAMPLE_SIZE
REGIME_MISMATCH
LOW_LIQUIDITY
STALE_NEWS
MODEL_DISAGREEMENT
```

---

# 20.58 Explainability

For every confidence score expose:

```text
positive confidence drivers
negative confidence drivers
```

---

# 20.59 Confidence Contribution Record

Store:

```text
dimension
score
weight
contribution
```

---

# 20.60 Model Monitoring

Track confidence degradation over time.

Possible:

```text
rolling IC decline
calibration deterioration
feature drift
prediction drift
```

---

# 20.61 Feature Drift

Measure whether feature distributions changed.

Possible:

```text
PSI
KS statistic
distribution distance
```

---

# 20.62 Prediction Drift

Track:

```text
mean prediction
prediction dispersion
rank distribution
```

---

# 20.63 Performance Drift

Track:

```text
rolling IC
rolling hit rate
rolling alpha spread
```

---

# 20.64 Drift Penalty

Possible:

```text
model_drift_penalty
```

---

# 20.65 Retraining Flag

For ML models:

```text
retraining_required
```

when drift or performance degradation breaches thresholds.

---

# 20.66 Confidence Calibration by Bucket

For each confidence bucket, validate:

```text
realized hit rate
realized alpha
forecast error
```

High-confidence buckets should empirically perform better.

---

# 20.67 Confidence Monotonicity

Desired:

```text
higher confidence
→ better realized signal reliability
```

Store:

```text
confidence_monotonicity_score
```

---

# 20.68 Confidence Backtest

Evaluate:

```text
alpha performance by confidence decile
```

---

# 20.69 Confidence Deciles

Store:

```text
confidence_decile
```

Recommended:

```text
10 = highest confidence
1 = lowest
```

---

# 20.70 Confidence Percentile

Cross-sectional:

```text
confidence_percentile
```

---

# 20.71 Daily Confidence Record

Recommended:

```text
date
instrument_key
signal_name
signal_version


# DATA

data_confidence_score
feature_coverage_pct
data_freshness_score


# AGREEMENT

signal_agreement_score
signal_conflict_score
independent_confirmation_count


# HISTORICAL

historical_ic_confidence
sample_size_score
historical_hit_rate


# REGIME

regime_fit_score
regime_adjusted_confidence


# STABILITY

model_stability_score
signal_stability_score
rank_stability_score


# MODEL UNCERTAINTY

ensemble_agreement_score
ensemble_prediction_std
forecast_uncertainty_score

calibration_confidence
ood_score


# ACTIONABILITY

liquidity_confidence_score
execution_confidence


# SOURCE-SPECIFIC

event_confidence
flow_confidence
derivatives_confidence
fundamental_confidence


# FINAL

confidence_score
confidence_percentile
confidence_decile
confidence_bucket

confidence_adjusted_alpha

confidence_valid
confidence_quality_status
```

---

# 20.72 Initial Production Confidence Model

V1 should remain simple and transparent.

Possible components:

```text
Data Quality
Signal Agreement
Historical IC Stability
Regime Fit
Liquidity
Signal Stability
```

Normalize each to:

```text
0 to 100
```

Then combine with researched weights.

---

# 20.73 Initial Production Outputs

Recommended:

```text
data_confidence_score
signal_agreement_score
historical_ic_confidence
regime_fit_score
signal_stability_score
liquidity_confidence_score

confidence_score
confidence_percentile
confidence_bucket

confidence_adjusted_alpha

confidence_valid
confidence_quality_status
```

---

# 20.74 Confidence Engine Processing Flow

Recommended:

```text
SIGNAL OUTPUT
        ↓
DATA QUALITY
        ↓
FEATURE COVERAGE / FRESHNESS
        ↓
SIGNAL AGREEMENT / CONFLICT
        ↓
HISTORICAL EFFICACY
        ↓
SAMPLE SIZE
        ↓
REGIME FIT
        ↓
MODEL / RANK STABILITY
        ↓
CALIBRATION / UNCERTAINTY
        ↓
OOD / DRIFT
        ↓
LIQUIDITY / EXECUTION
        ↓
SOURCE CONFIDENCE
        ↓
CONFIDENCE SCORE
        ↓
CONFIDENCE-ADJUSTED ALPHA
        ↓
QUALITY / REASON CODES
```

---

# 20.75 Point-in-Time Rule

At date T, confidence can only use:

```text
historical performance known before T
data available at T
regime known at T
model state available at T
```

Do not calculate confidence using future realized outcomes.

---

# 20.76 Rolling Research Window

Historical IC and hit-rate confidence should use rolling or expanding windows ending before the prediction date.

Example:

```text
training / evaluation history <= T-1
```

---

# 20.77 Avoid Look-Ahead Calibration

Calibration models must be fitted only on prior observations.

---

# 20.78 Confidence Model Versioning

Store:

```text
confidence_model_version
```

Any formula/weight change requires new version.

---

# 20.79 Confidence Quality Status

Possible:

```text
VALID
PARTIAL_INPUTS
LOW_SAMPLE_SIZE
LOW_DATA_QUALITY
REGIME_UNCERTAIN
HIGH_MODEL_DISAGREEMENT
OOD_WARNING
LOW_LIQUIDITY
INVALID
```

---

# 20.80 Important Quant Rules

## Rule 1 — Confidence Is Not Signal Strength

Keep them separate.

## Rule 2 — Confidence Must Be Evidence-Based

Do not assign arbitrary percentages.

## Rule 3 — Historical Efficacy Must Be Point-in-Time

No future outcomes.

## Rule 4 — Independent Confirmation Matters

Avoid double-counting correlated indicators.

## Rule 5 — Sample Size Matters

Small samples should lower confidence.

## Rule 6 — Regime Fit Matters

A historically good signal may be weak in the current regime.

## Rule 7 — Liquidity Affects Actionability

Untradeable alpha should not receive high practical confidence.

## Rule 8 — Model Agreement Alone Is Not Enough

Identical models can agree for the same reason.

## Rule 9 — OOD Conditions Must Reduce Trust

Models are least reliable outside their training domain.

## Rule 10 — Calibration Must Be Tested

High confidence should correspond to higher realized reliability.

## Rule 11 — Confidence Must Decay

Stale information should lose weight.

## Rule 12 — Confidence Must Be Explainable

Expose drivers and penalties.

---

# 20.81 Completion Criteria

Step 20 is complete when Open Analytics can answer:

1. How reliable is this signal?
2. Is the underlying data complete?
3. Is the data fresh?
4. Do independent signal components agree?
5. How strong is the historical IC?
6. Is the IC stable?
7. Is the sample size adequate?
8. Does the signal historically work in the current regime?
9. Is the signal stable?
10. Do multiple models agree?
11. How uncertain is the forecast?
12. Is the probability forecast calibrated?
13. Is the model operating outside its normal feature range?
14. Is the stock sufficiently liquid?
15. Are event/news inputs trustworthy?
16. Are flow and derivatives inputs reliable?
17. What are the main confidence penalties?
18. What are the main positive confidence drivers?
19. What is the final confidence score?
20. How does confidence affect final alpha?
21. Does higher confidence actually correspond to better historical outcomes?
22. Can the exact historical confidence score be reproduced?

Once these are reliable, the Confidence Engine is ready to feed:

```text
Step 21 — Portfolio Construction Engine
```

---

# Step 20 Final Output

The Confidence Engine transforms:

```text
Signal Output
+
Data Quality
+
Historical Signal Performance
+
Regime Fit
+
Model Stability
+
Liquidity
+
Source Reliability
```

into:

```text
Data Confidence
Signal Agreement
Historical IC Confidence
Regime Fit
Model Stability
Forecast Uncertainty
Calibration Confidence
OOD Risk
Liquidity Confidence
Execution Confidence
Source-Specific Confidence
Final Confidence Score
Confidence Percentile
Confidence-Adjusted Alpha
Confidence Quality Flags
```

This becomes the reliability layer for Open Analytics.
