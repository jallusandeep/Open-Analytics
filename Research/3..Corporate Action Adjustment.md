Next is **Step 3 — Corporate Action Adjustment**.

This step makes historical prices economically comparable across time. Without it, splits, bonuses, dividends, rights issues, mergers, and similar events can create fake returns and destroy momentum, volatility, drawdown, and factor calculations.

For each stock, we need to maintain raw and adjusted series separately:

```text
raw_open
raw_high
raw_low
raw_close
raw_volume

adjusted_open
adjusted_high
adjusted_low
adjusted_close
adjusted_volume
```

The core rule is:

> Never overwrite raw OHLCV. Always preserve the original exchange data and generate a separate adjusted series.

We need to detect and process corporate actions such as:

```text
stock_split
reverse_split
bonus_issue
cash_dividend
rights_issue
demerger
merger
spin_off
capital_reduction
symbol_change
isin_change
```

For a split or bonus event, historical price and volume need adjustment factors.

Example, 2:1 split:

```text
Old price        ₹1,000
New price          ₹500

Without adjustment:
return ≈ -50%

Economically:
no actual 50% loss
```

So the historical price series must be restated to remove that artificial break.

We should calculate and store fields like:

```text
corporate_action_type
ex_date
record_date
effective_date

price_adjustment_factor
volume_adjustment_factor

cash_dividend
rights_ratio
bonus_ratio
split_ratio

adjustment_source
adjustment_status
```

Then build a cumulative adjustment factor over time:

```text
cumulative_price_factor
cumulative_volume_factor
```

The engine should be able to produce at least two useful price series:

```text
Split/bonus-adjusted price
Total-return-adjusted price
```

The first is useful for technical and price-history continuity.

The second includes distributions such as dividends and is better for investor return calculations.

For example:

```text
price_return
total_return
```

These should not be treated as identical.

We also need validation around the event itself:

```text
Does the observed price jump match the announced action?
Is the adjustment factor plausible?
Is the event duplicated?
Are multiple actions effective on the same date?
```

For historical calculations, downstream engines should use a consistent adjusted series:

```text
Returns Engine
Momentum Engine
Volatility Engine
Drawdown Engine
Trend Engine
```

while raw data should still remain available for:

```text
execution analysis
actual historical traded prices
market microstructure
audit/debugging
```

A good final record might look like:

```text
instrument_key
date

raw_close
adjusted_close
total_return_close

price_adjustment_factor
volume_adjustment_factor

corporate_action_flag
corporate_action_type
adjustment_valid
```

The most important principle in Step 3 is:

> A real economic return should come from investor wealth change, not from a mechanical change in share count or corporate structure.
