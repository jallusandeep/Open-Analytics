from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.risk.risk_schema import RiskRequest, RiskBuildRequest, CovarianceRequest
from app.engines.risk.risk_service import calculate_risk
from app.engines.risk.risk_repository import build_risk, calculate_covariance, get_features, get_run

router = APIRouter(prefix='/risk', tags=['Risk Engine'], dependencies=[Depends(get_current_user)])


def database_call(function, *args):
    conn = get_connection()
    try:
        return function(conn, *args)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except ArithmeticError as error:
        raise HTTPException(422, 'Inputs exceed the numerical range supported by the risk estimators') from error
    finally:
        conn.close()


@router.post('/calculate')
def calculate(request: RiskRequest):
    try:
        return calculate_risk(request)
    except ArithmeticError as error:
        raise HTTPException(422, 'Inputs exceed the numerical range supported by the risk estimators') from error


@router.post('/build')
def build(request: RiskBuildRequest):
    return database_call(build_risk, request)


@router.post('/covariance')
def covariance(request: CovarianceRequest):
    return database_call(calculate_covariance, request)


@router.get('/runs/{run_id}')
def run_status(run_id: str):
    return database_call(get_run, run_id)


@router.get('/features')
def features(run_id: str, instrument_key: str | None = None,
             limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return database_call(get_features, run_id, instrument_key, limit, offset)
