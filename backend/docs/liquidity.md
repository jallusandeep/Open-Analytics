# Liquidity & Tradability — Research 06

The backend engine in `app/engines/liquidity/` implements daily activity,
historical liquidity rankings, quote/depth checks and strategy capacity controls.
It runs on demand. Startup creates `liquidity_runs` and `liquidity_features`;
collection jobs do not automatically calculate liquidity or submit trades.

## API

Bearer authentication and research (`recom`) app access are required.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/liquidity/calculate` | Calculate without writing |
| `POST /api/v1/liquidity/build` | Atomically save inputs and daily features |
| `GET /api/v1/liquidity/runs/{run_id}` | Read version, configuration and status |
| `GET /api/v1/liquidity/features?run_id=...` | Read features; optional instrument_key, limit, offset |

Both POST endpoints accept `LiquidityRequest`; `/docs` exposes all fields.
The request supplies `snapshot_id`, `calendar_version`, `as_of`, sorted unique
`sessions`, `instrument_keys`, `observations`, `memberships`, and optional `options`.
Requests are limited to 20,000 instrument/session combinations.

Each observation supplies instrument/date, `available_on`, raw OHLC and volume.
Set `quality_valid=true` only after data-quality validation. Amihud additionally
requires `adjusted_close` and `adjustment_valid=true` on adjacent sessions.
All amounts and capitalization inputs are INR; fractional spreads and returns
are ratios (0.01 means 1%). Delivery percentage is 0–100.

Memberships supply instrument/date, `available_on`, `universe_id`, research
eligibility and optional sector/size group. Supply the **complete historical
membership**, including members absent from the observation set. Missing members
block universe ranking rather than silently shrinking the comparison set.
Unknown membership blocks research and execution eligibility. Historical delisted
or suspended observations remain in the output; their execution eligibility is false.

### Example

This minimal example intentionally returns insufficient-history indicators.
Supply at least 20 sessions for ADV and 21 adjusted observations for 20-day Amihud.

```json
{
  "snapshot_id": "example-2026-09-14",
  "calendar_version": "NSE-example-v1",
  "as_of": "2026-09-14",
  "sessions": ["2026-09-14"],
  "instrument_keys": ["NSE_EQ|EXAMPLE"],
  "observations": [{
    "instrument_key": "NSE_EQ|EXAMPLE",
    "date": "2026-09-14",
    "available_on": "2026-09-14",
    "open": 100, "high": 102, "low": 99, "close": 101,
    "volume": 1000000, "quality_valid": true,
    "trading_status": "ACTIVE"
  }],
  "memberships": [{
    "instrument_key": "NSE_EQ|EXAMPLE",
    "date": "2026-09-14",
    "available_on": "2026-09-14",
    "universe_id": "example-universe"
  }]
}
```

## Calculation conventions

- Rolling metrics include the current session and require a full valid window.
  Missing sessions are unknown, never synthesized as zero volume. Known zero-volume
  sessions count against trading frequency. No observations after `as_of` are used.
- `available_on` is conservative session-level availability. Late data is excluded
  from its historical session, even if it is present in a later snapshot. Callers
  must provide historical capitalization, status and peer classifications; there
  are no joins to today's security master.
- Exchange traded value takes priority over `close * volume`; the source is
  recorded. Contradictory zero/nonzero volume and value invalidate traded value.
- Means cover volume windows 5/10/20/60/126/252 and value windows
  5/20/60/126/252. Medians cover 20/60/252. Population standard deviation is used
  for CV and z-scores; zero-variance z-scores are null. RVOL uses the inclusive mean.
- Amihud is absolute adjusted fractional return per INR; zero traded value,
  invalid adjustment or missing adjacent sessions yields null. No raw-price
  fallback is used. `amihud_*` and `amihud_illiquidity_*` are equivalent aliases.
- Turnover is traded value / contemporaneous cap; rolling turnover is the mean
  daily ratio. Velocity is 20-session traded value / current historical free-float cap.
- Quotes require timezone-aware `quote_timestamp` and `observation_timestamp`.
  Age must be between zero and `max_quote_age_seconds` (default 300). Crossed,
  missing or stale quotes yield null spread/depth. Daily spread averages require
  valid quotes throughout the window; these are daily snapshots, not intraday averages.
- Book levels must be ordered best to worst and match the supplied top quote.
  L1 sizes can substitute for an absent level list; L5 is null with fewer than five
  levels. Depth values sum price × size. Imbalance uses value-weighted sides.
- ADV capacity uses 20-day average traded value. Daily capacity is ADV × configured
  participation. Position-capacity aliases represent **one day's** capacity, not a
  recommended holding. Share capacity rounds down to the market lot.
- Order shares are valued at order price, falling back to close. If both shares
  and value are supplied they must agree. Positive positions with unknown/zero
  capacity fail the exit check; liquidation time is null, never infinite JSON.
- Optional impact is explicitly a configured square-root proxy:
  coefficient × 20-session adjusted-return volatility × sqrt(participation).
  Expected slippage is half quoted spread plus this impact, in bps. Both remain
  null without necessary inputs/configuration; this is not an empirical execution
  forecast. Realized buy/sell slippage uses supplied execution/reference prices.
- Trends compare metrics with 21 sessions earlier; relative changes are oriented
  so increasing ADV/depth and decreasing spread/Amihud improve liquidity. Their
  mean is classified using `trend_threshold`. Shocks compare adjacent sessions:
  volume/ADV/depth collapse or spread/Amihud spike. Outliers remain in all averages.

## Rankings, quality and eligibility

Percentiles use average tied ranks scaled 0–100. Larger percentiles always mean
better liquidity, including reversed spread and Amihud ranks. Z-scores retain
the source direction. Minimum peer count defaults to three. Sector/size ranks
compare composite scores within the dated peer group.

Default composite weights are ADV 40%, frequency 30%, Amihud 30%; they are
configurable engineering defaults, not calibrated investment parameters. At least
two positive supported components are required. Missing required components yield
null scores, never automatic reweighting. Buckets split scores into five equal
20-point bands from VERY_LOW to VERY_HIGH. `tradability_score` is the composite
when execution-eligible, zero when rejected, and may be null without peer scores.

Supported components also include spread, depth and estimated impact. Impact
percentiles reverse direction so lower impact is better. `delivery_zscore` aliases
the 20-session delivery-percentage z-score. `spread` and `trading_frequency` alias
fractional quoted spread and 20-session frequency for historical snapshots.

`research_eligible`, `liquidity_eligible` and `execution_eligible` are separate.
Execution additionally requires active status, fresh spread, lot/tick metadata,
acceptable requested size, and no supplied circuit/settlement/event restriction.
Depth is required by default. `liquidity_exclusion_detail` lists all failed checks;
`liquidity_exclusion_code` contains the first. Missing quote data reduces the
quality score: daily-only 50, valid spread 75, spread and depth 100; invalid ADV 0.

Optional `max_price_impact`, `max_expected_slippage_bps` and `max_volume_cv`
reject both unavailable estimates and values above their limits. Optional
`require_stable_order_book` and `require_derivatives` require explicit positive
historical evidence (`order_book_stable`, `derivatives_available`). Book stability
is supplied by the caller; it is not inferred from a single daily snapshot.
Unknown circuit limits produce a null circuit-risk flag, not an assertion of safety.

Default mechanical thresholds: INR 10 million ADV, 1% maximum spread, 95% trading
frequency, 5% participation and five liquidation days. Configure these for the
strategy. An eligibility result without order/position inputs only evaluates
instrument conditions; it does not certify a particular trade size.

Circuit proximity uses supplied limits and a default 1% buffer; auction,
settlement, trade-to-trade, special-series and event flags are caller supplied.
Unknown optional flags are not independently verified by the engine. There is no
live quote connector, tick-history model or automatic corporate-event enrichment.
Future liquidity-adjusted risk/alpha models remain downstream consumers, as in
Research 06 sections 6.49–6.50.

## Persistence and verification

Build IDs hash the calculation version plus the entire input/configuration.
Repeated identical builds reuse the snapshot. Inputs and features commit together;
failed writes roll back. Saved snapshots retain unavailable and ineligible rows.

Run `python -m pytest tests/unit/test_liquidity.py -o addopts= -q` from `backend`.
Tests cover formula values, missing/zero observations, late data, stale/future
quotes, historical rank completeness, capacity, invalid input, persistence and API auth.

## Research 06 audit matrix

The following maps all sections to implementation and verification. Tests are in
`tests/unit/test_liquidity.py`; they include a direct contract check against the
recommended record in section 6.54. "Conditional" means the feature is calculated
when the required caller-supplied historical inputs exist, and otherwise stays null.

| Research sections | Implementation | Verification |
| --- | --- | --- |
| 6.1–6.2 | Multidimensional daily inputs; explicit quality and availability | Schema, missing-data, composite tests |
| 6.3–6.9 | Volume/value windows, medians, frequency, zeros, CV, RVOL, z-scores | Hand-calculated series, full-year, zero-volume and event tests |
| 6.10 | Cap/free-float turnover and rolling means, conditional | Activity statistics test |
| 6.11–6.14 | Quoted/effective spread, book levels, value depth/imbalance, conditional | Spread/slippage, depth ordering and level tests |
| 6.15 | Adjusted-return Amihud and rolling windows | Adjacent-session, adjustment and full-year tests |
| 6.16–6.17 | Realized slippage; configured impact/slippage proxy, conditional | Buy/sell sign, impact and missing-estimate tests |
| 6.18–6.21 | Participation, ADV caps, shares, liquidation time | Capacity boundaries, lots, zero capacity, share-order tests |
| 6.22–6.25 | Composite buckets, percentiles, z-scores and weights | Direction, ties, impact composite and incomplete-universe tests |
| 6.26–6.28 | Separate eligibility/score and configurable strategy restrictions | Status, event, size and optional restriction tests |
| 6.29–6.31 | Configurable depth/spread/slippage/stability/exit controls | Strategy-specific and stable-book tests; no hard-coded strategy presets |
| 6.32–6.34 | Microcap, circuits and exceptional-market flags, conditional | Circuit metadata and market restriction tests |
| 6.35–6.37 | Delivery stats, trade counts, size/value and turnover velocity | Hand-calculated activity test |
| 6.38–6.39 | 21-session changes, trend and adjacent-session shocks | Three trend classifications and retained volume-event test |
| 6.40 | Universe, sector and size peer percentiles | Composite peer and incomplete-universe tests |
| 6.41–6.43 | Immutable dated snapshots and availability filtering | As-of truncation, future perturbation, delisting and immutable API build tests |
| 6.44–6.46 | Null missing/stale quote data and explicit quality flags | Missing/stale/future/crossed quotes and invalid-row contract tests |
| 6.47–6.48 | Preserve flagged volume and block/bulk values | Event retention and circuit metadata tests |
| 6.49–6.50 | Future risk/alpha consumers, explicitly deferred by specification | Not implemented in Step 06 |
| 6.51–6.53 | Reject oversize trades and list exclusion reasons | Participation/exit boundaries and strategy restriction tests |
| 6.54–6.55 | Recommended daily record and initial production metrics | Spec-derived field contract and metric tests |
| 6.56–6.58 | On-demand pipeline, guarded historical inputs, API/persistence | Calculation, API, rollback, snapshot and formula tests above |

Limitations: tick-by-tick ingestion, intraday book-history stability estimation,
empirically calibrated execution-cost models and live quote acquisition are not
implemented. Daily input snapshots support conditional quote/depth metrics and
explicitly labeled cost proxies. The engine does not claim the full advanced/live
execution system described as future work in the research document.
