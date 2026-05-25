from fastapi import APIRouter, Depends

from app.dependencies import require_admin_or_super_admin
from app.schemas.connection_schema import (
    ConnectionActionResponse,
    ConnectionsListResponse,
    UpstoxConnectionRequest
)
from app.services.connection_service import (
    disconnect_upstox_connection_service,
    list_connections_service,
    save_upstox_connection_service,
    test_upstox_connection_service
)


router = APIRouter(prefix="/connections", tags=["Connections"])


@router.get("", response_model=ConnectionsListResponse)
def list_connections(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return list_connections_service()


@router.post("/upstox", response_model=ConnectionActionResponse)
def save_upstox_connection(
    request: UpstoxConnectionRequest,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return save_upstox_connection_service(request, current_user)


@router.post("/upstox/test", response_model=ConnectionActionResponse)
def test_upstox_connection(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return test_upstox_connection_service(current_user)


@router.delete("/upstox", response_model=ConnectionActionResponse)
def disconnect_upstox_connection(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return disconnect_upstox_connection_service(current_user)