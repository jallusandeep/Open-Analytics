# Data Quality engine — Step 02

The engine lives in `backend/app/engines/data_quality/`. It validates data without
changing collected prices or deleting source records.

## Does it run automatically?

**No.** Validation runs when an authenticated API caller requests it, or when
Python code calls the validators. The collection queue, scheduler and startup
process do not invoke it. Reports are returned to the caller, not persisted.

A preflight endpoint and Python guard are available for research engines to call
before calculations. They do not intercept other database queries automatically.

## How validation works

1. Read supplied records or load stored data for one instrument.
2. Establish eligible sessions from an explicit calendar or a requested date range
   with stored exchange holidays, special openings and supplied listing boundaries.
3. Check each observation and compare related observations: duplicates, previous
   close, consecutive missing sessions, reporting periods and revisions.
4. Assign issues (`INFO`, `WARNING`, `CRITICAL`), flags, exclusion reasons and scores.
5. Return row results plus a summary. The optional preflight blocks unusable data.

## API

All paths start with `/api/v1/data-quality` and require bearer authentication and
research app access. Restart the backend to load changed routes; request examples
and schemas are also available in FastAPI `/docs`.

| POST endpoint | Purpose |
| --- | --- |
| `/ohlcv` | Validate supplied daily candles and action evidence |
| `/records` | Validate supplied fundamentals, news, actions or references |
| `/stored-daily` | Validate stored Upstox daily candles for one instrument |
| `/stored-records` | Load and validate stored auxiliary data |
| `/preflight` | Validate stored daily data; return HTTP 409 if unusable |

Stored daily request using the local calendar:

```json
{
  "instrument_key": "NSE_EQ|EXAMPLE",
  "start_date": "2026-09-01",
  "end_date": "2026-09-15",
  "exchange": "NSE"
}
```

Alternatively supply `sessions: ["2026-09-14", "2026-09-15"]`. Explicit sessions
represent the caller's authoritative eligibility list and enable preflight.
The stored holiday table does not certify completeness, so generated calendars
include a warning and `calendar_verified: false`; preflight requires explicit
sessions until calendar completeness can be verified. `listing_date` and
`delisting_date` optionally limit generated sessions. Eligibility is never guessed
from the first observed candle. Without listing dates the requested range is used.

For `/ohlcv`, supply `instrument_key`, `sessions`, `records` with
`date/open/high/low/close/volume/trading_symbol`, and optional `corporate_actions`.
Threshold defaults are five unchanged closes, ten consecutive missing sessions,
30% close-to-close outlier detection and 10% tolerance around an action-adjusted
expected price. These are configurable diagnostic policies, not calibrated models.

Stored auxiliary request:

```json
{"dataset": "fundamentals", "instrument_key": "NSE_EQ|EXAMPLE", "source": "collected"}
```

`collected` reads `upstox_company_fundamentals` for financial statements and actions;
`legacy` reads `fundamentals` or `corporate_actions`. News uses `equity_news` and
reference data uses `upstox_instruments`. Known list and category-history vendor
shapes are expanded; missing metadata stays missing and is reported. Fiscal labels
must be ISO period-end dates; unsupported textual labels fail validation rather
than being assigned guessed dates. Adjustment factors must be explicit numbers;
ambiguous vendor ratio strings are not automatically interpreted.

## Specification coverage

| Requirement | Implementation / boundary |
| --- | --- |
| Duplicate OHLCV, invalid prices and structural bounds | Critical; entire duplicate date excluded |
| Missing dates and coverage | Expected eligible sessions compared to unique observed dates |
| Zero/negative/missing volume | Zero warns; negative, missing or nonfinite excludes |
| Stale prices, abnormal gaps, symbol changes | Consecutive-close checks and review warnings |
| Missing runs | Calendar-session count, unaffected by unexpected weekend candles |
| Quality fields, severity and exclusion reasons | Row flags and instrument summary |
| Corporate-action moves | Must match a single validated price-changing action and tolerance |
| Genuine market moves | Remain unexplained unless caller supplies verified `confirmed_market_moves` dates |
| Action dates and factors | Parse supplied dates, check ordering, factor presence/direction and dividend amounts |
| Action conflicts | Normalize aliases such as `stock_split`/`split`, detect duplicates and factor conflicts |
| Fundamental periods | Duplicate identity includes statement/period type, period end and revision |
| Missing fiscal periods | Infer interior quarterly/annual/semiannual gaps; explicit expected periods also supported |
| Restatements | Validate nonnegative revision numbers and chronological publication dates; preserve every revision |
| Ratios | Finite values, holding percentages/totals, nonnegative liquidity ratios/yield, configurable `ratio_bounds` |
| Currency and report ordering | Currency-code format/consistency, period-end <= report date <= as-of |
| News | Duplicate URL (or title/timestamp), timestamps, source/title and supplied ticker mapping |
| Reference | Required key/symbol/exchange, duplicate keys and listing/delisting dates |
| Before research calculations | Callable `require_quality(report)` and `/preflight`; downstream callers must invoke them |

Impossible ratios cannot be exhaustively defined without financial context.
Negative P/E and ROE are allowed. Custom bounds accept `[lower, upper]` with `null`
for an open end. Restatements on the same date are allowed because the available
report field has day precision; the engine cannot determine their intraday order.

Ex-date is used for price comparisons. Effective dates are parsed and checked
against announcement ordering; different action types may legitimately have
separate ex/effective/record dates, so these are not forced to be identical.
Multiple simultaneous price-changing actions require review because their order
and ratio conventions cannot safely be inferred.

## Results and use in calculations

Row scores start at 100, subtract 50 per critical issue and 10 per warning, and
are floored at zero. Instrument score is the row-score average; worst severity
controls status. A high average does not override an excluded row.
`is_valid` is false for critical issues, missing candles and unexpected sessions.
Warnings about real observations can remain valid for review. Coverage counts
unique present dates, including invalid candles; `latest_valid_date` additionally
requires a usable observation. Empty input has no usable records.

`require_quality(report)` rejects empty reports, unverified generated calendars,
and any invalid/missing/off-calendar rows. Future return/risk/signal engines must
call this guard immediately before using the validated source snapshot. Checking
a report and subsequently loading changed raw data does not provide a safe gate.

## Remaining source and integration limits

- Collection does not trigger validation automatically and reports are not saved.
- Stored-calendar completeness and historical listing/ticker membership are not
  certified by the existing data sources. Current master mappings are labelled.
- Financial publication dates, explicit adjustment factors and revision metadata
  may be absent from vendor payloads. Such records cannot be certified by inference.
- Duplicate detection after collection cannot recover records already overwritten
  by a database primary key; validate supplied raw batches to inspect those duplicates.
- News duplication uses identifiers, not semantic matching of rewritten stories.

## Tests

From `backend`, with the project's test dependencies installed:

```powershell
python -m pytest tests/unit/test_data_quality.py tests/unit/test_data_quality_spec.py -o addopts= -p no:cacheprovider -q
```

Tests use synthetic data and in-memory databases, including action-factor matching,
malformed dates, fiscal gaps, revisions, exchange calendars, stored adapters and
preflight exclusion. The live database is not used for verification.
