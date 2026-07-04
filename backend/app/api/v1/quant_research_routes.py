"""Quant research API routes."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Query

from app.database import get_connection

from app.schemas.quant_research_schema import QuantActionResponse
from app.services.quant.quant_backtest_service import run_quant_backtest_service
from app.services.quant.quant_data_service import (
    get_quant_data_readiness_service,
    get_quant_pipeline_status_service
)
from app.services.quant.quant_deep_learning_service import (
    build_quant_deep_learning_dataset_service,
    get_quant_deep_learning_datasets_service,
    get_quant_deep_learning_models_service,
    train_quant_sequence_rule_baseline_service
)
from app.services.quant.quant_feature_service import build_quant_features_daily_service
from app.services.quant.quant_label_service import build_quant_labels_daily_service
from app.services.quant.quant_ml_service import (
    build_quant_ml_dataset_service,
    get_quant_ml_datasets_service,
    get_quant_ml_models_service,
    train_quant_rule_baseline_model_service
)
from app.services.quant.quant_ranking_service import (
    build_quant_rankings_daily_service,
    get_quant_rankings_service
)
from app.services.quant.quant_risk_service import (
    build_quant_risk_daily_service,
    get_quant_risk_daily_service
)
from app.services.quant.quant_trade_plan_service import (
    build_quant_trade_plans_service,
    get_quant_trade_plans_service
)
from app.services.quant.quant_walk_forward_service import run_quant_pattern_discovery_service

router = APIRouter(prefix="/quant-research", tags=["Quant Research"])


def action_response(data: dict[str, Any]) -> QuantActionResponse:
    return QuantActionResponse(
        status=str(data.get("status") or "ok"),
        message=data.get("message"),
        data=data
    )


def recommendation_from_score(score: float | None) -> str:
    if score is None:
        return "HOLD"

    if score >= 65:
        return "BUY"

    if score <= 40:
        return "SELL"

    return "HOLD"


def recommendation_from_signal(signal_label: str | None) -> str:
    clean_label = str(signal_label or "").strip().lower()

    if clean_label in {"strong watch", "watch"}:
        return "BUY"

    if clean_label in {"weak", "avoid"}:
        return "SELL"

    return "HOLD"


def clamp_score(value: Any, default: float | None = None) -> float | None:
    try:
        score = float(value)
    except Exception:
        return default

    return max(0.0, min(100.0, score))


def normalize_model_score(value: Any) -> float | None:
    try:
        raw_score = float(value)
    except Exception:
        return None

    return max(0.0, min(100.0, 50.0 + (raw_score / 2.0)))


def model_quality(model: dict[str, Any] | None) -> float:
    if not model:
        return 0.0

    values = []
    for key in ["precision_score", "recall_score", "accuracy"]:
        try:
            metric = float(model.get(key))
        except Exception:
            metric = 0.0

        if metric > 0:
            values.append(metric)

    if not values:
        return 0.0

    return max(0.05, min(1.0, sum(values) / len(values)))


def normalize_weights(source_quality: dict[str, float]) -> dict[str, float]:
    clean_quality = {
        key: max(0.0, float(value or 0.0))
        for key, value in source_quality.items()
    }
    total = sum(clean_quality.values())

    if total <= 0:
        return {"technical": 1.0, "ml": 0.0, "deep_learning": 0.0}

    return {
        key: value / total
        for key, value in clean_quality.items()
    }




TECHNICAL_INDICATORS = [
    {"key": "return_1d", "label": "Return 1D"},
    {"key": "return_5d", "label": "Return 5D"},
    {"key": "return_10d", "label": "Return 10D"},
    {"key": "return_20d", "label": "Return 20D"},
    {"key": "range_pct", "label": "Daily Range"},
    {"key": "close_position", "label": "Close Position"},
    {"key": "gap_pct", "label": "Gap"},
    {"key": "volume_ratio_20", "label": "Volume Ratio 20"},
    {"key": "distance_sma_20_pct", "label": "SMA 20 Distance"},
    {"key": "distance_sma_50_pct", "label": "SMA 50 Distance"},
    {"key": "volatility_20", "label": "Volatility 20"},
    {"key": "momentum_20", "label": "Momentum 20"},
    {"key": "rsi_14", "label": "RSI 14"},
    {"key": "macd_line", "label": "MACD Line"},
    {"key": "macd_signal", "label": "MACD Signal"},
    {"key": "macd_histogram", "label": "MACD Histogram"},
    {"key": "bollinger_position", "label": "Bollinger Position"},
    {"key": "bollinger_width", "label": "Bollinger Width"},
    {"key": "atr_14_pct", "label": "ATR 14 %"},
    {"key": "stochastic_k_14", "label": "Stochastic K 14"},
    {"key": "stochastic_d_3", "label": "Stochastic D 3"},
    {"key": "adx_14", "label": "ADX 14"},
    {"key": "roc_12", "label": "ROC 12"},
    {"key": "williams_r_14", "label": "Williams R 14"},
    {"key": "mfi_14", "label": "MFI 14"},
    {"key": "chaikin_money_flow_20", "label": "Chaikin Money Flow 20"},
    {"key": "vwap_distance_20", "label": "VWAP Distance 20"},
    {"key": "donchian_position_20", "label": "Donchian Position 20"},
    {"key": "obv_slope_20", "label": "OBV Slope 20"},
    {"key": "pvt_slope_20", "label": "PVT Slope 20"}
]


def normalize_indicator_weights(indicator_quality: dict[str, float]) -> dict[str, float]:
    keys = [indicator["key"] for indicator in TECHNICAL_INDICATORS]
    clean_quality = {
        key: max(0.0, float(indicator_quality.get(key) or 0.0))
        for key in keys
    }
    total = sum(clean_quality.values())

    if total <= 0:
        equal_weight = 1.0 / len(keys)
        return {key: equal_weight for key in keys}

    return {
        key: value / total
        for key, value in clean_quality.items()
    }


def get_dynamic_technical_profile() -> dict[str, Any]:
    conn = get_connection()
    indicator_select = ",\n                    ".join(
        f"feature.{indicator['key']}" for indicator in TECHNICAL_INDICATORS
    )
    metric_select = ",\n                ".join(
        f"COALESCE(CORR({indicator['key']}, target_value), 0.0) AS {indicator['key']}_corr"
        for indicator in TECHNICAL_INDICATORS
    )

    try:
        row = conn.execute(f"""
            WITH training_rows AS (
                SELECT
                    {indicator_select},
                    CASE WHEN label.future_positive_10d THEN 1.0 ELSE 0.0 END AS target_value
                FROM quant_features_daily feature
                JOIN quant_labels_daily label
                  ON label.instrument_key = feature.instrument_key
                 AND label.trading_date = feature.trading_date
                WHERE label.future_positive_10d IS NOT NULL
                  AND feature.trading_date < (
                      SELECT MAX(trading_date)
                      FROM quant_features_daily
                  )
                ORDER BY feature.trading_date DESC
                LIMIT 200000
            )
            SELECT
                COUNT(*) AS sample_count,
                {metric_select}
            FROM training_rows;
        """).fetchone()

        sample_count = int(row[0] or 0) if row else 0
        correlations: dict[str, float] = {}
        indicator_quality: dict[str, float] = {}
        indicator_direction: dict[str, int] = {}

        for index, indicator in enumerate(TECHNICAL_INDICATORS, start=1):
            key = indicator["key"]
            try:
                correlation = float(row[index] or 0.0) if row else 0.0
            except Exception:
                correlation = 0.0

            correlations[key] = correlation
            indicator_quality[key] = abs(correlation)
            indicator_direction[key] = -1 if correlation < 0 else 1

        indicator_weights = normalize_indicator_weights(indicator_quality)
        average_quality = sum(indicator_quality.values()) / len(indicator_quality)
        technical_quality = max(0.20, min(1.0, average_quality * 8.0)) if sample_count >= 100 else 0.35

        return {
            "sample_count": sample_count,
            "indicator_correlations": correlations,
            "indicator_quality": indicator_quality,
            "indicator_direction": indicator_direction,
            "indicator_weights": indicator_weights,
            "component_weights": {
                "return": sum(indicator_weights.get(key, 0.0) for key in ["return_1d", "return_5d", "return_10d", "return_20d", "momentum_20", "roc_12", "rsi_14", "williams_r_14", "stochastic_k_14", "stochastic_d_3"]),
                "volume": sum(indicator_weights.get(key, 0.0) for key in ["volume_ratio_20", "mfi_14", "chaikin_money_flow_20", "obv_slope_20", "pvt_slope_20"]),
                "trend": sum(indicator_weights.get(key, 0.0) for key in ["distance_sma_20_pct", "distance_sma_50_pct", "close_position", "gap_pct", "macd_line", "macd_signal", "macd_histogram", "adx_14", "donchian_position_20", "vwap_distance_20"]),
                "risk": sum(indicator_weights.get(key, 0.0) for key in ["range_pct", "volatility_20", "atr_14_pct", "bollinger_width"])
            },
            "technical_quality": technical_quality
        }

    except Exception:
        indicator_weights = normalize_indicator_weights({})
        return {
            "sample_count": 0,
            "indicator_correlations": {},
            "indicator_quality": {},
            "indicator_direction": {},
            "indicator_weights": indicator_weights,
            "component_weights": {
                "return": sum(indicator_weights.get(key, 0.0) for key in ["return_1d", "return_5d", "return_10d", "return_20d", "momentum_20", "roc_12", "rsi_14", "williams_r_14", "stochastic_k_14", "stochastic_d_3"]),
                "volume": sum(indicator_weights.get(key, 0.0) for key in ["volume_ratio_20", "mfi_14", "chaikin_money_flow_20", "obv_slope_20", "pvt_slope_20"]),
                "trend": sum(indicator_weights.get(key, 0.0) for key in ["distance_sma_20_pct", "distance_sma_50_pct", "close_position", "gap_pct", "macd_line", "macd_signal", "macd_histogram", "adx_14", "donchian_position_20", "vwap_distance_20"]),
                "risk": sum(indicator_weights.get(key, 0.0) for key in ["range_pct", "volatility_20", "atr_14_pct", "bollinger_width"])
            },
            "technical_quality": 0.35
        }

    finally:
        conn.close()


def get_latest_indicator_scores_by_instrument(trading_date: str | None, limit: int) -> dict[str, dict[str, float]]:
    if not trading_date:
        return {}

    conn = get_connection()
    score_columns = []
    for indicator in TECHNICAL_INDICATORS:
        key = indicator["key"]
        score_columns.append(f"""
                CASE
                    WHEN {key} IS NULL THEN NULL
                    ELSE CUME_DIST() OVER (ORDER BY {key}) * 100.0
                END AS {key}_score
        """)

    try:
        rows = conn.execute(f"""
            WITH latest_features AS (
                SELECT
                    instrument_key,
                    trading_symbol,
                    {", ".join(indicator["key"] for indicator in TECHNICAL_INDICATORS)}
                FROM quant_features_daily
                WHERE trading_date = TRY_CAST(? AS DATE)
            ),
            scored AS (
                SELECT
                    instrument_key,
                    trading_symbol,
                    {", ".join(score_columns)}
                FROM latest_features
            )
            SELECT
                instrument_key,
                {", ".join(indicator["key"] + "_score" for indicator in TECHNICAL_INDICATORS)}
            FROM scored
            LIMIT ?;
        """, [trading_date, limit]).fetchall()

        scores_by_key: dict[str, dict[str, float]] = {}
        for row in rows:
            instrument_key = row[0]
            scores_by_key[instrument_key] = {}
            for index, indicator in enumerate(TECHNICAL_INDICATORS, start=1):
                try:
                    score = float(row[index]) if row[index] is not None else None
                except Exception:
                    score = None
                if score is not None:
                    scores_by_key[instrument_key][indicator["key"]] = max(0.0, min(100.0, score))

        return scores_by_key

    except Exception:
        return {}

    finally:
        conn.close()


def weighted_technical_score(
    ranking: dict[str, Any],
    indicator_scores: dict[str, float],
    technical_profile: dict[str, Any]
) -> float | None:
    indicator_weights = technical_profile.get("indicator_weights") or {}
    indicator_direction = technical_profile.get("indicator_direction") or {}
    weighted_parts = []

    for indicator in TECHNICAL_INDICATORS:
        key = indicator["key"]
        score = indicator_scores.get(key)
        weight = float(indicator_weights.get(key) or 0.0)
        direction = int(indicator_direction.get(key) or 1)

        if score is None or weight <= 0:
            continue

        directional_score = 100.0 - score if direction < 0 else score
        weighted_parts.append((directional_score, weight))

    total_weight = sum(weight for _, weight in weighted_parts)
    if total_weight <= 0:
        return clamp_score(ranking.get("final_score"), 50.0)

    return sum(score * weight for score, weight in weighted_parts) / total_weight

def latest_model(models: list[dict[str, Any]]) -> dict[str, Any] | None:
    for model in models:
        if str(model.get("status") or "").lower() == "success":
            return model

    return models[0] if models else None


def get_latest_ml_predictions_by_instrument(limit: int) -> dict[str, dict[str, Any]]:
    conn = get_connection()

    try:
        rows = conn.execute("""
            WITH latest_model AS (
                SELECT model_id
                FROM quant_ml_models
                WHERE status = 'success'
                ORDER BY trained_at DESC
                LIMIT 1
            ),
            latest_predictions AS (
                SELECT
                    prediction.instrument_key,
                    prediction.trading_symbol,
                    prediction.trading_date,
                    prediction.prediction_score,
                    prediction.prediction_label,
                    ROW_NUMBER() OVER (
                        PARTITION BY prediction.instrument_key
                        ORDER BY prediction.trading_date DESC, prediction.created_at DESC
                    ) AS row_number
                FROM quant_ml_predictions prediction
                JOIN latest_model model ON model.model_id = prediction.model_id
            )
            SELECT
                instrument_key,
                trading_symbol,
                trading_date,
                prediction_score,
                prediction_label
            FROM latest_predictions
            WHERE row_number = 1
            LIMIT ?;
        """, [limit]).fetchall()

        return {
            row[0]: {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "trading_date": str(row[2]) if row[2] else None,
                "prediction_score": row[3],
                "prediction_label": row[4]
            }
            for row in rows
        }

    except Exception:
        return {}

    finally:
        conn.close()


def get_latest_deep_learning_predictions_by_instrument(limit: int) -> dict[str, dict[str, Any]]:
    conn = get_connection()

    try:
        rows = conn.execute("""
            WITH latest_model AS (
                SELECT dl_model_id
                FROM quant_deep_learning_models
                WHERE status = 'success'
                ORDER BY trained_at DESC
                LIMIT 1
            ),
            latest_predictions AS (
                SELECT
                    prediction.instrument_key,
                    prediction.trading_symbol,
                    prediction.target_date,
                    prediction.prediction_score,
                    prediction.prediction_label,
                    ROW_NUMBER() OVER (
                        PARTITION BY prediction.instrument_key
                        ORDER BY prediction.target_date DESC, prediction.created_at DESC
                    ) AS row_number
                FROM quant_deep_learning_predictions prediction
                JOIN latest_model model ON model.dl_model_id = prediction.dl_model_id
            )
            SELECT
                instrument_key,
                trading_symbol,
                target_date,
                prediction_score,
                prediction_label
            FROM latest_predictions
            WHERE row_number = 1
            LIMIT ?;
        """, [limit]).fetchall()

        return {
            row[0]: {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "target_date": str(row[2]) if row[2] else None,
                "prediction_score": row[3],
                "prediction_label": row[4]
            }
            for row in rows
        }

    except Exception:
        return {}

    finally:
        conn.close()


def build_prediction_payload(
    limit: int = 1000,
    rebuild: bool = False,
    include_deep_learning: bool = True,
    train_missing_models: bool = False,
    progress_callback: Callable[[str], None] | None = None
) -> dict[str, Any]:
    build_steps: list[dict[str, Any]] = []

    def report_progress(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    def run_step(name: str, action, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        display_name = name.replace("_", " ")
        report_progress(f"Building {display_name}...")
        result = action(payload) if payload is not None else action()
        build_steps.append({
            "step": name,
            "status": result.get("status"),
            "message": result.get("message")
        })
        report_progress(f"Completed {display_name}.")
        return result

    report_progress("Loading saved rankings...")
    rankings_result = get_quant_rankings_service(limit=limit)
    rankings = rankings_result.get("rankings", [])

    if rebuild or not rankings or len(rankings) < limit:
        for name, action, payload in [
            ("features", build_quant_features_daily_service, None),
            ("labels", build_quant_labels_daily_service, None),
            ("rankings", build_quant_rankings_daily_service, {"limit": limit}),
            ("risk", build_quant_risk_daily_service, {"limit": limit}),
            ("trade_plans", build_quant_trade_plans_service, {"limit": limit})
        ]:
            run_step(name, action, payload)

        report_progress("Reloading rankings...")
        rankings_result = get_quant_rankings_service(limit=limit)
        rankings = rankings_result.get("rankings", [])

    trading_date = rankings_result.get("trading_date")
    report_progress("Loading risk and trade plans...")
    risk_result = get_quant_risk_daily_service(trading_date=trading_date, limit=limit) if trading_date else {"risk": []}
    trade_plan_result = get_quant_trade_plans_service(trading_date=trading_date, limit=limit) if trading_date else {"plans": []}

    if rankings and trading_date and (not risk_result.get("risk") or not trade_plan_result.get("plans")):
        if not risk_result.get("risk"):
            run_step("risk", build_quant_risk_daily_service, {"trading_date": trading_date, "limit": limit})
            risk_result = get_quant_risk_daily_service(trading_date=trading_date, limit=limit)

        if not trade_plan_result.get("plans"):
            run_step("trade_plans", build_quant_trade_plans_service, {"trading_date": trading_date, "limit": limit})
            trade_plan_result = get_quant_trade_plans_service(trading_date=trading_date, limit=limit)

    report_progress("Loading ML predictions...")
    ml_models = get_quant_ml_models_service(limit=5).get("models", [])
    ml_model = latest_model(ml_models)
    ml_predictions = get_latest_ml_predictions_by_instrument(limit)

    if rankings and train_missing_models and (rebuild or not ml_model or not ml_predictions):
        run_step("ml_dataset", build_quant_ml_dataset_service, {"limit": 200000})
        run_step("ml_train", train_quant_rule_baseline_model_service, None)
        report_progress("Reloading ML predictions...")
        ml_models = get_quant_ml_models_service(limit=5).get("models", [])
        ml_model = latest_model(ml_models)
        ml_predictions = get_latest_ml_predictions_by_instrument(limit)

    dl_models: list[dict[str, Any]] = []
    dl_model: dict[str, Any] | None = None
    dl_predictions: dict[str, dict[str, Any]] = {}

    if include_deep_learning:
        report_progress("Loading deep-learning predictions...")
        dl_models = get_quant_deep_learning_models_service(limit=5).get("models", [])
        dl_model = latest_model(dl_models)
        dl_predictions = get_latest_deep_learning_predictions_by_instrument(limit)

        if rankings and train_missing_models and (rebuild or not dl_model or not dl_predictions):
            run_step("deep_learning_dataset", build_quant_deep_learning_dataset_service, {"limit": 100000})
            run_step("deep_learning_train", train_quant_sequence_rule_baseline_service, None)
            report_progress("Reloading deep-learning predictions...")
            dl_models = get_quant_deep_learning_models_service(limit=5).get("models", [])
            dl_model = latest_model(dl_models)
            dl_predictions = get_latest_deep_learning_predictions_by_instrument(limit)

    report_progress("Calculating dynamic indicator weights...")
    technical_profile = get_dynamic_technical_profile()
    latest_indicator_scores = get_latest_indicator_scores_by_instrument(trading_date, limit)
    weights = normalize_weights({
        "technical": technical_profile["technical_quality"],
        "ml": model_quality(ml_model),
        "deep_learning": model_quality(dl_model) if include_deep_learning else 0.0
    })

    risk_by_key = {
        row.get("instrument_key"): row
        for row in risk_result.get("risk", [])
        if row.get("instrument_key")
    }
    plan_by_key = {
        row.get("instrument_key"): row
        for row in trade_plan_result.get("plans", [])
        if row.get("instrument_key")
    }

    report_progress("Building final recommendation rows...")
    rows = []
    for ranking in rankings:
        instrument_key = ranking.get("instrument_key")
        risk = risk_by_key.get(instrument_key, {})
        plan = plan_by_key.get(instrument_key, {})
        signal_label = ranking.get("signal_label")
        technical_score = weighted_technical_score(ranking, latest_indicator_scores.get(instrument_key, {}), technical_profile)
        ml_prediction = ml_predictions.get(instrument_key, {})
        dl_prediction = dl_predictions.get(instrument_key, {})
        ml_score = normalize_model_score(ml_prediction.get("prediction_score"))
        dl_score = normalize_model_score(dl_prediction.get("prediction_score"))

        weighted_parts = []
        if technical_score is not None:
            weighted_parts.append((technical_score, weights.get("technical", 0.0)))
        if ml_score is not None:
            weighted_parts.append((ml_score, weights.get("ml", 0.0)))
        if dl_score is not None:
            weighted_parts.append((dl_score, weights.get("deep_learning", 0.0)))

        used_weight = sum(weight for _, weight in weighted_parts)
        ensemble_score = (
            sum(score * weight for score, weight in weighted_parts) / used_weight
            if used_weight > 0
            else technical_score
        )
        recommendation = recommendation_from_score(ensemble_score)

        rows.append({
            "instrument_key": instrument_key,
            "trading_symbol": ranking.get("trading_symbol"),
            "trading_date": ranking.get("trading_date"),
            "rank_number": ranking.get("rank_number"),
            "recommendation": recommendation,
            "technical_recommendation": recommendation_from_signal(signal_label),
            "signal_label": signal_label,
            "prediction_score": ensemble_score,
            "technical_score": technical_score,
            "ml_score": ml_score,
            "deep_learning_score": dl_score,
            "close_price": ranking.get("close_price"),
            "return_1d": ranking.get("return_1d"),
            "return_5d": ranking.get("return_5d"),
            "return_10d": ranking.get("return_10d"),
            "return_20d": ranking.get("return_20d"),
            "volume_ratio_20": ranking.get("volume_ratio_20"),
            "volatility_20": ranking.get("volatility_20"),
            "momentum_20": ranking.get("momentum_20"),
            "risk_level": risk.get("risk_level"),
            "risk_score": risk.get("risk_score", ranking.get("risk_score")),
            "entry_price": plan.get("entry_price"),
            "stop_loss_price": plan.get("stop_loss_price"),
            "target_1_price": plan.get("target_1_price"),
            "target_2_price": plan.get("target_2_price"),
            "reason": plan.get("plan_reason") or ranking.get("signal_reason")
        })

    rows.sort(key=lambda row: row.get("prediction_score") or 0, reverse=True)
    report_progress(f"Saving {len(rows)} prediction rows...")

    return {
        "status": rankings_result.get("status") or "success",
        "message": rankings_result.get("message"),
        "trading_date": trading_date,
        "build_steps": build_steps,
        "weights": weights,
        "technical_profile": technical_profile,
        "models": {
            "ml": ml_model,
            "deep_learning": dl_model
        },
        "row_count": len(rows),
        "rows": rows
    }

def ensure_prediction_cache_tables() -> None:
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quant_prediction_runs (
                run_id VARCHAR PRIMARY KEY,
                status VARCHAR NOT NULL,
                message VARCHAR,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                trading_date DATE,
                row_count INTEGER DEFAULT 0,
                config_json TEXT,
                weights_json TEXT,
                technical_profile_json TEXT,
                models_json TEXT,
                build_steps_json TEXT,
                error_message VARCHAR
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quant_prediction_rows (
                run_id VARCHAR NOT NULL,
                row_number INTEGER NOT NULL,
                instrument_key VARCHAR,
                trading_symbol VARCHAR,
                trading_date DATE,
                recommendation VARCHAR,
                prediction_score DOUBLE,
                row_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quant_prediction_runs_status_completed ON quant_prediction_runs(status, completed_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quant_prediction_rows_run_rank ON quant_prediction_rows(run_id, row_number);")
    finally:
        conn.close()


def latest_active_prediction_run() -> dict[str, Any] | None:
    ensure_prediction_cache_tables()
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT run_id, status, started_at, message
            FROM quant_prediction_runs
            WHERE status IN ('queued', 'running')
            ORDER BY started_at DESC
            LIMIT 1;
        """).fetchone()
        if not row:
            return None
        return {
            "run_id": row[0],
            "status": row[1],
            "started_at": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
            "message": row[3]
        }
    finally:
        conn.close()


def load_latest_prediction_cache(limit: int = 1000) -> dict[str, Any] | None:
    ensure_prediction_cache_tables()
    conn = get_connection()
    try:
        completed_runs = conn.execute("""
            SELECT
                run_id,
                status,
                message,
                started_at,
                completed_at,
                trading_date,
                row_count,
                weights_json,
                technical_profile_json,
                models_json,
                build_steps_json,
                config_json
            FROM quant_prediction_runs
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 10;
        """).fetchall()
        run = None
        run_config: dict[str, Any] = {}
        for candidate in completed_runs:
            candidate_config = json.loads(candidate[11] or "{}")
            candidate_limit = int(candidate_config.get("limit") or 0)
            if candidate_limit >= limit:
                run = candidate
                run_config = candidate_config
                break
        if not run:
            return None

        row_records = conn.execute("""
            SELECT row_json
            FROM quant_prediction_rows
            WHERE run_id = ?
            ORDER BY row_number
            LIMIT ?;
        """, [run[0], limit]).fetchall()
        rows = [json.loads(record[0]) for record in row_records]
        completed_at = run[4]

        return {
            "status": "success",
            "message": run[2] or "Loaded cached predictions.",
            "trading_date": str(run[5]) if run[5] else None,
            "build_steps": json.loads(run[10] or "[]"),
            "weights": json.loads(run[7] or "{}"),
            "technical_profile": json.loads(run[8] or "{}"),
            "models": json.loads(run[9] or "{}"),
            "row_count": run[6] or len(rows),
            "rows": rows,
            "cache_status": "ready",
            "cache_run_id": run[0],
            "cache_started_at": run[3].isoformat() if hasattr(run[3], "isoformat") else str(run[3]),
            "cache_completed_at": completed_at.isoformat() if hasattr(completed_at, "isoformat") else str(completed_at),
            "cache_config": run_config,
            "refresh_started": False
        }
    finally:
        conn.close()


def save_prediction_cache(payload: dict[str, Any], config: dict[str, Any]) -> str:
    ensure_prediction_cache_tables()
    run_id = str(uuid4())
    now = datetime.utcnow()
    rows = payload.get("rows") or []
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO quant_prediction_runs (
                run_id, status, message, started_at, completed_at, trading_date, row_count,
                config_json, weights_json, technical_profile_json, models_json, build_steps_json
            ) VALUES (?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, [
            run_id,
            payload.get("message"),
            now,
            now,
            payload.get("trading_date"),
            len(rows),
            json.dumps(config, default=str),
            json.dumps(payload.get("weights") or {}, default=str),
            json.dumps(payload.get("technical_profile") or {}, default=str),
            json.dumps(payload.get("models") or {}, default=str),
            json.dumps(payload.get("build_steps") or [], default=str)
        ])
        conn.executemany("""
            INSERT INTO quant_prediction_rows (
                run_id, row_number, instrument_key, trading_symbol, trading_date,
                recommendation, prediction_score, row_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, [
            [
                run_id,
                index,
                row.get("instrument_key"),
                row.get("trading_symbol"),
                row.get("trading_date"),
                row.get("recommendation"),
                row.get("prediction_score"),
                json.dumps(row, default=str)
            ]
            for index, row in enumerate(rows, start=1)
        ])
        return run_id
    finally:
        conn.close()


def update_prediction_refresh_progress(run_id: str, message: str) -> None:
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE quant_prediction_runs
            SET message = ?
            WHERE run_id = ? AND status = 'running';
        """, [message, run_id])
    finally:
        conn.close()


def cleanup_old_prediction_cache(keep_run_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM quant_prediction_rows WHERE run_id <> ?;", [keep_run_id])
        conn.execute("DELETE FROM quant_prediction_runs WHERE run_id <> ?;", [keep_run_id])
    finally:
        conn.close()


def mark_prediction_refresh_failed(run_id: str, error: Exception) -> None:
    ensure_prediction_cache_tables()
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE quant_prediction_runs
            SET status = 'failed', completed_at = ?, error_message = ?, message = ?
            WHERE run_id = ?;
        """, [datetime.utcnow(), str(error), "Prediction refresh failed.", run_id])
    finally:
        conn.close()


def refresh_prediction_cache_job(config: dict[str, Any]) -> None:
    ensure_prediction_cache_tables()
    run_id = str(uuid4())
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO quant_prediction_runs (run_id, status, message, started_at, config_json)
            VALUES (?, 'running', 'Prediction refresh is running in the background.', ?, ?);
        """, [run_id, datetime.utcnow(), json.dumps(config, default=str)])
    finally:
        conn.close()

    try:
        def report_progress(message: str) -> None:
            update_prediction_refresh_progress(run_id, message)

        payload = build_prediction_payload(**config, progress_callback=report_progress)
        completed_run_id = save_prediction_cache(payload, config)
        conn = get_connection()
        try:
            conn.execute("""
                UPDATE quant_prediction_runs
                SET status = 'superseded', completed_at = ?, message = ?
                WHERE run_id = ?;
            """, [datetime.utcnow(), f"Completed as cache run {completed_run_id}.", run_id])
        finally:
            conn.close()
        cleanup_old_prediction_cache(completed_run_id)
    except Exception as exc:
        mark_prediction_refresh_failed(run_id, exc)


def queue_prediction_refresh(background_tasks: BackgroundTasks, config: dict[str, Any]) -> bool:
    if latest_active_prediction_run():
        return False
    background_tasks.add_task(refresh_prediction_cache_job, config)
    return True


@router.post("/predictions/refresh", response_model=QuantActionResponse)
def quant_predictions_refresh(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=1000, ge=1, le=1000),
    rebuild: bool = Query(default=False),
    include_deep_learning: bool = Query(default=True),
    train_missing_models: bool = Query(default=False)
) -> QuantActionResponse:
    config = {
        "limit": limit,
        "rebuild": rebuild,
        "include_deep_learning": include_deep_learning,
        "train_missing_models": train_missing_models
    }
    queued = queue_prediction_refresh(background_tasks, config)
    return action_response({
        "status": "accepted" if queued else "running",
        "message": "Prediction refresh queued." if queued else "A prediction refresh is already running.",
        "refresh_started": queued,
        "active_run": latest_active_prediction_run()
    })


@router.get("/predictions/auto", response_model=QuantActionResponse)
def quant_auto_predictions(
    limit: int = Query(default=1000, ge=1, le=1000)
) -> QuantActionResponse:
    cached = load_latest_prediction_cache(limit=limit)
    active_run = latest_active_prediction_run()

    if cached:
        cached["refresh_started"] = False
        cached["active_run"] = active_run
        return action_response(cached)

    return action_response({
        "status": "missing",
        "message": "No saved prediction cache found. Use Refresh Predictions to build fresh data.",
        "trading_date": None,
        "row_count": 0,
        "rows": [],
        "weights": {},
        "technical_profile": {},
        "models": {},
        "cache_status": "missing",
        "refresh_started": False,
        "active_run": active_run
    })
@router.get("/readiness", response_model=QuantActionResponse)
def quant_readiness() -> QuantActionResponse:
    return action_response(get_quant_data_readiness_service())


@router.get("/pipeline/status", response_model=QuantActionResponse)
def quant_pipeline_status() -> QuantActionResponse:
    return action_response(get_quant_pipeline_status_service())


@router.post("/features/build", response_model=QuantActionResponse)
def quant_features_build() -> QuantActionResponse:
    return action_response(build_quant_features_daily_service())


@router.post("/labels/build", response_model=QuantActionResponse)
def quant_labels_build() -> QuantActionResponse:
    return action_response(build_quant_labels_daily_service())


@router.post("/patterns/discover", response_model=QuantActionResponse)
def quant_patterns_discover() -> QuantActionResponse:
    return action_response(run_quant_pattern_discovery_service())


@router.post("/backtests/run", response_model=QuantActionResponse)
def quant_backtests_run() -> QuantActionResponse:
    return action_response(run_quant_backtest_service())


@router.post("/rankings/build", response_model=QuantActionResponse)
def quant_rankings_build() -> QuantActionResponse:
    return action_response(build_quant_rankings_daily_service())


@router.post("/risk/build", response_model=QuantActionResponse)
def quant_risk_build() -> QuantActionResponse:
    return action_response(build_quant_risk_daily_service())


@router.post("/trade-plans/build", response_model=QuantActionResponse)
def quant_trade_plans_build() -> QuantActionResponse:
    return action_response(build_quant_trade_plans_service())


@router.post("/ml/datasets/build", response_model=QuantActionResponse)
def quant_ml_dataset_build() -> QuantActionResponse:
    return action_response(build_quant_ml_dataset_service())


@router.post("/ml/models/train", response_model=QuantActionResponse)
def quant_ml_model_train() -> QuantActionResponse:
    return action_response(train_quant_rule_baseline_model_service())


@router.get("/ml/datasets", response_model=QuantActionResponse)
def quant_ml_datasets() -> QuantActionResponse:
    return action_response(get_quant_ml_datasets_service())


@router.get("/ml/models", response_model=QuantActionResponse)
def quant_ml_models() -> QuantActionResponse:
    return action_response(get_quant_ml_models_service())


@router.post("/deep-learning/datasets/build", response_model=QuantActionResponse)
def quant_deep_learning_dataset_build() -> QuantActionResponse:
    return action_response(build_quant_deep_learning_dataset_service())


@router.post("/deep-learning/models/train", response_model=QuantActionResponse)
def quant_deep_learning_model_train() -> QuantActionResponse:
    return action_response(train_quant_sequence_rule_baseline_service())


@router.get("/deep-learning/datasets", response_model=QuantActionResponse)
def quant_deep_learning_datasets() -> QuantActionResponse:
    return action_response(get_quant_deep_learning_datasets_service())


@router.get("/deep-learning/models", response_model=QuantActionResponse)
def quant_deep_learning_models() -> QuantActionResponse:
    return action_response(get_quant_deep_learning_models_service())
