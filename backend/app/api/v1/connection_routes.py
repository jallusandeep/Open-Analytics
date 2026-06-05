from fastapi import APIRouter, Depends

from app.dependencies import require_admin_or_super_admin, get_current_user
from app.schemas.connection_schema import (
    ConnectionActionResponse,
    ConnectionsListResponse,
    TelegramConnectionRequest,
    TelegramUserLinkStartResponse,
    TelegramUserLinkStatusResponse,
    UpstoxAuthorizeUrlResponse,
    UpstoxCodeExchangeRequest,
    UpstoxConnectionRequest,
    UpstoxNotifierWebhookRequest
)
from app.services.connection_service import (
    disconnect_telegram_connection_service,
    disconnect_upstox_connection_service,
    exchange_upstox_auth_code_service,
    get_my_telegram_connection_status_service,
    get_upstox_authorize_url_service,
    handle_upstox_notifier_webhook_service,
    list_connections_service,
    save_telegram_connection_service,
    save_upstox_connection_service,
    start_my_telegram_connection_service,
    test_my_telegram_connection_service,
    test_telegram_connection_service,
    test_upstox_connection_service,
    verify_my_telegram_connection_service
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


@router.get("/upstox/authorize-url", response_model=UpstoxAuthorizeUrlResponse)
def get_upstox_authorize_url(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return get_upstox_authorize_url_service(current_user)


@router.post("/upstox/exchange-code", response_model=ConnectionActionResponse)
def exchange_upstox_auth_code(
    request: UpstoxCodeExchangeRequest,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return exchange_upstox_auth_code_service(request, current_user)


@router.post("/upstox/notifier", response_model=ConnectionActionResponse)
def handle_upstox_notifier_webhook(
    request: UpstoxNotifierWebhookRequest
):
    return handle_upstox_notifier_webhook_service(request)


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


@router.post("/telegram", response_model=ConnectionActionResponse)
def save_telegram_connection(
    request: TelegramConnectionRequest,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return save_telegram_connection_service(request, current_user)


@router.post("/telegram/test", response_model=ConnectionActionResponse)
def test_telegram_connection(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return test_telegram_connection_service(current_user)


@router.delete("/telegram", response_model=ConnectionActionResponse)
def disconnect_telegram_connection(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return disconnect_telegram_connection_service(current_user)


@router.get("/telegram/me", response_model=TelegramUserLinkStatusResponse)
def get_my_telegram_connection_status(
    current_user: dict = Depends(get_current_user)
):
    return get_my_telegram_connection_status_service(current_user)


@router.post("/telegram/me/start", response_model=TelegramUserLinkStartResponse)
def start_my_telegram_connection(
    current_user: dict = Depends(get_current_user)
):
    return start_my_telegram_connection_service(current_user)


@router.post("/telegram/me/verify", response_model=TelegramUserLinkStatusResponse)
def verify_my_telegram_connection(
    current_user: dict = Depends(get_current_user)
):
    return verify_my_telegram_connection_service(current_user)


@router.post("/telegram/me/test", response_model=ConnectionActionResponse)
def test_my_telegram_connection(
    current_user: dict = Depends(get_current_user)
):
    return test_my_telegram_connection_service(current_user)