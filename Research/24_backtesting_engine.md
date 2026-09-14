# Open Analytics — Step 24: Backtesting Engine

## Purpose

The **Backtesting Engine** simulates how a strategy, signal, factor model, portfolio construction process, risk-control system, and execution policy would have behaved historically using only information that would have been available at each point in time.

This is the primary validation layer for the Open Analytics quant stack.

The engine should answer:

- Would this strategy have worked historically?
- Was the result caused by genuine alpha or data leakage?
- Are returns robust across different periods?
- Are results still attractive after transaction costs?
- Does the strategy survive realistic slippage and liquidity limits?
- Does performance depend on a few stocks or a few months?
- Does the strategy work across market regimes?
- Does it survive out-of-sample testing?
- How sensitive is performance to parameter changes?
- What turnover and capacity does the strategy require?
- What drawdowns should be expected?
- Are there hidden factor, sector, or beta exposures?
- Can the entire test be reproduced exactly later?

The output feeds directly into:

- Performance Analytics
- Attribution
- Strategy Research
- Model Validation
- Production Approval
- ML Dataset Validation
- Portfolio Governance

---

# 24.1 Core Principle

A backtest is a simulation of decisions, not merely a calculation of historical returns.

A valid backtest must reproduce the historical sequence:

```text
Information becomes available
        ↓
Features are calculated
        ↓
Signal is generated
        ↓
Portfolio is constructed
        ↓
Risk controls are applied
        ↓
Orders are generated
        ↓
Execution is simulated
        ↓
Positions and cash are updated
        ↓
PnL is recorded
```

Do not jump directly from:

```text
historical factor rank
```

to:

```text
future return
```

and call that a production backtest.

---

# 24.2 Required Inputs

The Backtesting Engine may consume outputs from nearly every prior engine.

Required market data:

```text
historical prices
historical volumes
corporate actions
exchange calendar
```

Universe data:

```text
historical universe membership
historical listings
delistings
suspensions
```

Feature data:

```text
returns
risk
liquidity
trend
momentum
fundamentals
valuation
factors
news
flow
derivatives
breadth
regime
signals
confidence
```

Portfolio inputs:

```text
portfolio rules
risk rules
execution rules
transaction cost model
```

---

# 24.3 Point-in-Time Data Requirement

Every feature used at historical timestamp T must have been available by T.

This includes:

```text
prices
fundamentals
news
index membership
sector mapping
flow data
analyst estimates
macro data
```

No future revisions.

---

# 24.4 Look-Ahead Bias

The engine must explicitly prevent:

```text
future prices
future financial statements
future index constituents
future analyst revisions
future news classifications
future corporate-action knowledge
```

from entering past decisions.

---

# 24.5 Survivorship Bias

Historical tests must include:

```text
delisted stocks
failed companies
merged companies
stocks removed from indices
inactive securities
```

if they were eligible at the time.

---

# 24.6 Delisting Handling

A delisted stock cannot simply disappear.

Need logic for:

```text
last tradable price
delisting proceeds
forced exit
zero recovery where appropriate
```

Document methodology.

---

# 24.7 IPO Handling

A newly listed stock becomes eligible only when strategy requirements are met.

Example:

```text
minimum 63 valid sessions
```

for a 3-month momentum model.

---

# 24.8 Suspension Handling

Suspended stocks:

```text
cannot trade
cannot exit
```

during the suspension.

Backtest must retain exposure and mark risk appropriately.

---

# 24.9 Trading Calendar

Use actual exchange sessions.

Do not assume:

```text
252 exact sessions every year
```

for trade simulation.

---

# 24.10 Decision Timestamp

Store:

```text
decision_timestamp
```

This determines what data is available.

---

# 24.11 Signal Timestamp

Store:

```text
signal_timestamp
```

---

# 24.12 Portfolio Timestamp

Store:

```text
portfolio_timestamp
```

---

# 24.13 Execution Timestamp

Store:

```text
execution_timestamp
```

This separation prevents hidden same-bar leakage.

---

# 24.14 Signal at Close

If a strategy uses close price to generate a signal:

```text
do not assume same-close fill
```

unless the model explicitly participates in closing auction with valid assumptions.

---

# 24.15 Next-Open Execution

A conservative daily strategy baseline:

```text
signal at close T
execute at open T+1
```

with slippage/costs.

---

# 24.16 Next-VWAP Execution

Alternative:

```text
signal at close T
execute using simulated VWAP on T+1
```

if intraday data exists.

---

# 24.17 Intraday Strategies

Require timestamp-resolved:

```text
market data
signal data
order data
```

Daily OHLCV is insufficient for accurate intraday backtesting.

---

# 24.18 Event Timing

For news/event strategy:

```text
event public_available_at
```

determines earliest valid trade time.

---

# 24.19 Fundamental Timing

Use:

```text
filing / announcement availability date
```

not fiscal period-end date.

---

# 24.20 Macro Timing

Use:

```text
release_timestamp
```

not the reference month.

---

# 24.21 Universe Construction

For each test date:

```text
build historical eligible universe
```

from Step 1.

---

# 24.22 Universe Snapshot

Store:

```text
date
universe_id
eligible_instruments
```

for reproducibility.

---

# 24.23 Signal Generation

The backtester should call the same logical signal definitions used in production.

Avoid maintaining a separate simplified research-only formula unless explicitly versioned.

---

# 24.24 Portfolio Construction

Backtest must use the actual:

```text
selection
weighting
constraints
```

logic from Step 21.

---

# 24.25 Position Sizing

Use Step 22 logic:

```text
volatility scaling
confidence scaling
risk caps
liquidity caps
```

---

# 24.26 Execution Simulation

Use Step 23 logic.

Do not assume:

```text
infinite liquidity
zero slippage
zero spread
perfect fills
```

---

# 24.27 Transaction Costs

Include:

```text
spread
slippage
market impact
brokerage
exchange fees
taxes
stamp duty
STT where applicable
```

---

# 24.28 Cost Schedule Versioning

Historical cost schedules may change.

Store:

```text
fee_schedule_version
```

by period.

---

# 24.29 Slippage Model

Possible V1:

```text
half spread
+
volatility-scaled impact
+
order/ADV impact
```

---

# 24.30 Capacity Constraint

Limit historical trade size using:

```text
ADV
participation rate
days to liquidate
```

---

# 24.31 Partial Fill Simulation

Large orders may not fill fully.

Track:

```text
filled_quantity
unfilled_quantity
```

---

# 24.32 Limit Order Simulation

Daily high/low crossing a limit does not guarantee fill.

Use:

```text
intraday data
```

or conservative fill probability assumptions.

---

# 24.33 Stop-Loss Simulation

If price gaps through stop:

```text
fill at next available modeled price
```

not the stop level.

---

# 24.34 Market Order Simulation

Use realistic:

```text
spread
slippage
impact
```

---

# 24.35 Portfolio Accounting

Track:

```text
cash
positions
market value
equity
realized PnL
unrealized PnL
fees
```

---

# 24.36 Cash Ledger

Store:

```text
opening_cash
trade_cash_flow
fees
dividends
interest
closing_cash
```

---

# 24.37 Position Ledger

For each position:

```text
quantity
average_cost
market_price
market_value
unrealized_pnl
realized_pnl
```

---

# 24.38 Dividend Handling

Cash dividends should be credited on appropriate dates.

Avoid double counting when using total-return-adjusted prices.

---

# 24.39 Split Handling

Share quantity and price must adjust correctly.

---

# 24.40 Bonus Issue Handling

Likewise adjust quantity.

---

# 24.41 Rights Issue Handling

Need explicit methodology:

```text
participate
sell rights
ignore rights
```

depending on strategy assumptions.

---

# 24.42 Merger Handling

Map old security into new consideration.

---

# 24.43 Spin-Off Handling

Create new position if strategy assumes holder receives spun-off shares.

---

# 24.44 Cash Interest

If relevant, model:

```text
cash yield
```

---

# 24.45 Borrow Cost

For short portfolios:

```text
borrow fee
```

must be modeled.

---

# 24.46 Short Availability

Historical shortability may differ.

Use:

```text
short_eligible
```

where possible.

---

# 24.47 Margin

For derivatives or leveraged portfolios:

```text
margin used
margin available
```

must be simulated.

---

# 24.48 Leverage

Track:

```text
gross exposure
net exposure
leverage
```

---

# 24.49 Rebalance Frequency

Possible:

```text
DAILY
WEEKLY
MONTHLY
QUARTERLY
EVENT_DRIVEN
```

---

# 24.50 Rebalance Calendar

Store exact historical rebalance dates.

---

# 24.51 Entry Rules

Explicitly define:

```text
entry threshold
ranking cutoff
eligibility
```

---

# 24.52 Exit Rules

Explicitly define:

```text
rank exit
signal exit
stop exit
time exit
risk exit
event exit
```

---

# 24.53 Buffer Rules

Example:

```text
enter top 10%
exit below top 20%
```

must be implemented consistently.

---

# 24.54 No-Trade Zone

Avoid small target-weight changes.

---

# 24.55 Turnover

Track:

```text
daily turnover
monthly turnover
annual turnover
```

---

# 24.56 Gross Returns

Before transaction costs:

```text
gross_return
```

---

# 24.57 Net Returns

After costs:

```text
net_return
```

---

# 24.58 Daily Portfolio Return

Recommended:

```text
portfolio_return_t =
equity_t / equity_(t-1) - 1
```

adjusted for external cash flows.

---

# 24.59 Cumulative Return

```text
cumulative_return =
product(1 + daily_returns) - 1
```

---

# 24.60 CAGR

```text
CAGR =
(final_value / initial_value)^(1/years) - 1
```

---

# 24.61 Volatility

Annualized realized portfolio volatility.

---

# 24.62 Sharpe Ratio

```text
Sharpe =
annualized excess return
/
annualized volatility
```

Use point-in-time risk-free series where appropriate.

---

# 24.63 Sortino Ratio

Use downside deviation.

---

# 24.64 Max Drawdown

Track:

```text
maximum peak-to-trough decline
```

---

# 24.65 Drawdown Duration

Track:

```text
days underwater
```

---

# 24.66 Time to Recovery

Track.

---

# 24.67 Calmar Ratio

```text
CAGR / abs(max_drawdown)
```

---

# 24.68 Win Rate

For trade-based strategies:

```text
winning_trades / total_trades
```

---

# 24.69 Profit Factor

```text
gross_profit / gross_loss
```

---

# 24.70 Average Win

Track.

---

# 24.71 Average Loss

Track.

---

# 24.72 Payoff Ratio

```text
average_win / abs(average_loss)
```

---

# 24.73 Expectancy

```text
win_rate × avg_win
-
loss_rate × avg_loss
```

---

# 24.74 Holding Period

Track:

```text
average
median
distribution
```

---

# 24.75 Trade Count

Store:

```text
total_trades
```

---

# 24.76 Turnover Efficiency

Possible:

```text
net_return / turnover
```

---

# 24.77 Alpha Capture

Compare:

```text
gross expected alpha
vs
realized net alpha
```

---

# 24.78 Benchmark Return

Backtest against:

```text
NIFTY
sector index
custom benchmark
```

---

# 24.79 Excess Return

```text
portfolio_return - benchmark_return
```

---

# 24.80 Tracking Error

Benchmark-aware portfolios.

---

# 24.81 Information Ratio

```text
annualized excess return / tracking error
```

---

# 24.82 Beta

Portfolio beta to benchmark.

---

# 24.83 Alpha

Regression-based alpha where relevant.

---

# 24.84 Up Capture

Track.

---

# 24.85 Down Capture

Track.

---

# 24.86 Market Regime Performance

Split results by:

```text
BULL
BEAR
SIDEWAYS
HIGH_VOL
LOW_VOL
```

---

# 24.87 Sector Performance

Attribution by sector.

---

# 24.88 Factor Exposure Performance

Track factor exposures over time.

---

# 24.89 Liquidity Bucket Performance

Compare:

```text
high liquidity
low liquidity
```

---

# 24.90 Size-Bucket Performance

Compare:

```text
large cap
mid cap
small cap
```

---

# 24.91 Signal Decile Performance

For ranking strategies:

```text
decile 10
...
decile 1
```

---

# 24.92 Quantile Monotonicity

Check whether higher scores systematically lead to better future returns.

---

# 24.93 IC Backtest

Track:

```text
daily / weekly rank IC
```

---

# 24.94 IC Mean

Track.

---

# 24.95 IC IR

Track.

---

# 24.96 Positive IC Frequency

Track.

---

# 24.97 Factor Return Spread

Top-minus-bottom quantile return.

---

# 24.98 Exposure Drift

Track whether strategy unintentionally shifts toward:

```text
small caps
high beta
one sector
high volatility
```

---

# 24.99 Concentration

Track:

```text
top 1
top 5
top 10
HHI
effective position count
```

---

# 24.100 Risk Contribution

Track position/sector/factor risk contributions historically.

---

# 24.101 Capacity Analysis

Run same strategy at different capital levels.

Example:

```text
₹10 crore
₹50 crore
₹100 crore
```

and observe:

```text
impact
turnover
alpha decay
```

---

# 24.102 Cost Sensitivity

Run:

```text
base cost
1.5x cost
2x cost
```

---

# 24.103 Slippage Sensitivity

Same idea.

---

# 24.104 Parameter Sensitivity

Vary:

```text
lookback
threshold
holding period
position cap
sector cap
```

A robust strategy should not work only at one exact parameter.

---

# 24.105 Grid Search Warning

Avoid selecting the best parameter from thousands of trials without correction.

---

# 24.106 Multiple Testing Bias

The more strategies tested, the higher the chance of false discoveries.

Track:

```text
number_of_trials
```

---

# 24.107 Data Snooping

Avoid repeatedly tuning strategy on same historical period.

---

# 24.108 In-Sample Period

Explicitly define.

---

# 24.109 Validation Period

Explicitly define.

---

# 24.110 Out-of-Sample Period

Explicitly define.

---

# 24.111 Walk-Forward Testing

Recommended process:

```text
train
        ↓
validate
        ↓
test next period
        ↓
roll forward
```

---

# 24.112 Expanding Window

Example:

```text
train from start through T
test T+1 onward
```

---

# 24.113 Rolling Window

Example:

```text
use last N years
```

for each recalibration.

---

# 24.114 Purged Cross-Validation

For overlapping labels, prevent leakage between train/test.

Useful for ML research.

---

# 24.115 Embargo

Add temporal gap between train and test when needed.

---

# 24.116 Nested Validation

For hyperparameter tuning:

```text
inner validation
outer out-of-sample
```

---

# 24.117 Walk-Forward Recalibration

If factor weights or models change over time, recalibrate only using prior history.

---

# 24.118 Model Freeze

Store exact model/parameter version used in each test period.

---

# 24.119 Strategy Versioning

Store:

```text
strategy_name
strategy_version
```

---

# 24.120 Dataset Versioning

Store:

```text
dataset_version
```

---

# 24.121 Feature Versioning

Store feature-engine versions.

---

# 24.122 Cost Model Versioning

Store.

---

# 24.123 Portfolio Model Versioning

Store.

---

# 24.124 Risk Model Versioning

Store.

---

# 24.125 Reproducibility Hash

Possible:

```text
config_hash
dataset_hash
code_commit
```

---

# 24.126 Random Seed

For stochastic models:

```text
random_seed
```

must be stored.

---

# 24.127 Backtest Configuration

Recommended:

```text
start_date
end_date

initial_capital
benchmark

universe_id

signal_name
signal_version

portfolio_model_version
risk_control_version
execution_policy_version

rebalance_frequency

cost_model_version

random_seed
```

---

# 24.128 Backtest Run Record

```text
backtest_id
created_at

strategy_name
strategy_version

start_date
end_date

initial_capital
final_capital

gross_return
net_return

CAGR
volatility
Sharpe
Sortino

max_drawdown
Calmar

turnover
transaction_cost

benchmark_return
excess_return

status
```

---

# 24.129 Daily Portfolio Record

```text
backtest_id
date

cash
gross_exposure
net_exposure

market_value
portfolio_equity

gross_return
net_return

benchmark_return
excess_return

drawdown

portfolio_beta
portfolio_volatility

turnover
cost
```

---

# 24.130 Trade Record

```text
backtest_id
trade_id

instrument_key

signal_date
decision_date
execution_date

side
quantity

entry_price
exit_price

gross_pnl
net_pnl

fees
slippage
impact

holding_days

entry_reason
exit_reason
```

---

# 24.131 Position Record

```text
backtest_id
date
instrument_key

quantity
weight

market_value
unrealized_pnl

alpha_score
confidence
risk_contribution
```

---

# 24.132 Diagnostics Record

```text
backtest_id
date

IC
rank_IC

breadth
regime

turnover
cost

sector_exposures
factor_exposures
```

---

# 24.133 Initial Production Backtest Modes

Recommended:

```text
FACTOR_QUANTILE_TEST
LONG_ONLY_RANKING
LONG_SHORT_RANKING
PORTFOLIO_SIMULATION
EVENT_STUDY
SIGNAL_IC_TEST
```

---

# 24.134 Factor Quantile Test

Process:

```text
rank stocks
split into quantiles
measure forward returns
```

Useful for factor validation.

---

# 24.135 Long-Only Ranking Test

Example:

```text
hold top decile
```

with realistic turnover/costs.

---

# 24.136 Long-Short Ranking Test

Example:

```text
long top decile
short bottom decile
```

with borrow/cost assumptions.

---

# 24.137 Event Study

For events:

```text
pre-event window
event date
post-event window
```

Track abnormal returns.

---

# 24.138 Signal IC Test

For every date:

```text
signal rank
vs
future return rank
```

---

# 24.139 Portfolio Simulation

Full stack:

```text
signal
portfolio
risk
execution
cash
PnL
```

This is production-grade validation.

---

# 24.140 Initial Production V1

Recommended V1:

```text
1. Historical point-in-time universe.
2. Daily signal generation after close.
3. Execute next session with conservative cost model.
4. Apply portfolio and risk rules.
5. Track cash, positions, corporate actions.
6. Deduct realistic costs.
7. Compare with benchmark.
8. Save daily portfolio/trade records.
9. Report performance, drawdown, turnover, exposures.
10. Run walk-forward out-of-sample validation.
```

---

# 24.141 Backtest Processing Flow

Recommended:

```text
HISTORICAL POINT-IN-TIME DATA
        ↓
UNIVERSE SNAPSHOT
        ↓
FEATURE CALCULATION
        ↓
SIGNAL GENERATION
        ↓
CONFIDENCE
        ↓
PORTFOLIO CONSTRUCTION
        ↓
POSITION SIZING / RISK
        ↓
ORDER GENERATION
        ↓
EXECUTION SIMULATION
        ↓
COSTS
        ↓
CASH / POSITION ACCOUNTING
        ↓
DAILY NAV
        ↓
PERFORMANCE METRICS
        ↓
ATTRIBUTION
        ↓
OUT-OF-SAMPLE VALIDATION
        ↓
ROBUSTNESS TESTING
```

---

# 24.142 Point-in-Time Safety Checks

For every backtest date verify:

```text
feature_timestamp <= decision_timestamp
signal_timestamp <= decision_timestamp
news_available_at <= decision_timestamp
fundamental_available_at <= decision_timestamp
```

---

# 24.143 Leakage Audit

Create automated tests for:

```text
future price leakage
forward-return leakage
future membership leakage
future filing leakage
future estimate leakage
```

---

# 24.144 Survivorship Audit

Verify historical universe contains delisted/inactive names when required.

---

# 24.145 Corporate Action Audit

Verify:

```text
split
bonus
dividend
merger
```

handling.

---

# 24.146 Execution Audit

Check:

```text
same-close fills
zero slippage
oversized ADV participation
```

for unrealistic assumptions.

---

# 24.147 Cost Audit

Check transaction-cost assumptions are nonzero and strategy-appropriate.

---

# 24.148 Capacity Audit

Check order sizes do not exceed configured liquidity limits.

---

# 24.149 Rebalance Audit

Verify portfolio only changes on allowed dates/events.

---

# 24.150 Benchmark Alignment

Benchmark return series must match:

```text
same trading calendar
same currency
same frequency
```

---

# 24.151 Risk-Free Alignment

Use point-in-time risk-free data for Sharpe/excess return where needed.

---

# 24.152 Missing Price Handling

Do not invent prices.

If stock is not trading:

```text
carry prior mark only if economically valid
```

and block execution.

---

# 24.153 Stale Price Flag

Track.

---

# 24.154 Price Limit Handling

Circuit-bound stocks may not be executable.

---

# 24.155 Corporate Event Blackout

If strategy uses event blackout rules, apply historically.

---

# 24.156 Trade-Level Attribution

For each trade explain PnL from:

```text
signal
market move
sector move
execution cost
```

later in Step 26.

---

# 24.157 Strategy Comparison

Compare different strategy versions using same data and assumptions.

---

# 24.158 Baseline Strategies

Always include simple baselines:

```text
buy-and-hold benchmark
equal-weight universe
top-factor equal-weight
```

---

# 24.159 Benchmark Beating Is Not Enough

Assess:

```text
risk-adjusted return
drawdown
capacity
turnover
consistency
```

---

# 24.160 Statistical Significance

Estimate whether results are likely distinguishable from noise.

Possible:

```text
t-statistics
bootstrap confidence intervals
```

---

# 24.161 Bootstrap Analysis

Resample returns/trades to estimate performance uncertainty.

---

# 24.162 Block Bootstrap

Prefer block methods when serial dependence matters.

---

# 24.163 Monte Carlo Trade Resampling

For trade-based strategies, reorder/resample trades.

---

# 24.164 Drawdown Distribution

Estimate possible drawdown ranges.

---

# 24.165 Return Confidence Interval

Store.

---

# 24.166 Sharpe Uncertainty

Estimate confidence interval around Sharpe.

---

# 24.167 Deflated Sharpe Concept

For many strategy trials, adjust expectations for selection bias.

Advanced research diagnostic.

---

# 24.168 Probability of Backtest Overfitting

Advanced methods may be added later.

---

# 24.169 Stress Period Analysis

Explicitly inspect:

```text
market crashes
volatility spikes
liquidity crises
```

---

# 24.170 Regime Coverage

Ensure backtest includes multiple regimes where possible.

---

# 24.171 Year-by-Year Returns

Track.

---

# 24.172 Month-by-Month Returns

Track.

---

# 24.173 Rolling 12M Return

Track.

---

# 24.174 Rolling Sharpe

Track.

---

# 24.175 Rolling Drawdown

Track.

---

# 24.176 Rolling Beta

Track.

---

# 24.177 Rolling Turnover

Track.

---

# 24.178 Performance Concentration

Measure how much total return came from:

```text
best 10 days
best 10 trades
best year
best sector
```

---

# 24.179 Remove-Best-Days Test

Check fragility if strongest days are removed.

---

# 24.180 Remove-Best-Trades Test

Same for trade-based systems.

---

# 24.181 Return Contribution Distribution

Track whether performance is broad or concentrated.

---

# 24.182 Strategy Decay

Compare older vs recent performance.

---

# 24.183 Live-Like Simulation

Use:

```text
walk-forward
point-in-time
realistic costs
```

to mimic production as closely as possible.

---

# 24.184 Paper Trading Link

Backtest methodology should match later paper/live execution as much as possible.

---

# 24.185 Backtest Approval State

Possible:

```text
RESEARCH
VALIDATED
PAPER_READY
PRODUCTION_CANDIDATE
REJECTED
```

---

# 24.186 Backtest Quality Status

Possible:

```text
VALID
LEAKAGE_WARNING
SURVIVORSHIP_WARNING
COST_MODEL_WARNING
INSUFFICIENT_HISTORY
LOW_SAMPLE_SIZE
LOW_REGIME_COVERAGE
INVALID
```

---

# 24.187 Important Quant Rules

## Rule 1 — Backtest the Full Decision Process

Not only factor returns.

## Rule 2 — Point-in-Time Data Is Mandatory

No future information.

## Rule 3 — Survivorship Bias Must Be Eliminated

Historical failures matter.

## Rule 4 — Same-Close Fills Are Dangerous

Respect decision/execution timing.

## Rule 5 — Transaction Costs Must Be Included

Always.

## Rule 6 — Liquidity and Capacity Must Be Modeled

A theoretical strategy may be untradeable.

## Rule 7 — Corporate Actions Must Be Correct

Position quantities and cash flows matter.

## Rule 8 — Out-of-Sample Testing Is Mandatory

In-sample performance is not sufficient.

## Rule 9 — Parameter Robustness Matters

Avoid single-point optimization.

## Rule 10 — Compare Against Simple Baselines

Complexity must earn its place.

## Rule 11 — Store Every Version

Data, features, signals, risk, execution, and strategy.

## Rule 12 — Reproducibility Is Mandatory

A backtest should be rerunnable exactly.

---

# 24.188 Completion Criteria

Step 24 is complete when Open Analytics can answer:

1. What historical universe was used?
2. Was every feature point-in-time correct?
3. Were delisted and failed stocks included?
4. What signal version was tested?
5. What portfolio rules were used?
6. What risk controls were used?
7. What execution model was used?
8. What transaction-cost assumptions were used?
9. What was gross return?
10. What was net return?
11. What was CAGR?
12. What was volatility?
13. What were Sharpe and Sortino?
14. What was max drawdown?
15. How long did drawdowns last?
16. What was turnover?
17. What were transaction costs?
18. What was capacity?
19. How did the strategy perform by regime?
20. How did it perform by sector and size bucket?
21. Did top signal quantiles outperform lower ones?
22. What was IC / Rank IC?
23. Did performance survive out-of-sample testing?
24. Did it survive higher cost/slippage assumptions?
25. Was performance concentrated in a few periods?
26. Were any leakage/survivorship warnings detected?
27. Can the full backtest be reproduced exactly?

Once these are reliable, the Backtesting Engine is ready to feed:

```text
Step 25 — Performance Analytics Engine
```

---

# Step 24 Final Output

The Backtesting Engine transforms:

```text
Historical Point-in-Time Data
+
Signals
+
Portfolio Rules
+
Risk Controls
+
Execution Model
```

into:

```text
Historical Portfolio Simulation
Gross / Net Returns
NAV
PnL
Transaction Costs
Turnover
Sharpe / Sortino
Drawdowns
Benchmark Comparison
IC / Rank IC
Quantile Performance
Capacity
Regime Performance
Sensitivity Tests
Walk-Forward Results
Leakage Diagnostics
Reproducible Backtest Records
```

This becomes the strategy-validation layer for Open Analytics.
