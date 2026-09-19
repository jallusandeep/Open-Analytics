from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.cross_sectional_ranking.ranking_repository import (
    build_rankings, get_distributions, get_rankings, get_run,
)
from app.engines.cross_sectional_ranking.ranking_schema import RankingRequest
from app.engines.cross_sectional_ranking.ranking_service import calculate_rankings

router = APIRouter(prefix='/cross-sectional-ranking', tags=['Cross-Sectional Ranking Engine'],
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
def calculate(request: RankingRequest):
    return calculate_rankings(request)


@router.post('/build')
def build(request: RankingRequest):
    return database_call(build_rankings, request)


@router.get('/runs/{run_id}')
def run_status(run_id: str):
    return database_call(get_run, run_id)


@router.get('/rankings')
def rankings(run_id: str, instrument_key: str | None = None, metric_name: str | None = None,
             limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return database_call(get_rankings, run_id, instrument_key, metric_name, limit, offset)


@router.get('/distributions')
def distributions(run_id: str, metric_name: str | None = None,
                  limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return database_call(get_distributions, run_id, metric_name, limit, offset)
