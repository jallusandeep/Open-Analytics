from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.institutional_flow.institutional_flow_repository import build_institutional_flows, get_records, get_run
from app.engines.institutional_flow.institutional_flow_schema import InstitutionalFlowRequest
from app.engines.institutional_flow.institutional_flow_service import calculate_institutional_flows

router = APIRouter(prefix='/institutional-flow', tags=['Institutional Flow Engine'], dependencies=[Depends(get_current_user)])


def database_call(function, *args):
    conn = get_connection()
    try: return function(conn, *args)
    except LookupError as error: raise HTTPException(404, str(error)) from error
    except (ValueError, ArithmeticError) as error: raise HTTPException(422, str(error)) from error
    finally: conn.close()


@router.post('/calculate')
def calculate(request: InstitutionalFlowRequest): return calculate_institutional_flows(request)


@router.post('/build')
def build(request: InstitutionalFlowRequest): return database_call(build_institutional_flows, request)


@router.get('/runs/{run_id}')
def run_status(run_id: str): return database_call(get_run, run_id)


@router.get('/records')
def records(run_id: str, collection: Literal['market', 'sector', 'stock'] = 'market',
            limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return database_call(get_records, run_id, collection, limit, offset)
