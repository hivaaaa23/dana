"""مدل‌های Pydantic برای تنظیمات شخصی‌سازی کاربر"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Position = Literal["bottom-left", "bottom-right"]


class UserSettingsIn(BaseModel):
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None
    api_base_url: Optional[str] = None
    top_k: Optional[int] = Field(None, ge=1, le=20)

    widget_title: Optional[str] = Field(None, max_length=200)
    widget_welcome_message: Optional[str] = None
    widget_color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    widget_position: Optional[Position] = None
    # دامنه‌های مجاز ویجت، با کاما یا خط جدید جدا شوند؛ خالی = همه
    allowed_origins: Optional[str] = None


class UserSettingsOut(BaseModel):
    system_prompt: str
    temperature: float
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None
    api_base_url: Optional[str] = None
    top_k: int = 5
    widget_title: Optional[str] = None
    widget_welcome_message: Optional[str] = None
    widget_color: Optional[str] = None
    widget_position: str = "bottom-left"
    widget_key: Optional[str] = None
    allowed_origins: Optional[str] = None

    class Config:
        from_attributes = True
