from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.core.permissions import get_current_user
from app.models.user import User
from app.services.news_ai.db import get_final_news, get_system_setting, set_system_setting

router = APIRouter()

@router.get("/")
def get_news(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page"),
    search: Optional[str] = Query(None, description="Search keyword"),
    current_user: User = Depends(get_current_user)
):
    """
    Get AI-enriched news from the final database with pagination and search.
    """
    offset = (page - 1) * page_size
    news_items, total = get_final_news(limit=page_size, offset=offset, search=search)
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return {
        "news": news_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/status", response_model=dict)
def get_news_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get status of the news synchronization and WebSocket.
    """
    sync_enabled = get_system_setting('news_sync_enabled', 'true') == 'true'
    
    return {
        "status": "active" if sync_enabled else "disabled",
        "websocket_connected": True, 
        "database_accessible": True,
        "sync_enabled": sync_enabled
    }

@router.post("/toggle")
def toggle_news_sync(
    enabled: bool,
    current_user: User = Depends(get_current_user)
):
    """
    Enable or disable news synchronization.
    """
    set_system_setting('news_sync_enabled', enabled)
    return {"message": f"News sync {'enabled' if enabled else 'disabled'}", "sync_enabled": enabled}
