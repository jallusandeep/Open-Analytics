from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.factor.factor_repository import build_factors, get_records, get_run
from app.engines.factor.factor_schema import FactorRequest
from app.engines.factor.factor_service import calculate_factors

router = APIRouter(prefix='/factor', tags=['Factor Engine'], dependencies=[Depends(get_current_user)])


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
def calculate(request: FactorRequest):
    return calculate_factors(request)


@router.post('/build')
def build(request: FactorRequest):
    return database_call(build_factors, request)


@router.get('/runs/{run_id}')
def run_status(run_id: str):
    return database_call(get_run, run_id)


@router.get('/records')
def records(run_id: str, collection: Literal['features', 'composites', 'diagnostics', 'research_summaries', 'correlations'] = 'features',
            limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return database_call(get_records, run_id, collection, limit, offset)
