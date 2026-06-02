from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    login_identifier: str = Field(..., min_length=2, max_length=100)
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    mobile_number: str | None = Field(default=None, max_length=20)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")

        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")

        return self


class ForgotPasswordOtpRequest(BaseModel):
    login_identifier: str = Field(..., min_length=2, max_length=100)


class ResetPasswordWithOtpRequest(BaseModel):
    login_identifier: str = Field(..., min_length=2, max_length=100)
    otp: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")

        return self


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    login_id: str | None = None
    full_name: str
    email: EmailStr
    role: str


class CurrentUserResponse(BaseModel):
    status: str
    user: dict


class ProfileUpdateResponse(BaseModel):
    status: str
    message: str
    user: dict


class MessageResponse(BaseModel):
    status: str
    message: str