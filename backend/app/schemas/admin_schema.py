from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class AdminUserCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    mobile_number: Optional[str] = None
    password: str = Field(..., min_length=6)
    role: str = "user"
    access_restrictions: Optional[List[str]] = []


class AdminUserUpdateRequest(BaseModel):
    login_id: str = Field(..., min_length=2, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    mobile_number: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    access_restrictions: Optional[List[str]] = []


class AdminUserResponse(BaseModel):
    user_id: str
    login_id: Optional[str]
    full_name: str
    email: EmailStr
    mobile_number: Optional[str]
    role: str
    access_restrictions: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


class PaginatedUsersResponse(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int
    users: List[AdminUserResponse]