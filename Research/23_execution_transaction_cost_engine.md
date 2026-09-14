# Open Analytics — Step 23: Execution & Transaction Cost Engine

## Purpose

The **Execution & Transaction Cost Engine** converts approved target trades into executable orders while minimizing trading cost, market impact, slippage, and implementation risk.

This layer answers:

- What order should actually be sent?
- Which order type should be used?
- Should the trade execute immediately or be sliced over time?
- How much of market volume should the order participate in?
- What spread cost is expected?
- What slippage is expected?
- What market impact is expected?
- What is the total expected transaction cost?
- Should the order be delayed because liquidity is poor?
- Which execution benchmark should be used?
- How much alpha may decay while waiting?
- Is the trade still worthwhile after costs?
- How should partial fills, rejects, stale orders, and cancellations be handled?
- How should backtests simulate execution realistically?

The engine sits after:

```text
Step 22 — Position Sizing & Risk Controls
```

and before:

```text
live order routing
```

Outputs feed directly into:

- Broker / exchange order routing
- Live execution monitoring
- Backtesting
- Transaction-cost attribution
- Capacity analysis
- Portfolio reconciliation
- Performance attribution

---

# 23.1 Core Principle

A good signal can become a bad trade if execution is poor.

Execution quality depends on:

```text
Spread
Liquidity
Volatility
Order Size
Participation Rate
Urgency
Market Impact
Alpha Decay
Order Type
Timing
```

The objective is not always:

```text
get filled immediately
```

The objective is:

```text
capture as much expected alpha as possible
after trading costs and execution risk.
```

---

# 23.2 Required Inputs

From Step 22:

```text
instrument_key
trade_direction
target_units
current_units
trade_units

risk_status
max_order_participation_rate
```

From Step 6:

```text
ADV
spread
depth
liquidity_score
price_impact_estimate
```

From Step 19:

```text
expected_alpha
signal_half_life
signal_freshness
```

From market data:

```text
bid
ask
last
mid
volume
order_book
intraday bars
```

From broker:

```text
open_orders
fills
rejections
positions
margin
```

---

# 23.3 Trade Quantity

Calculate:

```text
trade_quantity =
target_quantity - current_quantity
```

Direction:

```text
BUY
SELL
SHORT
COVER
NONE
```

---

# 23.4 Trade Notional

```text
trade_notional =
abs(trade_quantity × reference_price)
```

---

# 23.5 Trade Urgency

Possible states:

```text
LOW
NORMAL
HIGH
IMMEDIATE
```

Inputs:

```text
signal decay
event urgency
risk breach
market conditions
liquidity
```

---

# 23.6 Alpha Decay

Execution speed should consider:

```text
signal_half_life
```

Fast-decaying signal:

```text
more urgent
```

Slow signal:

```text
more patient execution possible
```

---

# 23.7 Execution Objective

Possible objectives:

```text
MINIMIZE_COST
MINIMIZE_MARKET_IMPACT
MINIMIZE_IMPLEMENTATION_SHORTFALL
TRACK_VWAP
TRACK_TWAP
COMPLETE_BY_DEADLINE
IMMEDIATE_RISK_REDUCTION
```

---

# 23.8 Market Order

Advantages:

```text
high fill probability
fast
```

Disadvantages:

```text
spread cost
slippage
impact
```

Use when urgency is high and liquidity sufficient.

---

# 23.9 Limit Order

Advantages:

```text
price control
potential spread capture
```

Disadvantages:

```text
non-fill risk
adverse selection
alpha decay
```

---

# 23.10 Stop Order

Used for risk control.

Execution model must account for:

```text
gap-through-stop
slippage
```

---

# 23.11 Stop-Limit Order

Provides price control but may not fill in fast markets.

---

# 23.12 IOC / FOK

If supported:

```text
IOC
FOK
```

may be used for specific execution needs.

---

# 23.13 Passive Order

Place near:

```text
bid for buy
ask for sell
```

seeking spread capture.

---

# 23.14 Aggressive Order

Cross spread when urgency dominates cost.

---

# 23.15 Midpoint Order

If venue/broker supports midpoint execution.

---

# 23.16 Order-Type Decision

Inputs:

```text
urgency
spread
depth
volatility
order size
signal half-life
```

Output:

```text
recommended_order_type
```

---

# 23.17 Order Slicing

Large orders should be split into child orders.

Store:

```text
parent_order_id
child_order_id
```

---

# 23.18 Child Order Size

Possible:

```text
child_quantity =
min(
    remaining_quantity,
    participation_limit × recent_market_volume
)
```

---

# 23.19 Participation Rate

```text
participation_rate =
order_volume
/
market_volume
```

Store:

```text
target_participation_rate
actual_participation_rate
```

---

# 23.20 Participation Cap

Hard constraint:

```text
actual_participation_rate <= maximum_allowed
```

unless emergency risk reduction overrides.

---

# 23.21 POV Execution

Percentage-of-Volume strategy:

```text
execute X% of observed market volume
```

Store:

```text
POV_target
```

---

# 23.22 TWAP

Time-Weighted Average Price execution:

```text
split order evenly across time
```

Useful when:

```text
volume profile uncertain
order urgency moderate
```

---

# 23.23 VWAP

Volume-Weighted Average Price execution:

```text
follow expected intraday volume curve
```

Useful for larger orders.

---

# 23.24 Arrival Price

Reference benchmark:

```text
price when execution decision is made
```

Store:

```text
arrival_price
```

---

# 23.25 Implementation Shortfall

One of the most important execution metrics.

For a buy:

```text
implementation_shortfall =
actual_execution_cost
-
hypothetical_cost_at_arrival_price
```

Express:

```text
currency
bps
percentage
```

---

# 23.26 Delay Cost

If execution begins after decision:

```text
delay_cost =
price_at_execution_start - arrival_price
```

direction-adjusted.

---

# 23.27 Trading Cost

Difference between execution price and price when order becomes active.

---

# 23.28 Opportunity Cost

Unfilled quantity may miss price movement.

Store:

```text
opportunity_cost
```

---

# 23.29 Total Implementation Shortfall

Conceptually:

```text
delay cost
+
trading cost
+
opportunity cost
+
fees
```

---

# 23.30 Bid-Ask Spread

Quoted spread:

```text
spread =
ask - bid
```

Relative:

```text
spread_bps =
spread / mid × 10000
```

---

# 23.31 Half-Spread Cost

Crossing once approximately incurs:

```text
half_spread
```

from midpoint to execution side.

---

# 23.32 Effective Spread

For actual execution:

```text
effective_spread =
2 × direction × (execution_price - mid_at_order)
```

normalized as needed.

---

# 23.33 Realized Spread

Measure after subsequent price movement.

Useful for diagnosing:

```text
adverse selection
```

---

# 23.34 Slippage

For a buy:

```text
slippage =
execution_price - reference_price
```

For a sell use direction adjustment.

Store:

```text
slippage_bps
```

---

# 23.35 Market Impact

Order itself may move price.

Possible decomposition:

```text
temporary impact
permanent impact
```

---

# 23.36 Simple Impact Model

Possible:

```text
impact ∝
volatility × sqrt(order_size / ADV)
```

This is a common starting form.

Model parameters should be calibrated from actual fills.

---

# 23.37 Linear Impact Component

Possible:

```text
linear_cost =
spread_component
+
fee_component
```

---

# 23.38 Nonlinear Impact Component

Possible:

```text
nonlinear_cost =
k × volatility × sqrt(participation)
```

---

# 23.39 Expected Transaction Cost

Combine:

```text
spread
slippage
market impact
fees
taxes
```

Output:

```text
expected_transaction_cost
```

---

# 23.40 Transaction Cost in Basis Points

```text
expected_cost_bps
```

This is convenient for comparing against alpha.

---

# 23.41 Alpha-to-Cost Ratio

```text
alpha_cost_ratio =
expected_alpha_bps
/
expected_cost_bps
```

---

# 23.42 Minimum Alpha After Cost

Possible rule:

```text
expected_alpha_after_cost > threshold
```

before execution.

---

# 23.43 Trade Suppression

If:

```text
expected net alpha <= 0
```

trade may be suppressed.

Output:

```text
trade_economically_viable
```

---

# 23.44 Break-Even Cost

Store:

```text
break_even_cost_bps =
expected_alpha_bps
```

Cost above this destroys expected edge.

---

# 23.45 Cost Confidence

Transaction-cost estimates have uncertainty.

Store:

```text
cost_estimate_confidence
```

---

# 23.46 Liquidity Buckets for Execution

Possible:

```text
VERY_LIQUID
LIQUID
MODERATE
ILLIQUID
VERY_ILLIQUID
```

Execution policy can vary by bucket.

---

# 23.47 ADV Ratio

```text
order_adv_ratio =
trade_notional / ADV
```

---

# 23.48 Order-to-Depth Ratio

If market depth available:

```text
order_depth_ratio =
order_size / visible_depth
```

---

# 23.49 Spread Regime

Possible:

```text
TIGHT
NORMAL
WIDE
EXTREME
```

---

# 23.50 Volatility Regime for Execution

High volatility usually increases:

```text
slippage
impact
order risk
```

---

# 23.51 Intraday Volume Profile

Estimate expected volume by time of day.

Store:

```text
expected_volume_curve
```

Useful for VWAP execution.

---

# 23.52 Intraday Spread Profile

Spreads may differ:

```text
open
midday
close
```

Store:

```text
spread_by_time_bucket
```

---

# 23.53 Intraday Volatility Profile

Likewise.

---

# 23.54 Open Auction

Execution near open has unique risk.

Potential:

```text
opening_auction_flag
```

---

# 23.55 Closing Auction

Potentially useful for benchmark tracking.

Store:

```text
closing_auction_flag
```

---

# 23.56 Pre-Open Handling

Orders may need special logic before continuous trading begins.

---

# 23.57 Circuit Limits

If price is near circuit:

```text
fill probability
execution risk
```

changes materially.

---

# 23.58 Market Halt

Execution must stop or adapt.

---

# 23.59 Partial Fill

Track:

```text
filled_quantity
remaining_quantity
```

---

# 23.60 Fill Rate

```text
fill_rate =
filled_quantity / ordered_quantity
```

---

# 23.61 Average Fill Price

```text
average_fill_price =
sum(fill_price × fill_quantity)
/
total_fill_quantity
```

---

# 23.62 Weighted Fill Timestamp

Useful for timing diagnostics.

---

# 23.63 Order Rejection

Store:

```text
reject_code
reject_reason
```

---

# 23.64 Order Cancellation

Store:

```text
cancel_reason
```

---

# 23.65 Order Expiry

Possible:

```text
DAY
IOC
GTD
```

depending on broker support.

---

# 23.66 Stale Order Detection

If order remains live beyond expected duration:

```text
stale_order_flag
```

---

# 23.67 Reprice Logic

For passive limits:

```text
reprice after threshold
```

based on:

```text
time
price movement
spread
urgency
```

---

# 23.68 Chase Limit

Do not endlessly chase adverse price movement.

Store:

```text
max_price_chase_bps
```

---

# 23.69 Urgency Escalation

As deadline or alpha decay approaches:

```text
passive → neutral → aggressive
```

---

# 23.70 Execution Deadline

Possible:

```text
complete_by
```

---

# 23.71 Time-in-Force Policy

Store:

```text
time_in_force
```

---

# 23.72 Price Protection

Hard bounds:

```text
max_buy_price
min_sell_price
```

where appropriate.

---

# 23.73 Fat-Finger Protection

Reject orders with:

```text
abnormal quantity
abnormal notional
abnormal price
```

---

# 23.74 Duplicate Order Protection

Prevent accidental repeated submission.

Use:

```text
idempotency_key
```

---

# 23.75 Open-Order Reconciliation

Before new order:

```text
check existing open orders
```

to avoid overtrading.

---

# 23.76 Position Reconciliation

Before and after execution:

```text
internal position
broker position
```

must match.

---

# 23.77 Order State Machine

Recommended states:

```text
CREATED
VALIDATED
SUBMITTED
ACKNOWLEDGED
PARTIALLY_FILLED
FILLED
CANCEL_PENDING
CANCELLED
REJECTED
EXPIRED
ERROR
```

---

# 23.78 Parent Order State

Aggregate child-order status.

---

# 23.79 Execution Risk Controls

Before order submission check:

```text
kill switch
position limit
sector limit
cash
margin
liquidity
price validity
```

---

# 23.80 Pre-Trade Cost Estimate

Store:

```text
expected_spread_cost
expected_impact_cost
expected_fee_cost
expected_total_cost
```

---

# 23.81 Post-Trade Realized Cost

Store:

```text
realized_spread_cost
realized_slippage
realized_impact
realized_total_cost
```

---

# 23.82 Predicted vs Realized Cost Error

```text
cost_model_error =
realized_cost - predicted_cost
```

---

# 23.83 Cost Model Calibration

Use historical fills to recalibrate:

```text
impact coefficient
slippage coefficient
spread assumptions
```

---

# 23.84 Execution Alpha

Possible:

```text
execution_alpha =
benchmark_price - execution_price
```

direction-adjusted.

---

# 23.85 VWAP Slippage

```text
execution_price - market_vwap
```

direction-adjusted.

---

# 23.86 TWAP Slippage

Likewise against TWAP.

---

# 23.87 Arrival Slippage

Against:

```text
arrival_price
```

---

# 23.88 Close Benchmark Slippage

Against close if strategy benchmark requires.

---

# 23.89 Execution Benchmark Selection

Possible:

```text
ARRIVAL
VWAP
TWAP
CLOSE
OPEN
CUSTOM
```

---

# 23.90 Benchmark Must Match Strategy

Example:

```text
event signal → arrival price
index rebalance → close
large passive order → VWAP
```

---

# 23.91 Adverse Selection

If price continues moving against passive fill shortly afterward:

```text
adverse_selection_cost
```

---

# 23.92 Queue Risk

For limit orders:

```text
queue position
fill probability
```

may matter if L2 data exists.

---

# 23.93 Fill Probability Model

Possible inputs:

```text
distance from touch
queue depth
volume
volatility
time remaining
```

Output:

```text
fill_probability
```

---

# 23.94 Execution Confidence

Possible:

```text
execution_confidence
```

based on:

```text
liquidity
spread
depth
fill probability
cost model quality
```

---

# 23.95 Capacity Model

Estimate maximum deployable capital with acceptable impact.

Store:

```text
max_trade_capacity
max_strategy_capacity
```

---

# 23.96 Strategy Capacity

Depends on:

```text
universe liquidity
turnover
holding period
participation rate
```

---

# 23.97 Portfolio Capacity

Aggregate execution capacity across positions.

---

# 23.98 Trade Scheduling

Potential schedule:

```text
start_time
end_time
child_order_interval
target_curve
```

---

# 23.99 Urgent Risk Liquidation

Risk-reduction trades may override normal cost-minimization logic.

Objective becomes:

```text
reduce risk safely and quickly
```

---

# 23.100 Emergency Execution

Possible:

```text
aggressive order
higher participation
```

subject to safeguards.

---

# 23.101 Broker Routing

If multiple brokers/venues:

```text
route selection
```

may consider:

```text
fees
latency
fill quality
reliability
```

---

# 23.102 Smart Order Routing

Advanced:

```text
choose venue dynamically
```

where applicable.

---

# 23.103 Broker Failure

If routing fails:

```text
retry policy
fallback broker
halt policy
```

must be explicit.

---

# 23.104 API Retry Logic

Retries must be:

```text
idempotent
bounded
```

to avoid duplicate orders.

---

# 23.105 Latency Measurement

Store:

```text
decision_to_submit_ms
submit_to_ack_ms
ack_to_fill_ms
```

---

# 23.106 Latency Cost

Fast strategies may lose alpha from latency.

---

# 23.107 Market Data Latency

Store:

```text
market_data_age_ms
```

if real-time execution.

---

# 23.108 Execution Logging

Every order should log:

```text
decision
risk check
order request
broker response
fills
cancels
costs
```

---

# 23.109 Audit Trail

Required fields:

```text
who/what generated trade
signal version
portfolio version
risk-control version
execution-policy version
timestamps
```

---

# 23.110 Execution Policy Versioning

Store:

```text
execution_policy_version
cost_model_version
```

Any material logic change requires version change.

---

# 23.111 Backtest Execution Model

Backtests should not assume:

```text
perfect close fills
zero spread
zero slippage
infinite liquidity
```

---

# 23.112 Daily-Bar Backtest Fill

For daily strategies, conservative models may use:

```text
next open
next VWAP proxy
open ± slippage
```

depending on signal timing.

---

# 23.113 Signal-at-Close Rule

If signal uses closing price:

```text
cannot assume full execution at same close
```

unless auction logic explicitly supports it.

---

# 23.114 Gap Handling

If next open gaps:

```text
fill at actual modeled open
```

not prior close.

---

# 23.115 Limit Order Backtest

A daily high/low crossing limit does not guarantee fill.

Use conservative assumptions or intraday data.

---

# 23.116 Stop Order Backtest

If market gaps through stop:

```text
fill at modeled first available price
```

not stop level.

---

# 23.117 Partial Fill Simulation

Large orders should be limited by:

```text
ADV participation
```

even in backtests.

---

# 23.118 Slippage Model by Liquidity Bucket

Possible:

```text
liquid → lower bps
illiquid → higher bps
```

Prefer calibrated continuous model.

---

# 23.119 Cost Model by Order Size

Use:

```text
order / ADV
```

to scale impact.

---

# 23.120 Cost Model by Volatility

Higher volatility should increase expected slippage/impact.

---

# 23.121 Taxes and Fees

Include applicable:

```text
brokerage
exchange fees
taxes
stamp duty
STT where relevant
```

Use configurable schedules.

---

# 23.122 Cost Schedule Versioning

Store:

```text
fee_schedule_version
```

because statutory costs may change.

---

# 23.123 Turnover Cost Attribution

Track total trading cost caused by:

```text
signal changes
risk reduction
rebalance
cash flow
```

---

# 23.124 Execution Quality Score

Possible components:

```text
arrival slippage
fill rate
impact
cost forecast error
```

Output:

```text
execution_quality_score
```

---

# 23.125 Trade Outcome Record

Recommended:

```text
trade_id
portfolio_id
instrument_key

decision_timestamp
arrival_price

side
quantity
notional

expected_cost_bps
expected_alpha_bps

order_type
execution_algorithm

filled_quantity
average_fill_price

fill_rate

arrival_slippage_bps
vwap_slippage_bps
implementation_shortfall_bps

realized_cost_bps

execution_quality_score
```

---

# 23.126 Order Record

```text
order_id
parent_order_id

instrument_key
side

order_type
limit_price
stop_price

quantity
filled_quantity
remaining_quantity

status

submitted_at
acknowledged_at
completed_at

broker_order_id
reject_reason
```

---

# 23.127 Cost Model Record

```text
date
instrument_key

spread_bps
volatility
ADV

order_adv_ratio

predicted_spread_cost_bps
predicted_impact_cost_bps
predicted_fee_cost_bps

predicted_total_cost_bps

realized_total_cost_bps
cost_model_error_bps
```

---

# 23.128 Initial Production Execution Policy

Recommended V1:

```text
1. Compute required trade quantity.
2. Check pre-trade risk.
3. Estimate spread + impact + fees.
4. Suppress trade if expected net alpha is not positive.
5. Choose urgency from signal half-life / risk.
6. Use limit orders for normal liquid execution.
7. Slice large orders by participation limit.
8. Escalate urgency if signal decays or deadline approaches.
9. Reconcile every fill.
10. Record implementation shortfall.
```

---

# 23.129 Initial Production Cost Model

Start with:

```text
half-spread
+
slippage buffer
+
sqrt(order / ADV) impact
+
fees/taxes
```

Then calibrate from actual execution data.

---

# 23.130 Initial Production Outputs

Recommended:

```text
trade_quantity
trade_notional

recommended_order_type
execution_urgency

expected_spread_cost
expected_impact_cost
expected_fee_cost
expected_total_cost

expected_net_alpha

target_participation_rate
execution_algorithm

arrival_price

realized_fill_price
realized_slippage
implementation_shortfall

fill_rate

execution_quality_score
```

---

# 23.131 Execution Processing Flow

Recommended:

```text
FINAL SAFE POSITION SIZE
        ↓
CURRENT POSITION / OPEN ORDERS
        ↓
TRADE QUANTITY
        ↓
PRE-TRADE RISK CHECK
        ↓
LIQUIDITY / SPREAD / ADV
        ↓
TRANSACTION COST ESTIMATE
        ↓
ALPHA VS COST CHECK
        ↓
URGENCY
        ↓
ORDER TYPE / EXECUTION ALGORITHM
        ↓
ORDER SLICING
        ↓
BROKER ROUTING
        ↓
FILL MONITORING
        ↓
REPRICE / CANCEL / ESCALATE
        ↓
POSITION RECONCILIATION
        ↓
REALIZED COST
        ↓
IMPLEMENTATION SHORTFALL
        ↓
COST MODEL CALIBRATION
```

---

# 23.132 Point-in-Time Rule

At execution time T, use only:

```text
quotes available at T
volume available at T
open orders known at T
positions known at T
risk state known at T
```

No future VWAP or volume profile data unless using historically estimated profiles.

---

# 23.133 Expected Volume Curve Rule

VWAP execution may use:

```text
historical expected intraday volume profile
```

but not future realized same-day volume.

---

# 23.134 Cost Model Point-in-Time Rule

Cost model parameters must be calibrated only on prior execution history.

---

# 23.135 Execution Quality Status

Possible:

```text
VALID
PARTIAL_FILL
HIGH_SLIPPAGE
HIGH_IMPACT
LOW_LIQUIDITY
STALE_MARKET_DATA
BROKER_ERROR
REJECTED
HALTED
```

---

# 23.136 Research Diagnostics

Analyze execution cost by:

```text
liquidity bucket
order size
time of day
volatility regime
sector
order type
strategy
```

---

# 23.137 Slippage Distribution

Track:

```text
median
p75
p90
p95
worst
```

not only mean.

---

# 23.138 Cost Forecast Accuracy

Measure:

```text
MAE
RMSE
bias
```

between predicted and realized cost.

---

# 23.139 Alpha Capture Ratio

Possible:

```text
alpha_capture =
realized_post_cost_alpha
/
expected_pre_cost_alpha
```

---

# 23.140 Execution Drag

```text
execution_drag =
gross_strategy_return
-
net_strategy_return
```

---

# 23.141 Important Quant Rules

## Rule 1 — Alpha Must Be Compared with Cost

Do not trade economically negative opportunities.

## Rule 2 — Large Orders Must Be Capacity-Aware

Order size relative to ADV matters.

## Rule 3 — Market Impact Is Nonlinear

Doubling order size can more than double cost.

## Rule 4 — Urgency and Cost Trade Off

Faster execution usually costs more but reduces alpha-decay risk.

## Rule 5 — Backtests Must Use Realistic Fills

No free execution assumptions.

## Rule 6 — Same-Close Execution Can Cause Look-Ahead

Respect decision and execution timestamps.

## Rule 7 — Partial Fills Are Real

Not every order fills completely.

## Rule 8 — Risk Reduction Can Override Cost Minimization

Emergency exits prioritize safety.

## Rule 9 — Duplicate Orders Must Be Prevented

Idempotency is mandatory.

## Rule 10 — Reconciliation Is Mandatory

Internal and broker state must match.

## Rule 11 — Cost Models Need Continuous Calibration

Actual fills should improve estimates.

## Rule 12 — Every Order Must Be Auditable

Preserve full decision-to-fill history.

---

# 23.142 Completion Criteria

Step 23 is complete when Open Analytics can answer:

1. What quantity needs to be traded?
2. What is the trade notional?
3. How urgent is the trade?
4. Which order type should be used?
5. Should the order be sliced?
6. What participation rate should be used?
7. What is expected spread cost?
8. What is expected market impact?
9. What are expected taxes/fees?
10. What is total expected transaction cost?
11. Is expected alpha still positive after costs?
12. What execution benchmark applies?
13. What was the arrival price?
14. What was the average fill price?
15. What was realized slippage?
16. What was implementation shortfall?
17. Was the order partially filled?
18. Were any orders rejected or cancelled?
19. Does the broker position match the internal position?
20. How accurate was the cost model?
21. How much alpha was lost to execution?
22. Can the historical execution be reproduced realistically in backtests?

Once these are reliable, the Execution & Transaction Cost Engine is ready to feed:

```text
Step 24 — Backtesting Engine
```

---

# Step 23 Final Output

The Execution & Transaction Cost Engine transforms:

```text
Final Safe Position Targets
+
Market Liquidity
+
Signal Urgency
+
Broker State
```

into:

```text
Executable Orders
Order Slicing
Order-Type Selection
Participation Rates
Expected Spread Cost
Expected Slippage
Expected Market Impact
Expected Fees
Net Alpha After Cost
Execution Benchmarks
Fill Monitoring
Realized Slippage
Implementation Shortfall
Execution Quality
Cost Model Calibration
Audit Trail
```

This becomes the trade-realization layer for Open Analytics.
