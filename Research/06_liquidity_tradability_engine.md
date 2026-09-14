# Open Analytics — Step 6: Liquidity & Tradability Engine

## Purpose

The **Liquidity & Tradability Engine** determines whether a security can realistically be traded at the desired size without excessive spread, slippage, market impact, or execution risk.

A quant model may identify a statistically attractive stock, but that signal is not useful if the position cannot be entered or exited efficiently.

This engine should answer:

- How actively does the stock trade?
- How much rupee value trades each day?
- How stable is the trading activity?
- How wide is the bid-ask spread?
- How much market depth is available?
- How much slippage should we expect?
- How much capital can the strategy realistically deploy?
- How many days would it take to liquidate a position?
- Is the stock suitable for research only, or for actual live trading?
- How does its liquidity rank against peers?

The outputs feed directly into:

- Universe filtering
- Stock selection
- Position sizing
- Portfolio construction
- Execution
- Backtesting
- Transaction cost modeling
- Capacity analysis
- Risk management

---

# 6.1 Core Principle

Liquidity is multidimensional.

Do not define liquidity using volume alone.

The engine should consider:

```text
Trading Frequency
Share Volume
Rupee Traded Value
Turnover
Bid-Ask Spread
Market Depth
Price Impact
Slippage
Order Book Stability
Participation Capacity
Exit Capacity
```

A stock can have high share volume but still be difficult to trade if its price is very low or the order book is weak.

---

# 6.2 Required Inputs

Minimum inputs:

```text
instrument_key
date

open
high
low
close
volume
```

Preferred:

```text
adjusted_close

traded_value
number_of_trades

bid_price
ask_price
bid_size
ask_size

depth_levels

market_cap
free_float_market_cap

trading_status
data_quality_status
```

Optional advanced inputs:

```text
tick-by-tick trades
order book snapshots
market depth history
auction data
delivery quantity
delivery percentage
```

---

# 6.3 Daily Share Volume

Store raw daily volume:

```text
daily_volume
```

Rolling averages:

```text
avg_volume_5d
avg_volume_10d
avg_volume_20d
avg_volume_60d
avg_volume_126d
avg_volume_252d
```

Also calculate medians:

```text
median_volume_20d
median_volume_60d
median_volume_252d
```

Median can be more robust when occasional extreme-volume days distort the average.

---

# 6.4 Traded Value

Traded value is more comparable than raw share volume.

Approximation:

```text
traded_value =
close × volume
```

Better, where available:

```text
traded_value =
actual exchange-reported turnover
```

Store:

```text
daily_traded_value

avg_traded_value_5d
avg_traded_value_20d
avg_traded_value_60d
avg_traded_value_126d
avg_traded_value_252d

median_traded_value_20d
median_traded_value_60d
median_traded_value_252d
```

For Indian equities this should generally be expressed in INR, with display conversions to lakh/crore where useful.

---

# 6.5 Trading Frequency

A stock may have a valid price but not trade every session.

Calculate:

```text
traded_days_20d
traded_days_60d
traded_days_126d
traded_days_252d

trading_frequency_20d
trading_frequency_60d
trading_frequency_252d
```

Formula:

```text
trading_frequency =
traded_sessions / expected_sessions
```

Example:

```text
Expected sessions = 20
Traded sessions   = 20

Trading frequency = 100%
```

---

# 6.6 Zero-Volume Sessions

Track:

```text
zero_volume_days_20d
zero_volume_days_60d
zero_volume_days_252d
```

And:

```text
zero_volume_ratio
```

Frequent zero-volume sessions are a major warning sign.

---

# 6.7 Volume Stability

Liquidity should be stable, not merely high on one or two days.

Calculate:

```text
volume_std_20d
volume_cv_20d

traded_value_std_20d
traded_value_cv_20d
```

Coefficient of variation:

```text
CV =
standard_deviation / mean
```

High CV can indicate unstable liquidity.

---

# 6.8 Relative Volume

Relative Volume:

```text
rvol_20d =
current_volume / avg_volume_20d
```

Also:

```text
rvol_5d
rvol_20d
rvol_60d
```

Example:

```text
Current volume      = 4,000,000
20D average volume  = 1,000,000

RVOL = 4.0
```

This measures abnormal participation, not absolute liquidity.

---

# 6.9 Volume Z-Score

Standardize current volume relative to recent history:

```text
volume_zscore_20d =
(current_volume - mean_volume_20d)
/
std_volume_20d
```

Also:

```text
traded_value_zscore_20d
```

Useful for participation and breakout confirmation.

---

# 6.10 Turnover Ratio

If market cap or free-float market cap is available:

```text
turnover_ratio =
daily_traded_value / market_cap
```

Better for tradable float:

```text
free_float_turnover =
daily_traded_value / free_float_market_cap
```

Rolling:

```text
turnover_20d
turnover_60d
```

This helps compare trading activity relative to company size.

---

# 6.11 Bid-Ask Spread

Where quote data exists:

```text
spread =
ask_price - bid_price
```

Percentage spread:

```text
spread_pct =
(ask - bid) / midpoint
```

where:

```text
midpoint =
(bid + ask) / 2
```

Store:

```text
spread_abs
spread_pct

avg_spread_pct_5d
avg_spread_pct_20d
median_spread_pct_20d
```

Spread is one of the most direct transaction-cost measures.

---

# 6.12 Effective Spread

If trade prices are available:

```text
effective_spread =
2 × abs(trade_price - midpoint)
```

Percentage form:

```text
effective_spread_pct
```

This can better reflect actual execution cost than quoted spread alone.

---

# 6.13 Market Depth

If order book data exists, store liquidity available at several levels.

Example:

```text
bid_depth_l1
ask_depth_l1

bid_depth_l5
ask_depth_l5

total_bid_depth
total_ask_depth
```

Value-weighted depth:

```text
bid_depth_value
ask_depth_value
```

---

# 6.14 Depth Imbalance

Order-book imbalance:

```text
depth_imbalance =
(bid_depth - ask_depth)
/
(bid_depth + ask_depth)
```

Range:

```text
-1 to +1
```

Interpretation:

```text
positive → more displayed bid depth
negative → more displayed ask depth
```

This is more useful for short-horizon execution/microstructure models than long-term stock selection.

---

# 6.15 Amihud Illiquidity

A widely used price-impact proxy:

```text
amihud =
abs(return)
/
traded_value
```

Average over a window:

```text
amihud_illiquidity_20d
amihud_illiquidity_60d
amihud_illiquidity_252d
```

Higher values imply more price movement per unit of traded value, indicating lower liquidity.

Scale and units should be standardized for readability.

---

# 6.16 Price Impact

Estimate how much price tends to move when capital is traded.

Possible proxies:

```text
absolute_return / traded_value
spread-based impact
order-book impact
empirical execution impact
```

Store:

```text
estimated_price_impact
```

Eventually estimate impact as a function of order size.

---

# 6.17 Slippage

Slippage is the difference between expected/reference price and actual execution price.

For buys:

```text
slippage =
execution_price - reference_price
```

For sells:

```text
slippage =
reference_price - execution_price
```

Normalize:

```text
slippage_bps
```

where 1 basis point = 0.01%.

The live engine should later estimate:

```text
expected_slippage_bps
```

before placing a trade.

---

# 6.18 Participation Rate

A strategy should not assume it can trade unlimited size.

Participation rate:

```text
participation_rate =
order_value / expected_market_traded_value
```

Example:

```text
Order value        = ₹10 crore
Average daily value = ₹100 crore

Participation = 10%
```

Higher participation generally means more market impact.

---

# 6.19 ADV Capacity

Average Daily Value capacity is a core institutional-style control.

Possible rule:

```text
max_daily_order_value =
ADV × allowed_participation_rate
```

Example:

```text
ADV = ₹200 crore
Max participation = 5%

Max daily order size = ₹10 crore
```

This should be strategy configurable.

---

# 6.20 Days to Liquidate

Estimate exit time:

```text
days_to_liquidate =
position_value
/
allowed_daily_liquidation_value
```

where:

```text
allowed_daily_liquidation_value =
ADV × max_participation_rate
```

Example:

```text
Position = ₹50 crore
ADV      = ₹100 crore
Allowed participation = 10%

Daily liquidation capacity = ₹10 crore
Days to liquidate = 5
```

This is very important for portfolio risk.

---

# 6.21 Position Capacity

For each stock, calculate strategy-level capacity.

Possible fields:

```text
max_position_value_1pct_adv
max_position_value_5pct_adv
max_position_value_10pct_adv

max_position_shares
```

These are not recommendations; they are mechanical capacity constraints.

---

# 6.22 Liquidity Buckets

Possible normalized buckets:

```text
VERY_HIGH
HIGH
MEDIUM
LOW
VERY_LOW
```

Based on:

```text
ADV
spread
trading frequency
market depth
impact
```

Do not use ADV alone.

---

# 6.23 Liquidity Percentile

Rank stocks within the valid universe:

```text
liquidity_percentile
```

Also:

```text
adv_percentile
spread_percentile
depth_percentile
impact_percentile
```

For spread and impact, lower values are better, so ranking direction must be handled correctly.

---

# 6.24 Liquidity Z-Scores

Possible standardized features:

```text
adv_zscore
spread_zscore
amihud_zscore
depth_zscore
```

These can feed the later Liquidity Factor.

---

# 6.25 Composite Liquidity Score

Eventually construct:

```text
liquidity_score = 0 to 100
```

Possible components:

```text
Average traded value
Trading frequency
Spread
Depth
Amihud illiquidity
Estimated impact
```

Recommended interpretation:

```text
0   → extremely poor liquidity
100 → extremely strong liquidity
```

Weights should be researched and configurable.

Do not conceal underlying metrics behind the score.

---

# 6.26 Tradability Score

Liquidity and tradability are related but not identical.

Tradability may include:

```text
Liquidity
Active status
Suspension status
Price eligibility
Market lot / tick constraints
Data quality
Short-sale / derivatives availability where relevant
Corporate event restrictions
```

Output:

```text
tradability_score
```

---

# 6.27 Research Eligibility vs Execution Eligibility

Maintain separate flags:

```text
research_eligible
liquidity_eligible
execution_eligible
```

Example:

```text
Stock A

research_eligible = true
liquidity_eligible = false
execution_eligible = false
```

It may remain useful for academic research but not live trading.

---

# 6.28 Strategy-Specific Liquidity Rules

Different strategies require different liquidity.

A long-term monthly-rebalanced strategy may tolerate lower liquidity than an intraday strategy.

Therefore requirements should be supplied by strategy configuration.

Example:

```text
min_adv
max_spread_pct
min_trading_frequency
max_days_to_liquidate
max_participation_rate
```

---

# 6.29 Intraday Strategy Requirements

An intraday strategy may require:

```text
very high ADV
tight spread
high depth
high trading frequency
stable order book
low expected slippage
```

---

# 6.30 Swing Strategy Requirements

A swing strategy may prioritize:

```text
adequate ADV
moderate spread
stable liquidity
reasonable days-to-liquidate
```

---

# 6.31 Long-Term Strategy Requirements

A long-term strategy may accept lower turnover but must still ensure realistic entry/exit capacity.

Important:

```text
long holding period ≠ liquidity irrelevant
```

Large positions can still become trapped in illiquid securities.

---

# 6.32 Microcap Handling

Microcaps require additional caution because:

```text
volume can disappear quickly
spread can widen sharply
quoted depth can be unreliable
impact can be nonlinear
upper/lower circuits can limit exits
```

Add flags such as:

```text
microcap_liquidity_warning
circuit_risk_flag
```

where data permits.

---

# 6.33 Circuit Limit Risk

Indian equities may be subject to price bands/circuit limits.

Where available, track:

```text
upper_circuit_price
lower_circuit_price

near_upper_circuit
near_lower_circuit

circuit_hit_flag
```

Repeated circuit behavior can materially impair tradability.

---

# 6.34 Auction / Settlement Risk

For advanced execution analysis, track exceptional market conditions where available:

```text
auction_flag
settlement_issue_flag
special_series_flag
trade_to_trade_flag
```

Such classifications can affect execution eligibility.

---

# 6.35 Delivery Data

Where delivery statistics are available:

```text
delivery_quantity
delivery_percentage
```

Rolling:

```text
avg_delivery_pct_20d
delivery_zscore
```

This is not a direct liquidity metric but can help characterize participation quality.

---

# 6.36 Number of Trades

If available:

```text
trade_count
avg_trade_count_20d
```

Average trade size:

```text
avg_trade_size =
volume / trade_count
```

Value form:

```text
avg_trade_value =
traded_value / trade_count
```

Can help distinguish broad participation from a few large prints.

---

# 6.37 Turnover Velocity

Potential measure:

```text
turnover_velocity =
rolling_traded_value
/
free_float_market_cap
```

This indicates how quickly free-float value changes hands.

---

# 6.38 Liquidity Trend

Liquidity changes over time.

Calculate:

```text
adv_change_21d
spread_change_21d
depth_change_21d
amihud_change_21d
```

Classify:

```text
IMPROVING
STABLE
DETERIORATING
```

A stock becoming rapidly less liquid is a risk even if its trailing average remains acceptable.

---

# 6.39 Liquidity Shock

Detect sudden deterioration:

```text
volume collapse
ADV collapse
spread widening
depth disappearance
impact spike
```

Output:

```text
liquidity_shock_flag
```

This can later influence risk and execution engines.

---

# 6.40 Relative Liquidity

Compare stock liquidity with:

```text
whole universe
market-cap peers
sector peers
```

Outputs:

```text
universe_liquidity_percentile
sector_liquidity_percentile
size_bucket_liquidity_percentile
```

A ₹50 crore ADV may be high in one peer set and low in another.

---

# 6.41 Historical Liquidity Snapshot

All liquidity calculations must be point-in-time for backtesting.

Do not use today's ADV to decide whether a stock was tradable five years ago.

Store per date:

```text
date
instrument_key

adv
spread
trading_frequency
liquidity_score
execution_eligible
```

---

# 6.42 Survivor Bias Protection

Stocks that later became illiquid, suspended, or delisted must remain in historical liquidity snapshots.

Otherwise a backtest will systematically remove difficult securities after the fact.

---

# 6.43 Look-Ahead Protection

At date T, only use liquidity information available through T.

For example:

```text
avg_traded_value_20d at T
```

must use only sessions up to and including T.

Never use future volume.

---

# 6.44 Missing Quote Data

If bid/ask data is unavailable, do not invent zero spread.

Use:

```text
spread_available = false
spread_pct = null
```

Fall back to lower-fidelity liquidity metrics such as:

```text
ADV
trading frequency
Amihud
```

and lower the quality score.

---

# 6.45 Stale Quote Handling

Quotes should have freshness metadata.

Store:

```text
quote_timestamp
quote_age
quote_stale_flag
```

Do not calculate trusted spread/depth from stale quotes.

---

# 6.46 Data Quality Flags

Recommended:

```text
liquidity_valid
liquidity_quality_status

volume_valid
traded_value_valid
spread_valid
depth_valid

quote_stale_flag
abnormal_volume_flag

liquidity_invalid_reason
```

---

# 6.47 Abnormal Volume Events

Large event-driven volume should remain visible.

Do not automatically remove it.

Instead flag:

```text
volume_outlier_flag
```

Possible causes:

```text
earnings
block deal
corporate action
index rebalance
news event
unknown
```

This can help later event analysis.

---

# 6.48 Block and Bulk Deals

If available, separate unusual institutional prints from normal continuous-market activity.

Possible fields:

```text
block_deal_value
bulk_deal_value
```

This may improve interpretation of turnover and participation.

---

# 6.49 Liquidity-Adjusted Risk

Later risk models can combine volatility and liquidity.

Conceptually:

```text
high volatility + low liquidity
```

is more dangerous than:

```text
high volatility + very high liquidity
```

Possible future metric:

```text
liquidity_adjusted_risk_score
```

Do not collapse these dimensions too early.

---

# 6.50 Liquidity-Adjusted Signal

Later Alpha Engine may penalize signals that are expensive to execute.

Conceptually:

```text
net_signal =
raw_alpha
- expected_execution_cost
- liquidity_penalty
```

The Liquidity Engine must provide the cost/capacity inputs.

---

# 6.51 Backtest Transaction Capacity

A realistic backtest should ensure historical order sizes do not exceed configured liquidity participation.

Example:

```text
order_value <= 5% of historical ADV
```

If not:

```text
trade_rejected
```

or:

```text
position_size_reduced
```

depending on strategy rules.

---

# 6.52 Execution Eligibility

Possible mechanical conditions:

```text
is_active = true
trading_frequency >= threshold
ADV >= threshold
spread_pct <= threshold
days_to_liquidate <= threshold
data_quality = acceptable
```

Output:

```text
execution_eligible = true / false
```

---

# 6.53 Exclusion Reasons

Possible standardized codes:

```text
LOW_ADV
LOW_VOLUME
LOW_TRADING_FREQUENCY

HIGH_SPREAD
LOW_DEPTH
HIGH_PRICE_IMPACT

STALE_QUOTE
MISSING_QUOTE_DATA

SUSPENDED
INACTIVE
CIRCUIT_RISK

DAYS_TO_LIQUIDATE_TOO_HIGH

STRATEGY_CAPACITY_EXCEEDED
```

Store:

```text
liquidity_exclusion_code
liquidity_exclusion_detail
```

---

# 6.54 Recommended Daily Liquidity Record

A daily record could contain:

```text
instrument_key
date


# BASIC ACTIVITY

daily_volume
daily_traded_value

trade_count


# ROLLING VOLUME

avg_volume_5d
avg_volume_20d
avg_volume_60d

median_volume_20d
median_volume_60d


# ROLLING VALUE

avg_traded_value_5d
avg_traded_value_20d
avg_traded_value_60d
avg_traded_value_252d

median_traded_value_20d
median_traded_value_60d


# TRADING FREQUENCY

traded_days_20d
traded_days_60d
traded_days_252d

trading_frequency_20d
trading_frequency_60d
trading_frequency_252d

zero_volume_days_20d
zero_volume_days_60d


# PARTICIPATION

rvol_20d
volume_zscore_20d
traded_value_zscore_20d

turnover_ratio
free_float_turnover


# SPREAD

spread_abs
spread_pct

avg_spread_pct_5d
avg_spread_pct_20d


# DEPTH

bid_depth_value
ask_depth_value
total_depth_value

depth_imbalance


# ILLIQUIDITY / IMPACT

amihud_20d
amihud_60d
amihud_252d

estimated_price_impact
expected_slippage_bps


# CAPACITY

max_order_value_1pct_adv
max_order_value_5pct_adv
max_order_value_10pct_adv

days_to_liquidate


# RANKINGS

adv_percentile
spread_percentile
amihud_percentile
liquidity_percentile

liquidity_score
liquidity_bucket
liquidity_trend


# ELIGIBILITY

liquidity_eligible
execution_eligible

liquidity_exclusion_code


# QUALITY

liquidity_valid
liquidity_quality_status

spread_available
depth_available

quote_stale_flag
liquidity_invalid_reason
```

---

# 6.55 Initial Production Metrics

The first production version should focus on metrics already possible from daily OHLCV and basic quote data.

Recommended:

```text
daily_volume
daily_traded_value

avg_volume_20d
avg_volume_60d

avg_traded_value_20d
avg_traded_value_60d
avg_traded_value_252d

median_traded_value_20d
median_traded_value_60d

traded_days_20d
traded_days_60d

trading_frequency_20d
trading_frequency_60d

zero_volume_days_20d
zero_volume_days_60d

rvol_20d
volume_zscore_20d

turnover_ratio

amihud_20d
amihud_60d

liquidity_percentile
liquidity_score
liquidity_bucket

liquidity_eligible
liquidity_quality_status
```

When market-depth data becomes available, add:

```text
spread_pct
depth
impact
slippage
capacity
```

---

# 6.56 Liquidity Engine Processing Flow

Recommended:

```text
VALID MARKET DATA
        ↓
TRADING STATUS CHECK
        ↓
DAILY VOLUME / TRADED VALUE
        ↓
ROLLING ADV / MEDIAN VALUE
        ↓
TRADING FREQUENCY
        ↓
ZERO-VOLUME ANALYSIS
        ↓
RELATIVE VOLUME / Z-SCORE
        ↓
TURNOVER
        ↓
SPREAD
        ↓
MARKET DEPTH
        ↓
AMIHUD / IMPACT
        ↓
SLIPPAGE ESTIMATION
        ↓
PARTICIPATION CAPACITY
        ↓
DAYS TO LIQUIDATE
        ↓
CROSS-SECTIONAL RANKS
        ↓
LIQUIDITY SCORE
        ↓
EXECUTION ELIGIBILITY
        ↓
QUALITY FLAGS
```

---

# 6.57 Important Quant Rules

## Rule 1 — Volume Alone Is Not Liquidity

Always consider traded value and, where available, spread/depth.

---

## Rule 2 — Use Rupee Traded Value

Comparing raw share volume across differently priced stocks is misleading.

---

## Rule 3 — Median Matters

Occasional event-driven volume can inflate average liquidity.

Keep median values as well.

---

## Rule 4 — Liquidity Must Be Point-in-Time

Historical backtests must use historical liquidity.

---

## Rule 5 — Do Not Assume Infinite Capacity

Position size should be constrained relative to market participation.

---

## Rule 6 — Low Volatility Does Not Mean Safe

An illiquid security may show artificially low volatility.

---

## Rule 7 — Missing Spread Is Not Zero Spread

Unknown execution cost must remain unknown or estimated explicitly.

---

## Rule 8 — Liquidity Is Strategy-Specific

Intraday, swing, and long-term strategies require different thresholds.

---

## Rule 9 — Preserve Underlying Metrics

Do not rely only on one liquidity score.

---

## Rule 10 — Exit Liquidity Matters

The ability to enter a position does not guarantee the ability to exit during stress.

---

## Rule 11 — Use Historical Universe Membership

Cross-sectional liquidity ranks must use the valid universe for that date.

---

## Rule 12 — Costs Rise Nonlinearly

Large participation can create disproportionately larger market impact.

Simple linear estimates should be treated as approximations.

---

# 6.58 Completion Criteria

Step 6 is complete when Open Analytics can answer:

1. What is the stock's daily share volume?
2. What is its average and median traded value?
3. How consistently does it trade?
4. How many zero-volume sessions does it have?
5. Is current volume unusually high or low?
6. What is its turnover relative to size/free float?
7. What is the current and average spread where available?
8. How much displayed market depth exists?
9. What is its Amihud illiquidity?
10. What execution slippage is likely?
11. How much capital can reasonably be traded per day?
12. How many days would a given position take to liquidate?
13. Is liquidity improving or deteriorating?
14. How does the stock rank in liquidity versus peers?
15. What is its composite liquidity score?
16. Is it suitable for this strategy's execution requirements?
17. Why was it rejected from live trading?
18. Were all metrics calculated using only information known at that historical date?

Once these are reliable, the Liquidity & Tradability Engine is ready to feed:

```text
Step 7 — Trend Engine
```

---

# Step 6 Final Output

The Liquidity & Tradability Engine transforms:

```text
Price + Volume + Quote + Depth Data
```

into:

```text
Volume Metrics
Average Daily Traded Value
Trading Frequency
Relative Volume
Turnover
Spread
Depth
Illiquidity
Price Impact
Slippage
Participation Limits
Days to Liquidate
Liquidity Ranking
Liquidity Score
Execution Eligibility
Liquidity Quality Flags
```

This becomes the execution-feasibility layer for the rest of Open Analytics.
