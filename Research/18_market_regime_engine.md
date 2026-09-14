# Open Analytics — Step 18: Market Regime Engine

## Purpose

The **Market Regime Engine** classifies the current market environment so that signals, portfolio risk, factor weights, and strategy behavior can adapt to changing conditions.

The engine should answer:

- Is the market bullish, bearish, or sideways?
- Is volatility high or low?
- Is participation broad or narrow?
- Is liquidity improving or deteriorating?
- Are institutional flows supportive or hostile?
- Are derivatives confirming or contradicting the cash market?
- Is the market transitioning between regimes?
- How persistent is the current regime?
- How confident are we in the classification?
- Which factors and strategies historically perform best in this regime?
- Should portfolio risk be increased, maintained, or reduced?

Outputs feed directly into:

- Alpha / Signal Engine
- Portfolio Construction
- Position Sizing
- Risk Controls
- Dynamic Factor Weighting
- Execution
- Backtesting
- Performance Attribution
- Machine Learning

---

# 18.1 Core Principle

A market regime is not one indicator.

Open Analytics should classify regime using multiple independent dimensions:

```text
Trend
Volatility
Breadth
Liquidity
Institutional Flow
Derivatives
Correlation
Dispersion
Macro Context
```

A strong regime model should avoid:

```text
NIFTY above SMA200 = bull market
```

as the only rule.

---

# 18.2 Required Inputs

From Step 7 — Trend:

```text
market_trend_short
market_trend_medium
market_trend_long

market_slope
market_ma_alignment
market_trend_strength
```

From Step 5 — Risk:

```text
realized_volatility
downside_volatility
drawdown
correlation
tail risk
```

From Step 17 — Breadth:

```text
advance_pct
pct_above_sma50
pct_above_sma200
new_high_low_balance
breadth_score
breadth_regime
```

From Step 6 — Liquidity:

```text
market_liquidity_score
spread conditions
traded value
price impact
```

From Step 15 — Institutional Flow:

```text
foreign_flow_score
domestic_flow_score
institutional_flow_score
flow_regime
```

From Step 16 — Derivatives:

```text
atm_iv
iv_percentile
put_skew
futures_positioning
derivatives_risk
```

Optional macro:

```text
interest rates
yield curve
currency
crude oil
inflation
credit spreads
global market regime
```

---

# 18.3 Regime Dimensions

Recommended regime dimensions:

```text
TREND
VOLATILITY
BREADTH
LIQUIDITY
FLOW
DERIVATIVES
CORRELATION
DISPERSION
MACRO
```

Each should first be scored independently.

---

# 18.4 Trend Regime

Possible states:

```text
STRONG_UPTREND
UPTREND
SIDEWAYS
DOWNTREND
STRONG_DOWNTREND
```

Inputs may include:

```text
price vs SMA50
price vs SMA200
SMA slopes
regression slope
ADX
```

---

# 18.5 Trend Regime Score

Normalize to:

```text
-1 to +1
```

Example interpretation:

```text
+1 = strong bullish trend
0  = neutral / sideways
-1 = strong bearish trend
```

Store:

```text
trend_regime_score
```

---

# 18.6 Volatility Regime

Possible:

```text
VERY_LOW
LOW
NORMAL
HIGH
EXTREME
```

Inputs:

```text
realized volatility
implied volatility
IV percentile
volatility change
```

---

# 18.7 Volatility Regime Score

Possible scale:

```text
0 to 100
```

where:

```text
100 = extreme volatility
0 = very low volatility
```

Store:

```text
volatility_regime_score
```

---

# 18.8 Breadth Regime

Consume Step 17:

```text
VERY_STRONG
STRONG
NEUTRAL
WEAK
VERY_WEAK
```

Store:

```text
breadth_regime_score
```

---

# 18.9 Liquidity Regime

Possible states:

```text
ABUNDANT
NORMAL
TIGHT
STRESSED
```

Inputs:

```text
market traded value
spreads
price impact
liquidity score
```

---

# 18.10 Institutional Flow Regime

Possible:

```text
STRONG_ACCUMULATION
ACCUMULATION
NEUTRAL
DISTRIBUTION
STRONG_DISTRIBUTION
```

Store:

```text
flow_regime_score
```

---

# 18.11 Derivatives Regime

Possible:

```text
RISK_ON
NEUTRAL
RISK_OFF
VOLATILITY_STRESS
```

Inputs:

```text
IV
skew
OI positioning
futures basis
PCR context
```

---

# 18.12 Correlation Regime

Cross-sectional stock correlation matters.

Possible:

```text
LOW_CORRELATION
NORMAL_CORRELATION
HIGH_CORRELATION
CRISIS_CORRELATION
```

High correlation often reduces stock-selection opportunity.

Store:

```text
correlation_regime
```

---

# 18.13 Dispersion Regime

Measure cross-sectional return dispersion.

Possible states:

```text
LOW_DISPERSION
NORMAL
HIGH_DISPERSION
```

High dispersion can create more stock-selection opportunity.

---

# 18.14 Trend + Volatility Matrix

A useful first-order market state:

```text
Uptrend + Low Vol
Uptrend + High Vol
Sideways + Low Vol
Sideways + High Vol
Downtrend + Low Vol
Downtrend + High Vol
```

Store:

```text
trend_vol_regime
```

---

# 18.15 Risk-On / Risk-Off Classification

Possible:

```text
RISK_ON
NEUTRAL
RISK_OFF
```

Potential inputs:

```text
trend
breadth
volatility
flow
derivatives
```

---

# 18.16 Market Stress Score

Possible components:

```text
volatility
drawdown
breadth weakness
liquidity stress
foreign selling
put skew
correlation spike
```

Output:

```text
market_stress_score
```

Scale:

```text
0 to 100
```

---

# 18.17 Bull Market Regime

A robust bull state may require:

```text
positive long-term trend
strong breadth
moderate volatility
healthy liquidity
supportive flows
```

Store:

```text
bull_regime_probability
```

---

# 18.18 Bear Market Regime

Possible inputs:

```text
negative long-term trend
weak breadth
high drawdown
high volatility
distribution
```

Store:

```text
bear_regime_probability
```

---

# 18.19 Sideways Regime

Possible:

```text
flat trend
low slope
mixed breadth
low/normal volatility
```

Store:

```text
sideways_regime_probability
```

---

# 18.20 Transition Regime

Markets often move through transitions.

Possible:

```text
BULL_TO_NEUTRAL
NEUTRAL_TO_BEAR
BEAR_TO_RECOVERY
RECOVERY_TO_BULL
```

Store:

```text
regime_transition_state
```

---

# 18.21 Recovery Regime

Possible:

```text
price still below long-term trend
but breadth improving
volatility falling
flow improving
```

Store:

```text
recovery_regime_flag
```

---

# 18.22 Distribution Regime

Possible:

```text
index still strong
but breadth deteriorating
institutional selling increasing
volatility rising
```

Store:

```text
distribution_regime_flag
```

---

# 18.23 Accumulation Regime

Possible:

```text
price stabilizing
breadth improving
flows improving
volatility falling
```

Store:

```text
accumulation_regime_flag
```

---

# 18.24 Regime Probability Model

Instead of only hard labels, output probabilities.

Example:

```text
bull_probability
bear_probability
sideways_probability
stress_probability
```

This is preferable for downstream portfolio decisions.

---

# 18.25 Rule-Based Regime Model

Initial version can use deterministic rules.

Example conceptual logic:

```text
if long_trend positive
and breadth strong
and vol below stress threshold:
    regime = BULL
```

Keep thresholds configurable.

---

# 18.26 Score-Based Regime Model

More robust:

```text
regime_score =
w1 * trend
+
w2 * breadth
-
w3 * volatility
+
w4 * flow
+
w5 * liquidity
```

Weights should be researched.

---

# 18.27 Machine-Learned Regime Model

Later use:

```text
HMM
clustering
Gaussian mixture
tree models
neural models
```

Possible features:

```text
trend
volatility
breadth
flow
correlation
dispersion
liquidity
derivatives
```

But interpretable rule/score model should exist first.

---

# 18.28 Hidden Markov Model

HMM can identify latent regimes.

Possible states:

```text
LOW_VOL_BULL
HIGH_VOL_BULL
LOW_VOL_BEAR
HIGH_VOL_BEAR
SIDEWAYS
```

Use only after robust feature preparation.

---

# 18.29 Clustering-Based Regimes

Possible:

```text
KMeans
Gaussian Mixture
hierarchical clustering
```

Use standardized regime features.

Clusters must then be economically interpreted.

---

# 18.30 Regime Persistence

Track:

```text
days_in_current_regime
```

Also:

```text
regime_persistence_probability
```

---

# 18.31 Regime Transition Probability

Estimate:

```text
P(next_regime | current_regime)
```

Store transition matrix.

---

# 18.32 Regime Stability Score

Possible:

```text
regime_stability_score
```

Inputs:

```text
probability concentration
persistence
feature agreement
```

---

# 18.33 Regime Confidence

Possible:

```text
regime_confidence
```

High when:

```text
trend
breadth
volatility
flow
```

all agree.

Low when signals conflict.

---

# 18.34 Feature Agreement Score

Example:

```text
bullish trend
bullish breadth
supportive flows
low stress
```

→ high agreement.

Store:

```text
regime_feature_agreement
```

---

# 18.35 Conflicted Regime

Possible when:

```text
index uptrend
breadth weak
volatility rising
foreign selling
```

Store:

```text
conflicted_regime_flag
```

---

# 18.36 Index-Specific Regime

Support:

```text
NIFTY_50
BANK_NIFTY
MIDCAP
SMALLCAP
```

Each can have separate regime.

---

# 18.37 Sector Regime

For each sector:

```text
sector_trend
sector_breadth
sector_volatility
sector_flow
```

Output:

```text
sector_regime
```

---

# 18.38 Global Regime

Optional later:

```text
US equities
global rates
USD
crude
global volatility
```

Output:

```text
global_risk_regime
```

---

# 18.39 Macro Regime

Possible states:

```text
GROWTH_UP_INFLATION_DOWN
GROWTH_UP_INFLATION_UP
GROWTH_DOWN_INFLATION_UP
GROWTH_DOWN_INFLATION_DOWN
```

This can later condition factor behavior.

---

# 18.40 Rate Regime

Possible:

```text
RATES_RISING
RATES_FALLING
RATES_STABLE
```

Store:

```text
rate_regime
```

---

# 18.41 Inflation Regime

Possible:

```text
LOW
NORMAL
HIGH
ACCELERATING
DECELERATING
```

---

# 18.42 Currency Regime

For India:

```text
INR_STRENGTHENING
INR_STABLE
INR_WEAKENING
```

Can affect sector leadership.

---

# 18.43 Crude Oil Regime

Possible:

```text
RISING
FALLING
HIGH
LOW
```

Important for India macro context.

---

# 18.44 Correlation Spike

Store:

```text
market_correlation_z
```

High correlation often indicates systemic risk.

---

# 18.45 Dispersion Score

Store:

```text
cross_sectional_dispersion
dispersion_z
```

High dispersion can support stock selection.

---

# 18.46 Factor Opportunity Regime

Possible:

```text
HIGH_STOCK_SELECTION_OPPORTUNITY
NORMAL
LOW
```

Inputs:

```text
dispersion
correlation
breadth
```

---

# 18.47 Momentum-Friendly Regime

Research output:

```text
momentum_regime_score
```

based on historical factor performance by regime.

---

# 18.48 Value-Friendly Regime

Similarly:

```text
value_regime_score
```

---

# 18.49 Quality-Friendly Regime

```text
quality_regime_score
```

---

# 18.50 Low-Vol-Friendly Regime

```text
low_vol_regime_score
```

---

# 18.51 Dynamic Factor Weighting

Later:

```text
factor weights by regime
```

Example:

```text
high stress
→ increase quality / low-vol
```

But only after robust out-of-sample validation.

---

# 18.52 Regime-Based Risk Budget

Possible:

```text
BULL_LOW_VOL
→ higher risk budget

BEAR_HIGH_VOL
→ lower risk budget
```

Output:

```text
recommended_risk_budget_multiplier
```

This must be researched and configurable.

---

# 18.53 Regime-Based Gross Exposure

Possible:

```text
gross_exposure_multiplier
```

Use in portfolio construction later.

---

# 18.54 Regime-Based Position Size

Potential:

```text
position_size_multiplier
```

Again, downstream engine decides final sizing.

---

# 18.55 Regime-Based Signal Thresholds

A signal threshold may change by regime.

Example:

```text
high-volatility bear regime
→ require stronger alpha score
```

Store:

```text
signal_threshold_multiplier
```

---

# 18.56 Regime-Based Execution

Execution can adapt to:

```text
liquidity stress
volatility regime
spread regime
```

This integration belongs later.

---

# 18.57 Regime Historical Record

Recommended:

```text
date
market_id


# DIMENSIONS

trend_regime
trend_regime_score

volatility_regime
volatility_regime_score

breadth_regime
breadth_regime_score

liquidity_regime
liquidity_regime_score

flow_regime
flow_regime_score

derivatives_regime
derivatives_regime_score

correlation_regime
dispersion_regime


# COMPOSITES

risk_on_off_state
market_stress_score

bull_probability
bear_probability
sideways_probability

regime_label
regime_confidence

regime_transition_state
days_in_current_regime

regime_quality_status
```

---

# 18.58 Initial Production Regime Labels

Recommended simple set:

```text
BULL_LOW_VOL
BULL_HIGH_VOL
SIDEWAYS_LOW_VOL
SIDEWAYS_HIGH_VOL
BEAR_LOW_VOL
BEAR_HIGH_VOL
STRESS
RECOVERY
```

This is more informative than only:

```text
BULL / BEAR
```

---

# 18.59 Initial Production Inputs

Start with:

```text
market_return_21d
market_return_63d

price_vs_sma50
price_vs_sma200

market_slope_63d

realized_volatility_21d
realized_volatility_63d

current_drawdown

breadth_score
pct_above_sma50
pct_above_sma200

institutional_flow_score

atm_iv / India VIX
put_skew if available

market_liquidity_score
```

---

# 18.60 Initial Production Outputs

Recommended:

```text
trend_regime
volatility_regime
breadth_regime
flow_regime

risk_on_off_state
market_stress_score

bull_probability
bear_probability
sideways_probability

regime_label
regime_confidence

regime_transition_state
days_in_current_regime

regime_quality_status
```

---

# 18.61 Market Regime Engine Processing Flow

Recommended:

```text
MARKET PRICE / RETURNS
        ↓
TREND REGIME
        ↓
VOLATILITY REGIME
        ↓
BREADTH REGIME
        ↓
LIQUIDITY REGIME
        ↓
INSTITUTIONAL FLOW REGIME
        ↓
DERIVATIVES REGIME
        ↓
CORRELATION / DISPERSION
        ↓
REGIME FEATURE NORMALIZATION
        ↓
RULE / SCORE MODEL
        ↓
REGIME PROBABILITIES
        ↓
FINAL REGIME LABEL
        ↓
TRANSITION / PERSISTENCE
        ↓
CONFIDENCE
        ↓
DOWNSTREAM RISK / FACTOR CONTEXT
```

---

# 18.62 Point-in-Time Rule

At date T, regime classification may only use:

```text
market data through T
breadth through T
flow data available by T
derivatives data through T
macro data released by T
```

No future macro revisions.

---

# 18.63 Macro Release Lag

Economic data may refer to prior months but be released later.

Use:

```text
release_date
```

not:

```text
reference_period
```

for model availability.

---

# 18.64 Regime Revision

If regime model changes:

```text
regime_model_version
```

must change.

Historical outputs should be reproducible.

---

# 18.65 Regime Quality Status

Possible:

```text
VALID
PARTIAL_INPUTS
CONFLICTED_SIGNALS
LOW_BREADTH_COVERAGE
MISSING_FLOW
MISSING_DERIVATIVES
STALE_MACRO
INVALID
```

---

# 18.66 Regime Backtesting

For each regime, calculate:

```text
forward market return
forward volatility
drawdown
factor performance
strategy performance
```

---

# 18.67 Regime Duration Statistics

Track:

```text
average duration
median duration
max duration
```

by regime.

---

# 18.68 Regime Transition Matrix

Example:

```text
          Next
Current   Bull  Sideways  Bear
Bull      0.85    0.12    0.03
...
```

Useful for persistence research.

---

# 18.69 Regime Forward Return Distribution

For every regime:

```text
1D return
5D return
21D return
63D return
```

---

# 18.70 Regime Drawdown Distribution

Track:

```text
forward max drawdown
```

by regime.

---

# 18.71 Factor Performance by Regime

Evaluate:

```text
Momentum
Value
Quality
Growth
Low Vol
```

inside each regime.

---

# 18.72 Signal Performance by Regime

Later:

```text
alpha model hit rate
IC
turnover
drawdown
```

by regime.

---

# 18.73 Portfolio Performance by Regime

Track:

```text
return
Sharpe
drawdown
turnover
```

by regime.

---

# 18.74 Regime Detection Lag

A regime model may identify changes only after they occur.

Measure:

```text
transition_detection_lag
```

This matters in live use.

---

# 18.75 Regime False Transition Rate

Track how often:

```text
regime changes and quickly reverts
```

Store:

```text
false_transition_rate
```

---

# 18.76 Regime Smoothing

Optional:

```text
minimum persistence days
probability smoothing
hysteresis
```

This reduces noisy regime switching.

---

# 18.77 Hysteresis

Use different thresholds for entering and exiting a regime.

Example:

```text
enter high-vol at 80th percentile
exit only below 65th percentile
```

This can reduce flip-flopping.

---

# 18.78 Regime Score Explainability

For every day expose:

```text
trend contribution
breadth contribution
volatility contribution
flow contribution
derivatives contribution
```

---

# 18.79 Regime Dashboard Output

Possible UI:

```text
Current Regime: BULL_LOW_VOL
Confidence: 84%

Trend        Strong
Breadth      Strong
Volatility   Low
Liquidity    Normal
FII Flow     Positive
Derivatives  Neutral
```

Keep detailed numeric metrics available.

---

# 18.80 Research Guardrails

Avoid tuning regime thresholds to maximize one historical strategy.

Regime definitions should remain economically meaningful and robust.

---

# 18.81 Important Quant Rules

## Rule 1 — Regime Is Multi-Dimensional

Do not use one indicator only.

## Rule 2 — Probabilities Are Better Than Hard Labels Alone

Preserve uncertainty.

## Rule 3 — Trend and Volatility Must Be Separated

Bull-high-vol and bull-low-vol are different environments.

## Rule 4 — Breadth Confirms Market Health

Narrow index strength is different from broad strength.

## Rule 5 — Flow and Derivatives Are Context Layers

Do not let one source dominate without validation.

## Rule 6 — Regime Changes Must Be Point-in-Time

No future macro or revised data.

## Rule 7 — Measure Transition Lag

A good regime model must work live, not just retrospectively.

## Rule 8 — Avoid Excessive Regime Count

Too many states make models unstable.

## Rule 9 — Keep the Model Explainable

Downstream systems should know why the regime was classified.

## Rule 10 — Version Every Regime Model

Backtests must remain reproducible.

---

# 18.82 Completion Criteria

Step 18 is complete when Open Analytics can answer:

1. What is the current market trend regime?
2. What is the current volatility regime?
3. What is the current breadth regime?
4. What is the current liquidity regime?
5. What is the institutional-flow regime?
6. What is the derivatives regime?
7. Is the market risk-on or risk-off?
8. What is the market stress score?
9. What is the probability of bull, bear, and sideways regimes?
10. Is the market in a transition or stable state?
11. How long has the current regime persisted?
12. How confident is the regime classification?
13. Which inputs disagree with the dominant regime?
14. Is stock-selection opportunity high or low?
15. Which factors historically work best in this regime?
16. Should portfolio risk budget be increased or reduced?
17. Was every input available at the historical timestamp?
18. Can the exact historical regime classification be reproduced?

Once these are reliable, the Market Regime Engine is ready to feed:

```text
Step 19 — Alpha / Signal Engine
```

---

# Step 18 Final Output

The Market Regime Engine transforms:

```text
Trend
+
Volatility
+
Breadth
+
Liquidity
+
Institutional Flow
+
Derivatives
+
Macro Context
```

into:

```text
Trend Regime
Volatility Regime
Breadth Regime
Liquidity Regime
Flow Regime
Derivatives Regime
Correlation Regime
Dispersion Regime
Risk-On / Risk-Off State
Market Stress Score
Bull/Bear/Sideways Probabilities
Regime Transitions
Regime Persistence
Regime Confidence
Factor/Strategy Context
```

This becomes the environment-awareness layer for Open Analytics.
