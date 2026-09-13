Next is **Step 2 — Data Quality & Validation**.

This stage verifies that the market and reference data are trustworthy **before** we calculate returns, risk, momentum, factors, or signals.

The main objective is simple:

> Detect bad, missing, stale, duplicated, inconsistent, or structurally impossible data before it contaminates the quant pipeline.

For OHLCV, we need checks such as:

```text
duplicate rows
missing trading dates
null prices
zero/negative prices
negative volume
stale prices
abnormal gaps
unexpected symbol changes
```

And structural OHLC rules:

```text
High >= Open
High >= Close
High >= Low

Low <= Open
Low <= Close
Low <= High
```

We also need calendar-aware validation, so a missing Sunday is not treated as missing data, while a missing valid exchange trading session is.

The engine should calculate quality fields such as:

```text
expected_sessions
available_sessions
missing_sessions
coverage_pct

duplicate_count
invalid_ohlc_count
zero_volume_count
stale_price_days

largest_missing_streak
latest_valid_date

data_quality_score
data_quality_status
```

We should classify issues by severity:

```text
INFO
WARNING
CRITICAL
```

For example:

```text
1 isolated missing candle
→ WARNING

50 missing consecutive sessions
→ CRITICAL
```

Corporate actions must also be recognized here. A 50% price drop caused by a split must **not** be classified as a bad market price automatically.

So validation should distinguish:

```text
true market move
corporate action move
bad/raw data
```

The output should look conceptually like:

```text
instrument_key
date

is_valid
quality_status
quality_score

missing_flag
duplicate_flag
invalid_ohlc_flag
stale_flag
outlier_flag
corporate_action_flag

issue_count
critical_issue_count

exclusion_reason
```

And at instrument level:

```text
RELIANCE

coverage_pct          99.8
invalid_rows          0
duplicate_rows        0
largest_gap           1
latest_data_status    HEALTHY
quality_score         98.7
```

This step should also cover **fundamentals, corporate actions, news, and reference data**, not only OHLCV.

For fundamentals:

```text
duplicate reporting periods
missing fiscal periods
impossible ratios
restatement handling
currency consistency
reporting-date ordering
```

For news:

```text
duplicate stories
missing timestamps
wrong ticker mapping
future timestamps
bad source records
```

For corporate actions:

```text
duplicate actions
incorrect effective date
missing adjustment factor
conflicting split/bonus records
```
