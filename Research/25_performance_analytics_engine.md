# Open Analytics — Step 25: Performance Analytics Engine

## Purpose

The **Performance Analytics Engine** converts backtest, paper-trading, and live portfolio return streams into a complete professional performance evaluation.

This layer should answer:

- How much did the strategy make?
- How much risk was taken?
- Was performance consistent?
- What was the worst drawdown?
- How long did recovery take?
- How did the strategy compare with its benchmark?
- Was excess return driven by beta or genuine alpha?
- Was performance concentrated in a few periods or trades?
- How stable was Sharpe over time?
- How did results vary by market regime?
- How much performance was lost to turnover and transaction costs?
- How did live performance compare with backtest expectations?
- Is the strategy degrading?
- What return/risk profile should realistically be expected going forward?

The output feeds directly into:

- Attribution
- Strategy monitoring
- Production governance
- Capital allocation
- Model review
- Risk oversight
- Investor / research reporting
- ML / strategy lifecycle decisions

---

# 25.1 Core Principle

Performance should never be judged from:

```text
total return alone
```

A professional evaluation requires:

```text
Return
Risk
Drawdown
Consistency
Benchmark Relative Performance
Tail Behavior
Turnover
Costs
Capacity
Regime Stability
```

---

# 25.2 Required Inputs

Minimum:

```text
date
portfolio_return
portfolio_value
```

Preferred:

```text
gross_return
net_return
benchmark_return
risk_free_rate

gross_exposure
net_exposure
turnover
transaction_cost

drawdown
portfolio_beta
portfolio_volatility

market_regime
```

Optional:

```text
trade-level PnL
factor exposures
sector exposures
position-level contributions
```

---

# 25.3 Return Series

Store separately:

```text
gross_return
net_return
benchmark_return
excess_return
```

Do not overwrite gross returns with net returns.

---

# 25.4 Daily Return

```text
r_t =
NAV_t / NAV_(t-1) - 1
```

Adjust correctly for external capital flows.

---

# 25.5 Weekly Return

Compound daily returns:

```text
weekly_return =
product(1 + daily_returns) - 1
```

---

# 25.6 Monthly Return

Likewise:

```text
monthly_return
```

---

# 25.7 Quarterly Return

Store:

```text
quarterly_return
```

---

# 25.8 Annual Return

Store:

```text
calendar_year_return
```

---

# 25.9 Cumulative Return

```text
cumulative_return =
product(1 + r_t) - 1
```

---

# 25.10 CAGR

```text
CAGR =
(final_NAV / initial_NAV)^(1 / years) - 1
```

---

# 25.11 Geometric Mean Return

Store where useful:

```text
geometric_mean_return
```

---

# 25.12 Arithmetic Mean Return

Store:

```text
average_daily_return
average_monthly_return
```

---

# 25.13 Gross vs Net Return

Track:

```text
gross_cumulative_return
net_cumulative_return
```

Difference represents:

```text
execution + fees + financing drag
```

---

# 25.14 Cost Drag

```text
cost_drag =
gross_return - net_return
```

Store:

```text
cost_drag_bps
```

---

# 25.15 Annualized Volatility

```text
annualized_volatility =
std(daily_returns) × sqrt(annualization_factor)
```

Use actual platform convention consistently.

---

# 25.16 Downside Deviation

Calculate using returns below:

```text
0
```

or specified target return.

Store:

```text
downside_deviation
```

---

# 25.17 Upside Volatility

Optional:

```text
upside_volatility
```

---

# 25.18 Sharpe Ratio

```text
Sharpe =
annualized_excess_return
/
annualized_volatility
```

Use point-in-time risk-free rate where appropriate.

---

# 25.19 Sortino Ratio

```text
Sortino =
annualized_return - target_return
/
annualized_downside_deviation
```

---

# 25.20 Calmar Ratio

```text
Calmar =
CAGR / abs(max_drawdown)
```

---

# 25.21 Sterling Ratio

Optional:

```text
return / drawdown measure
```

Store only if methodology is fixed and documented.

---

# 25.22 Omega Ratio

Optional advanced metric.

Possible:

```text
Omega(threshold)
```

Useful when return distribution is non-normal.

---

# 25.23 Information Ratio

```text
IR =
annualized_excess_return
/
tracking_error
```

---

# 25.24 Tracking Error

```text
tracking_error =
annualized std(portfolio_return - benchmark_return)
```

---

# 25.25 Active Return

```text
active_return =
portfolio_return - benchmark_return
```

---

# 25.26 Jensen Alpha

Regression:

```text
portfolio excess return
=
alpha
+
beta × market excess return
+
error
```

Store:

```text
jensen_alpha
```

---

# 25.27 Beta

Store:

```text
portfolio_beta
```

Rolling and full-period.

---

# 25.28 R-Squared

Store:

```text
benchmark_r_squared
```

This shows how much variation is explained by benchmark movement.

---

# 25.29 Treynor Ratio

Optional:

```text
excess_return / beta
```

---

# 25.30 Up Capture Ratio

Measure performance when benchmark is positive.

Store:

```text
up_capture_ratio
```

---

# 25.31 Down Capture Ratio

Store:

```text
down_capture_ratio
```

---

# 25.32 Capture Ratio

Possible:

```text
up_capture / down_capture
```

---

# 25.33 Drawdown

For every date:

```text
drawdown =
NAV / running_peak_NAV - 1
```

---

# 25.34 Maximum Drawdown

Store:

```text
max_drawdown
```

---

# 25.35 Drawdown Start

Store:

```text
max_drawdown_start
```

---

# 25.36 Drawdown Trough

Store:

```text
max_drawdown_trough
```

---

# 25.37 Drawdown Recovery Date

Store:

```text
max_drawdown_recovery
```

if recovered.

---

# 25.38 Drawdown Duration

Track:

```text
days_from_peak_to_recovery
```

---

# 25.39 Time Under Water

Track cumulative percentage of time portfolio remains below previous peak.

Store:

```text
time_under_water_pct
```

---

# 25.40 Average Drawdown

Store.

---

# 25.41 Drawdown Distribution

Store:

```text
median_drawdown
p90_drawdown
p95_drawdown
```

where useful.

---

# 25.42 Top Drawdowns

Maintain:

```text
top_5_drawdowns
```

with:

```text
start
trough
recovery
depth
duration
```

---

# 25.43 Ulcer Index

Optional:

```text
sqrt(mean(drawdown^2))
```

Useful for persistent drawdown assessment.

---

# 25.44 Recovery Factor

Possible:

```text
net_profit / abs(max_drawdown)
```

---

# 25.45 Winning Days

```text
positive_day_ratio
```

---

# 25.46 Losing Days

```text
negative_day_ratio
```

---

# 25.47 Best Day

Store:

```text
best_daily_return
```

---

# 25.48 Worst Day

Store:

```text
worst_daily_return
```

---

# 25.49 Best Month

Store.

---

# 25.50 Worst Month

Store.

---

# 25.51 Positive Months

```text
positive_month_ratio
```

---

# 25.52 Positive Quarters

Store.

---

# 25.53 Positive Years

Store.

---

# 25.54 Return Consistency Score

Possible inputs:

```text
positive months
rolling Sharpe stability
drawdown frequency
return dispersion
```

Output:

```text
performance_consistency_score
```

---

# 25.55 Return Skewness

Store:

```text
return_skewness
```

---

# 25.56 Return Kurtosis

Store:

```text
return_kurtosis
```

---

# 25.57 Tail Ratio

Possible:

```text
95th percentile gain
/
abs(5th percentile loss)
```

Store:

```text
tail_ratio
```

---

# 25.58 VaR

Historical or model-based:

```text
portfolio_var
```

---

# 25.59 CVaR / Expected Shortfall

Store:

```text
portfolio_cvar
```

---

# 25.60 Worst N-Day Return

Recommended:

```text
worst_5d_return
worst_21d_return
```

---

# 25.61 Best N-Day Return

Store:

```text
best_5d_return
best_21d_return
```

---

# 25.62 Rolling Return

Recommended windows:

```text
rolling_21d_return
rolling_63d_return
rolling_126d_return
rolling_252d_return
```

---

# 25.63 Rolling Volatility

Store:

```text
rolling_vol_21d
rolling_vol_63d
rolling_vol_252d
```

---

# 25.64 Rolling Sharpe

Store:

```text
rolling_sharpe_63d
rolling_sharpe_126d
rolling_sharpe_252d
```

---

# 25.65 Rolling Sortino

Store where useful.

---

# 25.66 Rolling Beta

Store:

```text
rolling_beta_63d
rolling_beta_252d
```

---

# 25.67 Rolling Alpha

Store.

---

# 25.68 Rolling Tracking Error

Store.

---

# 25.69 Rolling Information Ratio

Store.

---

# 25.70 Rolling Max Drawdown

Store.

---

# 25.71 Rolling Turnover

Store:

```text
rolling_turnover_21d
rolling_turnover_63d
```

---

# 25.72 Rolling Cost Drag

Store.

---

# 25.73 Regime Performance

For each regime:

```text
return
volatility
Sharpe
drawdown
hit rate
turnover
```

Store:

```text
performance_by_regime
```

---

# 25.74 Bull Regime Performance

Store separately.

---

# 25.75 Bear Regime Performance

Store separately.

---

# 25.76 High-Volatility Regime Performance

Store separately.

---

# 25.77 Low-Volatility Regime Performance

Store separately.

---

# 25.78 Sector Performance

Track portfolio contribution by sector.

This becomes deeper in Step 26 Attribution.

---

# 25.79 Size Bucket Performance

Track:

```text
large cap
mid cap
small cap
```

---

# 25.80 Liquidity Bucket Performance

Track.

---

# 25.81 Factor Exposure Performance

Track strategy performance while exposure to each factor is high/low.

---

# 25.82 Trade-Level Performance

For strategies with trade records:

```text
win_rate
loss_rate
average_win
average_loss
payoff_ratio
profit_factor
expectancy
```

---

# 25.83 Win Rate

```text
winning_trades / total_closed_trades
```

---

# 25.84 Average Win

Store.

---

# 25.85 Average Loss

Store.

---

# 25.86 Payoff Ratio

```text
average_win / abs(average_loss)
```

---

# 25.87 Profit Factor

```text
gross_profit / abs(gross_loss)
```

---

# 25.88 Trade Expectancy

```text
win_rate × avg_win
+
loss_rate × avg_loss
```

with loss negative.

---

# 25.89 Median Trade Return

Store.

---

# 25.90 Holding Period

Store:

```text
average_holding_days
median_holding_days
```

---

# 25.91 MFE

Maximum Favorable Excursion:

```text
best unrealized move during trade
```

---

# 25.92 MAE

Maximum Adverse Excursion:

```text
worst unrealized move during trade
```

---

# 25.93 MFE/MAE Analysis

Useful for evaluating:

```text
stops
profit taking
entry quality
```

---

# 25.94 Entry Efficiency

Possible:

```text
entry price relative to subsequent favorable range
```

---

# 25.95 Exit Efficiency

Similar.

---

# 25.96 Turnover

Store:

```text
daily
monthly
annual
```

using one consistent convention.

---

# 25.97 Turnover Cost

Store:

```text
transaction_cost / turnover
```

---

# 25.98 Return per Unit Turnover

```text
net_return / turnover
```

Useful for strategy efficiency.

---

# 25.99 Alpha per Unit Turnover

Store.

---

# 25.100 Gross-to-Net Retention

```text
net_return / gross_return
```

where denominator meaningful.

---

# 25.101 Cost as Percentage of Gross Alpha

Store:

```text
cost_to_gross_alpha_pct
```

---

# 25.102 Implementation Shortfall Drag

Aggregate Step 23.

---

# 25.103 Capacity Analysis

Track performance at different capital levels.

Store:

```text
capacity_curve
```

---

# 25.104 Capacity-Adjusted Return

Possible:

```text
return after impact at capital level X
```

---

# 25.105 Capacity Breakeven

Capital level at which:

```text
expected net alpha ≈ 0
```

---

# 25.106 Concentration Analysis

Track:

```text
top_1_return_contribution
top_5_return_contribution
top_10_return_contribution
```

---

# 25.107 Performance Concentration by Time

Track contribution from:

```text
best 5 days
best 10 days
best month
best quarter
```

---

# 25.108 Performance Concentration by Position

Track.

---

# 25.109 Return Distribution by Position

Store:

```text
position_contribution_distribution
```

---

# 25.110 Dependency on Outliers

Measure strategy performance after removing extreme positive outcomes.

---

# 25.111 Remove Best Days Test

Store:

```text
return_without_best_5_days
return_without_best_10_days
```

---

# 25.112 Remove Best Trades Test

Store.

---

# 25.113 Stability Across Time

Split:

```text
early sample
middle sample
recent sample
```

and compare.

---

# 25.114 Year-by-Year Metrics

For each year:

```text
return
volatility
Sharpe
drawdown
turnover
cost
```

---

# 25.115 Month-by-Month Heatmap Data

Store monthly return matrix.

Useful UI output later.

---

# 25.116 Rolling Performance Stability

Measure variability of:

```text
rolling Sharpe
rolling alpha
rolling drawdown
```

---

# 25.117 Sharpe Stability Score

Possible:

```text
sharpe_stability_score
```

---

# 25.118 Alpha Stability Score

Store.

---

# 25.119 Drawdown Stability Score

Store.

---

# 25.120 Benchmark Comparison

Compare:

```text
return
volatility
Sharpe
max drawdown
```

with benchmark.

---

# 25.121 Excess CAGR

```text
portfolio_CAGR - benchmark_CAGR
```

---

# 25.122 Benchmark Hit Rate

Percentage of months portfolio beats benchmark.

Store:

```text
benchmark_outperformance_month_ratio
```

---

# 25.123 Relative Drawdown

Compare portfolio drawdown with benchmark drawdown.

---

# 25.124 Relative Wealth Curve

```text
portfolio_NAV / benchmark_NAV
```

Store:

```text
relative_wealth_index
```

---

# 25.125 Relative Strength of Strategy

Slope/trend of relative wealth.

---

# 25.126 Live vs Backtest Comparison

One of the most important production diagnostics.

Track:

```text
live_return
expected_return
backtest_return
```

---

# 25.127 Live Performance Gap

```text
live_vs_backtest_gap
```

---

# 25.128 Live Sharpe Gap

Store.

---

# 25.129 Live Cost Gap

Compare:

```text
realized transaction costs
vs
backtest cost assumptions
```

---

# 25.130 Live Slippage Gap

Store.

---

# 25.131 Signal Decay Gap

Compare live IC with research IC.

---

# 25.132 Production Degradation Score

Possible:

```text
production_degradation_score
```

Inputs:

```text
live IC decline
higher costs
lower hit rate
higher drawdown
```

---

# 25.133 Strategy Health Status

Possible:

```text
HEALTHY
WATCH
DEGRADED
CRITICAL
```

---

# 25.134 Strategy Health Score

Possible:

```text
0 to 100
```

Inputs:

```text
return quality
drawdown
IC
cost drift
live-vs-backtest gap
```

---

# 25.135 Performance Alerting

Possible alerts:

```text
drawdown breach
rolling Sharpe collapse
live cost spike
alpha decay
turnover spike
```

---

# 25.136 Performance Benchmarking

Compare strategy against:

```text
market benchmark
equal-weight universe
simple factor baseline
cash / risk-free
```

---

# 25.137 Risk-Adjusted Benchmarking

A higher-return strategy with much higher risk may not be superior.

Use:

```text
Sharpe
Sortino
Calmar
IR
```

---

# 25.138 Return Efficiency

Possible:

```text
return / gross exposure
```

---

# 25.139 Capital Efficiency

Possible:

```text
return / deployed capital
```

---

# 25.140 Margin Efficiency

For derivatives:

```text
return / average margin used
```

---

# 25.141 Risk Budget Efficiency

Possible:

```text
return / average risk budget used
```

---

# 25.142 Confidence-Conditioned Performance

Evaluate performance by confidence bucket:

```text
VERY_HIGH
HIGH
MEDIUM
LOW
```

High-confidence trades should empirically perform better if Confidence Engine is calibrated.

---

# 25.143 Signal-Strength Performance

Evaluate by alpha decile.

---

# 25.144 Alpha Calibration Performance

Compare:

```text
predicted expected return
vs
realized return
```

---

# 25.145 Forecast Error

```text
forecast_error =
realized_return - expected_return
```

---

# 25.146 MAE of Return Forecast

Store.

---

# 25.147 RMSE of Return Forecast

Store.

---

# 25.148 Calibration by Alpha Bucket

Track.

---

# 25.149 Statistical Significance

Possible diagnostics:

```text
t-stat
bootstrap confidence interval
```

---

# 25.150 Sharpe Confidence Interval

Estimate.

---

# 25.151 CAGR Confidence Interval

Estimate using bootstrap/simulation as appropriate.

---

# 25.152 Drawdown Confidence Range

Estimate via resampling.

---

# 25.153 Monte Carlo Performance Paths

Optional:

```text
trade resampling
return block bootstrap
```

Output possible distributions for:

```text
return
drawdown
Sharpe
```

---

# 25.154 Expected Drawdown Distribution

Store.

---

# 25.155 Probability of Negative Year

Estimate from historical/simulated paths.

---

# 25.156 Probability of Drawdown > X

Estimate.

---

# 25.157 Sequence Risk

Trade ordering can materially affect drawdown.

Analyze with resampling.

---

# 25.158 Regime Sequence Risk

Optional advanced analysis.

---

# 25.159 Strategy Capacity Curve

Store:

```text
capital_level
gross_alpha
impact_cost
net_alpha
```

---

# 25.160 Performance by Rebalance Frequency

Compare:

```text
daily
weekly
monthly
```

where strategy supports it.

---

# 25.161 Performance by Cost Assumption

Compare.

---

# 25.162 Performance by Turnover Constraint

Compare.

---

# 25.163 Performance by Position Count

Compare.

---

# 25.164 Performance by Position Cap

Compare.

---

# 25.165 Performance by Sector Cap

Compare.

---

# 25.166 Performance by Regime Filter

Compare strategy with/without regime conditioning.

---

# 25.167 Performance by Confidence Filter

Compare.

---

# 25.168 Performance by Liquidity Filter

Compare.

---

# 25.169 Performance Diagnostics Record

Recommended:

```text
strategy_id
strategy_version

period_start
period_end

gross_return
net_return
CAGR

volatility
downside_deviation

Sharpe
Sortino
Calmar
information_ratio

max_drawdown
drawdown_duration

beta
alpha
tracking_error
r_squared

turnover
transaction_cost
cost_drag

win_rate
profit_factor
expectancy

positive_month_ratio

capacity_estimate

performance_consistency_score
strategy_health_score
strategy_health_status
```

---

# 25.170 Daily Performance Record

```text
date
strategy_id

NAV
gross_return
net_return
benchmark_return

excess_return

drawdown

rolling_volatility
rolling_sharpe
rolling_beta

gross_exposure
net_exposure

turnover
cost

market_regime
```

---

# 25.171 Monthly Performance Record

```text
year
month

gross_return
net_return
benchmark_return
excess_return

volatility
Sharpe

max_drawdown

turnover
cost
```

---

# 25.172 Drawdown Episode Record

```text
drawdown_id

peak_date
trough_date
recovery_date

depth
peak_to_trough_days
total_recovery_days
```

---

# 25.173 Live-vs-Backtest Record

```text
date

live_return
expected_backtest_return

live_cost
expected_cost

live_slippage
expected_slippage

live_IC
historical_IC

performance_gap
degradation_score
```

---

# 25.174 Initial Production Metrics

Recommended V1:

```text
gross_return
net_return
CAGR

annualized_volatility
Sharpe
Sortino
Calmar

max_drawdown
drawdown_duration
time_under_water

benchmark_return
excess_return
tracking_error
information_ratio
beta
alpha

turnover
transaction_cost
cost_drag

positive_month_ratio

rolling_63d_return
rolling_63d_volatility
rolling_63d_sharpe

yearly_return
monthly_return

strategy_health_score
```

---

# 25.175 Performance Analytics Processing Flow

Recommended:

```text
BACKTEST / LIVE NAV
        ↓
RETURN SERIES
        ↓
GROSS VS NET RETURNS
        ↓
VOLATILITY / DOWNSIDE RISK
        ↓
SHARPE / SORTINO / CALMAR
        ↓
DRAWDOWN ANALYSIS
        ↓
BENCHMARK RELATIVE METRICS
        ↓
ROLLING PERFORMANCE
        ↓
TRADE-LEVEL STATISTICS
        ↓
TURNOVER / COST EFFICIENCY
        ↓
REGIME / SECTOR / SIZE PERFORMANCE
        ↓
CAPACITY
        ↓
ROBUSTNESS / STABILITY
        ↓
LIVE VS BACKTEST
        ↓
STRATEGY HEALTH
```

---

# 25.176 Point-in-Time Rule

Performance metrics calculated at date T may only use returns realized through T.

Do not allow:

```text
future drawdown recovery
future annual return
future Sharpe
```

to appear in live monitoring.

Historical reports can of course calculate completed-period metrics.

---

# 25.177 Metric Versioning

Store:

```text
performance_metric_version
```

if formulas or conventions change.

---

# 25.178 Return Convention

Define once:

```text
simple returns
```

for portfolio reporting unless otherwise specified.

---

# 25.179 Annualization Convention

Store platform constants:

```text
trading_days_per_year assumption
```

and use consistently.

---

# 25.180 Turnover Convention

Define whether turnover is:

```text
sum(abs(weight changes))
```

or:

```text
0.5 × sum(abs(weight changes))
```

Do not mix conventions.

---

# 25.181 Risk-Free Convention

Define:

```text
daily interpolated risk-free
```

or equivalent.

---

# 25.182 Benchmark Convention

Benchmark must match:

```text
currency
calendar
return type
```

---

# 25.183 Missing Return Handling

Do not silently replace missing portfolio returns with zero.

Use explicit quality flags.

---

# 25.184 Performance Quality Status

Possible:

```text
VALID
PARTIAL_PERIOD
LOW_SAMPLE_SIZE
MISSING_BENCHMARK
MISSING_COSTS
LIVE_DATA_GAP
INVALID
```

---

# 25.185 Minimum Sample Requirements

Metrics such as Sharpe should carry sample-size context.

Store:

```text
observation_count
```

---

# 25.186 Short History Warning

If strategy has insufficient live history:

```text
LOW_SAMPLE_SIZE
```

---

# 25.187 Strategy Comparison Framework

When comparing strategies use same:

```text
period
benchmark
cost assumptions
capital level
universe
```

---

# 25.188 Apples-to-Apples Rule

Do not compare:

```text
gross backtest
```

with:

```text
net live return
```

without adjustment.

---

# 25.189 Performance Attribution Boundary

Step 25 answers:

```text
How well did the strategy perform?
```

Step 26 answers:

```text
Why did it perform that way?
```

Keep these separate.

---

# 25.190 Important Quant Rules

## Rule 1 — Net Performance Matters Most

Gross return is not deployable return.

## Rule 2 — Return Must Be Evaluated With Risk

Always pair return with volatility/drawdown.

## Rule 3 — Drawdown Duration Matters

Not just drawdown depth.

## Rule 4 — Benchmark Comparison Must Be Fair

Same period and conventions.

## Rule 5 — Rolling Metrics Matter

Full-period Sharpe can hide deterioration.

## Rule 6 — Cost Drag Must Be Visible

Separate signal quality from execution drag.

## Rule 7 — Performance Concentration Must Be Tested

A strategy dependent on a few outliers is fragile.

## Rule 8 — Regime Stability Matters

A strategy should not be judged only on aggregate return.

## Rule 9 — Live vs Backtest Must Be Monitored

Production decay is real.

## Rule 10 — Sample Size Matters

Do not overinterpret short histories.

## Rule 11 — Metrics Need Fixed Conventions

Sharpe/turnover/annualization definitions must be consistent.

## Rule 12 — Performance Must Be Reproducible

All metrics should trace back to NAV, trades, and cost records.

---

# 25.191 Completion Criteria

Step 25 is complete when Open Analytics can answer:

1. What was gross return?
2. What was net return?
3. What was CAGR?
4. What was annualized volatility?
5. What were Sharpe and Sortino?
6. What was Calmar?
7. What was maximum drawdown?
8. How long was the worst drawdown?
9. How much time was spent underwater?
10. What was benchmark-relative return?
11. What were tracking error and information ratio?
12. What were beta and alpha?
13. What percentage of months were positive?
14. What were the best and worst months?
15. What is rolling Sharpe doing?
16. Is recent performance deteriorating?
17. How much return was lost to costs?
18. What was turnover?
19. How efficient was return per unit turnover?
20. How did performance vary by market regime?
21. Was performance concentrated in a few periods/trades?
22. What is estimated strategy capacity?
23. How does live performance compare with backtest expectations?
24. Is the strategy currently healthy or degrading?
25. Can every performance metric be reproduced from source records?

Once these are reliable, the Performance Analytics Engine is ready to feed:

```text
Step 26 — Attribution Engine
```

---

# Step 25 Final Output

The Performance Analytics Engine transforms:

```text
Backtest / Live NAV
+
Portfolio Returns
+
Benchmark Returns
+
Transaction Costs
+
Trade Records
```

into:

```text
Gross / Net Performance
CAGR
Volatility
Sharpe
Sortino
Calmar
Drawdown Depth / Duration
Benchmark-Relative Performance
Tracking Error
Information Ratio
Beta / Alpha
Rolling Metrics
Trade Statistics
Turnover Efficiency
Cost Drag
Capacity
Regime Performance
Performance Stability
Live-vs-Backtest Diagnostics
Strategy Health
```

This becomes the professional performance-evaluation layer for Open Analytics.
