# Open Analytics — Step 28: ML / Forecasting Engine

## Purpose

The **ML / Forecasting Engine** trains, validates, deploys, and monitors statistical and machine-learning models that convert point-in-time features into forecasts.

This engine should answer:

- What exactly is the model predicting?
- Is the problem regression, classification, ranking, volatility forecasting, or regime prediction?
- Which features are used?
- Which training window is used?
- How are hyperparameters selected?
- How is leakage prevented?
- How is walk-forward validation performed?
- How stable is performance across time, sectors, and regimes?
- Is the forecast calibrated?
- Which features drive predictions?
- How uncertain is the forecast?
- Does the model outperform simple baselines?
- Has the model degraded in live use?
- When should the model be retrained or disabled?
- How are model versions linked to datasets and feature versions?

Outputs feed directly into:

- Alpha / Signal Engine
- Confidence Engine
- Risk forecasting
- Market Regime Engine
- Portfolio Construction
- Strategy research
- Live production inference
- Model governance

---

# 28.1 Core Principle

Machine learning should improve:

```text
prediction
ranking
calibration
risk estimation
```

not merely complexity.

The correct standard is:

```text
Does the ML model add stable, out-of-sample, net-of-cost value
over simpler baselines?
```

A complex model that cannot beat a simple factor blend should not be promoted.

---

# 28.2 Supported ML Problem Types

Recommended:

```text
REGRESSION
CLASSIFICATION
LEARNING_TO_RANK
VOLATILITY_FORECASTING
RISK_FORECASTING
REGIME_CLASSIFICATION
EVENT_RESPONSE_MODELING
```

Each model must explicitly declare its problem type.

---

# 28.3 Regression

Typical target:

```text
forward_return_21d
```

Output:

```text
predicted_return
```

Potential models:

```text
Linear Regression
Ridge
Lasso
Elastic Net
Random Forest Regressor
Gradient Boosting
XGBoost / LightGBM equivalent if introduced later
Neural Network later
```

Start with transparent baselines.

---

# 28.4 Classification

Typical targets:

```text
up/down
outperform/not outperform
top-decile/not
```

Outputs:

```text
probability_positive_return
probability_outperform
```

Potential models:

```text
Logistic Regression
Regularized Logistic Regression
Random Forest
Gradient Boosting
Neural Network later
```

---

# 28.5 Learning to Rank

For cross-sectional stock selection, ranking may be more natural than raw-return prediction.

Target:

```text
forward_return_rank
```

Group:

```text
date
```

Output:

```text
predicted_rank_score
```

This directly supports portfolio ranking.

---

# 28.6 Volatility Forecasting

Targets:

```text
future_realized_volatility_5d
future_realized_volatility_21d
```

Outputs feed:

```text
risk
position sizing
portfolio volatility targeting
```

---

# 28.7 Drawdown / Tail Risk Forecasting

Possible targets:

```text
future_max_drawdown_21d
tail_loss_probability
```

Useful for:

```text
risk controls
confidence
```

---

# 28.8 Regime Forecasting

Possible target:

```text
future regime
```

or latent regime modeling.

Outputs may feed Step 18 as an optional learned overlay.

---

# 28.9 Event Response Modeling

For Step 14 events:

```text
event_type
sentiment
materiality
novelty
```

predict:

```text
post_event_abnormal_return
volume response
IV response
```

---

# 28.10 Baseline Models

Every ML research project must compare against simple baselines.

Recommended:

```text
historical mean
sector mean
linear model
equal-weight factor score
single best factor
```

No model is accepted without baseline comparison.

---

# 28.11 Linear Regression Baseline

Useful because it is:

```text
fast
interpretable
stable
easy to debug
```

Store:

```text
linear_model_baseline_metric
```

---

# 28.12 Ridge Regression

Useful when features are correlated.

Penalty:

```text
L2
```

Good baseline for factor-heavy datasets.

---

# 28.13 Lasso

Penalty:

```text
L1
```

can perform feature selection.

Use carefully because unstable correlated-feature selection can occur.

---

# 28.14 Elastic Net

Combines:

```text
L1 + L2
```

Good for correlated financial features.

---

# 28.15 Logistic Regression

Strong baseline for binary classification.

Important outputs:

```text
probability
calibration
coefficients
```

---

# 28.16 Tree Models

Potential:

```text
Decision Tree
Random Forest
Gradient Boosted Trees
```

Advantages:

```text
nonlinear interactions
missing-value robustness
less scaling dependence
```

Risks:

```text
overfitting
unstable feature importance
regime dependence
```

---

# 28.17 Random Forest

Useful for nonlinear baseline.

Track:

```text
feature importance
OOB diagnostics where applicable
```

---

# 28.18 Gradient Boosting

Often strong for tabular data.

Important:

```text
walk-forward validation
regularization
early stopping
```

---

# 28.19 Neural Networks

Use only after:

```text
dataset size
feature stability
baseline quality
```

justify additional complexity.

Potential later:

```text
MLP
LSTM
Transformer
Temporal Fusion
```

Do not start here.

---

# 28.20 Time-Series Models

For market-level forecasting, possible:

```text
AR
ARIMA
GARCH
state-space
```

These remain useful classical baselines.

---

# 28.21 GARCH Family

Useful for volatility forecasting.

Potential:

```text
GARCH
EGARCH
GJR-GARCH
```

Compare with ML volatility models.

---

# 28.22 Cross-Sectional vs Time-Series Models

Keep separate.

Cross-sectional:

```text
which stock should outperform peers?
```

Time-series:

```text
what happens to this asset over time?
```

---

# 28.23 Model Registry

Maintain:

```text
model_name
model_version
problem_type

target_name
target_version

dataset_id
dataset_version

feature_set_version

algorithm
hyperparameters

training_window
validation_method

status
```

---

# 28.24 Model Versioning

Any material change requires a new version.

Examples:

```text
new features
different target
different hyperparameters
different training window
different preprocessing
different algorithm
```

---

# 28.25 Model Artifact Metadata

Store:

```text
model_file_reference
created_at
code_commit
random_seed
library_versions
```

---

# 28.26 Training Window

Possible:

```text
EXPANDING
ROLLING
FIXED
```

---

# 28.27 Expanding Window

Use all prior history.

Advantages:

```text
more data
```

Risks:

```text
old regimes may dominate
```

---

# 28.28 Rolling Window

Use last N years/sessions.

Advantages:

```text
adapts to recent structure
```

Risks:

```text
smaller sample
```

---

# 28.29 Training Recency Weighting

Optional:

```text
newer observations weighted more heavily
```

Must be explicitly validated.

---

# 28.30 Validation Framework

Recommended:

```text
walk-forward validation
```

not random K-fold by default.

---

# 28.31 Walk-Forward Training

Example:

```text
Train 2015–2019
Validate 2020
Test 2021

Train 2015–2020
Validate 2021
Test 2022
```

Exact periods configurable.

---

# 28.32 Purging

Use Step 27 purge logic to remove overlapping labels.

---

# 28.33 Embargo

Use where label overlap or leakage risk justifies it.

---

# 28.34 Hyperparameter Tuning

Tune only on:

```text
training + validation
```

Never final test.

---

# 28.35 Search Methods

Possible:

```text
grid search
random search
Bayesian optimization later
```

Do not excessively search huge parameter spaces.

---

# 28.36 Hyperparameter Overfitting

Track:

```text
number_of_trials
```

Large search count increases false-discovery risk.

---

# 28.37 Early Stopping

For boosting/neural models:

```text
stop when validation metric no longer improves
```

---

# 28.38 Model Selection Metric

Must match strategy objective.

Examples:

Regression:

```text
Rank IC
Spearman correlation
MAE
RMSE
```

Classification:

```text
AUC
log loss
Brier score
precision/recall
```

Ranking:

```text
NDCG
top-decile spread
Rank IC
```

---

# 28.39 Financial Model Selection Metrics

For stock selection, prefer:

```text
Rank IC
IC IR
top-bottom spread
monotonicity
turnover
net-of-cost return
```

over RMSE alone.

---

# 28.40 Regression Metrics

Store:

```text
MAE
RMSE
R2
Pearson correlation
Spearman correlation
```

---

# 28.41 Classification Metrics

Store:

```text
accuracy
precision
recall
F1
ROC AUC
PR AUC
log loss
Brier score
```

Accuracy alone is insufficient.

---

# 28.42 Ranking Metrics

Store:

```text
Rank IC
NDCG
top-k precision
quantile spread
```

---

# 28.43 Calibration

For probabilistic outputs, validate:

```text
predicted probability
vs
observed frequency
```

---

# 28.44 Probability Calibration

Possible methods:

```text
Platt scaling
isotonic regression
```

Fit only on calibration/validation data.

---

# 28.45 Calibration Error

Store:

```text
ECE
Brier score
reliability curve
```

---

# 28.46 Forecast Distribution

Advanced models may output:

```text
mean
standard deviation
quantiles
```

Example:

```text
predicted_return_p10
predicted_return_p50
predicted_return_p90
```

---

# 28.47 Quantile Regression

Useful for:

```text
return distribution
tail risk
```

---

# 28.48 Prediction Interval

Store:

```text
prediction_lower
prediction_upper
```

where model supports it.

---

# 28.49 Forecast Uncertainty

Output:

```text
forecast_uncertainty
```

feeds Confidence Engine.

---

# 28.50 Ensemble Models

Combine multiple models.

Possible:

```text
linear
tree
factor baseline
ranking model
```

---

# 28.51 Simple Average Ensemble

Baseline:

```text
ensemble =
mean(model predictions)
```

---

# 28.52 Weighted Ensemble

Weights may use:

```text
historical IC
regime performance
calibration
stability
```

---

# 28.53 Stacking

Advanced:

```text
meta-model learns how to combine predictions
```

Must be trained leakage-safely.

---

# 28.54 Ensemble Diversity

Measure correlation among model predictions.

Store:

```text
model_prediction_correlation
ensemble_diversity_score
```

---

# 28.55 Ensemble Agreement

Store:

```text
ensemble_agreement_score
```

Feeds confidence.

---

# 28.56 Feature Importance

Possible methods:

```text
linear coefficients
tree split importance
permutation importance
SHAP later
```

---

# 28.57 Permutation Importance

Preferred over naive tree importance for many analyses.

Evaluate on validation/test only.

---

# 28.58 SHAP

Advanced explainability tool.

Can provide:

```text
global importance
local prediction explanation
```

Use cautiously with highly correlated features.

---

# 28.59 Global Explainability

Answer:

```text
Which features matter overall?
```

---

# 28.60 Local Explainability

Answer:

```text
Why did this stock receive this forecast today?
```

---

# 28.61 Feature Directionality

For linear models:

```text
positive coefficient
negative coefficient
```

For nonlinear models use partial dependence carefully.

---

# 28.62 Partial Dependence

Optional diagnostic.

---

# 28.63 ICE Plots

Optional advanced diagnostic.

---

# 28.64 Feature Interaction Analysis

Identify:

```text
momentum × regime
value × quality
news × volume
```

effects.

---

# 28.65 Feature Leakage Audit

Before training check:

```text
future labels
future timestamps
post-event reaction
future universe membership
```

---

# 28.66 Target Leakage Audit

Any feature with extremely strong direct relationship to target must be investigated.

---

# 28.67 Model Memorization Check

If model performs very well in-sample but collapses out-of-sample:

```text
likely overfit
```

---

# 28.68 Train vs Validation Gap

Store:

```text
train_metric
validation_metric
generalization_gap
```

---

# 28.69 Validation vs Test Gap

Store.

---

# 28.70 Time Stability

Evaluate performance by year.

---

# 28.71 Regime Stability

Evaluate by:

```text
bull
bear
high vol
low vol
```

---

# 28.72 Sector Stability

Evaluate predictive performance by sector.

---

# 28.73 Size Stability

Evaluate:

```text
large
mid
small cap
```

---

# 28.74 Liquidity Stability

Evaluate across liquidity buckets.

---

# 28.75 Prediction Turnover

For ranking models:

```text
rank turnover
```

matters because unstable rankings create costs.

---

# 28.76 Prediction Autocorrelation

Store:

```text
prediction_rank_autocorrelation
```

---

# 28.77 Forecast Decay

Measure predictive strength versus horizon:

```text
1D
5D
21D
63D
```

---

# 28.78 Model Half-Life

Possible:

```text
prediction_half_life
```

---

# 28.79 Feature Drift

Monitor live vs training distributions.

Consume Step 27 drift diagnostics.

---

# 28.80 Prediction Drift

Track:

```text
mean prediction
std prediction
rank dispersion
```

---

# 28.81 Performance Drift

Track:

```text
rolling IC
hit rate
calibration
```

---

# 28.82 Concept Drift

Underlying relationship between features and target may change.

Possible indicators:

```text
IC decline
feature importance shift
regime-specific failure
```

---

# 28.83 Drift Score

Output:

```text
model_drift_score
```

---

# 28.84 Model Health Status

Possible:

```text
HEALTHY
WATCH
DEGRADED
CRITICAL
```

---

# 28.85 Retraining Trigger

Possible triggers:

```text
scheduled interval
drift threshold
performance degradation
new data volume
regime change
```

---

# 28.86 Scheduled Retraining

Possible:

```text
monthly
quarterly
```

depending on model.

---

# 28.87 Event-Driven Retraining

Possible when:

```text
structural drift
```

is detected.

---

# 28.88 Retraining Guardrail

Do not retrain automatically from a tiny recent sample.

---

# 28.89 Champion / Challenger Framework

Maintain:

```text
champion model
challenger models
```

---

# 28.90 Promotion Rule

Challenger replaces champion only after:

```text
out-of-sample improvement
stability
cost-aware benefit
```

---

# 28.91 Shadow Deployment

Run challenger in production without influencing trades initially.

Store predictions.

---

# 28.92 Model Rollback

Support:

```text
rollback to prior model version
```

---

# 28.93 Production Inference

At timestamp T:

```text
fetch latest valid point-in-time features
apply production preprocessing
generate forecast
```

---

# 28.94 Training-Serving Parity

Production preprocessing must match training exactly.

---

# 28.95 Feature Order

For models requiring ordered arrays, store exact:

```text
feature_order
```

---

# 28.96 Missing Feature Handling in Production

If required feature missing:

```text
apply registered missing policy
```

or reject inference.

---

# 28.97 Inference Eligibility

Consume Step 27:

```text
inference_eligible
```

---

# 28.98 Prediction Record

Recommended:

```text
prediction_id
model_name
model_version

as_of_timestamp
instrument_key

raw_prediction
calibrated_prediction

prediction_rank
prediction_percentile

forecast_uncertainty

inference_quality_status
```

---

# 28.99 Feature Snapshot for Prediction

Store or hash:

```text
features used for inference
```

for auditability.

---

# 28.100 Model Input Hash

Possible:

```text
feature_vector_hash
```

---

# 28.101 Prediction Explainability Record

Store:

```text
top_positive_features
top_negative_features
feature_contributions
```

---

# 28.102 Model Prediction as Alpha Input

ML output should feed Step 19 as:

```text
ml_alpha_score
```

not directly become a trade.

---

# 28.103 Model Confidence

Model output should also expose:

```text
ml_confidence
```

based on:

```text
calibration
uncertainty
OOD
stability
```

---

# 28.104 Regression-to-Alpha Mapping

If model predicts:

```text
forward return
```

convert to:

```text
cross-sectional rank
percentile
expected alpha
```

---

# 28.105 Classification-to-Alpha Mapping

If output is:

```text
probability_outperform
```

map to signal score using validated calibration.

---

# 28.106 Ranking Output

For learning-to-rank:

```text
ranking_score
```

can directly feed cross-sectional alpha rank.

---

# 28.107 Ensemble Alpha

Possible:

```text
final_ml_alpha =
weighted combination of model outputs
```

---

# 28.108 ML and Rule-Based Ensemble

Potential:

```text
factor alpha
+
ML alpha
```

with separate weights.

---

# 28.109 ML Weight Cap

Initially cap ML influence.

Example concept:

```text
ML contributes no more than X% of final alpha
```

until robust live evidence exists.

---

# 28.110 Out-of-Distribution Detection

Possible methods:

```text
feature-distance score
Mahalanobis distance
isolation model
autoencoder later
```

---

# 28.111 OOD Penalty

High OOD:

```text
reduce confidence
```

possibly suppress prediction.

---

# 28.112 Extrapolation Warning

Tree models may behave differently than linear models outside training domain.

Store:

```text
extrapolation_warning
```

---

# 28.113 Probability of Positive Return

Output:

```text
prob_positive_return
```

if calibrated.

---

# 28.114 Probability of Outperformance

Output:

```text
prob_outperform_benchmark
```

---

# 28.115 Expected Return

Regression output:

```text
expected_return
```

---

# 28.116 Expected Excess Return

Output:

```text
expected_excess_return
```

---

# 28.117 Predicted Rank

Store.

---

# 28.118 Predicted Volatility

Store where relevant.

---

# 28.119 Predicted Drawdown

Store where relevant.

---

# 28.120 Multi-Horizon Forecasts

Possible:

```text
pred_5d
pred_21d
pred_63d
```

Separate models may be better than one generic model.

---

# 28.121 Multi-Task Learning

Later:

```text
return
volatility
drawdown
```

joint model.

Use only if validated.

---

# 28.122 Sector-Specific Models

Possible:

```text
banking model
IT model
```

if sector behavior differs materially.

Avoid fragmentation without sufficient sample size.

---

# 28.123 Regime-Specific Models

Possible:

```text
bull model
bear model
```

but beware sample reduction and regime-classification error.

---

# 28.124 Mixture of Experts

Advanced:

```text
regime gate
+
specialized models
```

---

# 28.125 Meta-Labeling

Possible later:

```text
primary signal generates candidate
ML model predicts whether to take trade
```

Useful for confidence/filtering.

---

# 28.126 Meta-Label Target

Possible:

```text
1 if candidate trade succeeds
0 otherwise
```

---

# 28.127 Triple-Barrier Method

Advanced event-labeling framework:

```text
profit-taking barrier
stop-loss barrier
time barrier
```

Can be useful for trade classification models.

---

# 28.128 Sample Weighting by Uniqueness

For overlapping events/labels, advanced methods may weight by observation uniqueness.

---

# 28.129 Model Portfolio Impact Test

Do not evaluate model only statistically.

Backtest:

```text
model-driven portfolio
```

through Steps 21–24.

---

# 28.130 Net-of-Cost ML Evaluation

A model with higher IC but much higher turnover may be worse.

Track:

```text
net alpha
turnover
cost
capacity
```

---

# 28.131 Model Capacity

Check whether model concentrates in illiquid securities.

---

# 28.132 Model Concentration

Track:

```text
prediction concentration
top-decile concentration
sector concentration
size concentration
```

---

# 28.133 Model Factor Exposure

Measure whether ML model simply reproduces:

```text
momentum
size
beta
value
```

---

# 28.134 Residual ML Alpha

Neutralize model score to known factors where research objective requires.

---

# 28.135 Model Purity

Possible:

```text
residual IC after known factor neutralization
```

---

# 28.136 Feature Importance Stability

Track importance across:

```text
time folds
regimes
```

---

# 28.137 Feature Sign Stability

For linear models, track coefficient signs.

---

# 28.138 Model Complexity Penalty

Prefer simpler model if performance difference is marginal.

---

# 28.139 Production Latency

Track:

```text
feature load time
inference time
total prediction time
```

---

# 28.140 Batch Inference

For daily cross-sectional models:

```text
predict full universe in one batch
```

---

# 28.141 Real-Time Inference

For intraday models, low-latency design needed.

Not required for initial daily production.

---

# 28.142 Model Storage

Store artifacts securely and versioned.

Possible:

```text
joblib
pickle with caution
ONNX later
native model format
```

---

# 28.143 Reproducibility

Store:

```text
dataset version
feature set
target
hyperparameters
seed
code commit
library versions
```

---

# 28.144 Model Training Record

Recommended:

```text
model_id
model_name
model_version

created_at

problem_type
algorithm

dataset_id
dataset_version

feature_set_version
target_name
target_version

training_start
training_end

validation_start
validation_end

hyperparameters

random_seed

train_metric
validation_metric
test_metric

model_status
```

---

# 28.145 Model Evaluation Record

```text
model_id
evaluation_period

Rank_IC
IC_IR

MAE
RMSE

AUC
Brier
log_loss

top_decile_return
bottom_decile_return
long_short_spread

turnover
net_alpha
```

Populate only relevant metrics.

---

# 28.146 Walk-Forward Prediction Record

```text
fold_id
train_period
validation_period
test_period

model_version
prediction_count

IC
Sharpe
turnover
cost
```

---

# 28.147 Model Drift Record

```text
date
model_id

feature_drift_score
prediction_drift_score
performance_drift_score
OOD_rate

rolling_IC
rolling_hit_rate

model_health_status
```

---

# 28.148 Initial Production ML Model

Recommended V1:

```text
Cross-sectional 21D return ranking
```

using:

```text
point-in-time daily equity dataset
```

with features from:

```text
momentum
trend
risk
liquidity
volume
quality
value
growth
market regime
breadth
```

Baseline models:

```text
Ridge
Elastic Net
Gradient Boosting
```

Compare against:

```text
equal-weight factor composite
```

---

# 28.149 Initial Production Target

Recommended:

```text
21D sector-relative forward return
```

or rank thereof.

Also research:

```text
5D
63D
```

but keep separate.

---

# 28.150 Initial Production Evaluation

Require:

```text
Rank IC
IC IR
top-bottom decile spread
monotonicity
turnover
net-of-cost return
drawdown
regime stability
```

---

# 28.151 Initial Production Inference Outputs

Recommended:

```text
ml_expected_return_21d
ml_rank_score
ml_percentile

prob_outperform
forecast_uncertainty

ml_confidence

top_feature_drivers

model_health_status
```

---

# 28.152 ML / Forecasting Processing Flow

Recommended:

```text
VERSIONED ML DATASET
        ↓
MODEL DEFINITION
        ↓
BASELINE MODEL
        ↓
CHRONOLOGICAL TRAINING
        ↓
PURGED WALK-FORWARD VALIDATION
        ↓
HYPERPARAMETER TUNING
        ↓
OUT-OF-SAMPLE TEST
        ↓
CALIBRATION
        ↓
FEATURE IMPORTANCE / EXPLAINABILITY
        ↓
PORTFOLIO BACKTEST
        ↓
NET-OF-COST EVALUATION
        ↓
MODEL REGISTRY
        ↓
PRODUCTION INFERENCE
        ↓
DRIFT / HEALTH MONITORING
        ↓
RETRAIN / CHAMPION-CHALLENGER
```

---

# 28.153 Point-in-Time Rule

Every prediction at time T must use:

```text
features available at T
preprocessing fitted using data before T
model trained using labels available before T
```

---

# 28.154 Training Label Availability Rule

Training rows may only be used after their label horizon has completed.

Example:

For 21D labels at training date T:

```text
last usable training observation
must have label_end <= T
```

---

# 28.155 Retraining Cutoff Rule

Prevent model from training on rows whose labels are not yet fully realized.

---

# 28.156 No Test Leakage

Test-set performance cannot influence:

```text
feature selection
hyperparameters
model choice
```

---

# 28.157 Model Quality Status

Possible:

```text
VALID
LOW_SAMPLE_SIZE
OVERFIT_WARNING
CALIBRATION_WARNING
DRIFT_WARNING
OOD_WARNING
LIVE_DEGRADED
INVALID
```

---

# 28.158 Promotion Criteria

A model is production candidate only if:

```text
out-of-sample performance positive
net-of-cost value-add positive
stable across periods
reasonable turnover
acceptable capacity
explainable
reproducible
```

---

# 28.159 Rejection Criteria

Reject if:

```text
only in-sample performance
unstable IC
high turnover destroys alpha
heavy leakage risk
poor calibration
severe regime dependence
no improvement over baseline
```

---

# 28.160 Research Diagnostics

Always inspect:

```text
IC by year
IC by regime
IC by sector
prediction dispersion
rank stability
turnover
cost
factor exposure
```

---

# 28.161 Model Debugging Sequence

If model fails:

```text
1. Check data leakage.
2. Check target definition.
3. Check feature availability.
4. Check splits.
5. Check baseline.
6. Check overfitting.
7. Check turnover/cost.
8. Check regime dependence.
```

Do not immediately add more complexity.

---

# 28.162 Important Quant Rules

## Rule 1 — ML Must Beat a Simple Baseline

Complexity must earn its place.

## Rule 2 — Walk-Forward Validation Is Mandatory

Random shuffling is not the default.

## Rule 3 — Labels Must Be Fully Realized Before Training

Prevent subtle future leakage.

## Rule 4 — Financial Metrics Matter More Than RMSE Alone

Use IC, spreads, turnover, and net alpha.

## Rule 5 — Calibration Matters

Probability outputs must correspond to real frequencies.

## Rule 6 — Model Explainability Matters

Especially before using predictions in production.

## Rule 7 — Drift Must Be Monitored

Historical relationships can change.

## Rule 8 — Model Output Is an Input to the Signal Engine

Not an automatic trade.

## Rule 9 — Net-of-Cost Evaluation Is Mandatory

Predictive power without economic value is insufficient.

## Rule 10 — Version Everything

Dataset, features, model, preprocessing, and target.

## Rule 11 — Keep Champion / Challenger Models

Do not replace production models casually.

## Rule 12 — Prefer Stable Models Over Fragile High Backtest Scores

Robustness is more valuable than peak in-sample performance.

---

# 28.163 Completion Criteria

Step 28 is complete when Open Analytics can answer:

1. What exactly does the model predict?
2. What dataset version trained it?
3. What features were used?
4. What target definition was used?
5. What model algorithm was used?
6. What training window was used?
7. What validation scheme was used?
8. Were labels fully realized before training?
9. Were overlapping labels purged?
10. What baseline was compared?
11. What was out-of-sample Rank IC?
12. What was IC IR?
13. What was top-bottom quantile spread?
14. What was turnover?
15. What was net-of-cost performance?
16. Was performance stable across regimes?
17. Was performance stable across sectors and size buckets?
18. Is the forecast calibrated?
19. What is forecast uncertainty?
20. Which features drive the model?
21. Is the model currently experiencing drift?
22. What is model health status?
23. When was it last retrained?
24. Is a challenger model better?
25. Can every live prediction be reproduced from the stored model and features?
26. Does the ML model add genuine value over the simple factor baseline?

Once these are reliable, the ML / Forecasting Engine is ready to feed:

```text
Step 29 — Stock Search / Screener Engine
```

---

# Step 28 Final Output

The ML / Forecasting Engine transforms:

```text
Versioned ML Dataset
+
Feature Set
+
Targets
+
Walk-Forward Training
```

into:

```text
Expected Return Forecasts
Outperformance Probabilities
Cross-Sectional Rank Scores
Volatility Forecasts
Risk Forecasts
Forecast Uncertainty
Calibration Metrics
Feature Importance
Local Explanations
Model Health
Drift Monitoring
Champion / Challenger Models
Production Predictions
```

This becomes the predictive-model layer for Open Analytics.
