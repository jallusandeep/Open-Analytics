"""Authenticated research validation. Reports never modify collected data."""
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.data_quality.data_quality_schema import OhlcvQualityRequest, RecordsQualityRequest, StoredQualityRequest, StoredRecordsRequest
from app.engines.data_quality.data_quality_service import validate_ohlcv, validate_records, require_quality
from app.engines.data_quality.data_quality_repository import validate_stored_daily, validate_stored_records

router = APIRouter(prefix='/data-quality', tags=['Data Quality'], dependencies=[Depends(get_current_user)])


@router.post('/ohlcv')
def check_ohlcv(request: OhlcvQualityRequest):
    return validate_ohlcv(**request.model_dump())


@router.post('/records')
def check_records(request: RecordsQualityRequest):
    return validate_records(**request.model_dump())


@router.post('/stored-daily')
def check_stored_daily(request: StoredQualityRequest):
    conn = get_connection()
    try:
        return validate_stored_daily(conn, request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        conn.close()


@router.post('/stored-records')
def check_stored_records(request: StoredRecordsRequest):
    conn = get_connection()
    try:
        return validate_stored_records(conn, request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        conn.close()


@router.post('/preflight')
def check_research_preflight(request: StoredQualityRequest):
    report = check_stored_daily(request)
    try:
        return require_quality(report)
    except ValueError as error:
        raise HTTPException(status_code=409, detail={'message': str(error), 'report': report}) from error
