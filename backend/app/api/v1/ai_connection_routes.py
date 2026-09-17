from fastapi import APIRouter, Depends, Response

from app.dependencies import require_admin_or_super_admin
from app.schemas.ai_connection_schema import AiConnectionRequest, AiModelListRequest
from app.services.ai_connections import (
    delete_ai_connection, list_ai_connections, discover_models, save_ai_connection,
    select_default, test_ai_connection,
)

router = APIRouter(prefix="/connections/ai", tags=["AI Connections"], dependencies=[Depends(require_admin_or_super_admin)])


@router.get("")
def list_connections(response: Response):
    response.headers["Cache-Control"] = "no-store, private"
    return list_ai_connections()


@router.post("")
def create_connection(payload: AiConnectionRequest, user: dict = Depends(require_admin_or_super_admin)):
    return save_ai_connection(payload, user)


@router.post("/models")
def models(payload: AiModelListRequest, response: Response):
    response.headers["Cache-Control"] = "no-store, private"
    return discover_models(payload)


@router.put("/{connection_id}")
def update_connection(connection_id: str, payload: AiConnectionRequest, user: dict = Depends(require_admin_or_super_admin)):
    return save_ai_connection(payload, user, connection_id)


@router.post("/{connection_id}/default")
def set_default(connection_id: str, user: dict = Depends(require_admin_or_super_admin)):
    return select_default(connection_id, user)


@router.post("/{connection_id}/test")
def test_connection(connection_id: str):
    return test_ai_connection(connection_id)


@router.delete("/{connection_id}")
def delete_connection(connection_id: str):
    return delete_ai_connection(connection_id)
