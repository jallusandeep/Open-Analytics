# Open Analytics — Step 30: Final Research Decision Layer

## Purpose

The **Final Research Decision Layer** is the top-level synthesis layer of Open Analytics.

It converts the outputs of all prior engines into a clear, auditable, research-oriented decision state for each security.

This layer should answer:

- Is this stock currently attractive or unattractive?
- Is the opportunity strong enough to act on?
- How confident are we?
- What is the expected return horizon?
- What are the strongest reasons supporting the decision?
- What are the strongest reasons against it?
- What are the key risks?
- Does the current market regime support the idea?
- Is liquidity sufficient?
- Are there important upcoming events?
- Is the stock already overextended?
- Does the ML forecast agree with the factor/signal model?
- Is there institutional or derivatives confirmation?
- Is the opportunity suitable for research only, watchlist, portfolio entry, reduction, or avoidance?
- What must change before the decision changes?
- Can the exact decision be reproduced later?

The layer should not create new raw alpha independently.

It should synthesize, gate, explain, and prioritize the outputs produced by the rest of the Open Analytics stack.

---

# 30.1 Core Principle

The final decision is not:

```text
one indicator
```

and not:

```text
one model score
```

It is a structured synthesis of:

```text
Expected Alpha
Confidence
Risk
Liquidity
Trend
Momentum
Fundamentals
Valuation
News / Events
Institutional Flow
Derivatives
Market Regime
ML Forecasts
Portfolio Context
```

The final output should remain:

```text
Explainable
Point-in-Time
Versioned
Auditable
Non-Leaky
Risk-Aware
Cost-Aware
```

---

# 30.2 Decision vs Prediction

Important distinction:

```text
Prediction:
What is likely to happen?

Decision:
Given expected return, uncertainty, risk, cost, regime, and constraints,
what should Open Analytics recommend doing?
```

The same forecast may produce different decisions depending on:

```text
liquidity
market stress
portfolio exposure
confidence
event risk
```

---

# 30.3 Required Inputs

From Step 19 — Alpha / Signal:

```text
raw_alpha_score
final_alpha_score
alpha_percentile

signal_direction
signal_strength

expected_return
expected_horizon

confirmation_score
signal_conflict_score
```

From Step 20 — Confidence:

```text
confidence_score
confidence_bucket
confidence_adjusted_alpha

forecast_uncertainty
regime_fit_score
```

From Step 5 — Risk:

```text
volatility
beta
drawdown
CVaR
tail_risk
```

From Step 6 — Liquidity:

```text
liquidity_score
ADV
spread
days_to_liquidate
trading_eligible
```

From Step 7 / 8 / 9:

```text
trend_state
momentum_state
participation_state
```

From Steps 11 / 12 / 13:

```text
quality_factor
growth_factor
value_factor
factor_composite
```

From Step 14:

```text
news_factor_score
positive_catalyst_score
negative_catalyst_score
event_risk_score
upcoming_event_flag
```

From Step 15:

```text
institutional_flow_score
flow_regime
```

From Step 16:

```text
derivatives_score
derivatives_risk_score
expected_move
IV_percentile
```

From Step 18:

```text
market_regime
market_stress_score
bull_probability
bear_probability
```

From Step 28:

```text
ml_expected_return
ml_rank_score
prob_outperform
ml_confidence
model_health_status
```

From Step 21 / 22:

```text
portfolio_current_weight
portfolio_target_weight
risk_budget
position_limit
sector_exposure
```

---

# 30.4 Decision State

Recommended primary states:

```text
STRONG_BUY
BUY
WATCH
HOLD
REDUCE
SELL
AVOID
RESEARCH_ONLY
```

If short selling is supported:

```text
STRONG_SHORT
SHORT
```

Continuous scores should remain primary internally.

---

# 30.5 Research-Oriented Interpretation

Suggested meanings:

```text
STRONG_BUY
= high expected alpha
+ high confidence
+ acceptable risk/liquidity
+ strong confirmation

BUY
= positive expected alpha
+ sufficient confidence
+ no major blocking risk

WATCH
= promising but one or more required confirmations missing

HOLD
= existing position remains acceptable but new entry edge is limited

REDUCE
= edge weakened or risk increased

SELL
= negative expected alpha or materially deteriorating thesis

AVOID
= unacceptable risk, liquidity, data quality, or unresolved event

RESEARCH_ONLY
= useful analytical case but not currently actionable
```

---

# 30.6 Final Decision Score

Possible continuous output:

```text
decision_score
```

Recommended scale:

```text
-100 to +100
```

Interpretation:

```text
+100 = strongest positive decision state
0    = neutral / insufficient edge
-100 = strongest negative decision state
```

---

# 30.7 Decision Score Components

Possible:

```text
Alpha
Confidence
Risk
Liquidity
Regime Fit
Fundamentals
Valuation
Event / News
Flow
Derivatives
ML
```

Weights must be configurable and research-validated.

---

# 30.8 Alpha Component

Primary driver:

```text
alpha_component
```

Use:

```text
final_alpha_score
alpha_percentile
expected_return
```

---

# 30.9 Confidence Component

Use:

```text
confidence_score
```

Confidence should scale trust in alpha, not replace alpha.

---

# 30.10 Risk Penalty

Possible:

```text
risk_penalty
```

Inputs:

```text
volatility
drawdown
tail risk
CVaR
beta
```

---

# 30.11 Liquidity Penalty

Possible:

```text
liquidity_penalty
```

Inputs:

```text
spread
ADV
impact
days_to_liquidate
```

---

# 30.12 Regime Adjustment

Possible:

```text
regime_adjustment
```

Example:

```text
momentum strategy in bullish regime
→ positive adjustment

high-beta stock in stress regime
→ negative adjustment
```

---

# 30.13 Fundamental Adjustment

Possible:

```text
fundamental_adjustment
```

From:

```text
quality
growth
financial strength
```

---

# 30.14 Valuation Adjustment

Possible:

```text
valuation_adjustment
```

Do not automatically equate:

```text
cheap = buy
```

Use as context.

---

# 30.15 Event Adjustment

Use:

```text
positive catalyst
negative catalyst
event risk
```

---

# 30.16 Flow Adjustment

Use:

```text
institutional_flow_score
```

as confirmation/context.

---

# 30.17 Derivatives Adjustment

Use derivatives positioning as:

```text
confirmation
risk context
```

not a standalone decision.

---

# 30.18 ML Adjustment

Possible:

```text
ml_adjustment
```

Only if:

```text
model_health valid
forecast confidence sufficient
```

---

# 30.19 ML Weight Cap

ML should initially have a bounded influence.

Example concept:

```text
maximum ML contribution <= configured cap
```

until long production history validates it.

---

# 30.20 Decision Gates

Before final scoring, apply gates.

Recommended gates:

```text
Data Quality Gate
Tradability Gate
Liquidity Gate
Risk Gate
Event Gate
Model Health Gate
```

---

# 30.21 Data Quality Gate

If:

```text
critical data-quality issue
```

then:

```text
decision_state = RESEARCH_ONLY
```

or:

```text
AVOID
```

depending on severity.

---

# 30.22 Tradability Gate

If:

```text
trading_eligible = false
```

then no actionable BUY/SELL order state should be produced.

---

# 30.23 Liquidity Gate

If liquidity below minimum:

```text
AVOID
```

or:

```text
RESEARCH_ONLY
```

---

# 30.24 Risk Gate

Potential blockers:

```text
extreme volatility
extreme CVaR
critical drawdown
portfolio risk breach
```

---

# 30.25 Event Gate

Possible blockers:

```text
pending regulatory outcome
suspension risk
major unresolved fraud event
```

---

# 30.26 Model Health Gate

If ML model:

```text
DEGRADED
CRITICAL
```

its contribution should be reduced or disabled.

---

# 30.27 Hard Overrides

Possible hard overrides:

```text
SUSPENDED
CRITICAL_DATA_FAILURE
MARGIN_BREACH
UNTRADEABLE
FRAUD_CRITICAL
LIQUIDITY_FAILURE
```

Hard overrides must be explicit and auditable.

---

# 30.28 Soft Penalties

Possible:

```text
high valuation
moderate volatility
weak flow
minor event uncertainty
```

These should reduce score, not automatically block.

---

# 30.29 Positive Drivers

For every security identify:

```text
top_positive_drivers
```

Example:

```text
Strong 6M momentum
High quality
Positive earnings surprise
Broad volume confirmation
High ML rank
```

---

# 30.30 Negative Drivers

Identify:

```text
top_negative_drivers
```

Example:

```text
Expensive valuation
Weak FII flow
High IV
Event risk
Low liquidity
```

---

# 30.31 Decision Explanation

Output concise explanation:

```text
Decision
Score
Expected Return
Confidence
Key Drivers
Key Risks
```

---

# 30.32 Decision Reason Codes

Examples:

```text
ALPHA_TOP_DECILE
HIGH_CONFIDENCE
STRONG_TREND
POSITIVE_NEWS_CATALYST
FLOW_CONFIRMATION
VALUATION_EXPENSIVE
EVENT_RISK_HIGH
LIQUIDITY_LOW
ML_CONFIRMATION
```

---

# 30.33 Decision Horizon

Every decision must have:

```text
decision_horizon
```

Examples:

```text
1D
5D
21D
63D
```

Do not mix short-term and long-term signals.

---

# 30.34 Short-Term Decision

Potentially emphasizes:

```text
momentum
trend
volume
news
derivatives
```

---

# 30.35 Medium-Term Decision

Potentially emphasizes:

```text
momentum
quality
value
growth
flow
```

---

# 30.36 Long-Term Research Decision

Potentially emphasizes:

```text
fundamentals
valuation
quality
growth
capital efficiency
```

---

# 30.37 Multi-Horizon Output

Possible:

```text
decision_5d
decision_21d
decision_63d
```

Store separately.

---

# 30.38 Horizon Conflict

Example:

```text
5D bullish
63D neutral
```

Store:

```text
horizon_conflict_flag
```

---

# 30.39 Entry Suitability

Output:

```text
entry_suitability_score
```

This may consider:

```text
alpha
trend
overextension
liquidity
event timing
```

---

# 30.40 Hold Suitability

For existing position:

```text
hold_suitability_score
```

---

# 30.41 Exit Suitability

Possible:

```text
exit_pressure_score
```

---

# 30.42 Thesis Strength

Possible:

```text
thesis_strength_score
```

based on:

```text
driver breadth
confidence
historical robustness
```

---

# 30.43 Thesis Conflict

Store:

```text
thesis_conflict_score
```

---

# 30.44 Thesis Freshness

Track:

```text
thesis_age
```

and whether key drivers are stale.

---

# 30.45 Decision Freshness

Possible:

```text
FRESH
ACTIVE
AGING
STALE
```

---

# 30.46 Decision Expiry

Some decisions should expire after:

```text
N sessions
```

unless refreshed.

---

# 30.47 Decision Change Trigger

Possible triggers:

```text
alpha crosses threshold
confidence changes materially
market regime changes
major event occurs
risk breach
```

---

# 30.48 Thesis Invalidation Rules

Every actionable thesis should define what invalidates it.

Examples:

```text
trend breaks
earnings thesis fails
liquidity collapses
event risk materializes
alpha falls below threshold
```

---

# 30.49 Thesis Confirmation Rules

Possible:

```text
breakout confirmed
volume confirms
flow improves
fundamental revision positive
```

---

# 30.50 Decision Transition States

Examples:

```text
WATCH → BUY
BUY → HOLD
HOLD → REDUCE
REDUCE → SELL
WATCH → AVOID
```

---

# 30.51 Decision Persistence

Track:

```text
days_in_current_decision_state
```

---

# 30.52 Decision Churn

Track frequent state changes.

High churn may indicate unstable thresholds.

---

# 30.53 Hysteresis

Use different thresholds for entering and exiting decision states.

Example:

```text
BUY entry >= 75
remain BUY until < 65
```

This reduces flip-flopping.

---

# 30.54 Portfolio Context

Final decision should know:

```text
current portfolio exposure
current sector exposure
existing position
risk budget
```

---

# 30.55 Candidate Decision vs Portfolio Decision

Keep separate:

```text
security_research_decision
```

and:

```text
portfolio_action_decision
```

A great stock may not be added because portfolio is already overexposed.

---

# 30.56 Security Research Decision

Independent of current holdings.

Example:

```text
BUY
```

---

# 30.57 Portfolio Action Decision

Possible:

```text
ENTER
ADD
HOLD
TRIM
EXIT
NO_ACTION
```

---

# 30.58 Existing Position Logic

If already held:

```text
BUY
```

might translate to:

```text
ADD
```

or:

```text
HOLD
```

depending on target weight.

---

# 30.59 New Position Logic

If not held:

```text
BUY
```

may translate to:

```text
ENTER
```

if portfolio constraints allow.

---

# 30.60 Portfolio Blocked Opportunity

Possible:

```text
research_decision = BUY
portfolio_action = NO_ACTION
reason = sector limit
```

This distinction is critical.

---

# 30.61 Risk-Adjusted Decision

Possible output:

```text
risk_adjusted_decision_score
```

---

# 30.62 Cost-Adjusted Decision

If expected alpha after costs is poor:

```text
decision should weaken
```

---

# 30.63 Capacity-Adjusted Decision

Large-capital portfolios may receive different actionability from small-capital research.

---

# 30.64 Event-Aware Decision

If major event imminent:

```text
pre_event_risk_flag
```

may alter actionability.

---

# 30.65 Earnings-Aware Decision

Example:

```text
strong signal
but earnings tomorrow
```

Potential:

```text
WATCH
```

instead of immediate BUY unless strategy explicitly trades earnings.

---

# 30.66 Overextension Check

Strong trend may be:

```text
too extended
```

for immediate entry.

Inputs:

```text
distance from moving average
RSI
ATR extension
```

---

# 30.67 Pullback Suitability

Possible:

```text
wait_for_pullback_flag
```

---

# 30.68 Breakout Suitability

Possible:

```text
breakout_entry_flag
```

---

# 30.69 Liquidity Suitability

Output:

```text
actionability_liquidity_score
```

---

# 30.70 Timing Suitability

Possible:

```text
timing_score
```

Separate:

```text
good company
```

from:

```text
good entry now
```

---

# 30.71 Fundamental Thesis

Summarize:

```text
quality
growth
financial strength
```

---

# 30.72 Valuation Thesis

Summarize:

```text
cheap
fair
expensive
```

relative to:

```text
history
sector
growth
quality
```

---

# 30.73 Technical Thesis

Summarize:

```text
trend
momentum
breakout
volume
```

---

# 30.74 Catalyst Thesis

Summarize:

```text
news
events
earnings
orders
regulatory
```

---

# 30.75 Flow Thesis

Summarize:

```text
institutional support
distribution
```

---

# 30.76 Derivatives Thesis

Summarize:

```text
futures positioning
IV
skew
OI
```

---

# 30.77 ML Thesis

Summarize:

```text
expected return
rank
probability
uncertainty
```

---

# 30.78 Risk Thesis

Summarize:

```text
volatility
drawdown
tail risk
liquidity
```

---

# 30.79 Regime Thesis

Summarize:

```text
market regime
sector regime
```

---

# 30.80 Thesis Synthesis

Example structured output:

```text
Fundamental: Strong
Valuation: Neutral
Trend: Strong
Momentum: Strong
Volume: Confirming
News: Positive
Flow: Positive
Derivatives: Neutral
ML: Positive
Risk: Moderate
Regime: Supportive
```

---

# 30.81 Decision Matrix

Possible qualitative matrix:

```text
High Alpha + High Confidence + Low/Moderate Risk
→ BUY / STRONG_BUY

High Alpha + Low Confidence
→ WATCH

Low Alpha + High Risk
→ AVOID

Negative Alpha + High Confidence
→ SELL / SHORT
```

---

# 30.82 Decision Probability

Optional:

```text
probability_decision_is_correct
```

Only if genuinely calibrated.

Do not invent this from confidence score directly.

---

# 30.83 Expected Upside

Possible:

```text
expected_upside
```

from calibrated return forecast.

---

# 30.84 Expected Downside

Possible:

```text
expected_downside
```

from risk/forecast distribution.

---

# 30.85 Reward-to-Risk

Possible:

```text
expected_reward_risk_ratio
```

---

# 30.86 Upside / Downside Distribution

Advanced:

```text
p10 return
median return
p90 return
```

---

# 30.87 Decision Confidence

Use Step 20:

```text
confidence_score
```

Do not derive a second unrelated confidence unless necessary.

---

# 30.88 Decision Quality Status

Possible:

```text
VALID
PARTIAL_INPUTS
LOW_CONFIDENCE
CONFLICTED
EVENT_UNCERTAIN
LOW_LIQUIDITY
MODEL_WARNING
RISK_BLOCKED
INVALID
```

---

# 30.89 Research Notes

Allow structured note fields:

```text
thesis_summary
key_risks
catalysts
invalidation_conditions
```

---

# 30.90 Machine-Generated Summary

Can generate readable research summary from structured features.

Important:

```text
summary must be grounded in actual engine outputs
```

No unsupported narrative.

---

# 30.91 Decision Snapshot

Recommended record:

```text
date
instrument_key
decision_version

research_decision
portfolio_action

decision_score
risk_adjusted_decision_score

expected_return
decision_horizon

alpha_score
alpha_percentile

confidence_score

risk_score
liquidity_score

trend_state
momentum_state

quality_factor
value_factor
growth_factor

news_score
flow_score
derivatives_score

market_regime

ml_expected_return
ml_percentile
ml_confidence

entry_suitability_score
timing_score

thesis_strength_score
thesis_conflict_score

decision_freshness

quality_status
```

---

# 30.92 Decision Driver Record

```text
date
instrument_key

driver_name
driver_family

raw_value
normalized_value

direction
weight
contribution

reason_code
```

---

# 30.93 Decision Risk Record

```text
date
instrument_key

risk_type
risk_score
severity

blocking_flag

description
```

---

# 30.94 Decision Transition Record

```text
instrument_key

previous_decision
new_decision

transition_timestamp

trigger
reason_codes
```

---

# 30.95 Decision Audit Record

Store:

```text
feature_snapshot_version
alpha_model_version
confidence_model_version
regime_model_version
ml_model_version
decision_model_version
```

---

# 30.96 Final Research Card

Recommended UI structure:

```text
Company / Symbol

Decision
Score
Expected Return
Horizon
Confidence

Why Positive
Why Negative

Trend
Momentum
Quality
Value
News
Flow
Derivatives
ML

Risk
Liquidity
Market Regime

Key Catalyst
Key Risk
Invalidation Condition
```

---

# 30.97 Compact Decision Output

Possible:

```text
RELIANCE
BUY
Score: 82
Confidence: 78
21D Expected Alpha: +4.6%

Drivers:
+ Strong momentum
+ High quality
+ Positive flow

Risks:
- Expensive valuation
- Elevated volatility
```

Values are illustrative only.

---

# 30.98 Decision Ranking

Across universe:

```text
decision_rank
decision_percentile
```

---

# 30.99 Top Research Ideas

Possible output:

```text
Top 10 Strong Buy candidates
```

subject to filters.

---

# 30.100 Avoid List

Possible:

```text
highest-risk / negative-alpha names
```

---

# 30.101 Watch List

Candidates that need one more confirmation.

---

# 30.102 Decision Breadth

Track:

```text
strong_buy_count
buy_count
watch_count
sell_count
avoid_count
```

This gives system-wide market opportunity context.

---

# 30.103 Decision Dispersion

Measure spread of decision scores.

High dispersion can indicate stronger stock-selection opportunity.

---

# 30.104 Sector Decision Breadth

For each sector:

```text
buy_count
sell_count
average_decision_score
```

---

# 30.105 Decision Regime

Possible:

```text
OPPORTUNITY_RICH
NORMAL
LOW_OPPORTUNITY
RISK_DOMINATED
```

across the research universe.

---

# 30.106 Decision Calibration

Evaluate whether:

```text
higher decision scores
```

produce higher subsequent returns.

---

# 30.107 Decision Quantile Test

Split:

```text
top decile
...
bottom decile
```

and measure future performance.

---

# 30.108 Decision Hit Rate

Track by state:

```text
STRONG_BUY
BUY
WATCH
SELL
```

---

# 30.109 Decision IC

For continuous decision score:

```text
Rank IC
```

vs future returns.

---

# 30.110 Decision Turnover

Track state changes and rank turnover.

---

# 30.111 Decision Stability

Measure:

```text
decision_state persistence
score autocorrelation
```

---

# 30.112 Decision Cost Awareness

Evaluate:

```text
gross future alpha
net future alpha after estimated trading cost
```

---

# 30.113 Portfolio Actionability

A decision is actionable only if:

```text
trading eligible
risk valid
liquidity valid
portfolio room exists
```

---

# 30.114 Candidate vs Executable

Store:

```text
research_candidate = true
```

and separately:

```text
execution_candidate = true/false
```

---

# 30.115 Human Review State

Possible:

```text
AUTO_APPROVED_RESEARCH
REVIEW_REQUIRED
BLOCKED
```

This is particularly useful for:

```text
major events
low-confidence data
unusual model disagreement
```

---

# 30.116 Research Approval

The system may flag a candidate as:

```text
RESEARCH_APPROVED
```

without automatically trading it.

---

# 30.117 Live Trading Separation

The Final Research Decision Layer should not directly bypass:

```text
Portfolio Construction
Risk Controls
Execution
```

Even a STRONG_BUY must still pass those layers.

---

# 30.118 Decision Model Types

Possible:

```text
RULE_BASED
SCORE_BASED
ENSEMBLE
ML_ASSISTED
```

Recommended V1:

```text
SCORE_BASED + explicit gates
```

---

# 30.119 Rule-Based Decision

Simple and explainable.

Example:

```text
alpha percentile
confidence
risk
liquidity
```

---

# 30.120 Score-Based Decision

Combine normalized inputs.

Recommended for V1.

---

# 30.121 ML-Assisted Decision

ML can assist but should not fully obscure reasoning.

---

# 30.122 Decision Model Registry

Recommended:

```text
decision_model_name
decision_model_version

component_names
component_weights

gate_rules
state_thresholds

hysteresis_rules

active
```

---

# 30.123 Decision Model Versioning

Any change to:

```text
weights
thresholds
gates
reason logic
```

requires version change.

---

# 30.124 Initial Production V1

Recommended V1 process:

```text
1. Start from final alpha score.
2. Apply confidence scaling.
3. Apply hard data/tradability/liquidity gates.
4. Apply risk penalty.
5. Apply regime adjustment.
6. Add controlled fundamental/news/flow/ML confirmations.
7. Calculate decision score.
8. Map score to decision state with hysteresis.
9. Generate reason codes.
10. Produce research decision and separate portfolio action.
```

---

# 30.125 Initial V1 Decision Inputs

Recommended:

```text
final_alpha_percentile
confidence_score

risk_score
liquidity_score

trend_factor
momentum_factor
quality_factor
value_factor

news_factor_score
institutional_flow_score

market_regime
market_stress_score

ml_percentile
ml_confidence
```

---

# 30.126 Initial V1 Decision States

Recommended:

```text
STRONG_BUY
BUY
WATCH
HOLD
REDUCE
SELL
AVOID
```

---

# 30.127 Initial V1 Gates

Recommended hard gates:

```text
data quality valid
research eligible
trading eligible for actionable decisions
minimum liquidity
no critical risk block
```

---

# 30.128 Initial V1 Explainability

Every decision must display at least:

```text
Top 3 positive drivers
Top 3 risks / negative drivers
Expected horizon
Confidence
Decision score
```

---

# 30.129 Processing Flow

Recommended:

```text
POINT-IN-TIME SECURITY SNAPSHOT
        ↓
FINAL ALPHA
        ↓
CONFIDENCE
        ↓
DATA / TRADABILITY GATES
        ↓
RISK / LIQUIDITY GATES
        ↓
REGIME CONTEXT
        ↓
FUNDAMENTAL / VALUATION CONTEXT
        ↓
NEWS / FLOW / DERIVATIVES
        ↓
ML FORECAST
        ↓
DECISION SCORE
        ↓
HYSTERESIS / STATE MAPPING
        ↓
RESEARCH DECISION
        ↓
PORTFOLIO CONTEXT
        ↓
PORTFOLIO ACTION
        ↓
EXPLANATION / REASON CODES
        ↓
AUDIT SNAPSHOT
```

---

# 30.130 Point-in-Time Rule

At date/time T, decision can only use:

```text
features known by T
alpha known by T
confidence known by T
regime known by T
ML model valid at T
portfolio state known at T
```

No future outcomes.

---

# 30.131 No Future Performance in Decision

Fields such as:

```text
forward_return
future_drawdown
future_event_reaction
```

are labels only.

Never feed them into live decisions.

---

# 30.132 Historical Decision Replay

System should reproduce:

```text
what decision would have been generated on date T
```

using historical model versions and point-in-time features.

---

# 30.133 Retrospective Decision Analysis

If today's model is applied to old data, label:

```text
RETROSPECTIVE_RESEARCH
```

not historical production state.

---

# 30.134 Decision Backtesting

Evaluate:

```text
decision score deciles
decision state returns
turnover
cost-adjusted returns
drawdown
```

---

# 30.135 Decision Performance by Regime

Track by:

```text
bull
bear
high vol
low vol
```

---

# 30.136 Decision Performance by Sector

Track.

---

# 30.137 Decision Performance by Market Cap

Track.

---

# 30.138 Decision Performance by Confidence

Track.

---

# 30.139 Decision Calibration Table

Example:

```text
Score 80–100 → realized median return
Score 60–80  → realized median return
...
```

---

# 30.140 State Calibration

Check:

```text
STRONG_BUY > BUY > WATCH > SELL
```

in realized forward-return ordering.

---

# 30.141 Decision Monotonicity

Store:

```text
decision_monotonicity_score
```

---

# 30.142 Decision Stability Metric

Possible:

```text
average days in state
state turnover
```

---

# 30.143 Decision Drift

Track if same model begins producing very different state distribution.

---

# 30.144 Decision Health Status

Possible:

```text
HEALTHY
WATCH
DEGRADED
CRITICAL
```

---

# 30.145 Decision Model Monitoring

Track:

```text
Rank IC
state hit rate
state return spread
turnover
calibration
```

---

# 30.146 Model Degradation Handling

If decision model degrades:

```text
reduce automation confidence
```

or return to simpler baseline.

---

# 30.147 Champion / Challenger Decisions

Later compare:

```text
decision_v1
decision_v2
```

without changing production immediately.

---

# 30.148 Decision Governance

Production changes should require:

```text
version
research validation
backtest
approval record
```

---

# 30.149 Auditability

Every decision should trace to:

```text
raw data
feature values
engine outputs
model versions
thresholds
reason codes
```

---

# 30.150 Full Decision Record

Recommended:

```text
decision_id

as_of_timestamp
instrument_key

decision_model_name
decision_model_version


# RESEARCH DECISION

research_decision
decision_score
decision_percentile

decision_horizon

expected_return
expected_excess_return


# SIGNAL

alpha_score
alpha_percentile
signal_strength


# CONFIDENCE

confidence_score
confidence_bucket


# RISK / LIQUIDITY

risk_score
liquidity_score

trading_eligible


# CONTEXT

trend_state
momentum_state

quality_factor
value_factor
growth_factor

news_factor_score
institutional_flow_score
derivatives_score

market_regime
market_stress_score


# ML

ml_expected_return
ml_percentile
ml_confidence
ml_model_version


# TIMING

entry_suitability_score
timing_score
decision_freshness


# PORTFOLIO

current_weight
target_weight
portfolio_action


# EXPLAINABILITY

top_positive_drivers
top_negative_drivers
reason_codes

thesis_summary
key_risks
invalidation_conditions


# QUALITY

decision_quality_status
```

---

# 30.151 Initial Production Database Outputs

Recommended logical tables:

```text
research_decision_daily
research_decision_drivers
research_decision_risks
research_decision_transitions
research_decision_model_registry
```

---

# 30.152 UI Output

Recommended research page sections:

```text
Decision Summary
Signal Strength
Confidence
Expected Return
Risk
Liquidity
Fundamental
Valuation
Technical
News / Events
Institutional Flow
Derivatives
ML Forecast
Market Regime
Drivers
Risks
Invalidation
```

---

# 30.153 Decision Color Semantics

UI colors should use existing Open Analytics design system.

Do not embed model meaning only in color.

Always display text labels.

---

# 30.154 Final Decision Is Not Execution

Important architecture:

```text
Final Research Decision
        ↓
Portfolio Construction
        ↓
Position Sizing / Risk
        ↓
Execution
```

The research layer can recommend:

```text
STRONG_BUY
```

while the portfolio layer may still choose:

```text
NO_ACTION
```

due to constraints.

---

# 30.155 Explainable No-Action

Example:

```text
Research Decision: BUY
Portfolio Action: NO_ACTION
Reason: Sector exposure limit reached
```

---

# 30.156 Explainable Reduce

Example:

```text
Research Decision: HOLD
Portfolio Action: TRIM
Reason: Position exceeds risk target after volatility increase
```

---

# 30.157 Decision vs Recommendation Language

For research UI, prefer precise states such as:

```text
Research Decision
Signal State
Portfolio Action
```

rather than implying guaranteed outcomes.

---

# 30.158 Important Quant Rules

## Rule 1 — Final Decision Is a Synthesis Layer

Do not rebuild raw indicators here.

## Rule 2 — Alpha and Confidence Are Separate

A strong alpha with weak confidence should not be treated as a high-conviction idea.

## Rule 3 — Hard Risk / Liquidity Gates Override Score

Actionability matters.

## Rule 4 — Research Decision and Portfolio Action Are Different

Portfolio constraints can block attractive ideas.

## Rule 5 — Decision Must Be Horizon-Specific

Do not mix short-term and long-term theses.

## Rule 6 — ML Is One Input, Not the Final Authority

Keep ML bounded and monitored.

## Rule 7 — Explainability Is Mandatory

Every state must show supporting and opposing drivers.

## Rule 8 — Use Hysteresis

Avoid noisy state switching.

## Rule 9 — Historical Decisions Must Be Reproducible

Use point-in-time features and historical model versions.

## Rule 10 — Never Use Future Returns as Decision Inputs

They are evaluation labels only.

## Rule 11 — Decision Calibration Must Be Tested

Higher scores should lead to better realized outcomes.

## Rule 12 — Final Decision Does Not Bypass Risk or Execution

All downstream controls still apply.

---

# 30.159 Completion Criteria

Step 30 is complete when Open Analytics can answer:

1. What is the current research decision for a stock?
2. What is the continuous decision score?
3. What is the expected return horizon?
4. What is the expected return?
5. What is confidence?
6. What are the top positive drivers?
7. What are the top risks?
8. Is the opportunity actionable?
9. Is liquidity sufficient?
10. Is there a hard risk block?
11. Does market regime support the thesis?
12. Do fundamentals support it?
13. Is valuation attractive or expensive?
14. Do trend and momentum support it?
15. Is news/event flow supportive or risky?
16. Are institutions supporting the move?
17. Are derivatives confirming or warning?
18. Does the ML forecast agree?
19. Is the idea suitable for entry now or only for watchlist?
20. What invalidates the thesis?
21. What changed since the prior decision?
22. What is the separate portfolio action?
23. Why might a BUY research decision still result in NO_ACTION?
24. Can the exact decision be reproduced historically?
25. Does decision score monotonically relate to future returns?
26. Is the decision model healthy and stable?

---

# 30.160 Complete Open Analytics Quant Pipeline

With Step 30 complete, the complete research pipeline becomes:

```text
1. Universe Definition
        ↓
2. Data Quality & Validation
        ↓
3. Corporate Action Adjustment
        ↓
4. Returns Engine
        ↓
5. Risk Engine
        ↓
6. Liquidity & Tradability
        ↓
7. Trend Engine
        ↓
8. Momentum Engine
        ↓
9. Volume & Participation
        ↓
10. Cross-Sectional Ranking
        ↓
11. Fundamental Engine
        ↓
12. Valuation Engine
        ↓
13. Factor Engine
        ↓
14. News & Event Engine
        ↓
15. Institutional Flow Engine
        ↓
16. Derivatives Engine
        ↓
17. Market Breadth Engine
        ↓
18. Market Regime Engine
        ↓
19. Alpha / Signal Engine
        ↓
20. Confidence Engine
        ↓
21. Portfolio Construction
        ↓
22. Position Sizing & Risk Controls
        ↓
23. Execution & Transaction Cost
        ↓
24. Backtesting
        ↓
25. Performance Analytics
        ↓
26. Attribution
        ↓
27. ML Dataset Engine
        ↓
28. ML / Forecasting
        ↓
29. Stock Search / Screener
        ↓
30. Final Research Decision Layer
```

---

# 30.161 Final System Architecture

The platform can now be separated into major layers:

## Data Layer

```text
Security Master
OHLCV
Fundamentals
News
Corporate Actions
Flows
Derivatives
Reference Data
```

## Feature Layer

```text
Returns
Risk
Liquidity
Trend
Momentum
Volume
Fundamentals
Valuation
Factors
News Features
Flow Features
Derivatives Features
Breadth
Regime
```

## Intelligence Layer

```text
Alpha
Confidence
ML Forecasting
Final Research Decision
```

## Portfolio Layer

```text
Portfolio Construction
Position Sizing
Risk Controls
Execution
```

## Research Validation Layer

```text
Backtesting
Performance Analytics
Attribution
ML Dataset
```

## Discovery Layer

```text
Stock Search
Screener
Watchlists
```

---

# 30.162 Final Output of the Entire System

For each security, Open Analytics should ultimately be able to produce:

```text
Security Identity

Current Price

Trend
Momentum
Volume Participation

Returns
Risk
Liquidity

Fundamental Quality
Growth
Valuation

Factor Scores

News / Event State
Institutional Flow
Derivatives State

Market Breadth Context
Market Regime

Alpha Score
Expected Return

Confidence
Forecast Uncertainty

ML Forecast

Final Research Decision
Decision Score
Decision Horizon

Top Positive Drivers
Top Negative Drivers

Key Risks
Catalysts
Invalidation Conditions

Portfolio Action

Position Size

Execution Plan

Historical Backtest Evidence

Performance / Attribution Evidence
```

This is the full end-to-end quant research and decision architecture for Open Analytics.

---

# Step 30 Final Output

The Final Research Decision Layer transforms:

```text
Alpha
+
Confidence
+
Risk
+
Liquidity
+
Fundamentals
+
Valuation
+
Trend
+
Momentum
+
News
+
Institutional Flow
+
Derivatives
+
Market Regime
+
ML Forecasts
+
Portfolio Context
```

into:

```text
Final Research Decision
Decision Score
Decision Horizon
Expected Return
Decision Confidence
Entry / Hold / Exit Suitability
Research Decision
Portfolio Action
Positive Drivers
Negative Drivers
Key Risks
Catalysts
Invalidation Conditions
Decision Transitions
Decision Audit Trail
```

This becomes the final research-intelligence layer for Open Analytics.
