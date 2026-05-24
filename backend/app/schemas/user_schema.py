from pydantic import BaseModel, EmailStr


class CurrentUserResponse(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: str