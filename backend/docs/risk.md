# Risk Engine — Research 05

## Purpose and scope

Step 5 converts clean adjusted returns into measures of volatility, downside loss,
drawdown, market sensitivity, tail loss and diversification. The implementation
lives in `backend/app/engines/risk/` and implements the initial production set in
Research `05_Risk_engine.md`, section 5.56, plus several supporting metrics.

This is a backend research engine. It uses the existing embedded DuckDB connection.
It does not add Quack, place trades or change portfolio positions.

## Does it run automatically?

**Calculations are explicitly requested through the API.** Application startup
creates `risk_runs` and `risk_features` if needed. Startup does not calculate risk,
and collection or Returns builds do not automatically trigger a Risk build.

The intended sequence is:

1. Validate prices and establish corporate-action adjustment provenance.
2. Build a point-in-time Returns snapshot with an authoritative session calendar,
   instrument eligibility and benchmark mappings.
3. Call `POST /api/v1/risk/build` with its `returns_run_id`.
4. Read the saved features and their per-metric quality metadata.

This prevents a scheduled job from silently treating unvalidated raw prices as
approved research inputs. Upstream validation/adjustment flags are a trusted
input contract; the Risk Engine does not perform corporate-action adjustment.

## API

All endpoints require authentication and the existing `recom` app entitlement.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/risk/calculate` | Calculate from an inline Returns request; no writes |
| `POST /api/v1/risk/build` | Build and save risk from an existing complete Returns run |
| `GET /api/v1/risk/runs/{run_id}` | Run provenance, calculation version and configuration |
| `GET /api/v1/risk/features?run_id=...` | Features, quality, rankings, flags and score |
| `POST /api/v1/risk/covariance` | On-demand covariance/correlation for up to 50 instruments |

Features support `instrument_key`, `limit` (1–5000) and `offset`. Unknown runs
return 404; invalid inputs, raw price basis and incompatible Returns runs return
422. Calculations are synchronous and bounded by the Returns request limits
(20,000 instrument-session observations). This is a bounded research API, not a
full-market distributed calculation service.

### Build from a saved Returns run

```json
{
  "returns_run_id": "<run_id returned by /api/v1/returns/build>",
  "options": {
    "annualization_sessions": 252,
    "minimum_coverage": 1.0,
    "minimum_beta_observations": 20,
    "minimum_tail_observations": 100,
    "ranking_window": 63,
    "minimum_rank_count": 3
  },
  "trading_checks": []
}
```

For preview, `/calculate` accepts `{"returns": <ReturnsRequest>, "options": {...},
"trading_checks": [...]}`. See [Returns documentation](returns.md) for the full
Returns input contract and examples. Inline calculations do not require a saved run.

### Optional point-in-time trading evidence

```json
{
  "instrument_key": "NSE_EQ|EXAMPLE",
  "date": "2026-01-05",
  "available_on": "2026-01-05",
  "stale_price_flag": false,
  "liquidity_status": "LIQUID",
  "trading_status": "ACTIVE"
}
```

Supply these records in `trading_checks`. Evidence available after the feature's
date is ignored. Duplicate instrument/date checks are rejected. Unknown liquidity
is reported as `LIQUIDITY_UNVERIFIED`, not assumed liquid. Explicit illiquidity,
suspension, delisting or stale-price evidence invalidates affected observations.
Five identical consecutive valid closes also trigger a configurable conservative
staleness heuristic. This can flag actively traded flat prices; it is not a
replacement for the later Liquidity Engine.

## Calculation conventions

Returns and percentages use **decimal fractions**: `0.02` means 2%. Annualization
uses configurable sessions per year (default 252). Trading-session counts refer
to the supplied calendar; this engine does not infer exchange holidays.

### Volatility and downside

- Windows: 5, 10, 21, 42, 63, 126 and 252 sessions.
- `vol_Nd`: sample standard deviation of daily simple returns (`ddof=1`).
- `ann_vol_Nd`: `vol_Nd * sqrt(annualization_sessions)`.
- `log_vol_Nd`: sample standard deviation of `log(1 + return)`.
- `downside_vol_Nd` / `upside_vol_Nd`: sample standard deviation conditional on
  strictly negative / positive returns. Fewer than two conditional observations
  yields null, not a manufactured zero.
- `downside_semidev_Nd`: `sqrt(mean(min(return - target, 0)^2))` over all usable
  observations. Target is ZERO, MINIMUM_ACCEPTABLE (explicit daily return),
  RISK_FREE (point-in-time daily series), or BENCHMARK. Missing targets invalidate
  this metric rather than substituting zero.
- `ewma_vol_21d` / `ewma_vol_63d`: a forecast at session t using returns through
  t−1. Initialize variance with the first window return squared, then update
  `lambda * variance + (1-lambda) * return^2`. Default lambda is 0.94. These are
  finite-window seeded forecasts, not an infinite-history EWMA.

### Range and gap risk

Range calculations always use consistently adjusted OHLC, including when close
returns use a total-return basis. They never combine raw highs with adjusted lows.

- `atr_14`, `atr_21`: arithmetic mean of true range, not Wilder smoothing.
  True range is `max(high-low, abs(high-previous_close), abs(low-previous_close))`.
- `atr_pct_N`: ATR divided by current adjusted close.
- Parkinson: `sqrt(mean(log(high/low)^2)/(4*log(2)))`.
- Garman–Klass: square root of the mean of
  `0.5*log(high/low)^2 - (2*log(2)-1)*log(close/open)^2`.
- Range estimators are daily, unannualized. All required prices must be valid;
  missing OHLC is not relaxed by `minimum_coverage`.
- Gap windows 21, 63 and 252 report overnight sample volatility, positive/negative
  frequency, large-gap frequency, and positive/negative extrema. Large gap uses
  `large_gap_threshold` (default 3%). Frequencies are fractions, not percentages.

### Drawdown and recovery

Drawdowns are negative fractions: `close / running_peak - 1`. The chosen close
basis matches the Returns snapshot. “All history” means the supplied, known
history from its first valid close, not an assertion of complete listing history.
The start date is returned as `drawdown_history_start`.

- `current_drawdown`, `max_drawdown_all` and duration/recovery metrics use that
  history. Interior invalid/missing prices invalidate this path; they are not
  bridged or silently restarted after a gap.
- Rolling maximum drawdown and Ulcer Index use N+1 price levels over N intervals.
  Windows include 21/63/126/252 sessions and 3y/5y aliases for 756/1260 sessions.
- Ulcer Index is RMS fractional drawdown, not percentage points.
- Current duration is the number of sessions strictly below the last peak.
  Maximum duration includes an unresolved current episode. Average duration uses
  completed episodes only.
- Recovery days count trading sessions from trough to recovery. Recovery averages
  include completed episodes only. Unresolved recovery dates stay null.
- `drawdown_context` contains the worst episode's peak, trough and known recovery
  dates, plus whether the current price has recovered. No future recovery is used.

### Benchmark, sector and active risk

For each feature date the engine resolves its historical benchmark and sector
benchmark mapping, then uses that same reference throughout the trailing window.
It aligns observations by session; no forward fills or concatenated reference
regimes are used.

- Beta is sample covariance(stock, benchmark) / sample benchmark variance.
- Correlation is Pearson correlation; R² is its square for intercept OLS.
- `idio_vol_Nd` (also `idiosyncratic_volatility_Nd`) is daily sample standard
  deviation of intercept-regression residuals (`ddof=1`, not an n−2 regression
  standard-error estimator).
- CAPM-style `alpha_Nd` uses stock and benchmark returns less each session's
  known daily risk-free return. Missing rates yield null alpha. `ann_alpha_Nd`
  multiplies the daily intercept by annual sessions; it does not compound it.
- `active_return`, `mean_active_return_Nd`, `tracking_error_Nd` and
  `ann_tracking_error_Nd` supply inputs for later performance ratios.
- Zero benchmark variance makes beta/regression unavailable. Constant stock
  returns make correlation unavailable, even when beta can be zero.

### Tail risk

- Historical VaR is `max(0, -quantile(returns, 1-confidence))`, with linear
  interpolation. CVaR is `max(0, -mean(returns <= that quantile))` including ties.
- Parametric VaR is `max(0, z(confidence)*sample_std - mean_return)` under a normal
  approximation. Outputs are one-session loss magnitudes, not maximum-loss limits.
- Confidence levels are 95% and 99%; each window must meet the configured minimum
  tail count (100 by default, never less than 60). Thus default 21D/63D tail
  estimates are explicitly unavailable. A 99% tail still contains few observations
  even with 252 sessions; these are historical estimates, not calibrated guarantees.
- Skewness uses the bias-corrected Fisher–Pearson estimator. Kurtosis is
  bias-corrected **excess** kurtosis, with normal-distribution reference zero.
- `worst_1d_return_Nd` / `best_1d_return_Nd` retain signed extremes.

Statistical conventions correspond to the published
[linear quantile definition](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html),
[adjusted skewness](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.skew.html)
and [Fisher excess kurtosis](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kurtosis.html).
The implementation uses Python's standard library, adding no SciPy dependency.

## Quality and minimum history

Every metric has an entry in `metric_quality`:

```json
{
  "beta_252d": {
    "valid": false,
    "observation_count": 44,
    "invalid_reason": "INSUFFICIENT_HISTORY"
  }
}
```

Windows stay on the session grid. By default all N observations must be available.
Coverage can be relaxed to at least 80%, but explicit bad-price, corporate-action,
stale, suspended and illiquid observations still invalidate their affected return
windows. A missing current return cannot be replaced by yesterday's result.
Regressions also require `minimum_beta_observations` and sufficient overlapping
valid pairs. Per-metric counts make the sample sizes visible.

Rows provide `risk_valid`, `risk_quality_status` (INVALID/PARTIAL/WARNING/HEALTHY),
`risk_invalid_reasons` and warnings. Row validity means the designated initial
core metrics are all available; it does not mean every optional metric or the
composite score is available. Consumers must check each requested metric's quality.
Short-history IPOs keep usable short-horizon features and null long-horizon ones.

## Rankings, regime and score

Rankings use only the explicit point-in-time universe membership for that date.
If any declared member is absent from the run, ranking is invalidated rather than
presenting a smaller subset as the complete universe. Invalid metrics are excluded
from their respective peer samples and their population counts are reported.

Volatility, downside, beta, drawdown and idiosyncratic risk use `ranking_window`
(63 default). VaR/CVaR rankings always use 252D estimates. Drawdown and beta are
ranked by magnitude, so a large negative beta represents large market sensitivity.
Higher percentile means more measured risk; highest risk has rank 1. Ties receive
average ranks. Z-scores use configurable winsorization (1%/99% defaults) and
population standard deviation; identical peers have null z-scores.

`volatility_historical_percentile` compares today's annualized 21D volatility to
past valid values in the previous 252 sessions, requiring 21 by default. It uses
strictly earlier values. `historical_vol_zscore` is a separate own-history measure.
Volatility changes (5/21-session lags), the 21/252 ratio, historical-percentile
regimes and a 21-session volatility direction (`risk_trend`) are also returned.
Regimes use historical percentile cutoffs 20/80/95; they are descriptive rules,
not fitted market-regime predictions.

**No production weights are invented.** `risk_score` is null with
`WEIGHTS_NOT_CONFIGURED` until the caller supplies positive weights for any of
`volatility`, `downside`, `beta`, `drawdown`, `var`, `cvar`, `idiosyncratic`.
Configured weights are normalized and applied to the corresponding peer risk
percentiles. Every selected component must be available; missing components are
not silently reweighted. Preserve/review the selected research methodology before
using a score for decisions.

`risk_percentile` ranks valid composite scores among peers. `risk_bucket` is LOW
below 25, MEDIUM below 50, HIGH below 90 and EXTREME otherwise. These are descriptive
percentile labels, not investment suitability recommendations. Flags use the
configurable peer percentile (90 default), deep drawdown (20%) and gap (3%) limits.

## Covariance

```json
{
  "returns_run_id": "<saved run>",
  "instrument_keys": ["A", "B"],
  "as_of": "2026-01-05",
  "window": 63
}
```

Covariance uses a **common complete set of dates across all requested securities**
(listwise alignment), preserving a coherent positive-semidefinite sample covariance
matrix instead of combining incompatible pairwise samples. Response includes daily
and annualized covariance, correlation, common observation count and validity.
Undefined constant-series correlations are null. Results are calculated on demand;
the engine does not persist every pair for every day. Dates after the source cutoff
and instruments absent from the source run are rejected.

## Persistence and reproducibility

`risk_runs` stores source Returns run ID, full request configuration, calculation
version, status and creation time. `risk_features` stores each daily feature record
as JSON with a `(run_id, instrument_key, date)` primary key.

Run IDs hash the calculation version and canonical build request. Repeating an
identical build reuses the completed run; changing options or trading evidence
creates a different run. Writes are transactional. Failed writes roll back both
run metadata and features. Source Returns runs must be complete, contain the full
expected feature grid, and match the supported Returns version. Builds consume
saved return features and snapshot prices, never forward-return labels.

No automatic transaction replay is added. Concurrent builds can surface DuckDB
write conflicts; callers may retry an idempotent build after rollback.

## Research coverage and follow-ups

Implemented: the section 5.56 initial metric set; conditional upside risk,
semideviation, log volatility, EWMA, Parkinson/Garman–Klass, gap statistics,
drawdown context/recovery/Ulcer Index, sector beta, alpha/R², volatility history,
rank/z-score/flags, opt-in composite scoring and on-demand covariance.

Explicitly deferred: Rogers–Satchell/Yang–Zhang (5.13 marks these optional),
multi-day worst/best tail returns and separate tail means, upside/downside capture,
industry/portfolio-specific regressions, beta/correlation/tail slopes, portfolio
contribution, liquidity/event/derivatives models and risk-adjusted performance
ratios. Risk trend currently describes volatility direction only. Automatic
scheduled builds, a frontend dashboard and full-universe scaling are not part of
this implementation. The broader section 5.59 vision remains dependent on later
engines and verified upstream datasets.

## Validation

From `backend`:

```text
python -m pytest tests/unit/test_risk.py tests/unit/test_returns.py tests/unit/test_database.py -o addopts= -p no:cacheprovider -q
```

Tests use generated data and temporary/in-memory databases. They check analytic
beta/alpha/volatility, drawdown/recovery, tail conventions, missing/stale/illiquid
data, timestamp leakage, insufficient IPO history, adjusted ranges, peer scope,
configuration validation, saved builds, covariance and authenticated routes.
They do not access or modify the live application database.
