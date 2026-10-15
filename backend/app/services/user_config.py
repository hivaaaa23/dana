"""تنظیمات AI یک کاربر (کلید، مدل‌ها، پرامپت) — مشترک بین Playground و ویجت"""
import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.settings import UserSettings
from app.models.user import User
from app.services import embedding_service, llm_client
from app.utils.security import decrypt_api_key


def new_widget_key() -> str:
    return "gk_" + secrets.token_urlsafe(24)


def ensure_settings(db: Session, user_id: int) -> UserSettings:
    """رکورد تنظیمات کاربر را برمی‌گرداند؛ اگر نبود می‌سازد و کلید ویجت هم می‌دهد."""
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if s is None:
        s = UserSettings(user_id=user_id, widget_key=new_widget_key())
        db.add(s)
        db.commit()
        db.refresh(s)
    elif not s.widget_key:
        s.widget_key = new_widget_key()
        db.commit()
        db.refresh(s)
    return s


def get_user_ai_config(db: Session, user: User) -> dict:
    if not getattr(user, "api_key_encrypted", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ابتدا باید API Key خود را در بخش تنظیمات وارد کنید.",
        )
    s = ensure_settings(db, user.id)
    return {
        "api_key": decrypt_api_key(user.api_key_encrypted),
        "base_url": s.api_base_url or "https://api.openai.com/v1",
        "chat_model": s.chat_model or llm_client.DEFAULT_CHAT_MODEL,
        "embedding_model": s.embedding_model or embedding_service.DEFAULT_EMBEDDING_MODEL,
        "system_prompt": s.system_prompt,
        "temperature": s.temperature,
        "top_k": s.top_k or 5,
    }
