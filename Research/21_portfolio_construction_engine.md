# Open Analytics — Step 21: Portfolio Construction Engine

## Purpose

The **Portfolio Construction Engine** converts stock-level alpha, confidence, risk, liquidity, and regime information into an investable portfolio.

The engine should answer:

- Which stocks should actually enter the portfolio?
- What weight should each stock receive?
- How many positions should be held?
- How concentrated should the portfolio be?
- How much sector exposure is allowed?
- How much factor exposure is intentional versus accidental?
- How should risk be distributed?
- How much turnover is acceptable?
- How much capital can realistically be deployed?
- How should confidence modify target weights?
- How should the portfolio change in different market regimes?
- How should constraints be handled when they conflict?
- What is the expected portfolio return and risk?
- What is the portfolio’s expected alpha after transaction costs?
- Is the portfolio diversified enough?
- How should the next rebalance differ from the current portfolio?

The output feeds directly into:

- Position Sizing
- Risk Controls
- Execution
- Backtesting
- Performance Attribution
- Live Portfolio Management

---

# 21.1 Core Principle

Portfolio construction is not:

```text
buy top 10 stocks equally
```

unless that is intentionally chosen as a simple benchmark.

Professional portfolio construction balances:

```text
Expected Alpha
Confidence
Risk
Correlation
Diversification
Liquidity
Turnover
Transaction Costs
Capacity
Constraints
Market Regime
```

---

# 21.2 Required Inputs

From Step 19 — Alpha / Signal Engine:

```text
final_alpha_score
expected_return
alpha_percentile
signal_direction
```

From Step 20 — Confidence Engine:

```text
confidence_score
confidence_adjusted_alpha
```

From Step 5 — Risk Engine:

```text
volatility
beta
covariance
correlation
drawdown
tail risk
```

From Step 6 — Liquidity Engine:

```text
ADV
spread
market impact
position_capacity
tradability
```

From Step 18 — Market Regime:

```text
regime_label
market_stress_score
risk_budget_multiplier
```

From Step 13 — Factors:

```text
factor exposures
```

From current portfolio:

```text
current_weight
current_position
cost_basis
```

---

# 21.3 Portfolio Modes

Support multiple portfolio styles:

```text
LONG_ONLY
LONG_SHORT
MARKET_NEUTRAL
BENCHMARK_AWARE
SECTOR_NEUTRAL
FACTOR_NEUTRAL
RISK_PARITY
MINIMUM_VARIANCE
MAX_SHARPE
MAX_ALPHA
```

Each should be explicit.

---

# 21.4 Simple Ranking Portfolio

Baseline research portfolio:

```text
select top N alpha-ranked stocks
```

Then:

```text
equal weight
```

This is useful as a simple benchmark.

Do not skip this baseline before using optimization.

---

# 21.5 Equal Weight Portfolio

For N selected stocks:

```text
weight_i = 1 / N
```

Advantages:

```text
simple
robust
low model dependence
```

Useful as baseline.

---

# 21.6 Alpha-Weighted Portfolio

Possible:

```text
weight_i ∝ positive_alpha_i
```

Normalize:

```text
sum(weights) = 1
```

---

# 21.7 Confidence-Weighted Portfolio

Possible:

```text
weight_i ∝ alpha_i × confidence_i
```

Keep raw alpha and confidence separate in diagnostics.

---

# 21.8 Risk-Adjusted Alpha Weighting

Possible:

```text
score_i =
expected_alpha_i / expected_volatility_i
```

Then allocate proportionally.

---

# 21.9 Inverse Volatility Weighting

```text
weight_i ∝ 1 / volatility_i
```

Useful as a simple risk-aware baseline.

---

# 21.10 Risk Parity

Allocate so each position contributes approximately equal portfolio risk.

Concept:

```text
risk_contribution_i ≈ equal
```

Requires covariance matrix.

---

# 21.11 Minimum Variance Portfolio

Optimization:

```text
minimize portfolio variance
```

subject to constraints.

Useful as defensive benchmark.

---

# 21.12 Maximum Sharpe Portfolio

Conceptually:

```text
maximize
(expected_portfolio_return - risk_free_rate)
/
portfolio_volatility
```

Very sensitive to expected-return estimates.

Use robust constraints.

---

# 21.13 Maximum Alpha Portfolio

Objective:

```text
maximize expected alpha
```

subject to:

```text
risk
liquidity
sector
turnover
position limits
```

---

# 21.14 Mean-Variance Optimization

Classic:

```text
maximize:
alpha' w
-
lambda × w'Σw
```

where:

```text
w = portfolio weights
Σ = covariance matrix
lambda = risk aversion
```

---

# 21.15 Alpha-to-Risk Tradeoff

The optimizer should balance:

```text
expected return
vs
portfolio variance
```

Store:

```text
risk_aversion_parameter
```

as configuration.

---

# 21.16 Long-Only Constraint

```text
w_i >= 0
```

---

# 21.17 Long-Short Constraint

Allow:

```text
w_i < 0
```

with explicit gross/net limits.

---

# 21.18 Gross Exposure

```text
gross_exposure =
sum(abs(weights))
```

---

# 21.19 Net Exposure

```text
net_exposure =
sum(weights)
```

---

# 21.20 Gross Exposure Limit

Example configurable constraint:

```text
gross_exposure <= G
```

---

# 21.21 Net Exposure Target

Examples:

```text
long-only = 1.0

market-neutral = 0

long-short directional = configurable
```

---

# 21.22 Maximum Position Weight

Constraint:

```text
w_i <= max_position_weight
```

This prevents excessive concentration.

---

# 21.23 Minimum Position Weight

Optional:

```text
if selected:
    w_i >= minimum_position_weight
```

Avoid tiny uneconomic positions.

---

# 21.24 Maximum Number of Positions

Possible:

```text
max_positions
```

---

# 21.25 Minimum Number of Positions

Possible:

```text
min_positions
```

Supports diversification.

---

# 21.26 Concentration Metrics

Track:

```text
top_1_weight
top_5_weight
top_10_weight
```

---

# 21.27 Herfindahl Concentration Index

```text
HHI =
sum(weight_i^2)
```

Higher = more concentrated.

---

# 21.28 Effective Number of Positions

```text
effective_positions =
1 / sum(weight_i^2)
```

Useful portfolio diversification measure.

---

# 21.29 Sector Exposure

Calculate:

```text
sector_weight
```

for each sector.

---

# 21.30 Sector Weight Limits

Possible:

```text
sector_weight <= max_sector_weight
```

or benchmark-relative:

```text
abs(portfolio_sector_weight - benchmark_sector_weight)
<= sector_active_limit
```

---

# 21.31 Industry Exposure

Similarly:

```text
industry_weight
```

with limits if necessary.

---

# 21.32 Benchmark-Relative Sector Exposure

For benchmark-aware portfolios:

```text
active_sector_weight =
portfolio_sector_weight
-
benchmark_sector_weight
```

---

# 21.33 Factor Exposure

Portfolio factor exposure:

```text
portfolio_factor_exposure =
sum(weight_i × factor_exposure_i)
```

Track:

```text
Momentum
Value
Quality
Size
LowVol
Beta
Liquidity
```

---

# 21.34 Factor Exposure Constraints

Possible:

```text
abs(portfolio_size_exposure) <= limit
```

or:

```text
momentum exposure >= target
```

depending on strategy.

---

# 21.35 Beta Constraint

Portfolio beta:

```text
portfolio_beta =
sum(weight_i × beta_i)
```

Possible targets:

```text
beta ≈ 1
beta ≈ 0
beta within range
```

---

# 21.36 Market-Neutral Constraint

Possible:

```text
net exposure ≈ 0
beta ≈ 0
```

These are not the same constraint.

---

# 21.37 Dollar Neutrality

```text
long_notional = short_notional
```

---

# 21.38 Beta Neutrality

```text
portfolio_beta ≈ 0
```

---

# 21.39 Sector Neutrality

For each sector:

```text
long sector exposure
≈
short sector exposure
```

or benchmark-relative neutrality.

---

# 21.40 Factor Neutrality

Possible:

```text
size exposure ≈ 0
value exposure ≈ 0
```

unless those are intentional alpha sources.

---

# 21.41 Covariance Matrix

Portfolio optimization needs:

```text
Σ
```

Possible estimators:

```text
sample covariance
EWMA covariance
shrinkage covariance
factor-model covariance
```

---

# 21.42 Shrinkage Covariance

Recommended because raw sample covariance can be unstable.

Potential methods:

```text
Ledoit-Wolf style shrinkage
```

Implementation should be validated.

---

# 21.43 Factor Risk Model

Advanced:

```text
stock returns =
factor exposures × factor returns
+
idiosyncratic residual
```

Portfolio variance:

```text
factor risk
+
specific risk
```

---

# 21.44 Portfolio Volatility

```text
portfolio_variance =
w'Σw

portfolio_volatility =
sqrt(portfolio_variance)
```

---

# 21.45 Portfolio Beta

Store:

```text
portfolio_beta
```

---

# 21.46 Portfolio Tracking Error

Benchmark-aware:

```text
active_weights =
portfolio_weights - benchmark_weights
```

Then:

```text
tracking_error =
sqrt(active_weights' Σ active_weights)
```

---

# 21.47 Active Share

```text
active_share =
0.5 × sum(abs(portfolio_weight - benchmark_weight))
```

---

# 21.48 Expected Portfolio Return

```text
expected_portfolio_return =
sum(weight_i × expected_return_i)
```

---

# 21.49 Expected Portfolio Alpha

```text
expected_portfolio_alpha =
sum(weight_i × expected_alpha_i)
```

---

# 21.50 Confidence-Adjusted Portfolio Alpha

```text
expected_conf_adj_alpha =
sum(weight_i × confidence_adjusted_alpha_i)
```

---

# 21.51 Portfolio Sharpe Forecast

```text
expected_sharpe =
expected_excess_return
/
expected_volatility
```

Treat carefully because expected return is uncertain.

---

# 21.52 Marginal Risk Contribution

For position i:

```text
MRC_i =
∂ portfolio volatility
/
∂ weight_i
```

---

# 21.53 Component Risk Contribution

```text
CRC_i =
weight_i × MRC_i
```

Store:

```text
risk_contribution_i
```

---

# 21.54 Risk Contribution Percentage

```text
risk_contribution_pct_i
```

Useful for concentration control.

---

# 21.55 Maximum Risk Contribution Constraint

Possible:

```text
risk_contribution_i <= threshold
```

---

# 21.56 Sector Risk Contribution

Aggregate risk by sector.

---

# 21.57 Factor Risk Contribution

Aggregate by factor.

---

# 21.58 Liquidity Capacity Constraint

From Step 6:

```text
position_value
<=
ADV × participation_limit × liquidation_horizon
```

---

# 21.59 ADV Position Limit

Possible:

```text
position_value <= X% of ADV
```

X must be strategy-specific.

---

# 21.60 Days-to-Liquidate Constraint

```text
days_to_liquidate <= max_days
```

---

# 21.61 Turnover

Portfolio turnover:

```text
turnover =
sum(abs(target_weight - current_weight))
```

Convention may divide by 2; choose one platform standard.

---

# 21.62 Turnover Constraint

Possible:

```text
turnover <= max_turnover
```

---

# 21.63 Turnover Penalty

Optimization objective can include:

```text
- lambda_turnover × turnover
```

---

# 21.64 Transaction Cost Penalty

Better:

```text
maximize:
expected_alpha
-
risk_penalty
-
expected_transaction_cost
```

---

# 21.65 Linear Cost Model

Simple:

```text
cost =
spread_component × traded_value
```

---

# 21.66 Nonlinear Market Impact

Possible:

```text
impact ∝ volatility × sqrt(order_size / ADV)
```

or model-specific.

Keep versioned.

---

# 21.67 Rebalance Threshold

Avoid tiny trades.

Possible:

```text
trade only if abs(target_weight-current_weight) >= threshold
```

---

# 21.68 No-Trade Band

Create:

```text
lower_target_band
upper_target_band
```

Current position remains unchanged inside the band.

This reduces turnover.

---

# 21.69 Buffer Rules

Example:

```text
enter top 10%
exit only below top 20%
```

This reduces ranking churn.

---

# 21.70 Entry Rank Threshold

Store:

```text
entry_rank_threshold
```

---

# 21.71 Exit Rank Threshold

Store:

```text
exit_rank_threshold
```

Separate entry/exit thresholds provide hysteresis.

---

# 21.72 Rebalance Frequency

Possible:

```text
DAILY
WEEKLY
MONTHLY
QUARTERLY
```

Signal refresh frequency may differ from portfolio rebalance frequency.

---

# 21.73 Event-Driven Rebalance

Possible triggers:

```text
critical risk event
suspension
major earnings surprise
large regime shift
```

---

# 21.74 Regime-Based Risk Budget

Consume Step 18.

Example:

```text
BULL_LOW_VOL
→ normal/high risk budget

BEAR_HIGH_VOL
→ reduced risk budget
```

Store:

```text
portfolio_risk_budget_multiplier
```

---

# 21.75 Regime-Based Gross Exposure

Possible:

```text
gross_exposure_target
```

varies by regime.

Must be backtested.

---

# 21.76 Cash Allocation

Long-only portfolio may hold:

```text
cash_weight
```

when:

```text
few attractive signals
high market stress
liquidity constraints
```

---

# 21.77 Minimum Cash

Possible:

```text
cash_weight >= minimum_cash
```

---

# 21.78 Maximum Cash

Possible:

```text
cash_weight <= maximum_cash
```

---

# 21.79 Benchmark Weight Constraint

For benchmark-aware mandates:

```text
portfolio_weight_i
within
benchmark_weight_i ± active_limit
```

---

# 21.80 Active Weight

```text
active_weight_i =
portfolio_weight_i - benchmark_weight_i
```

---

# 21.81 Maximum Active Weight

Constraint:

```text
abs(active_weight_i) <= max_active_weight
```

---

# 21.82 Tracking Error Target

Possible:

```text
tracking_error <= target
```

---

# 21.83 Portfolio Objective Functions

Supported objective examples:

```text
MAX_ALPHA
MAX_SHARPE
MIN_VARIANCE
MAX_DIVERSIFICATION
RISK_PARITY
MIN_TRACKING_ERROR
ALPHA_MINUS_RISK_MINUS_COST
```

---

# 21.84 Recommended Practical Objective

For Open Analytics, a robust production objective can be:

```text
maximize:
expected_alpha
-
lambda_risk × portfolio_variance
-
lambda_cost × expected_transaction_cost
-
lambda_turnover × turnover
```

subject to constraints.

---

# 21.85 Soft Constraints

Soft constraints can enter objective as penalties.

Examples:

```text
sector exposure
turnover
factor exposure
```

---

# 21.86 Hard Constraints

Examples:

```text
tradability
maximum position weight
gross exposure
minimum cash
regulatory restrictions
```

---

# 21.87 Constraint Priority

Define priority:

```text
1. Legal / tradability
2. Risk
3. Liquidity
4. Exposure
5. Alpha preference
```

If optimization is infeasible, system should report which constraints conflict.

---

# 21.88 Feasibility Check

Before optimization:

```text
check constraints are jointly feasible
```

Output:

```text
portfolio_feasible
```

---

# 21.89 Constraint Relaxation

If infeasible:

```text
do not silently break rules
```

Instead expose:

```text
constraint_violation
required_relaxation
```

---

# 21.90 Cardinality Constraint

Number of positions:

```text
N_min <= selected_positions <= N_max
```

This can make optimization harder.

---

# 21.91 Lot Size Constraint

For derivatives or discrete share portfolios:

```text
shares must be integer
lot size respected
```

---

# 21.92 Fractional Shares

If not supported:

```text
integer share quantity
```

must be used.

---

# 21.93 Capital Allocation

Convert weights into:

```text
target_position_value
```

---

# 21.94 Share Quantity

```text
target_shares =
target_position_value / price
```

Apply lot/integer rounding.

---

# 21.95 Rounding Drift

After integer rounding:

```text
actual weight
```

may differ from target.

Track:

```text
rounding_error
```

---

# 21.96 Residual Cash

After rounding:

```text
residual_cash
```

may remain.

---

# 21.97 Portfolio Diversification Score

Possible components:

```text
effective number of positions
sector concentration
factor concentration
correlation
```

Output:

```text
diversification_score
```

---

# 21.98 Correlation Concentration

Check if selected stocks are highly correlated.

Store:

```text
average_pairwise_correlation
max_pairwise_correlation
```

---

# 21.99 Cluster Exposure

Group securities by return correlation or factor exposure.

Limit excessive weight in one cluster.

---

# 21.100 Tail Risk Constraint

Potential:

```text
portfolio_CVaR <= limit
```

Advanced.

---

# 21.101 Drawdown-Aware Constraint

Possible:

```text
limit exposure to high drawdown / high tail-risk names
```

---

# 21.102 Volatility Targeting

Scale portfolio:

```text
leverage_multiplier =
target_volatility / forecast_volatility
```

subject to max leverage.

---

# 21.103 Portfolio Volatility Target

Store:

```text
target_volatility
```

---

# 21.104 Leverage Constraint

```text
gross exposure <= max_leverage
```

---

# 21.105 Margin Constraint

For derivatives:

```text
required_margin <= available_margin
```

---

# 21.106 Short Borrow Constraint

For short portfolios:

```text
borrow_available
borrow_cost
```

must be considered.

---

# 21.107 Shortability Filter

```text
short_eligible
```

---

# 21.108 Corporate Event Constraint

Potential temporary limits around:

```text
earnings
merger vote
suspension risk
```

---

# 21.109 News Risk Constraint

High event-risk names may have reduced max weight.

---

# 21.110 Confidence-Based Position Cap

Possible:

```text
max_weight_i =
base_max_weight × confidence_multiplier
```

---

# 21.111 Alpha-Based Position Cap

Possible:

```text
target position increases with alpha
```

up to max risk constraints.

---

# 21.112 Portfolio Confidence

Aggregate:

```text
portfolio_confidence =
weighted average of position confidence
```

also consider concentration.

---

# 21.113 Portfolio Alpha Dispersion

Store:

```text
alpha_dispersion_selected
```

Low dispersion may mean little differentiation between names.

---

# 21.114 Expected Cost

Estimate:

```text
commission
taxes
spread
slippage
impact
```

---

# 21.115 Expected Net Alpha

```text
expected_net_alpha =
expected_gross_alpha
-
expected_cost
```

---

# 21.116 Rebalance Benefit

Estimate:

```text
expected_alpha_gain_from_rebalance
-
transaction_cost
```

Trade only if benefit is positive beyond threshold.

---

# 21.117 Trade Suppression

Suppress marginal trades where:

```text
expected improvement < cost
```

---

# 21.118 Portfolio Buffering

Use target bands to reduce churn.

---

# 21.119 Portfolio Transition Optimization

Optimize from:

```text
current portfolio
```

to:

```text
target portfolio
```

rather than rebuilding from zero.

---

# 21.120 Current Holdings Constraint

Possible:

```text
existing holdings receive exit buffer
```

to reduce turnover.

---

# 21.121 Tax-Aware Construction

Optional later.

Potential:

```text
realized gain
holding period
tax lot
```

Keep separate from first production.

---

# 21.122 Portfolio Snapshot Record

Recommended:

```text
portfolio_id
date
portfolio_version

capital

gross_exposure
net_exposure
cash_weight

expected_return
expected_alpha
expected_net_alpha

expected_volatility
expected_sharpe
portfolio_beta
tracking_error

turnover
expected_transaction_cost

position_count
effective_position_count
diversification_score

portfolio_confidence
market_regime

optimization_status
constraint_status
```

---

# 21.123 Position Record

```text
portfolio_id
date
instrument_key

current_weight
target_weight
active_weight

target_value
target_shares

expected_alpha
confidence_score
volatility
beta

risk_contribution
risk_contribution_pct

sector
factor_exposures

liquidity_score
days_to_liquidate

trade_required
trade_direction
trade_value

position_reason
constraint_flags
```

---

# 21.124 Portfolio Exposure Record

```text
portfolio_id
date

sector_exposures
industry_exposures

factor_exposures

beta
size
momentum
value
quality
low_vol

gross_exposure
net_exposure

liquidity_exposure
```

---

# 21.125 Optimization Diagnostic Record

Store:

```text
solver_status
objective_value

expected_alpha_component
risk_penalty
cost_penalty
turnover_penalty

constraint_slacks
constraint_violations

solve_time
optimizer_version
```

---

# 21.126 Initial Production Portfolio Model

V1 should stay robust and interpretable.

Recommended:

```text
1. Select top alpha percentile names.
2. Apply tradability/liquidity filters.
3. Apply confidence minimum.
4. Cap sector exposure.
5. Cap individual position weight.
6. Weight by risk-adjusted alpha.
7. Scale to target portfolio volatility.
8. Apply turnover buffer.
```

This is safer as a first production baseline than an unconstrained complex optimizer.

---

# 21.127 Initial Production Constraints

Recommended configurable parameters:

```text
max_position_weight
max_sector_weight
min_position_count
max_position_count

minimum_liquidity_score
minimum_confidence

max_turnover
max_days_to_liquidate

target_volatility
max_gross_exposure
```

---

# 21.128 Initial Production Outputs

Recommended:

```text
selected_positions
target_weights

expected_portfolio_alpha
expected_net_alpha
expected_volatility
portfolio_beta

gross_exposure
net_exposure
cash_weight

sector_exposure
factor_exposure

turnover
expected_transaction_cost

effective_position_count
diversification_score

portfolio_confidence

optimization_status
```

---

# 21.129 Portfolio Construction Processing Flow

Recommended:

```text
FINAL ALPHA + CONFIDENCE
        ↓
TRADABILITY FILTER
        ↓
CURRENT PORTFOLIO
        ↓
EXPECTED RETURN / RISK INPUTS
        ↓
COVARIANCE MATRIX
        ↓
REGIME RISK BUDGET
        ↓
SELECTION
        ↓
POSITION WEIGHTING
        ↓
SECTOR / FACTOR CONSTRAINTS
        ↓
LIQUIDITY / CAPACITY CONSTRAINTS
        ↓
TURNOVER / COST PENALTIES
        ↓
OPTIMIZATION / TARGET WEIGHTS
        ↓
FEASIBILITY CHECK
        ↓
INTEGER / LOT ROUNDING
        ↓
FINAL PORTFOLIO
        ↓
EXPOSURE / RISK DIAGNOSTICS
```

---

# 21.130 Point-in-Time Rule

At date T, construction may only use:

```text
signals available at T
risk estimates available at T
liquidity available at T
benchmark weights known at T
current holdings as of T
regime known at T
```

No future prices or returns.

---

# 21.131 Rebalance Timing Rule

Define:

```text
signal_timestamp
portfolio_decision_timestamp
execution_timestamp
```

This prevents look-ahead bias.

---

# 21.132 Transaction Cost Point-in-Time Rule

Cost estimates should use information available before execution.

---

# 21.133 Portfolio Model Versioning

Store:

```text
portfolio_model_version
```

Any change to:

```text
objective
constraints
risk model
weighting
```

requires a version change.

---

# 21.134 Optimization Quality Status

Possible:

```text
VALID
SUBOPTIMAL
INFEASIBLE
PARTIAL_INPUTS
COVARIANCE_WARNING
LIQUIDITY_CONSTRAINED
TURNOVER_CONSTRAINED
INVALID
```

---

# 21.135 Research Diagnostics

Test:

```text
equal-weight baseline
alpha-weighted baseline
risk-adjusted baseline
optimized portfolio
```

Compare:

```text
return
Sharpe
drawdown
turnover
costs
concentration
```

---

# 21.136 Out-of-Sample Portfolio Testing

Never choose constraints only from in-sample performance.

Use:

```text
walk-forward
rolling out-of-sample
```

---

# 21.137 Sensitivity Analysis

Vary:

```text
max position
sector cap
risk aversion
turnover penalty
```

Portfolio behavior should not collapse under small parameter changes.

---

# 21.138 Constraint Stress Test

Check:

```text
high volatility
low liquidity
few eligible names
large redemptions
```

---

# 21.139 Capacity Stress Test

Test portfolio at larger capital sizes.

Track:

```text
cost increase
days to liquidate
alpha erosion
```

---

# 21.140 Important Quant Rules

## Rule 1 — Portfolio Construction Is an Optimization Problem

Alpha alone is not enough.

## Rule 2 — Use Current Portfolio State

Optimize transition, not only final target.

## Rule 3 — Risk Is Covariance, Not Just Individual Volatility

Correlation matters.

## Rule 4 — Liquidity Constraints Are Real

A theoretical portfolio may be impossible to trade.

## Rule 5 — Turnover Must Be Penalized

Frequent small changes destroy net alpha.

## Rule 6 — Sector and Factor Exposure Must Be Visible

Avoid accidental concentrated bets.

## Rule 7 — Hard and Soft Constraints Must Be Different

Do not silently violate hard limits.

## Rule 8 — Confidence Can Modify Weight, Not Replace Alpha

Keep them conceptually separate.

## Rule 9 — Regime Changes Risk Budget, Not Historical Facts

Regime should condition risk, not rewrite signals.

## Rule 10 — Simple Baselines Are Mandatory

Compare complex optimizer against equal-weight and risk-weighted baselines.

## Rule 11 — Version Every Construction Model

Backtests must remain reproducible.

## Rule 12 — Optimize Net Alpha

Gross alpha without costs is insufficient.

---

# 21.141 Completion Criteria

Step 21 is complete when Open Analytics can answer:

1. Which stocks belong in the portfolio?
2. What is each target weight?
3. Why was each stock selected?
4. What is expected portfolio alpha?
5. What is expected net alpha after costs?
6. What is expected portfolio volatility?
7. What is portfolio beta?
8. What is gross exposure?
9. What is net exposure?
10. How concentrated is the portfolio?
11. What is the effective number of positions?
12. What are sector exposures?
13. What are factor exposures?
14. What is each stock’s risk contribution?
15. Is any position too large relative to liquidity?
16. How many days would liquidation take?
17. What turnover is required?
18. What transaction cost is expected?
19. Is the portfolio within all hard constraints?
20. Is the optimization feasible?
21. How does the portfolio compare with a simple equal-weight baseline?
22. How does current market regime affect risk budget?
23. Can the exact historical target portfolio be reproduced?
24. Can target weights be converted cleanly into executable orders?

Once these are reliable, the Portfolio Construction Engine is ready to feed:

```text
Step 22 — Position Sizing & Risk Controls Engine
```

---

# Step 21 Final Output

The Portfolio Construction Engine transforms:

```text
Alpha
+
Confidence
+
Risk
+
Liquidity
+
Correlation
+
Market Regime
+
Current Holdings
```

into:

```text
Stock Selection
Target Weights
Expected Portfolio Alpha
Expected Net Alpha
Portfolio Volatility
Portfolio Beta
Gross / Net Exposure
Cash Allocation
Sector Exposure
Factor Exposure
Risk Contributions
Turnover
Transaction Cost
Liquidity Capacity
Diversification Metrics
Optimization Diagnostics
Final Target Portfolio
```

This becomes the portfolio-allocation layer for Open Analytics.
