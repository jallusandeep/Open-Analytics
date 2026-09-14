# Open Analytics — Step 22: Position Sizing & Risk Controls Engine

## Purpose

The **Position Sizing & Risk Controls Engine** converts target portfolio intent into safe, bounded, risk-aware position sizes.

This layer answers:

- How large should each position actually be?
- How much capital should be at risk on each trade?
- How should volatility change position size?
- How should confidence change position size?
- How should liquidity limit position size?
- How should stops, drawdowns, and regime stress affect exposure?
- What happens if portfolio risk exceeds limits?
- What happens if one sector or factor becomes too concentrated?
- What hard limits should override alpha?
- When should the system reduce or fully stop trading?
- How should risk recover after losses?
- How should sizing differ across low-volatility and high-volatility regimes?

This engine sits between:

```text
Portfolio Construction
```

and:

```text
Execution
```

Outputs feed directly into:

- Order generation
- Execution
- Live risk monitoring
- Backtesting
- Portfolio governance
- Drawdown control
- Kill-switch logic

---

# 22.1 Core Principle

Position size should not be based only on conviction.

Professional sizing balances:

```text
Expected Alpha
Confidence
Volatility
Liquidity
Correlation
Portfolio Risk
Drawdown
Market Regime
Capital Limits
Execution Capacity
```

The strongest signal does not automatically deserve the largest position.

---

# 22.2 Required Inputs

From Step 21:

```text
target_weight
target_position_value
portfolio_risk_budget
portfolio_beta
sector_exposure
factor_exposure
```

From Step 19:

```text
expected_alpha
signal_strength
```

From Step 20:

```text
confidence_score
```

From Step 5:

```text
volatility
ATR
drawdown
beta
CVaR
```

From Step 6:

```text
ADV
spread
price_impact
days_to_liquidate
position_capacity
```

From Step 18:

```text
market_regime
market_stress_score
risk_budget_multiplier
```

From current account state:

```text
equity
cash
margin_available
current_positions
open_orders
```

---

# 22.3 Position Sizing Modes

Support multiple methods:

```text
FIXED_WEIGHT
FIXED_RISK
VOLATILITY_TARGET
ATR_RISK
CONFIDENCE_WEIGHTED
ALPHA_RISK_WEIGHTED
KELLY_FRACTION
PORTFOLIO_RISK_CONTRIBUTION
```

Do not force one sizing method across all strategies.

---

# 22.4 Fixed Weight

Simple:

```text
position_weight = fixed percentage
```

Useful baseline only.

---

# 22.5 Fixed Capital Allocation

Example:

```text
₹100,000 per position
```

Simple but ignores volatility and liquidity.

---

# 22.6 Fixed Risk Per Trade

Common framework:

```text
risk_per_trade =
portfolio_equity × risk_fraction
```

Then:

```text
position_size =
risk_per_trade / stop_distance
```

---

# 22.7 ATR-Based Risk Sizing

Use:

```text
stop_distance =
ATR × multiplier
```

Then:

```text
position_units =
risk_budget / stop_distance
```

This normalizes position risk across stocks with different volatility.

---

# 22.8 Volatility Target Sizing

Possible:

```text
weight_i ∝ target_risk / volatility_i
```

Higher-volatility stocks receive smaller weights.

---

# 22.9 Confidence-Weighted Sizing

Possible:

```text
size_multiplier =
confidence_score / 100
```

Then:

```text
adjusted_position =
base_position × size_multiplier
```

Keep confidence and alpha separate.

---

# 22.10 Alpha-Weighted Sizing

Possible:

```text
size ∝ expected_alpha
```

subject to all risk caps.

---

# 22.11 Alpha-to-Risk Sizing

Potential:

```text
size_score =
expected_alpha / expected_volatility
```

This is more robust than pure alpha sizing.

---

# 22.12 Fractional Kelly

Conceptually:

```text
Kelly fraction
```

can estimate optimal growth sizing.

Because full Kelly can be extremely aggressive, use:

```text
fractional Kelly
```

such as:

```text
0.25 Kelly
0.5 Kelly
```

Only if win/loss distribution estimates are reliable.

---

# 22.13 Kelly Guardrails

Never use Kelly without:

```text
maximum position cap
portfolio risk cap
uncertainty adjustment
liquidity cap
```

---

# 22.14 Per-Position Risk Budget

Store:

```text
position_risk_budget
```

Possible basis:

```text
portfolio equity
portfolio volatility budget
trade-specific stop loss
```

---

# 22.15 Maximum Position Weight

Hard limit:

```text
position_weight <= max_position_weight
```

---

# 22.16 Minimum Position Weight

Avoid uneconomic positions:

```text
position_weight >= minimum_position_weight
```

if position is active.

---

# 22.17 Maximum Capital per Position

Store:

```text
max_position_value
```

---

# 22.18 Maximum ADV Participation

Possible:

```text
position_value <= ADV × max_adv_multiple
```

or:

```text
daily_order <= ADV × max_participation_rate
```

---

# 22.19 Days-to-Liquidate Limit

Hard constraint:

```text
days_to_liquidate <= max_days_to_liquidate
```

---

# 22.20 Liquidity Haircut

Possible:

```text
liquidity_multiplier
```

where low liquidity reduces size.

---

# 22.21 Volatility Haircut

Possible:

```text
volatility_multiplier
```

Higher volatility reduces size.

---

# 22.22 Drawdown Haircut

If stock is in severe drawdown:

```text
drawdown_multiplier
```

may reduce size.

---

# 22.23 Market Regime Multiplier

Possible:

```text
BULL_LOW_VOL     = 1.0
BEAR_HIGH_VOL    < 1.0
STRESS           << 1.0
```

Exact values must be researched.

---

# 22.24 Market Stress Multiplier

Potential:

```text
stress_multiplier =
function(market_stress_score)
```

As stress rises, aggregate allowed exposure falls.

---

# 22.25 Portfolio-Level Risk Budget

Store:

```text
portfolio_risk_budget
```

Possible:

```text
target volatility
maximum VaR
maximum CVaR
maximum gross exposure
```

---

# 22.26 Target Portfolio Volatility

Example:

```text
target_portfolio_volatility = 12%
```

Sizing engine scales positions to remain near target.

---

# 22.27 Volatility Scaling

Possible:

```text
scale =
target_volatility
/
forecast_portfolio_volatility
```

Subject to leverage cap.

---

# 22.28 Portfolio VaR Limit

Possible hard limit:

```text
portfolio_VaR <= VaR_limit
```

---

# 22.29 Portfolio CVaR Limit

Possible:

```text
portfolio_CVaR <= CVaR_limit
```

---

# 22.30 Portfolio Drawdown Limit

Store:

```text
max_allowed_drawdown
```

---

# 22.31 Drawdown-Based De-Risking

Example concept:

```text
drawdown < 5%
→ normal risk

drawdown 5–10%
→ reduce risk

drawdown > 10%
→ strong de-risking
```

Exact thresholds must be configurable.

---

# 22.32 Drawdown Ladder

Possible:

```text
risk multiplier by drawdown band
```

Store as configuration rather than hard-coded logic.

---

# 22.33 Drawdown Recovery

Risk should not instantly return to maximum after one positive day.

Possible:

```text
gradual risk restoration
```

Store:

```text
risk_recovery_rate
```

---

# 22.34 Daily Loss Limit

Possible:

```text
max_daily_loss
```

If breached:

```text
block new risk
```

---

# 22.35 Weekly Loss Limit

Possible:

```text
max_weekly_loss
```

---

# 22.36 Monthly Loss Limit

Possible:

```text
max_monthly_loss
```

---

# 22.37 Strategy-Level Loss Limit

Each strategy can have its own:

```text
strategy_drawdown_limit
```

---

# 22.38 Position Stop Loss

Possible:

```text
fixed percentage stop
ATR stop
volatility stop
technical stop
```

---

# 22.39 ATR Stop

Example:

```text
stop =
entry_price - ATR × multiplier
```

for long positions.

---

# 22.40 Trailing Stop

Possible:

```text
highest_price_since_entry - ATR × multiplier
```

or percentage-based.

---

# 22.41 Time Stop

Exit after:

```text
maximum holding period
```

if alpha has not materialized.

---

# 22.42 Signal Stop

Exit when:

```text
signal falls below threshold
```

---

# 22.43 Confidence Stop

Reduce/exit if:

```text
confidence collapses
```

even if price stop not triggered.

---

# 22.44 Regime Stop

Potential:

```text
market regime changes to STRESS
```

and strategy is not designed for that state.

---

# 22.45 Event Stop

Possible triggers:

```text
fraud allegation
default
suspension
critical governance event
```

Hard override may be necessary.

---

# 22.46 Hard Risk Override

Risk rules must be able to override alpha.

Examples:

```text
suspension
critical liquidity failure
margin breach
portfolio loss limit
```

---

# 22.47 Portfolio Gross Exposure Limit

```text
gross_exposure <= max_gross_exposure
```

---

# 22.48 Portfolio Net Exposure Limit

```text
net_exposure within allowed range
```

---

# 22.49 Leverage Limit

```text
leverage <= max_leverage
```

---

# 22.50 Cash Buffer

Maintain:

```text
minimum_cash_buffer
```

---

# 22.51 Margin Buffer

Maintain:

```text
minimum_margin_buffer
```

---

# 22.52 Sector Exposure Limit

Possible:

```text
sector_weight <= sector_cap
```

---

# 22.53 Industry Exposure Limit

Similarly.

---

# 22.54 Factor Exposure Limit

Possible:

```text
size exposure
momentum exposure
beta exposure
```

bounded.

---

# 22.55 Correlation Cluster Limit

Limit exposure to highly correlated groups.

Example:

```text
banking stocks
metal stocks
IT exporters
```

---

# 22.56 Single-Theme Concentration

Potential:

```text
theme_exposure_limit
```

if thematic mapping exists.

---

# 22.57 Risk Contribution Cap

Possible:

```text
position risk contribution <= X%
```

of total portfolio risk.

---

# 22.58 Sector Risk Contribution Cap

Likewise.

---

# 22.59 Factor Risk Contribution Cap

Likewise.

---

# 22.60 Beta Limit

Possible:

```text
portfolio_beta <= max_beta
```

or target range.

---

# 22.61 Downside Beta Limit

Optional.

---

# 22.62 Tail Risk Limit

Possible:

```text
portfolio_tail_risk_score <= threshold
```

---

# 22.63 Gap Risk Limit

Reduce position size for stocks with:

```text
high overnight gap risk
```

---

# 22.64 Event Risk Haircut

If major event imminent:

```text
earnings
regulatory decision
court ruling
```

apply:

```text
event_risk_multiplier
```

---

# 22.65 Earnings Risk Rule

Possible:

```text
reduce size before earnings
```

unless strategy specifically trades earnings.

---

# 22.66 Overnight Risk Rule

Intraday strategies may force:

```text
overnight_weight = 0
```

---

# 22.67 Weekend Risk Rule

Optional reduction before non-trading gaps.

---

# 22.68 Circuit Risk

Stocks near price-band limits may require reduced size or exclusion.

---

# 22.69 Short Squeeze Risk

For short positions:

```text
high short interest
low float
high borrow cost
high squeeze risk
```

should reduce size.

---

# 22.70 Borrow Availability

Short sizing must consume:

```text
borrow_available
borrow_cost
```

---

# 22.71 Margin Requirement

Position size must respect:

```text
broker/exchange margin
```

---

# 22.72 Derivatives Lot Size

Position sizing must respect lot multiples.

---

# 22.73 Integer Share Rounding

Cash equities require integer shares.

---

# 22.74 Position Rounding Error

Store:

```text
target_weight
actual_weight
rounding_error
```

---

# 22.75 Minimum Trade Size

Avoid very small orders:

```text
minimum_trade_value
```

---

# 22.76 Maximum Order Size

Possible per-order cap:

```text
max_order_value
```

---

# 22.77 Order Participation Limit

Execution-level:

```text
max_order_participation_rate
```

---

# 22.78 Intraday Risk Budget

Separate:

```text
intraday_risk_budget
```

from overnight risk.

---

# 22.79 Overnight Risk Budget

Store:

```text
overnight_risk_budget
```

---

# 22.80 Strategy Risk Budget

If multiple strategies:

```text
strategy_risk_allocation
```

---

# 22.81 Capital Allocation Across Strategies

Possible:

```text
momentum strategy 40%
value strategy 30%
event strategy 30%
```

but should be optimized/researched.

---

# 22.82 Strategy Correlation

Risk allocation should account for strategy correlations.

---

# 22.83 Portfolio Heat

Possible concept:

```text
sum(position risk budgets)
```

Store:

```text
portfolio_heat
```

---

# 22.84 Maximum Portfolio Heat

Hard cap:

```text
portfolio_heat <= max_portfolio_heat
```

---

# 22.85 Stop Distance Consistency

Every risk-based position should have:

```text
entry
stop
risk per unit
position units
```

auditable.

---

# 22.86 Slippage Buffer

Risk sizing should account for:

```text
stop slippage
gap risk
```

Potential:

```text
effective_stop_distance =
planned_stop_distance + slippage_buffer
```

---

# 22.87 Transaction Cost Buffer

Very small expected alpha should not justify full size if costs are high.

---

# 22.88 Capacity-Based Size Cap

Possible:

```text
max_position =
min(
    alpha-based size,
    risk-based size,
    liquidity-based size,
    concentration-based size
)
```

This is a strong general framework.

---

# 22.89 Final Position Size

Conceptually:

```text
final_size =
min(
    target_portfolio_size,
    risk_cap,
    liquidity_cap,
    sector_cap,
    factor_cap,
    margin_cap,
    event_cap
)
```

---

# 22.90 Size Reason Codes

Examples:

```text
VOLATILITY_LIMITED
LIQUIDITY_LIMITED
SECTOR_LIMITED
RISK_BUDGET_LIMITED
CONFIDENCE_LIMITED
EVENT_RISK_LIMITED
MARGIN_LIMITED
```

---

# 22.91 Position Sizing Explainability

For every position expose:

```text
base target size
alpha multiplier
confidence multiplier
volatility multiplier
regime multiplier
liquidity cap
final size
```

---

# 22.92 Position Risk Record

Recommended:

```text
date
portfolio_id
instrument_key

entry_price
current_price

base_target_weight
portfolio_target_weight

alpha_score
confidence_score

volatility
ATR
beta

stop_price
stop_distance

risk_per_unit
position_risk_budget

risk_based_units
liquidity_based_units
margin_based_units

final_units
final_position_value
final_weight

risk_contribution
risk_contribution_pct

size_reason_code
risk_status
```

---

# 22.93 Portfolio Risk State Record

```text
date
portfolio_id

equity
cash
margin_available

gross_exposure
net_exposure
leverage

portfolio_volatility
portfolio_beta

VaR
CVaR

current_drawdown

daily_pnl
weekly_pnl
monthly_pnl

portfolio_heat

risk_budget_multiplier

risk_state
kill_switch_status
```

---

# 22.94 Risk States

Possible:

```text
NORMAL
CAUTION
REDUCED_RISK
DEFENSIVE
HALTED
```

---

# 22.95 Kill Switch

Hard emergency state.

Potential triggers:

```text
daily loss breach
critical drawdown
market dislocation
broker/API issue
data integrity failure
position reconciliation failure
```

Output:

```text
kill_switch = true
```

---

# 22.96 Kill Switch Actions

Possible:

```text
block new orders
cancel unfilled orders
reduce risk
flatten positions
```

Exact behavior must be strategy-specific and explicitly configured.

---

# 22.97 Data Integrity Kill Switch

If market data is invalid:

```text
do not generate new risk
```

---

# 22.98 Connectivity Kill Switch

If broker/order status cannot be confirmed:

```text
freeze new orders
```

---

# 22.99 Position Reconciliation Failure

If internal positions differ from broker positions:

```text
risk_state = HALTED
```

until reconciled.

---

# 22.100 Stale Price Protection

If price feed stale:

```text
block new sizing
```

for affected instrument.

---

# 22.101 Abnormal Price Protection

If impossible price jump or bad tick:

```text
do not resize automatically
```

until validated.

---

# 22.102 Market Halt Handling

If exchange/segment halted:

```text
freeze execution
```

and maintain risk state.

---

# 22.103 Risk Limit Breach Handling

For every risk limit define:

```text
WARNING
SOFT_BREACH
HARD_BREACH
```

---

# 22.104 Risk Breach Actions

Possible:

```text
notify
block new risk
reduce exposure
force exit
```

---

# 22.105 Risk Limit Hierarchy

Recommended:

```text
1. Data/operational safety
2. Legal/margin constraints
3. Portfolio drawdown/loss limits
4. Position/sector/factor limits
5. Liquidity constraints
6. Alpha/confidence sizing
```

---

# 22.106 Risk Override Audit Trail

Store:

```text
original target
risk-adjusted target
rule triggered
timestamp
reason
```

---

# 22.107 Intraday Monitoring

Live systems should continuously monitor:

```text
PnL
exposure
margin
drawdown
price gaps
liquidity
open orders
```

---

# 22.108 End-of-Day Risk Check

Recompute:

```text
portfolio volatility
beta
sector exposure
factor exposure
drawdown
liquidity
```

---

# 22.109 Pre-Trade Risk Check

Before each order:

```text
position limit
sector limit
gross/net exposure
liquidity
margin
kill switch
```

must pass.

---

# 22.110 Post-Trade Risk Check

After fill:

```text
recalculate actual exposure
```

---

# 22.111 Risk Budget by Regime

Potential:

```text
BULL_LOW_VOL → 1.0
BULL_HIGH_VOL → 0.8
BEAR_HIGH_VOL → 0.4
STRESS → 0.2
```

These are illustrative only.

---

# 22.112 Confidence-Based Scaling

Possible:

```text
confidence 90–100 → full allowed size
confidence 70–90 → moderate
confidence < threshold → no position
```

Exact mapping must be researched.

---

# 22.113 Conviction Cap

Even maximum conviction cannot override:

```text
hard risk limits
```

---

# 22.114 Risk Budget Utilization

Store:

```text
risk_budget_used_pct
```

---

# 22.115 Unused Risk Budget

Store:

```text
remaining_risk_budget
```

---

# 22.116 Position Risk Concentration

Track if a few positions consume most risk.

---

# 22.117 Sector Risk Concentration

Track.

---

# 22.118 Factor Risk Concentration

Track.

---

# 22.119 Drawdown Attribution

Identify which:

```text
positions
sectors
factors
strategies
```

are causing current drawdown.

---

# 22.120 Recovery Mode

After large losses:

```text
risk_recovery_mode = true
```

Potential gradual restoration.

---

# 22.121 Risk Cooldown

Possible:

```text
minimum cooldown period
```

after severe breach.

---

# 22.122 Manual Override

Allow:

```text
manual risk override
```

only with:

```text
user
timestamp
reason
```

and audit trail.

---

# 22.123 Initial Production Sizing Model

Recommended V1:

```text
1. Start from Step 21 target weight.
2. Apply maximum position cap.
3. Apply volatility scaling.
4. Apply confidence multiplier.
5. Apply market-regime risk multiplier.
6. Apply liquidity/ADV cap.
7. Apply sector/factor caps.
8. Apply portfolio volatility target.
9. Apply drawdown risk multiplier.
10. Convert to integer shares / lot size.
```

This is transparent and robust.

---

# 22.124 Initial Production Risk Controls

Recommended configurable hard controls:

```text
max_position_weight
max_sector_weight
max_gross_exposure
max_net_exposure
max_portfolio_beta

target_portfolio_volatility
max_portfolio_volatility

max_daily_loss
max_weekly_loss
max_drawdown

max_days_to_liquidate
max_ADV_participation

minimum_cash_buffer
minimum_margin_buffer

kill_switch_enabled
```

---

# 22.125 Initial Production Outputs

Recommended:

```text
base_position_weight
risk_adjusted_weight

final_position_value
final_units

position_risk_budget
risk_contribution

portfolio_heat

risk_budget_used_pct

current_risk_state
drawdown_multiplier
regime_multiplier

risk_limit_breaches
kill_switch_status
```

---

# 22.126 Position Sizing Processing Flow

Recommended:

```text
TARGET PORTFOLIO
        ↓
ALPHA / CONFIDENCE
        ↓
VOLATILITY / ATR
        ↓
BASE RISK SIZE
        ↓
REGIME MULTIPLIER
        ↓
LIQUIDITY / CAPACITY CAP
        ↓
POSITION / SECTOR / FACTOR LIMITS
        ↓
PORTFOLIO VOLATILITY TARGET
        ↓
DRAWDOWN / LOSS CONTROLS
        ↓
MARGIN / CASH CHECK
        ↓
INTEGER / LOT ROUNDING
        ↓
PRE-TRADE RISK CHECK
        ↓
FINAL POSITION SIZE
        ↓
LIVE RISK MONITORING
```

---

# 22.127 Point-in-Time Rule

At date/time T, sizing may only use:

```text
prices known at T
risk estimates known at T
portfolio state at T
margin known at T
regime known at T
```

No future prices.

---

# 22.128 Risk Model Versioning

Store:

```text
risk_control_version
position_sizing_version
```

Any material logic change requires new version.

---

# 22.129 Risk Quality Status

Possible:

```text
VALID
PARTIAL_DATA
STALE_RISK_INPUTS
LIQUIDITY_WARNING
MARGIN_WARNING
LIMIT_BREACH
HALTED
INVALID
```

---

# 22.130 Backtesting Requirements

Backtest:

```text
position sizing
stops
drawdown rules
portfolio caps
```

using realistic execution assumptions.

---

# 22.131 Avoid Stop-Loss Look-Ahead

For daily bars, do not assume perfect stop fill if:

```text
price gaps through stop
```

Execution model must handle gap slippage.

---

# 22.132 Intraday Stop Simulation

Requires intraday bars or conservative assumptions.

---

# 22.133 Risk-Control Attribution

Measure:

```text
return lost from de-risking
drawdown avoided
turnover added
cost incurred
```

This shows whether risk controls improve outcomes.

---

# 22.134 Sensitivity Testing

Test different:

```text
risk per trade
vol target
drawdown thresholds
ADV caps
```

Results should be robust.

---

# 22.135 Stress Testing

Test:

```text
market crash
gap-down
liquidity freeze
volatility spike
correlation spike
```

---

# 22.136 Scenario Analysis

Possible shocks:

```text
NIFTY -5%
sector -10%
INR shock
crude spike
volatility doubling
```

Estimate portfolio impact.

---

# 22.137 Important Quant Rules

## Rule 1 — Position Size Is a Risk Decision

Not only a conviction decision.

## Rule 2 — Hard Limits Override Alpha

Always.

## Rule 3 — Volatility Must Influence Size

Equal capital does not mean equal risk.

## Rule 4 — Liquidity Caps Are Mandatory

A position must be exit-able.

## Rule 5 — Drawdown Controls Must Be Systematic

Avoid discretionary panic reduction.

## Rule 6 — Confidence Can Scale Risk

But cannot override safety constraints.

## Rule 7 — Regime Can Scale Portfolio Risk

But should not rewrite historical signals.

## Rule 8 — Stops Need Realistic Execution

Gap risk matters.

## Rule 9 — Portfolio Risk Must Be Monitored After Every Fill

Targets are not actual exposures.

## Rule 10 — Kill Switches Need Explicit Triggers

Do not make them ambiguous.

## Rule 11 — Every Risk Override Must Be Auditable

Store reason and timestamp.

## Rule 12 — Risk Logic Must Be Versioned

Backtests must remain reproducible.

---

# 22.138 Completion Criteria

Step 22 is complete when Open Analytics can answer:

1. What is the base target position?
2. What is the risk-adjusted position?
3. How much capital is at risk?
4. How does volatility affect position size?
5. How does confidence affect position size?
6. How does market regime affect position size?
7. Does liquidity cap the position?
8. Does sector/factor concentration cap the position?
9. What is the final number of shares/contracts?
10. What is the stop distance?
11. What is the position risk contribution?
12. What percentage of total risk budget is being used?
13. What is current portfolio heat?
14. Is any hard risk limit breached?
15. What is current drawdown?
16. Has risk been reduced because of drawdown?
17. Are daily/weekly loss limits breached?
18. Is there enough cash and margin?
19. Is kill switch active?
20. Why was any position reduced or blocked?
21. Can every risk adjustment be reproduced historically?
22. Can the final safe position size be passed directly to execution?

Once these are reliable, the Position Sizing & Risk Controls Engine is ready to feed:

```text
Step 23 — Execution & Transaction Cost Engine
```

---

# Step 22 Final Output

The Position Sizing & Risk Controls Engine transforms:

```text
Target Portfolio
+
Alpha
+
Confidence
+
Volatility
+
Liquidity
+
Market Regime
+
Portfolio Risk State
```

into:

```text
Risk-Adjusted Position Sizes
Capital-at-Risk
Volatility Scaling
Confidence Scaling
Regime Scaling
Liquidity Caps
Sector / Factor Limits
Stop Levels
Portfolio Heat
Drawdown Controls
Loss Limits
Margin / Cash Controls
Kill-Switch State
Final Safe Shares / Contracts
Risk Audit Trail
```

This becomes the capital-protection and position-sizing layer for Open Analytics.
