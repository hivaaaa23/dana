"""
Endpoint خواندن/نوشتن تنظیمات شخصی‌سازی کاربر
(System Prompt + Temperature + انتخاب مدل + تنظیمات ظاهری ویجت)
مسئول: نفر ۲
"""
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.settings import UserSettings
from app.schemas.settings import UserSettingsIn, UserSettingsOut
from app.services.user_config import ensure_settings, new_widget_key
from app.utils.security import decrypt_api_key

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=UserSettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """خواندن تنظیمات کاربر (در صورت نبود رکورد، با مقادیر پیش‌فرض ساخته می‌شود)"""
    return ensure_settings(db, current_user.id)


@router.put("", response_model=UserSettingsOut)
def update_settings(
    payload: UserSettingsIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """به‌روزرسانی تنظیمات کاربر - فقط فیلدهای ارسال‌شده تغییر می‌کنند"""
    user_settings = ensure_settings(db, current_user.id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user_settings, field, value)

    db.commit()
    db.refresh(user_settings)
    return user_settings


@router.post("/widget-key/regenerate", response_model=UserSettingsOut)
def regenerate_widget_key(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """کلید عمومی ویجت را عوض می‌کند (کلید قبلی فوراً از کار می‌افتد)."""
    user_settings = ensure_settings(db, current_user.id)
    user_settings.widget_key = new_widget_key()
    db.commit()
    db.refresh(user_settings)
    return user_settings


@router.post("/test-connection")
def test_connection(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """با API Key ذخیره‌شده و Base URL کاربر یک درخواست سبک (لیست مدل‌ها) می‌زند."""
    if not current_user.api_key_encrypted:
        raise HTTPException(status_code=400, detail="ابتدا API Key را ذخیره کنید.")
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    base_url = (user_settings.api_base_url if user_settings else None) or "https://api.openai.com/v1"
    try:
        client = OpenAI(
            api_key=decrypt_api_key(current_user.api_key_encrypted),
            base_url=base_url,
            timeout=15,
        )
        models = [m.id for m in client.models.list().data][:100]
    except OpenAIError as e:
        raise HTTPException(status_code=502, detail=f"اتصال ناموفق بود: {e}")
    return {"ok": True, "models": models}
