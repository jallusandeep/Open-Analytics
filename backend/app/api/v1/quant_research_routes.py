"""Quant research API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

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


def recommendation_from_signal(signal_label: str | None) -> str:
    clean_label = str(signal_label or "").strip().lower()

    if clean_label in {"strong watch", "watch"}:
        return "BUY"

    if clean_label in {"weak", "avoid"}:
        return "SELL"

    return "HOLD"


@router.get("/predictions/auto", response_model=QuantActionResponse)
def quant_auto_predictions(
    limit: int = Query(default=1000, ge=1, le=1000),
    rebuild: bool = Query(default=False)
) -> QuantActionResponse:
    build_steps: list[dict[str, Any]] = []

    def run_step(name: str, action, payload: dict[str, Any] | None = None) -> None:
        result = action(payload) if payload is not None else action()
        build_steps.append({
            "step": name,
            "status": result.get("status"),
            "message": result.get("message")
        })

    rankings_result = get_quant_rankings_service(limit=limit)
    rankings = rankings_result.get("rankings", [])

    if rebuild or not rankings:
        for name, action, payload in [
            ("features", build_quant_features_daily_service, None),
            ("labels", build_quant_labels_daily_service, None),
            ("rankings", build_quant_rankings_daily_service, {"limit": limit}),
            ("risk", build_quant_risk_daily_service, {"limit": limit}),
            ("trade_plans", build_quant_trade_plans_service, {"limit": limit})
        ]:
            run_step(name, action, payload)

        rankings_result = get_quant_rankings_service(limit=limit)
        rankings = rankings_result.get("rankings", [])

    trading_date = rankings_result.get("trading_date")
    risk_result = get_quant_risk_daily_service(trading_date=trading_date, limit=limit) if trading_date else {"risk": []}
    trade_plan_result = get_quant_trade_plans_service(trading_date=trading_date, limit=limit) if trading_date else {"plans": []}

    if rankings and trading_date and (not risk_result.get("risk") or not trade_plan_result.get("plans")):
        if not risk_result.get("risk"):
            run_step("risk", build_quant_risk_daily_service, {"trading_date": trading_date, "limit": limit})
            risk_result = get_quant_risk_daily_service(trading_date=trading_date, limit=limit)

        if not trade_plan_result.get("plans"):
            run_step("trade_plans", build_quant_trade_plans_service, {"trading_date": trading_date, "limit": limit})
            trade_plan_result = get_quant_trade_plans_service(trading_date=trading_date, limit=limit)

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

    rows = []
    for ranking in rankings:
        instrument_key = ranking.get("instrument_key")
        risk = risk_by_key.get(instrument_key, {})
        plan = plan_by_key.get(instrument_key, {})
        signal_label = ranking.get("signal_label")

        rows.append({
            "instrument_key": instrument_key,
            "trading_symbol": ranking.get("trading_symbol"),
            "trading_date": ranking.get("trading_date"),
            "rank_number": ranking.get("rank_number"),
            "recommendation": recommendation_from_signal(signal_label),
            "signal_label": signal_label,
            "prediction_score": ranking.get("final_score"),
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

    return action_response({
        "status": rankings_result.get("status") or "success",
        "message": rankings_result.get("message"),
        "trading_date": trading_date,
        "build_steps": build_steps,
        "row_count": len(rows),
        "rows": rows
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

