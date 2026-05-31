from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.schemas.auth_schema import (
    AuthResponse,
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    MessageResponse,
    ProfileUpdateResponse,
    RegisterRequest,
    UpdateProfileRequest
)
from app.services.auth_service import (
    change_password_service,
    login_user,
    register_user,
    update_profile_service
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    return register_user(
        full_name=request.full_name,
        email=request.email,
        password=request.password
    )


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    return login_user(
        email=request.email,
        password=request.password
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_my_profile(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "user": current_user
    }


@router.put("/me", response_model=ProfileUpdateResponse)
def update_my_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    return update_profile_service(
        user_id=current_user["user_id"],
        full_name=request.full_name,
        email=request.email,
        mobile_number=request.mobile_number
    )


@router.put("/password", response_model=MessageResponse)
def change_my_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    return change_password_service(
        user_id=current_user["user_id"],
        current_password=request.current_password,
        new_password=request.new_password,
        confirm_password=request.confirm_password
    )