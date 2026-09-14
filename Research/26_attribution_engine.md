# Open Analytics — Step 26: Attribution Engine

## Purpose

The **Attribution Engine** explains where portfolio returns, alpha, risk, and drawdowns came from.

Step 25 answers:

```text
How well did the strategy perform?
```

Step 26 answers:

```text
Why did it perform that way?
```

The engine should answer:

- Which stocks contributed most to return?
- Which sectors helped or hurt?
- Was performance driven by stock selection or sector allocation?
- Was excess return genuine alpha or market beta?
- Which factors drove performance?
- Which signals generated profitable trades?
- Which signals generated losses?
- How much performance was lost to transaction costs?
- How much came from market timing, regime scaling, or position sizing?
- Which positions caused drawdowns?
- Which risk-control decisions helped or hurt?
- Did performance come from a few concentrated bets?
- How did performance drivers change across regimes?
- Did live performance differ because signals weakened or execution got worse?

Outputs feed directly into:

- Strategy review
- Model diagnostics
- Portfolio governance
- Factor research
- Risk review
- Capital allocation
- Production monitoring
- Research reporting

---

# 26.1 Core Principle

Performance attribution should decompose:

```text
Portfolio Return
```

into understandable sources.

Possible decomposition dimensions:

```text
Security
Sector
Industry
Factor
Signal
Strategy
Risk Control
Execution
Regime
Benchmark
```

The exact attribution method depends on the portfolio type.

---

# 26.2 Required Inputs

Minimum:

```text
portfolio weights
security returns
portfolio return
```

Preferred:

```text
benchmark weights
benchmark constituent returns

sector classifications
factor exposures
factor returns

signal scores
position sizing changes
risk-control actions

transaction costs
execution slippage

market regime
```

Optional:

```text
trade-level expected alpha
forecast confidence
model ensemble outputs
```

---

# 26.3 Security-Level Contribution

For stock i:

```text
security_contribution_i =
weight_i × return_i
```

For daily attribution use beginning-of-period weight convention.

Store:

```text
security_return_contribution
```

---

# 26.4 Contribution in Basis Points

```text
contribution_bps =
security_contribution × 10000
```

Useful for reporting.

---

# 26.5 Top Contributors

Store:

```text
top_positive_contributors
```

---

# 26.6 Top Detractors

Store:

```text
top_negative_contributors
```

---

# 26.7 Cumulative Security Contribution

Over a reporting period:

```text
sum daily contribution
```

or geometrically linked methodology.

Use a consistent attribution-linking method.

---

# 26.8 Sector Contribution

Aggregate security contributions by:

```text
sector
```

Store:

```text
sector_return_contribution
```

---

# 26.9 Industry Contribution

Likewise:

```text
industry_return_contribution
```

---

# 26.10 Market-Cap Bucket Contribution

Possible:

```text
large_cap_contribution
mid_cap_contribution
small_cap_contribution
```

---

# 26.11 Long Contribution

For long-short portfolios:

```text
long_book_contribution
```

---

# 26.12 Short Contribution

Store:

```text
short_book_contribution
```

---

# 26.13 Gross vs Net Contribution

Separate:

```text
gross_security_contribution
net_security_contribution
```

after costs.

---

# 26.14 Benchmark Relative Attribution

For benchmark-aware portfolios, compare:

```text
portfolio weight
benchmark weight
portfolio constituent return
benchmark constituent return
```

---

# 26.15 Brinson-Style Attribution

Possible components:

```text
Allocation Effect
Selection Effect
Interaction Effect
```

Useful for sector-based benchmark portfolios.

---

# 26.16 Allocation Effect

Conceptually:

```text
(portfolio_sector_weight - benchmark_sector_weight)
×
(benchmark_sector_return - benchmark_total_return)
```

Store:

```text
allocation_effect
```

---

# 26.17 Selection Effect

Conceptually:

```text
portfolio_sector_weight
×
(portfolio_sector_return - benchmark_sector_return)
```

Store:

```text
selection_effect
```

---

# 26.18 Interaction Effect

Captures joint effect of:

```text
over/underweight
and
security selection
```

Store:

```text
interaction_effect
```

---

# 26.19 Active Return Attribution

Total active return should reconcile approximately to:

```text
allocation
+
selection
+
interaction
```

subject to linking methodology.

---

# 26.20 Alpha vs Beta Attribution

Decompose return into:

```text
market beta component
residual alpha component
```

Conceptually:

```text
portfolio_return =
beta × market_return
+
alpha/residual
```

---

# 26.21 Market Beta Contribution

Store:

```text
market_beta_contribution
```

---

# 26.22 Residual Alpha Contribution

Store:

```text
residual_alpha_contribution
```

---

# 26.23 Factor Attribution

Use factor model:

```text
portfolio return =
factor exposures × factor returns
+
specific return
```

Potential factors:

```text
Momentum
Value
Quality
Size
Low Vol
Market
Sector
Liquidity
```

---

# 26.24 Factor Exposure Contribution

For factor f:

```text
factor_contribution_f =
portfolio_factor_exposure_f
×
factor_return_f
```

---

# 26.25 Specific Return Contribution

Residual after factor explanation:

```text
specific_return_contribution
```

This can approximate stock-selection alpha.

---

# 26.26 Factor Attribution by Period

Store:

```text
daily
monthly
quarterly
annual
```

factor contributions.

---

# 26.27 Momentum Contribution

Store:

```text
momentum_factor_contribution
```

---

# 26.28 Value Contribution

Store.

---

# 26.29 Quality Contribution

Store.

---

# 26.30 Size Contribution

Store.

---

# 26.31 Low-Vol Contribution

Store.

---

# 26.32 Liquidity Contribution

Store where factor model supports it.

---

# 26.33 Sector Factor Contribution

Separate:

```text
sector_effect
```

from style factors when possible.

---

# 26.34 Signal Attribution

The portfolio may combine multiple alpha sources.

Examples:

```text
momentum signal
value signal
news signal
flow signal
derivatives signal
```

Estimate:

```text
signal_return_contribution
```

---

# 26.35 Signal Contribution from Portfolio Weights

If weight construction tracks component contributions:

```text
signal_component_weight
```

then estimate contribution from resulting positions.

---

# 26.36 Signal-Level PnL

For trade-based signals, tag each trade with:

```text
signal_source
```

Then aggregate:

```text
PnL by signal_source
```

---

# 26.37 Multi-Signal Trade Attribution

If one trade has multiple drivers, allocate by:

```text
component contribution weights
```

or:

```text
Shapley-style attribution
```

later.

---

# 26.38 Signal Strength Attribution

Group trades by:

```text
alpha decile
```

and calculate return contribution.

---

# 26.39 Confidence Attribution

Group by:

```text
confidence bucket
```

to test whether high-confidence signals contribute more.

---

# 26.40 News Contribution

Aggregate returns of trades where:

```text
news/event component materially influenced signal
```

Store:

```text
news_signal_contribution
```

---

# 26.41 Institutional Flow Contribution

Store:

```text
flow_signal_contribution
```

---

# 26.42 Derivatives Contribution

Store.

---

# 26.43 Fundamental Contribution

Store.

---

# 26.44 Technical Contribution

Possible combined:

```text
trend + momentum + participation
```

Store.

---

# 26.45 Portfolio Construction Attribution

Compare actual portfolio with simple baseline.

Example:

```text
optimized portfolio return
-
equal-weight selected basket return
```

This isolates:

```text
portfolio construction value-add
```

---

# 26.46 Weighting Value-Add

Store:

```text
weighting_alpha
```

---

# 26.47 Risk Model Value-Add

Compare optimized portfolio with/without risk adjustment.

Store:

```text
risk_model_value_add
```

---

# 26.48 Confidence Weighting Value-Add

Compare:

```text
confidence-weighted
vs
non-confidence-weighted
```

---

# 26.49 Regime Overlay Attribution

Compare portfolio with:

```text
regime scaling
```

versus identical portfolio without regime scaling.

Output:

```text
regime_overlay_contribution
```

---

# 26.50 Risk-Control Attribution

Measure effect of:

```text
position caps
drawdown de-risking
volatility scaling
stop losses
```

---

# 26.51 Stop-Loss Attribution

Compare realized exit with hypothetical no-stop path carefully.

This is counterfactual and must be labelled as such.

Store:

```text
stop_loss_value_add
```

---

# 26.52 Drawdown-Control Attribution

Store:

```text
drawdown_control_value_add
```

---

# 26.53 Volatility Scaling Attribution

Store.

---

# 26.54 Position Cap Attribution

Store.

---

# 26.55 Liquidity Cap Attribution

Store.

---

# 26.56 Risk-Override Attribution

Track performance impact of hard overrides.

---

# 26.57 Execution Attribution

Separate:

```text
signal/portfolio return
```

from:

```text
execution drag
```

---

# 26.58 Spread Cost Contribution

Store:

```text
spread_cost_drag
```

---

# 26.59 Slippage Contribution

Store.

---

# 26.60 Market Impact Contribution

Store.

---

# 26.61 Fees and Taxes Contribution

Store.

---

# 26.62 Implementation Shortfall Contribution

Aggregate:

```text
implementation_shortfall
```

---

# 26.63 Delay Cost Contribution

Store.

---

# 26.64 Opportunity Cost Contribution

Store.

---

# 26.65 Gross-to-Net Attribution

Conceptually:

```text
gross return
-
spread
-
slippage
-
impact
-
fees
=
net return
```

---

# 26.66 Turnover Attribution

Separate turnover caused by:

```text
signal change
rebalance
risk control
cash flow
universe change
```

---

# 26.67 Signal-Driven Turnover

Store.

---

# 26.68 Risk-Driven Turnover

Store.

---

# 26.69 Universe-Change Turnover

Store.

---

# 26.70 Event-Driven Turnover

Store.

---

# 26.71 Drawdown Attribution

For each drawdown episode identify:

```text
largest position contributors
largest sector contributors
largest factor contributors
```

---

# 26.72 Drawdown Security Attribution

Store:

```text
drawdown_security_contribution
```

---

# 26.73 Drawdown Sector Attribution

Store.

---

# 26.74 Drawdown Factor Attribution

Store.

---

# 26.75 Drawdown Regime Attribution

Store regime during:

```text
peak
decline
trough
recovery
```

---

# 26.76 Recovery Attribution

Which stocks/sectors/factors drove recovery?

Store.

---

# 26.77 Regime Attribution

For each regime calculate:

```text
return contribution
risk contribution
cost contribution
```

---

# 26.78 Bull Regime Contribution

Store.

---

# 26.79 Bear Regime Contribution

Store.

---

# 26.80 High-Vol Regime Contribution

Store.

---

# 26.81 Sideways Regime Contribution

Store.

---

# 26.82 Regime Transition Attribution

Analyze performance around:

```text
bull → neutral
neutral → bear
bear → recovery
```

---

# 26.83 Timing Attribution

If portfolio changes exposure over time:

```text
exposure timing contribution
```

can estimate value from de-risking/risk-on shifts.

---

# 26.84 Market Timing Contribution

Potentially compare:

```text
dynamic net exposure
```

against:

```text
fixed net exposure
```

---

# 26.85 Cash Allocation Contribution

Store:

```text
cash_drag_or_benefit
```

---

# 26.86 Leverage Contribution

Store:

```text
leverage_return_contribution
```

---

# 26.87 Financing Cost Contribution

For leveraged portfolios:

```text
financing_cost_drag
```

---

# 26.88 Short Borrow Cost Contribution

Store.

---

# 26.89 Dividend Contribution

For long portfolios:

```text
dividend_contribution
```

---

# 26.90 FX Contribution

If portfolio includes foreign assets:

```text
currency_contribution
```

Optional later.

---

# 26.91 Position Sizing Attribution

Compare actual size with:

```text
equal-weight
```

or base target.

Store:

```text
sizing_value_add
```

---

# 26.92 Confidence Sizing Attribution

Store.

---

# 26.93 Volatility Sizing Attribution

Store.

---

# 26.94 Liquidity Sizing Attribution

Store.

---

# 26.95 Security Selection Attribution

For long-only portfolio:

```text
selection contribution
```

can be estimated against benchmark/universe return.

---

# 26.96 Selection Breadth

Count:

```text
positive contribution positions
negative contribution positions
```

---

# 26.97 Hit Contribution Ratio

Possible:

```text
sum positive contributions
/
sum absolute contributions
```

---

# 26.98 Contribution Concentration

Measure whether return came from few positions.

Use:

```text
top_5_contribution_share
top_10_contribution_share
```

---

# 26.99 Contribution HHI

```text
contribution_hhi
```

based on absolute contributions.

---

# 26.100 Contribution Diversification Score

Possible inverse of concentration.

---

# 26.101 Sector Allocation Attribution

For benchmark-aware portfolio:

```text
sector over/underweight
```

effects.

---

# 26.102 Sector Selection Attribution

Within-sector stock selection effects.

---

# 26.103 Cross-Sector Interaction

Optional.

---

# 26.104 Factor Timing Attribution

If factor exposures change dynamically:

```text
factor_timing_contribution
```

---

# 26.105 Factor Selection Attribution

For multi-factor models:

```text
factor mix contribution
```

---

# 26.106 Alpha Model Attribution

Compare actual model with baseline:

```text
alpha_model_value_add
```

---

# 26.107 Confidence Model Attribution

Compare with confidence disabled.

Store:

```text
confidence_model_value_add
```

---

# 26.108 Regime Model Attribution

Compare with static strategy.

Store.

---

# 26.109 Risk Model Attribution

Store.

---

# 26.110 Execution Model Attribution

Store.

---

# 26.111 Full Stack Attribution

Potential decomposition:

```text
Baseline Strategy Return
+
Alpha Model Value Add
+
Confidence Value Add
+
Portfolio Construction Value Add
+
Risk Control Value Add
+
Regime Overlay Value Add
-
Execution Drag
=
Final Net Return
```

This is extremely useful for system-level evaluation.

---

# 26.112 Counterfactual Attribution

Some attribution requires running alternate portfolio simulations.

Examples:

```text
without regime overlay
without stop loss
without confidence
without optimizer
```

Mark these as:

```text
counterfactual
```

not direct arithmetic decomposition.

---

# 26.113 Shapley Attribution

Advanced method to allocate value-add among interacting components.

Useful when:

```text
alpha
confidence
risk
regime
```

interact nonlinearly.

Computationally expensive.

---

# 26.114 Attribution Linking

Daily attribution should link correctly to period return.

Possible methods:

```text
arithmetic linking
geometric linking
Carino-style linking
```

Choose one platform convention.

---

# 26.115 Residual Attribution

Any unexplained difference should be stored:

```text
attribution_residual
```

Do not silently force reconciliation.

---

# 26.116 Reconciliation Rule

Target:

```text
sum(attributed components)
≈
reported return
```

within tolerance.

---

# 26.117 Attribution Tolerance

Store:

```text
reconciliation_tolerance_bps
```

---

# 26.118 Benchmark Attribution Record

Recommended:

```text
date
portfolio_id
sector

portfolio_weight
benchmark_weight

portfolio_sector_return
benchmark_sector_return

allocation_effect
selection_effect
interaction_effect

total_active_contribution
```

---

# 26.119 Security Attribution Record

```text
date
portfolio_id
instrument_key

weight
return

gross_contribution
net_contribution

benchmark_weight
active_weight

sector
factor_exposures

signal_source
confidence_bucket
```

---

# 26.120 Factor Attribution Record

```text
date
portfolio_id
factor_name

factor_exposure
factor_return
factor_contribution

factor_model_version
```

---

# 26.121 Signal Attribution Record

```text
date
portfolio_id
signal_name

signal_weight
signal_contribution

gross_pnl
net_pnl

trade_count
hit_rate
```

---

# 26.122 Execution Attribution Record

```text
date
portfolio_id

spread_cost
slippage_cost
impact_cost
fees
taxes

delay_cost
opportunity_cost

implementation_shortfall

total_execution_drag
```

---

# 26.123 Risk-Control Attribution Record

```text
date
portfolio_id

risk_rule
baseline_weight
actual_weight

counterfactual_return
actual_return

estimated_value_add
```

---

# 26.124 Drawdown Attribution Record

```text
drawdown_id

security_contributions
sector_contributions
factor_contributions

execution_drag
risk_control_effect

market_regime
```

---

# 26.125 Monthly Attribution Record

Recommended reporting layer:

```text
year
month

portfolio_return
benchmark_return
active_return

security_selection
sector_allocation
factor_contribution
regime_overlay
risk_control_value_add
execution_drag

attribution_residual
```

---

# 26.126 Initial Production Attribution

V1 should focus on directly measurable contributions.

Recommended:

```text
security contribution
sector contribution
benchmark active return
gross vs net cost drag
long vs short contribution
signal bucket contribution
confidence bucket contribution
regime contribution
```

Then add:

```text
Brinson
factor model attribution
counterfactual strategy components
```

---

# 26.127 Initial Production Outputs

Recommended:

```text
top_contributors
top_detractors

sector_contribution

long_book_contribution
short_book_contribution

gross_return
execution_drag
net_return

benchmark_active_return

signal_contribution
confidence_bucket_contribution

regime_contribution

drawdown_contributors

attribution_residual
```

---

# 26.128 Attribution Processing Flow

Recommended:

```text
PORTFOLIO / TRADE HISTORY
        ↓
SECURITY CONTRIBUTION
        ↓
SECTOR / INDUSTRY AGGREGATION
        ↓
BENCHMARK RELATIVE ATTRIBUTION
        ↓
FACTOR ATTRIBUTION
        ↓
SIGNAL ATTRIBUTION
        ↓
CONFIDENCE ATTRIBUTION
        ↓
PORTFOLIO-CONSTRUCTION VALUE ADD
        ↓
RISK-CONTROL VALUE ADD
        ↓
REGIME OVERLAY ATTRIBUTION
        ↓
EXECUTION DRAG
        ↓
DRAWDOWN ATTRIBUTION
        ↓
FULL-STACK RECONCILIATION
```

---

# 26.129 Point-in-Time Rule

Attribution is retrospective, but every attributed component must use the historical data/model state that actually existed during the period.

Do not reclassify historical positions using today's:

```text
sector map
factor model
signal version
```

without clearly labeling it as restated analysis.

---

# 26.130 Historical Classification

Use point-in-time:

```text
sector
industry
factor exposures
signal version
```

where available.

---

# 26.131 Attribution Versioning

Store:

```text
attribution_model_version
```

---

# 26.132 Factor Model Versioning

Store exact risk/factor model used.

---

# 26.133 Benchmark Versioning

Historical benchmark membership/weights must be point-in-time.

---

# 26.134 Attribution Quality Status

Possible:

```text
VALID
PARTIAL
MISSING_BENCHMARK
MISSING_FACTOR_DATA
RECONCILIATION_WARNING
COUNTERFACTUAL_ONLY
INVALID
```

---

# 26.135 Reconciliation Check

For each report period:

```text
abs(
portfolio_return
-
sum(attributed_return)
)
<= tolerance
```

where method should reconcile.

---

# 26.136 Residual Warning

If residual exceeds threshold:

```text
RECONCILIATION_WARNING
```

---

# 26.137 Performance Driver Stability

Track whether return drivers change over time.

Example:

```text
2024: momentum-driven
2025: sector-allocation-driven
2026: event-alpha-driven
```

---

# 26.138 Attribution Concentration

Measure concentration of performance drivers.

---

# 26.139 Negative Attribution Persistence

Identify repeatedly damaging:

```text
signals
sectors
factors
```

---

# 26.140 Positive Attribution Persistence

Identify repeatable strengths.

---

# 26.141 Signal Decay Attribution

If a signal historically contributed but recently detracts:

```text
signal_decay_flag
```

---

# 26.142 Factor Crowding Attribution

If factor contribution turns sharply negative while exposure remains high:

```text
factor_crowding_warning
```

optional later.

---

# 26.143 Regime Failure Attribution

Identify strategies that fail in particular regimes.

---

# 26.144 Execution Deterioration Attribution

Separate poor live return caused by:

```text
worse fills
```

from:

```text
weaker alpha
```

---

# 26.145 Live-vs-Backtest Attribution

Possible decomposition:

```text
live gap =
signal degradation
+
portfolio drift
+
cost increase
+
execution slippage
+
capacity effect
+
unexplained residual
```

---

# 26.146 Research Attribution

During factor research attribute quantile return to:

```text
sector composition
size bias
beta bias
```

to detect hidden exposures.

---

# 26.147 Factor Purity Attribution

Evaluate whether nominal momentum factor return is actually driven by:

```text
small-cap bias
sector bias
beta
```

---

# 26.148 Portfolio Active Risk Attribution

Decompose tracking error by:

```text
security
sector
factor
specific risk
```

---

# 26.149 Risk Attribution

Return attribution and risk attribution are different.

Risk attribution answers:

```text
where portfolio volatility came from
```

---

# 26.150 Position Risk Contribution

Consume Step 21/22.

---

# 26.151 Sector Risk Contribution

Store.

---

# 26.152 Factor Risk Contribution

Store.

---

# 26.153 Specific Risk Contribution

Store.

---

# 26.154 Tracking Error Contribution

For active portfolios:

```text
marginal contribution to tracking error
```

---

# 26.155 Return-on-Risk Attribution

Compare:

```text
return contribution
/
risk contribution
```

by position/sector/factor.

---

# 26.156 Efficient Contributors

Positions with:

```text
high return contribution
low risk contribution
```

---

# 26.157 Inefficient Contributors

Positions with:

```text
negative return contribution
high risk contribution
```

---

# 26.158 Capital Allocation Review

Attribution should inform future:

```text
strategy capital weights
factor weights
risk budgets
```

but not automatically change them without research validation.

---

# 26.159 Attribution Dashboard Outputs

Possible:

```text
Return Waterfall
Top Contributors / Detractors
Sector Attribution
Factor Attribution
Signal Attribution
Cost Drag
Drawdown Attribution
Regime Attribution
```

---

# 26.160 Waterfall Reconciliation

Example:

```text
Market/Beta         +6.2%
Stock Selection     +4.1%
Sector Allocation   +1.0%
Regime Overlay      +0.8%
Risk Controls       +0.4%
Execution Costs     -1.3%
Other/Residual      -0.2%
-------------------------
Net Return          11.0%
```

---

# 26.161 Important Quant Rules

## Rule 1 — Contribution Is Not Causality

A stock contributed return; that does not prove why it moved.

## Rule 2 — Direct and Counterfactual Attribution Must Be Separate

Do not mix arithmetic decomposition with hypothetical simulations.

## Rule 3 — Benchmark Attribution Needs Historical Benchmark Weights

Avoid using today's composition.

## Rule 4 — Factor Attribution Needs a Defined Factor Model

Do not improvise factor returns after the fact.

## Rule 5 — Gross and Net Attribution Must Be Separate

Execution costs matter.

## Rule 6 — Risk Attribution Is Different from Return Attribution

Track both.

## Rule 7 — Drawdown Attribution Matters

Average-period attribution can hide tail losses.

## Rule 8 — Reconciliation Must Be Explicit

Keep residuals visible.

## Rule 9 — Attribution Must Use Historical Model Versions

No silent reclassification.

## Rule 10 — Attribution Should Drive Research Questions

Not automatic strategy changes.

---

# 26.162 Completion Criteria

Step 26 is complete when Open Analytics can answer:

1. Which stocks contributed most to return?
2. Which stocks detracted most?
3. Which sectors contributed positively or negatively?
4. Was active return driven by allocation or selection?
5. How much return came from market beta?
6. How much came from residual alpha?
7. Which factors generated return?
8. Which signals generated return?
9. Did high-confidence signals contribute more?
10. How much value did portfolio construction add?
11. How much did risk controls add or subtract?
12. How much did regime scaling add or subtract?
13. How much return was lost to execution costs?
14. Which positions caused the worst drawdown?
15. Which factors caused the worst drawdown?
16. Was performance concentrated in a few contributors?
17. Why did live results differ from backtest?
18. Where did portfolio risk come from?
19. Which positions delivered the best return per unit risk?
20. Does attribution reconcile to reported portfolio return?
21. Can the full attribution be reproduced using historical model versions?

Once these are reliable, the Attribution Engine is ready to feed:

```text
Step 27 — ML Dataset Engine
```

---

# Step 26 Final Output

The Attribution Engine transforms:

```text
Portfolio Returns
+
Positions
+
Benchmark
+
Factor Exposures
+
Signals
+
Risk Controls
+
Execution Costs
```

into:

```text
Security Contribution
Sector Contribution
Allocation Effect
Selection Effect
Interaction Effect
Beta Contribution
Residual Alpha
Factor Contribution
Signal Contribution
Confidence Contribution
Portfolio-Construction Value Add
Risk-Control Value Add
Regime-Overlay Value Add
Execution Drag
Drawdown Attribution
Risk Attribution
Live-vs-Backtest Attribution
Full-Stack Return Reconciliation
```

This becomes the performance-explanation layer for Open Analytics.
