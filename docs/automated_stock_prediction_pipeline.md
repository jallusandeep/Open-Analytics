# Automated Stock Prediction Pipeline

This document explains the end-to-end prediction flow behind the frontend Predictions tab.

## Purpose

The Predictions tab automatically shows equity recommendations without asking the user for manual inputs. It combines:

- OHLCV-derived technical rankings
- Risk and trade-plan outputs
- Machine-learning baseline predictions
- Deep-learning sequence baseline predictions, when a trained deep-learning model exists

The final recommendation is an ensemble score converted into `BUY`, `HOLD`, or `SELL`.

## Frontend Files

### `frontend/src/App.jsx`

Registers the `/predictions` route and renders the prediction page through the protected route wrapper.

Key behavior:

- `/predictions` opens `QuantResearch`
- User must be authenticated
- The sidebar item already points to `/predictions` from `MainLayout`

### `frontend/src/api/quantResearchApi.js`

Contains API helpers for quant research and prediction calls.

Main prediction function:

```js
getAutomatedStockPredictions()
```

It calls:

```text
GET /api/v1/quant-research/predictions/auto
```

This is a fast cached read. If no cache exists, or the cache is stale, the backend queues a background refresh and the page polls automatically until saved rows are available. The frontend does not wait for heavy OHLCV, indicator, ML, or deep-learning computation inside the browser request.

Background refresh endpoint:

```text
POST /api/v1/quant-research/predictions/refresh
```

The refresh stores results in DuckDB cache tables:

- `quant_prediction_runs`: run status, trading date, weights, model metadata, build steps, and config
- `quant_prediction_rows`: saved prediction rows as JSON for fast readback

Current query parameters:

```text
limit=1000
rebuild=false
include_deep_learning=true
train_missing_models=false
stale_minutes=30
auto_refresh=true
```

Meaning:

- `limit=1000`: return up to 1000 ranked equities
- `rebuild=false`: do not rebuild all feature/ranking tables on every page load
- `include_deep_learning=true`: include deep-learning predictions if available
- `train_missing_models=false`: do not train ML/DL models during normal page load
- `stale_minutes=30`: treat cached results older than 30 minutes as stale
- `auto_refresh=true`: queue a backend refresh when cache is stale or missing

### `frontend/src/pages/admin/QuantResearch.jsx`

This is the Predictions page UI.

Behavior:

- Fetches predictions automatically in `useEffect`
- No manual inputs or action buttons
- Shows active ensemble weights
- Displays a table of predictions for equities

Important displayed fields:

- Symbol
- Final prediction: `BUY`, `HOLD`, `SELL`
- Final ensemble score
- Technical score
- ML score
- Deep-learning score
- Close price
- 1D, 5D, 10D, 20D returns
- Volume ratio
- Volatility
- Risk level
- Entry price
- Stop loss
- Targets
- Reason

## Backend Files

### `backend/app/main.py`

Registers the quant research router:

```python
app.include_router(quant_research_router, prefix="/api/v1")
```

This exposes all quant endpoints under:

```text
/api/v1/quant-research/...
```

### `backend/app/schemas/quant_research_schema.py`

Defines the shared response wrapper:

```python
class QuantActionResponse(BaseModel):
    status: str
    message: str | None = None
    data: dict[str, Any] | None = None
```

All quant endpoints return this shape.

### `backend/app/api/v1/quant_research_routes.py`

This is the main orchestration layer for the Predictions tab.

Main endpoint:

```text
GET /api/v1/quant-research/predictions/auto
```

Main function:

```python
quant_auto_predictions()
```

Responsibilities:

1. `GET /predictions/auto` reads the latest completed prediction cache from DuckDB.
2. If cache is missing or stale, it queues a background refresh and returns immediately.
3. `POST /predictions/refresh` starts the same background refresh directly.
4. The background builder loads latest technical rankings.
5. If no rankings exist, it builds features, labels, rankings, risk, and trade plans.
6. It loads risk rows and trade plans for the latest trading date.
7. It loads latest ML predictions and deep-learning predictions when available.
8. It computes dynamic source and indicator weights.
9. It blends technical, ML, and deep-learning scores.
10. It saves final rows to `quant_prediction_rows` for high-speed readback.

Supporting functions:

- `recommendation_from_score()` converts final score to `BUY`, `HOLD`, `SELL`.
- `normalize_weights()` normalizes technical/ML/deep-learning weights to add up to 100%.
- `model_quality()` calculates a model quality score from accuracy, precision, and recall.
- `get_latest_ml_predictions_by_instrument()` loads latest ML prediction per equity.
- `get_latest_deep_learning_predictions_by_instrument()` loads latest DL prediction per equity.

## Quant Service Files

### `backend/app/services/quant/quant_feature_service.py`

Builds `quant_features_daily` from `ohlcv_daily`.

Main function:

```python
build_quant_features_daily_service()
```

Generated features include:

- 1D, 5D, 10D, 20D returns
- Range percentage
- Gap percentage
- Volume average and volume ratio
- SMA 20 and SMA 50 distance
- Volatility 20
- Momentum 20

### `backend/app/services/quant/quant_label_service.py`

Builds `quant_labels_daily` from OHLCV data.

Main function:

```python
build_quant_labels_daily_service()
```

Labels represent future movement, currently focused around a future 10-day positive return target.

### `backend/app/services/quant/quant_ranking_service.py`

Builds `quant_rankings_daily`.

Main functions:

```python
build_quant_rankings_daily_service()
get_quant_rankings_service()
```

It converts features into technical ranking scores:

- Momentum score
- Volume score
- Trend score
- Risk score
- Final score
- Signal label: `Strong Watch`, `Watch`, `Neutral`, `Weak`, `Avoid`

### `backend/app/services/quant/quant_risk_service.py`

Builds `quant_risk_daily`.

Main functions:

```python
build_quant_risk_daily_service()
get_quant_risk_daily_service()
```

Outputs:

- Risk level
- Risk score
- Suggested stop-loss percentage
- Suggested position size percentage
- Risk reason

### `backend/app/services/quant/quant_trade_plan_service.py`

Builds `quant_trade_plans` from rankings and features.

Main functions:

```python
build_quant_trade_plans_service()
get_quant_trade_plans_service()
```

Outputs:

- Entry price
- Entry zone
- Stop loss
- Target 1
- Target 2
- Reward/risk
- Holding days
- Plan reason

### `backend/app/services/quant/quant_ml_service.py`

Builds and trains the ML baseline.

Main functions:

```python
build_quant_ml_dataset_service()
train_quant_rule_baseline_model_service()
get_quant_ml_models_service()
```

Tables:

- `quant_ml_datasets`
- `quant_ml_dataset_rows`
- `quant_ml_models`
- `quant_ml_predictions`

The current ML model is a rule baseline, not an external ML library model. It still produces model metrics and prediction rows that are used by the ensemble.

### `backend/app/services/quant/quant_deep_learning_service.py`

Builds and trains the deep-learning sequence baseline.

Main functions:

```python
build_quant_deep_learning_dataset_service()
train_quant_sequence_rule_baseline_service()
get_quant_deep_learning_models_service()
```

Tables:

- `quant_deep_learning_datasets`
- `quant_deep_learning_sequences`
- `quant_deep_learning_models`
- `quant_deep_learning_predictions`

The deep-learning dataset uses rolling sequences from feature rows. The trained sequence baseline produces deep-learning prediction scores and model metrics.

## Current End-to-End Flow

### Normal Page Load

1. User clicks Predictions in the sidebar.
2. React opens `/predictions`.
3. `QuantResearch.jsx` calls `getAutomatedStockPredictions()`.
4. Frontend calls:

```text
GET /api/v1/quant-research/predictions/auto?limit=1000&rebuild=false&include_deep_learning=true&train_missing_models=false
```

5. Backend loads latest rankings.
6. Backend loads risk and trade plans for the ranking date.
7. Backend loads the latest successful ML model and predictions.
8. Backend loads the latest successful deep-learning model and predictions.
9. Backend calculates dynamic weights.
10. Backend returns table rows.
11. Frontend renders the table.

### When No Rankings Exist

If no rankings exist, the endpoint automatically builds:

1. Features
2. Labels
3. Rankings
4. Risk rows
5. Trade plans

It does not train ML or deep-learning models unless `train_missing_models=true` is explicitly passed.

## Dynamic Weighting

The ensemble currently uses three possible sources:

```text
technical
ml
deep_learning
```

Technical quality is derived from historical feature-to-label signal strength.

The technical input weights are learned from correlations against `future_positive_10d` for every generated indicator:

- `return_1d`
- `return_5d`
- `return_10d`
- `return_20d`
- `range_pct`
- `close_position`
- `gap_pct`
- `volume_ratio_20`
- `distance_sma_20_pct`
- `distance_sma_50_pct`
- `volatility_20`
- `momentum_20`
- `rsi_14`
- `macd_line`
- `macd_signal`
- `macd_histogram`
- `bollinger_position`
- `bollinger_width`
- `atr_14_pct`
- `stochastic_k_14`
- `stochastic_d_3`
- `adx_14`
- `roc_12`
- `williams_r_14`
- `mfi_14`
- `chaikin_money_flow_20`
- `vwap_distance_20`
- `donchian_position_20`
- `obv_slope_20`
- `pvt_slope_20`

The UI also shows grouped summaries for return, volume, trend, risk, and classic indicator families such as RSI, MACD, Bollinger, ATR, stochastic, ADX, ROC, Williams %R, MFI, Chaikin Money Flow, VWAP distance, Donchian position, OBV slope, and PVT slope.

ML and deep-learning quality come from model metrics:

- Accuracy
- Precision
- Recall

The backend averages available metrics and normalizes all source qualities so weights add up to 100%.

Example after a deep-learning model is trained:

```text
technical:     34.30%
ml:            21.92%
deep_learning: 43.78%
```

## Final Score Calculation

For each equity:

1. Technical indicator weights are learned from historical correlations against `future_positive_10d`.
2. Technical score is recomputed from every generated indicator using learned indicator-level weights and direction.
3. ML score comes from latest `quant_ml_predictions.prediction_score`, normalized into a 0-100 range.
4. Deep-learning score comes from latest `quant_deep_learning_predictions.prediction_score`, normalized into a 0-100 range.
5. Available scores are blended using dynamic model-source weights.
6. The final score maps to recommendation:

```text
>= 65  BUY
<= 40  SELL
else   HOLD
```

## Deep Learning Model Added Locally

A deep-learning sequence dataset and model were created through the backend API.

Dataset:

```text
19d7e8b9-cf53-465f-9ec0-482fc40d09f1
```

Model:

```text
3bd5c3db-3750-4025-8813-1ba666b3c36a
```

Metrics:

```text
accuracy: 84.04%
precision: 100.00%
recall: 64.82%
```

Because this model exists, the Predictions page now includes deep-learning weight and deep-learning scores where matching sequence predictions exist.

## Useful API Calls

### Fetch Predictions

```text
GET /api/v1/quant-research/predictions/auto?limit=1000&rebuild=false&include_deep_learning=true&train_missing_models=false
```

### Force Rebuild Technical Pipeline

```text
GET /api/v1/quant-research/predictions/auto?limit=1000&rebuild=true&include_deep_learning=true&train_missing_models=false
```

### Build Deep-Learning Dataset

```text
POST /api/v1/quant-research/deep-learning/datasets/build
```

Payload example:

```json
{
  "limit": 100000
}
```

### Train Deep-Learning Model

```text
POST /api/v1/quant-research/deep-learning/models/train
```

Payload example:

```json
{}
```

### Train Missing Models From Auto Endpoint

This is intentionally disabled in the frontend because it can be slow.

```text
GET /api/v1/quant-research/predictions/auto?limit=1000&rebuild=false&include_deep_learning=true&train_missing_models=true
```

## Operational Notes

- Use the backend API for heavy DB writes when uvicorn is running. Direct Python scripts can hit DuckDB WAL locks if the server already owns the database.
- Normal page load should use `train_missing_models=false` to avoid blocking the UI.
- Rebuilding features/labels/rankings can be expensive, so normal page load uses `rebuild=false`.
- Deep-learning scores appear only for instruments that have matching latest sequence predictions.

## Current Limitation

The ML and deep-learning implementations are rule baselines stored in ML/DL tables. They are integrated into the ensemble and weighted by model metrics, but they are not yet neural-network models from a framework such as PyTorch or TensorFlow.
