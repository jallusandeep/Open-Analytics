from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection
from app.dependencies import get_current_user
from app.engines.returns.returns_schema import ReturnsRequest, LabelRequest
from app.engines.returns.returns_service import calculate_returns
from app.engines.returns.returns_repository import build_returns, build_labels, get_rows

router = APIRouter(prefix='/returns', tags=['Returns Engine'], dependencies=[Depends(get_current_user)])


@router.post('/calculate')
def calculate(request: ReturnsRequest):
    return calculate_returns(request)


@router.post('/build')
def build(request: ReturnsRequest):
    conn = get_connection()
    try:
        return build_returns(conn, request)
    finally:
        conn.close()


@router.post('/labels/build')
def labels(request: LabelRequest):
    conn = get_connection()
    try:
        return build_labels(conn, request)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    finally:
        conn.close()


@router.get('/runs/{run_id}')
def run_status(run_id: str):
    conn = get_connection()
    try:
        row = conn.execute('SELECT snapshot_id, calculation_version, status, created_at FROM returns_runs WHERE run_id = ?', [run_id]).fetchone()
        if row is None:
            raise HTTPException(404, 'Returns run not found')
        return dict(run_id=run_id, snapshot_id=row[0], calculation_version=row[1], status=row[2], created_at=row[3])
    finally:
        conn.close()


def read(kind, run_id, instrument_key, limit, offset):
    conn = get_connection()
    try:
        return get_rows(conn, kind, run_id, instrument_key, limit, offset)
    finally:
        conn.close()


@router.get('/series')
def series(run_id: str, instrument_key: str | None = None, limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return read('series', run_id, instrument_key, limit, offset)


@router.get('/features')
def features(run_id: str, instrument_key: str | None = None, limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return read('features', run_id, instrument_key, limit, offset)


@router.get('/rankings')
def rankings(run_id: str, instrument_key: str | None = None, limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return read('rankings', run_id, instrument_key, limit, offset)


@router.get('/periods')
def periods(run_id: str, instrument_key: str | None = None, limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return read('periods', run_id, instrument_key, limit, offset)


@router.get('/labels')
def forward_labels(run_id: str, instrument_key: str | None = None, limit: int = Query(1000, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return read('labels', run_id, instrument_key, limit, offset)
