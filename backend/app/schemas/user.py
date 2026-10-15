from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
class UserRegister(BaseModel):
    email: EmailStr
    password: str
class UserLogin(BaseModel):
    email: EmailStr
    password: str
class UserPublic(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    role: str = "user"
    # فقط وقتی توکن «ورود به جای کاربر» باشد true است
    impersonated: bool = False
    impersonated_by: int | None = None
    model_config = ConfigDict(from_attributes=True)
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
class ImpersonationResponse(TokenResponse):
    impersonated: bool = True
    expires_in: int
    target_email: EmailStr
class ApiKeyInput(BaseModel):
    api_key: str
class ApiKeyStatus(BaseModel):
    configured: bool
