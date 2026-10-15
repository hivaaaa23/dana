"""
اندپوینت‌های عمومی ویجت (روی سایت‌های دیگر، بدون لاگین).

احراز هویت: «کلید عمومی ویجت» (gk_...) که هر کاربر دارد. این کلید فقط اجازه‌ی
چت با مخزن همان کاربر را می‌دهد، نه چیز دیگری. چون کلید داخل HTML سایت مقصد دیده
می‌شود، دو لایه محافظ هست: لیست دامنه‌های مجاز (allowed_origins) و Rate Limit.
"""
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import widget_origins_required
from app.database import get_db
from app.models.settings import UserSettings
from app.models.user import User
from app.services import chat_log_service, injection_guard, rag_service
from app.services.rate_limit import client_ip, is_rate_limited
from app.services.user_config import get_user_ai_config

router = APIRouter(prefix="/api/widget", tags=["Widget (public)"])

MAX_MESSAGE_CHARS = 1000


def _host(value: str) -> str:
    value = value.strip().lower()
    if "://" not in value:
        value = "//" + value
    return urlparse(value).netloc or ""


def _origin_allowed(settings: UserSettings, request: Request) -> bool:
    allowed = [h for h in (_host(x) for x in (settings.allowed_origins or "").replace("\n", ",").split(",")) if h]
    if not allowed:
        # در production بدون «دامنه‌های مجاز» ویجت بسته است (کلید در HTML سایت‌ها دیده می‌شود)
        return not widget_origins_required()
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    return _host(origin) in allowed


def _load(db: Session, key: str, request: Request) -> tuple[UserSettings, User]:
    s = db.query(UserSettings).filter(UserSettings.widget_key == key).first() if key else None
    if s is None:
        raise HTTPException(status_code=401, detail="کلید ویجت نامعتبر است.")
    user = db.get(User, s.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="کلید ویجت نامعتبر است.")
    if not _origin_allowed(s, request):
        raise HTTPException(status_code=403, detail="این دامنه اجازه‌ی استفاده از ویجت را ندارد یا «دامنه‌های مجاز» هنوز تنظیم نشده است.")
    return s, user


@router.get("/config")
def widget_config(key: str, request: Request, db: Session = Depends(get_db)):
    s, _ = _load(db, key, request)
    return {
        "title": s.widget_title,
        "welcome_message": s.widget_welcome_message,
        "color": s.widget_color,
        "position": s.widget_position,
    }


class WidgetChatRequest(BaseModel):
    key: str
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_CHARS)


@router.post("/chat")
def widget_chat(payload: WidgetChatRequest, request: Request, db: Session = Depends(get_db)):
    s, user = _load(db, payload.key, request)
    if is_rate_limited(payload.key, client_ip(request)):
        raise HTTPException(status_code=429, detail="تعداد پیام‌ها زیاد است؛ کمی بعد دوباره تلاش کنید.")

    guard = injection_guard.check(payload.message)
    if injection_guard.should_block(guard):
        chat_log_service.record(db, user.id, "widget", ok=True, question=payload.message,
                                flagged=True, flag_reason=guard.reason)
        return {"answer": injection_guard.REFUSAL_TEXT}

    config = get_user_ai_config(db, user)
    try:
        result = rag_service.answer_question(
            user_id=user.id,
            question=payload.message,
            system_prompt=config["system_prompt"],
            temperature=config["temperature"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            chat_model=config["chat_model"],
            embedding_model=config["embedding_model"],
            top_k=config["top_k"],
        )
    except RuntimeError:
        chat_log_service.record(db, user.id, "widget", ok=False, question=payload.message,
                                flagged=guard.flagged, flag_reason=guard.reason)
        # جزئیات خطای سرویس (ممکن است حاوی اطلاعات حساب باشد) به بیننده‌ی عمومی نشان داده نمی‌شود
        raise HTTPException(status_code=502, detail="پاسخ‌دهی موقتاً ممکن نیست.")

    chat_log_service.record(
        db, user.id, "widget", ok=True, sources_count=len(result["sources"]),
        question=payload.message, answer=result["answer"],
        flagged=guard.flagged, flag_reason=guard.reason,
    )
    return {"answer": result["answer"]}
