# Market Regime Engine — Step 18

Initial deterministic implementation of `Research/18_market_regime_engine.md`.
The service consumes prepared daily market features; it does not fetch or recompute
the upstream trend, risk, breadth, flow, liquidity or derivatives engines.

Authenticated endpoints under `/api/v1/market-regime`:

- `POST /calculate`: calculate without persistence.
- `POST /build`: persist inputs, configuration, model version, records and transition matrix.
- `GET /runs/{run_id}`: retrieve reproducible run inputs and summary.
- `GET /records?run_id=...&limit=1000&offset=0`: chronological records.

Example calculation body:

```json
{
  "snapshot_id": "nifty-close-2026-09-18",
  "as_of": "2026-09-18",
  "sessions": ["2026-09-18"],
  "observations": [{
    "date": "2026-09-18",
    "available_on": "2026-09-18",
    "market_id": "NIFTY_50",
    "source_reference": "snapshot://prepared-market-features/2026-09-18",
    "market_return_21d": 0.04,
    "market_return_63d": 0.08,
    "price_vs_sma50": 0.03,
    "price_vs_sma200": 0.08,
    "market_slope_63d": 0.001,
    "realized_volatility_21d": 0.15,
    "realized_volatility_63d": 0.16,
    "current_drawdown": -0.02,
    "breadth_score": 75,
    "breadth_coverage": 0.95,
    "institutional_flow_score": 65,
    "market_liquidity_score": 80,
    "derivatives_sentiment_score": 65,
    "derivatives_risk_score": 25
  }]
}
```

## Input contract and historical safety

Returns, price-relative-to-MA (`price / MA - 1`), daily regression slope,
annualized realized volatility, ATM IV and dispersion use decimal units.
Drawdown is in `[-1, 0]`. India VIX uses index points (15 means 15%).
Breadth/flow/liquidity/derivatives scores and IV percentile use `[0, 100]`.
MA participation and breadth coverage use `[0, 1]`; correlation uses `[-1, 1]`.
Null means missing; zero is a valid measurement.

`available_on` must be the latest availability date of **every** component in
the observation and cannot exceed its classification date. Callers must select
point-in-time upstream snapshots, including release/revision availability. This
daily API relies on that provenance contract and does not validate intraday
release times or fetch historical revisions. `source_reference` records lineage.
Observations must be unique by date/scope/market and belong to supplied sorted,
unique trading sessions. Future sessions are rejected.

Supply all authoritative sessions, including sessions with missing observations:
gaps and invalid classifications reset persistence and transition smoothing.
`days_in_current_regime` counts consecutive observed trading sessions, not calendar
days, and is left-censored at the beginning of the supplied history. Index, sector,
and global histories are isolated using `(scope, market_id)`.

## Model and outputs

Trend features are clipped to `[-1, 1]` and averaged. Volatility is normalized
between configured annualized volatility bounds; IV percentile can supplement it.
Breadth uses the supplied score or the mean available MA participation fractions.
Six normalized dimensions produce an explainable weighted score, renormalizing
weights over available inputs. Stress averages bounded volatility, drawdown,
breadth weakness, liquidity weakness, flow weakness, derivatives risk and
correlation. Per-dimension scores, contributions and disagreements are retained.

Outputs include the six trend/volatility combinations, `STRESS` and `RECOVERY`,
risk-on/off state, recovery/accumulation/distribution flags, quality flags,
confidence, transitions, persistence, correlation/dispersion context and stock
selection opportunity. Dispersion and correlation z-scores use up to 252 prior
observations only and remain null without enough history.

Bull/bear/sideways probabilities are a softmax of rule-based scores and sum to one.
They are **uncalibrated heuristic probabilities**. Stress probability is a separate
stress indicator and is not a fourth mutually exclusive softmax state. Transition
probabilities are unsmoothed empirical counts; absent history yields null persistence
probability. Each row only uses transitions observed through that date; the run's
summary matrix uses the full requested history.

High-volatility hysteresis uses separate entry/exit thresholds. Optional minimum
persistence delays label changes, while stress entry is immediate. The raw label,
current features and probabilities remain visible when a label change is delayed.
The hysteresis flag can stay high after the standalone volatility band falls.

Options expose trend/volatility normalization, regime thresholds, dimension weights,
coverage, persistence and risk budget mapping. Risk multipliers default to 1 with
`UNVALIDATED_NEUTRAL` status; configured values are advisory for downstream sizing.
Invalid classifications have null probabilities and risk multipliers. Missing
dimensions and poor breadth coverage reduce confidence and are explicitly flagged.

Builds hash canonical inputs, all options and `VERSION` for idempotent run identity.
Persisted records include `regime_model_version`; change `VERSION` whenever the
calculation semantics change.

## Deferred research extensions

Macro release/revision ingestion, HMM/clustering, calibrated probabilities,
forward-return/drawdown studies, factor/strategy attribution, detection-lag studies,
and validated dynamic factor/exposure/execution policies are not implemented.
No historical factor superiority is inferred without those research results.

Run focused tests from `backend`:

```text
python -m pytest tests/unit/test_market_regime_engine.py -o addopts= -p no:cacheprovider -q
```
