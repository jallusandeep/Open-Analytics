from typing import List, Optional

from pydantic import BaseModel


class UpstoxConnectionRequest(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    redirect_url: Optional[str] = None
    authorization_code: Optional[str] = None
    access_token: Optional[str] = None


class TelegramConnectionRequest(BaseModel):
    bot_token: Optional[str] = None


class TelegramUserLinkStartResponse(BaseModel):
    status: str
    message: str
    telegram_url: Optional[str] = None
    bot_username: Optional[str] = None
    connection_status: Optional[str] = None


class TelegramUserLinkStatusResponse(BaseModel):
    status: str
    message: str
    connection_status: str
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
    updated_at: Optional[str] = None


class ConnectionResponse(BaseModel):
    connection_id: str
    provider: str
    api_key: Optional[str] = None
    redirect_url: Optional[str] = None
    connection_status: str
    has_api_secret: bool
    has_access_token: bool
    last_tested_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConnectionsListResponse(BaseModel):
    connections: List[ConnectionResponse]


class ConnectionActionResponse(BaseModel):
    status: str
    message: str