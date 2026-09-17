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

## Detailed execution walkthrough

### 1. Request parsing

`data_quality_schema.py` checks request shape and limits before business rules run.
For example, a negative stale-session threshold is rejected with HTTP 422 rather
than interpreted as a market-data problem. Raw candle values remain uncoerced so
the validator can report invalid observations instead of silently repairing them.

`data_quality_routes.py` applies authentication and delegates to either the pure
validator or the stored-data repository. Database connections are closed after
each request. Reading a report does not write corrected candles back to storage.

### 2. Identify the expected records

For daily OHLCV, the validator groups input records by session date and walks the
union of expected dates and observed dates. It creates a synthetic missing-row
result when an expected session has no candle. An observed date outside the
calendar becomes an unexpected-session result. Invalid date values are reported
with their input `source_row` index.

Two candles on one date produce one duplicate-date result. Neither candle is
chosen as authoritative. `duplicate_count` counts the extra observations; coverage
counts that date once. The stored adapter scopes provider, source, mode and daily
interval so multiple sources are not accidentally interpreted as duplicates.

### 3. Validate candle values

All four prices must be finite and greater than zero. High must be at least every
other OHLC value, and low must be at most every other value. Volume must be finite
and nonnegative. A missing or invalid volume is critical; zero volume is a warning.
A candle explicitly naming another instrument is critical.

The validator then compares consecutive usable closes. Missing/invalid sessions
reset that comparison. A configured run of unchanged closes produces a stale
warning; it does not prove the exchange record is wrong. Symbol changes produce
a warning because a legitimate rename also needs reference-history confirmation.

### 4. Explain unusual moves

A sufficiently large close-to-close move first becomes an outlier. Action records
are independently validated before being considered explanatory. A price-changing
action must have a usable factor or dividend amount and match the observed move
within tolerance. Mere coincidence with an action date cannot suppress a warning.

Example with prior close 100 and current close 50:

| Evidence | Result |
| --- | --- |
| Valid split, adjustment factor 0.5 | Informational corporate-action move |
| Symbol change only | Unexplained-move warning |
| Split with no usable factor | Unexplained-move warning |
| Split factor 0.25 | Unexplained-move warning because the move does not match |
| Invalid OHLC bounds | Critical data failure regardless of an action |

`confirmed_market_moves` represents verification supplied by the caller; the
engine itself does not consult exchange announcements or confirm news externally.

### 5. Validate auxiliary records

Fundamentals are grouped by instrument, statement type and period type. Duplicate
identity additionally includes period end and revision. Revisions are checked in
revision-number order against their report dates. Inferred fiscal gaps cover only
the interval between observed periods; discovering an absent latest filing needs
an explicitly supplied expected reporting calendar.

News duplicate identity uses instrument plus URL, falling back to title and
timestamp. This identifies duplicate records, not all semantically similar news.
Missing/future timestamps and missing source/title values are reported. Naive
timestamps are interpreted as UTC with a warning. A supplied reference mapping
allows instrument and ticker checks; a current mapping can flag historical renames.

Corporate actions normalize aliases before comparing identities. Conflicting
factors remain critical. The validator does not calculate cumulative price/volume
adjustments; that is Step 03's responsibility. Reference checks validate identity
fields, duplicates and chronological listing/delisting boundaries.

### 6. Interpret the report correctly

An isolated missing candle can have `quality_status: WARNING` and `is_valid: false`.
These fields answer different questions: severity describes the issue, while
validity says whether that observation can be used. Never accept a missing row
because its score is relatively high. A zero-volume candle may remain a warning
in Data Quality; the Returns engine applies a stricter no-trading rule.

Instrument coverage measures presence, not correctness. Consequently, 100%
coverage can coexist with critical duplicate/price failures. The average quality
score likewise does not override critical status or row exclusions.

## Python usage and downstream integration

```python
from app.engines.data_quality.data_quality_service import validate_ohlcv, require_quality

report = validate_ohlcv(
    instrument_key="EXAMPLE",
    sessions=["2026-09-14", "2026-09-15"],
    records=[
        {"date": "2026-09-14", "open": 100, "high": 102,
         "low": 99, "close": 101, "volume": 1000},
        {"date": "2026-09-15", "open": 101, "high": 104,
         "low": 100, "close": 103, "volume": 1200},
    ],
)
require_quality(report)  # Raises ValueError if the batch is unusable.
```

The guard is intentionally strict at the batch level. Returns uses per-metric
validity because a historical gap should not block every unrelated calculation.
For a Returns snapshot, the producer associates each source observation with its
quality result, obtains Step 03 adjusted prices and versions, then supplies
`quality_valid`, `adjustment_valid`, adjustment provenance and historical eligibility.
The Returns engine also checks its own numeric requirements, missing sessions,
no-trading state and adjustment availability.

This is an explicit producer contract. The Returns API does not automatically
fetch a Data Quality report or certify a caller's `quality_valid: true` claim.
Its immutable stored request preserves the exact inputs used. See `docs/returns.md`
for calculation examples, versioned storage, label isolation and the full plan.

## Operating checklist

1. Load a complete eligible calendar and historical reference mapping.
2. Validate supplied records or call a stored-data endpoint.
3. Inspect critical issues and missing inputs before interpreting scores.
4. Correct source records or metadata through the collection/reference workflow.
5. Revalidate the same requested scope after correction.
6. Pass a consistent validated snapshot to the next engine.

There is no scheduled validation job, persisted report history or repair workflow
in this module. API calls return reports immediately. Automatic scheduling and
report persistence remain integration work; restarting the application alone does
not validate its historical database.
