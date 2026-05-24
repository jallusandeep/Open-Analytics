from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import require_admin_or_super_admin
from app.schemas.admin_schema import (
    AdminUserCreateRequest,
    AdminUserResponse,
    PaginatedUsersResponse
)
from app.services.admin_service import (
    list_users_service,
    create_user_service,
    delete_user_service
)


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=PaginatedUsersResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    search: str = "",
    role: str = "all",
    is_active: Optional[bool] = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return list_users_service(
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        is_active=is_active
    )


@router.post("/users", response_model=AdminUserResponse)
def create_user(
    request: AdminUserCreateRequest,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return create_user_service(
        request=request,
        current_user=current_user
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return delete_user_service(
        user_id=user_id,
        current_user=current_user
    )