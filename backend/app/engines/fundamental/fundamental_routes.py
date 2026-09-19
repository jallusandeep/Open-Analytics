from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.fundamental.fundamental_repository import build_fundamentals, get_features, get_run
from app.engines.fundamental.fundamental_schema import FundamentalRequest
from app.engines.fundamental.fundamental_service import calculate_fundamentals

router = APIRouter(prefix='/fundamental', tags=['Fundamental Engine'], dependencies=[Depends(get_current_user)])


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
def calculate(request: FundamentalRequest):
    return calculate_fundamentals(request)


@router.post('/build')
def build(request: FundamentalRequest):
    return database_call(build_fundamentals, request)


@router.get('/runs/{run_id}')
def run_status(run_id: str):
    return database_call(get_run, run_id)


@router.get('/features')
def features(run_id: str, instrument_key: str | None = None,
             limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return database_call(get_features, run_id, instrument_key, limit, offset)
