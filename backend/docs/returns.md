# Returns Engine — Research Step 04

## Purpose and implementation status

The Returns engine converts a versioned, validated market-data snapshot into daily
returns, trailing performance, calendar-period performance, reference comparisons,
historical-universe rankings and separately generated forward labels.

Implementation: `backend/app/engines/returns/`.
Research source: `Research/04_returns_engine.md`.
Companion validation guide: `docs/data-quality.md`.

This is a working calculation and persistence engine with authenticated APIs.
It accepts supplied adjusted snapshots; it does **not** generate corporate-action
adjustments or claim that the current instrument master is a historical universe.
Those upstream services are still required for automatic production builds.

## Does it run automatically?

No. Neither application startup nor collection completion launches a Returns
build. Startup creates the storage tables. An API request or Python caller starts
calculation, storage or label generation explicitly.

Planned automatic sequence, once upstream contracts are reliable:

```text
Collection completes
  -> Data Quality validation on the input snapshot
  -> Corporate Action Adjustment publishes versioned prices
  -> Historical universe and benchmark mappings are attached
  -> Returns build
  -> Cross-sectional rankings
  -> Separately authorized label build
```

Calling Data Quality and later loading different data is not a safe gate. Producers
must pass the same validated snapshot and its provenance into Returns.

## Package and responsibilities

| File | Responsibility |
| --- | --- |
| `returns_schema.py` | Bounded input contracts and label requests |
| `returns_service.py` | Session alignment, per-metric validity, returns and forward targets |
| `cross_sectional.py` | Historical-universe and sector-peer ranks, winsorization and z-scores |
| `returns_repository.py` | Tables, content-addressed snapshots, transactions and reads |
| `returns_routes.py` | Authenticated calculation, build and read endpoints |

Calendar, relative-return and label calculations currently share the service
module. They were separate modules in the implementation plan; keeping them
together avoids duplicating the session-grid and validity logic.

## Input contract and upstream dependencies

Every request supplies:

- `snapshot_id`: producer's input-snapshot identifier.
- `calendar_version`: identifier for the authoritative exchange calendar.
- `as_of`: last date whose data can be used.
- `sessions`: sorted, unique official sessions, including sessions with missing data.
- `instrument_keys`: securities to calculate. Reference indices may appear in
  `prices` without appearing here.
- `prices`: dated, versioned observations.
- `eligibility`: dated membership, horizon eligibility and benchmark mappings.
- `price_basis`: `adjusted` (default), `total_return`, or explicit diagnostic `raw`.

Each price observation has `instrument_key`, `date`, `available_on`, optional raw
and adjusted OHLC, `total_return_close`, volume, quality and adjustment flags.
`quality_valid` and `adjustment_valid` default to false. Adjusted calculations also
require `adjustment_source` and `adjustment_version`. These are attestations from
the producer, not an independent certification of the adjustment method.

An observation published after its session is excluded from that session's
point-in-time feature. A daily bar cannot be declared available before its session.
This API has **day precision**: its outputs are end-of-session features and must
not be used as same-day opening-time signals.

Eligibility contains `eligible_horizons`, optional `universe_id`, `sector_id`,
`benchmark_id`, `sector_benchmark_id`, and `industry_benchmark_id`, plus `date` and
`available_on`. Mappings first known after their effective session are excluded.
Duplicate mappings are rejected. One universe membership per instrument/date is
supported per run; build a separate run for another universe.

The current reference-data UI/master is not a substitute for these historical
snapshots. The engine cannot verify that a submitted calendar or membership list
is complete; the producer owns that contract.

## API examples

All routes start with `/api/v1/returns` and require bearer authentication and
research app access. Restart the backend to register the routes and create tables.

Minimal two-session calculation:

```json
{
  "snapshot_id": "example-v1",
  "calendar_version": "example-calendar-v1",
  "as_of": "2026-09-15",
  "sessions": ["2026-09-14", "2026-09-15"],
  "instrument_keys": ["EXAMPLE"],
  "prices": [
    {
      "instrument_key": "EXAMPLE", "date": "2026-09-14",
      "available_on": "2026-09-14", "adjusted_open": 100,
      "adjusted_close": 100, "volume": 1000,
      "quality_valid": true, "adjustment_valid": true,
      "adjustment_source": "example", "adjustment_version": "1"
    },
    {
      "instrument_key": "EXAMPLE", "date": "2026-09-15",
      "available_on": "2026-09-15", "adjusted_open": 102,
      "adjusted_close": 103, "volume": 1200,
      "quality_valid": true, "adjustment_valid": true,
      "adjustment_source": "example", "adjustment_version": "1"
    }
  ],
  "eligibility": [
    {"instrument_key": "EXAMPLE", "date": "2026-09-14", "available_on": "2026-09-14", "eligible_horizons": []},
    {"instrument_key": "EXAMPLE", "date": "2026-09-15", "available_on": "2026-09-15", "eligible_horizons": [1]}
  ]
}
```

`POST /calculate` returns the results without storing them. September 15's simple
return is `0.03`, overnight return is `0.02`, and intraday return is `103/102 - 1`.
Returns are decimals, not display percentages. Unavailable metrics remain null.

Use the same body with `POST /build` to save a versioned run. It returns `run_id`.

| Endpoint | Behavior |
| --- | --- |
| `POST /calculate` | Calculate features, completed-period returns and ranks; no write |
| `POST /build` | Calculate and persist a complete immutable snapshot |
| `GET /runs/{run_id}` | Run status and provenance |
| `GET /series?run_id=...` | Daily return series |
| `GET /features?run_id=...` | Trailing and relative-return features, never labels |
| `GET /rankings?run_id=...` | Universe/sector statistics |
| `GET /periods?run_id=...` | Completed weekly/monthly/quarterly/annual observations |
| `POST /labels/build` | Generate labels from an existing stored snapshot |
| `GET /labels?run_id=...` | Read separately stored research labels |

Read endpoints accept optional `instrument_key`, `limit` (up to 5,000), and `offset`.
A calculation accepts at most 20,000 instrument-session output positions and
20,000 input price rows; split larger workloads into coherent universe/date batches.
Do not split a ranking universe into partial batches and interpret partial ranks
as full-universe ranks.

Label request:

```json
{"run_id": "<returned run id>", "horizons": [1, 2, 5, 10, 21, 63]}
```

## Calculation rules and output

Each feature row carries `metrics`, `invalid_reasons`, price basis, availability
date, adjustment provenance, membership/mapping identifiers and quality flags.

| Group | Implemented calculations |
| --- | --- |
| Daily | Simple return, log return, raw/adjusted price/total-return diagnostics |
| Session | Intraday, overnight, open-to-open, gap and interaction component |
| Range | High/low ratio, open-to-high/low, close-to-high/low distances |
| Trading horizons | 1, 2, 3, 5, 10, 21, 42, 63, 126, 189, 252, 504, 756, 1260 sessions |
| Calendar | WTD, MTD, QTD, YTD and previous completed week/month/quarter/year |
| Growth | Cumulative return, 2/3/5-year CAGR |
| Relative | Market, sector and industry reference returns and arithmetic differences |
| Risk-free | Daily asset return minus supplied, already frequency-aligned risk-free return |
| Behavior | Positive/negative/zero flags and current/maximum sign streaks |
| Quality | Null reasons, extreme-return warnings, last trade date and last valid daily return |

### Session indexing and missing observations

`return_Nd = P[t] / P[t-N] - 1`; N counts supplied exchange sessions. N-session
returns require N+1 endpoints on that calendar and producer-provided eligibility.
Friday to Monday can be one session. Missing Monday is not removed from the grid.

The engine never forward-fills prices or converts missing returns to zero. It
conservatively rejects windows with invalid interior observations as well as bad
endpoints. Each metric has its own required fields: a missing previous close does
not invalidate today's open-to-close return, and a missing current close does not
invalidate a usable previous-close-to-current-open return.

Daily `return_valid` describes `return_1d`; inspect `invalid_reasons` for each other
metric. An IPO may have valid intraday data but no daily or annual return yet.
Historical output is not filtered against today's active instruments. Supplied
terminal states are retained; a delisting payout is not invented.

Exclusion reasons include insufficient history, missing price, invalid price,
duplicate price, quality failure, no trading, suspension, unresolved corporate
action, missing eligibility, ineligible horizon and invalid observation in window.
Volume zero is no trading; absent volume is permitted for index series when the
producer marks their quality valid. Structural adjusted high/low bounds are also
checked when supplied.

### Price versus total return

Adjusted prices must be split/bonus adjusted without implicitly reinvesting cash
dividends. `total_return_close` must be a consistent wealth index produced by
Step 03 under a documented reinvestment policy. The engine calculates ratios of
that series; it does not add cash dividends to it again.

`dividend_return_component` is the difference between daily total return and price
return. Interpret it as a distribution component only when both supplied series
share a compatible adjustment convention. Intraday and overnight diagnostics are
price-based, even when the selected trailing-return basis is total return.

Unresolved corporate actions block affected calculations. Raw mode is explicitly
diagnostic and can show mechanical split movements; it is not a substitute for
adjusted production performance. No adjusted-price fallback to raw data occurs.

### Calendar performance and CAGR

MTD/QTD/YTD use the last supplied session before the calendar period begins.
Previous-period metrics compare the previous period's closing boundary with its
preceding boundary. Weekly boundaries use ISO weeks. Completed-period records
require a subsequent supplied session proving that the period ended. Include
calendar lookahead even when prices stop at `as_of`.

Cumulative return uses `cumulative_start`, or the first supplied session. If that
starting observation is invalid, later values remain null rather than silently
choosing a later start. CAGR uses the last session on/before the 2/3/5-year
anniversary and actual elapsed days divided by 365.2425; corresponding 504/756/1260
eligibility is required. Leap-day anniversaries fall back to February 28.

### Reference returns and rankings

Stock and reference windows share identical calendar endpoints and price basis.
Missing reference observations invalidate only the comparison. The upstream
producer must supply comparable reference price/total-return series; the engine
cannot identify a mislabelled provider series from prices alone.

Rank horizons are 5/21/63/126/252 sessions. Ranks use historical membership, with
best performance ranked first and average ranks for ties. Percentiles map average
ascending ranks onto 0–100. Tied values receive the same percentile. Z-scores use
population standard deviation after configurable 1%/99% winsorization; original
returns remain unchanged. A constant population has null z-score. Fewer than
three usable peers by default yields `INSUFFICIENT_PEERS`.

If declared universe members are omitted from the calculated instrument set,
rankings are marked `INCOMPLETE_UNIVERSE`. Members with unavailable horizon returns
are excluded from that horizon's numeric population, whose count is returned.
Sector-peer groups are scoped within the selected universe.

## Storage, reproducibility and labels

| Table | Contents |
| --- | --- |
| `returns_runs` | Canonical input JSON, snapshot identifier, version, status and timestamp |
| `historical_returns` | Daily metrics and provenance |
| `return_features` | Full trailing/relative feature records |
| `return_periods` | Completed calendar-period performance |
| `return_rankings` | Universe and sector ranking records |
| `forward_return_labels` | Research-only forward results |

Payloads are stored as JSON with indexed identity columns/primary keys. Run IDs
hash the normalized request and calculation version. Identical ordered inputs
reuse the completed run. Changed data creates another run, preserving the previous
snapshot. Builds write atomically; a failed transaction leaves no partial run.
Concurrent build scheduling and automatic promotion of a latest run are not
implemented. Consumers select an explicit run ID.

Labels use `P[t+N]/P[t]-1`. One-session labels also contain next-session intraday
and overnight targets. Target/availability date is the future session, and
unavailable future prices produce null labels. Feature APIs do not query the
label table. Growing the dataset requires a new input run before newly matured
labels can be generated. Downstream training must enforce target availability
and appropriate train/test boundaries.

## Implementation plan and delivery mapping

The plan from the Step 04 review was:

1. Define upstream contracts: Step 01 historical eligibility; Step 02 quality;
   Step 03 adjusted/total-return prices; authoritative calendars and mappings.
2. Establish an isolated engine package.
3. Build core daily, session, trailing and calendar returns with per-metric validity.
4. Add same-window benchmark, sector and industry comparisons.
5. Add historical-universe ranks, robust scores and sector-peer statistics.
6. Separate daily data, features, rankings, provenance and future labels in storage.
7. Extend horizons, CAGR, period aggregation, diagnostics and forward targets.
8. Add authenticated APIs, repeatable builds and eventually automatic orchestration.
9. Validate against the research completion criteria using deterministic examples.

Steps 2–7 and the manual API/storage portion of step 8 are implemented against
the explicit contracts in step 1. Tests cover step 9. Upstream production data
provision and automatic orchestration remain integrations, not completed features.

## Deliberate boundaries and remaining work

- No live raw-candle-to-adjusted-series pipeline: Step 03 must supply adjustments.
- No historical-universe reconstruction or certified calendar service.
- No automatic scheduler trigger, incremental recomputation or latest-run promotion.
  Corrected input requires explicitly rebuilding the affected snapshot and labels.
- No tick/minute/hourly engine. Daily bars supply intraday open-to-close diagnostics.
- No residual regression, factor attribution, capture ratios or model estimation;
  these belong in later Risk/Factor/Performance engines. Aligned return components
  are exposed for them.
- No intraday publication timestamps or automatic historical correction replay.
- No claim that supplied validity flags or snapshot IDs certify external data.

## Downstream Risk Engine

Saved complete Returns runs can feed `POST /api/v1/risk/build` using their
`returns_run_id`. Risk builds use adjusted or total-return snapshots and never
consume forward labels. They run on demand; completing a Returns build does not
automatically launch a Risk build. See [Risk Engine documentation](risk.md) for
metrics, quality rules, API examples and configuration.

## Verification

Run from `backend` with test dependencies installed:

```powershell
python -m pytest tests/unit/test_returns.py tests/unit/test_data_quality.py tests/unit/test_data_quality_spec.py -o addopts= -p no:cacheprovider -q
```

Tests cover known return arithmetic, split/dividend separation, overnight/intraday
compounding, missing sessions and fields, suspensions, eligibility, delayed data,
calendar periods, reference gaps, ranks/ties, future-data independence, label
separation, repeatable storage and authenticated APIs. They use synthetic snapshots
and in-memory DuckDB; they do not modify the live market-data database.
