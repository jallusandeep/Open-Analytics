from fastapi import APIRouter
from app.schemas.auth_schema import RegisterRequest, LoginRequest, AuthResponse
from app.services.auth_service import register_user, login_user


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