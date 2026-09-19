from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.market_regime.market_regime_repository import build_market_regime, get_records, get_run
from app.engines.market_regime.market_regime_schema import MarketRegimeRequest
from app.engines.market_regime.market_regime_service import calculate_market_regime

router = APIRouter(prefix='/market-regime', tags=['Market Regime Engine'],
                   dependencies=[Depends(get_current_user)])


def database_call(function, *args):
    conn = get_connection()
    try:
        return function(conn, *args)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except (ValueError, ArithmeticError) as error:
        raise HTTPException(422, str(error)) from error
    finally:
        conn.close()


@router.post('/calculate')
def calculate(request: MarketRegimeRequest):
    return calculate_market_regime(request)


@router.post('/build')
def build(request: MarketRegimeRequest):
    return database_call(build_market_regime, request)


@router.get('/runs/{run_id}')
def run_status(run_id: str):
    return database_call(get_run, run_id)


@router.get('/records')
def records(run_id: str, limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return database_call(get_records, run_id, limit, offset)
