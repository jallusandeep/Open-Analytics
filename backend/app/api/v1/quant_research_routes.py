"""Quant research API routes.

These starter routes are intentionally simple. Register this router in backend/app/main.py
after reviewing the existing route style.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.quant_research_schema import QuantActionResponse
from app.services.quant.quant_backtest_service import run_quant_backtest
from app.services.quant.quant_data_service import get_quant_data_readiness
from app.services.quant.quant_feature_service import build_quant_features
from app.services.quant.quant_label_service import build_quant_labels
from app.services.quant.quant_pattern_service import discover_quant_patterns
from app.services.quant.quant_ranking_service import build_quant_rankings

router = APIRouter(prefix="/quant-research", tags=["Quant Research"])


@router.get("/readiness", response_model=QuantActionResponse)
def quant_readiness() -> QuantActionResponse:
    return QuantActionResponse(status="ok", data=get_quant_data_readiness())


@router.post("/features/build", response_model=QuantActionResponse)
def quant_features_build() -> QuantActionResponse:
    return QuantActionResponse(status="ok", data=build_quant_features())


@router.post("/labels/build", response_model=QuantActionResponse)
def quant_labels_build() -> QuantActionResponse:
    return QuantActionResponse(status="ok", data=build_quant_labels())


@router.post("/patterns/discover", response_model=QuantActionResponse)
def quant_patterns_discover() -> QuantActionResponse:
    return QuantActionResponse(status="ok", data=discover_quant_patterns())


@router.post("/backtests/run", response_model=QuantActionResponse)
def quant_backtests_run() -> QuantActionResponse:
    return QuantActionResponse(status="ok", data=run_quant_backtest())


@router.post("/rankings/build", response_model=QuantActionResponse)
def quant_rankings_build() -> QuantActionResponse:
    return QuantActionResponse(status="ok", data=build_quant_rankings())
