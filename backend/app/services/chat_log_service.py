"""
ثبت لاگ مکالمات.

پیش‌فرض فقط متادیتا (زمان، منبع، موفق/ناموفق، تعداد منبع) ذخیره می‌شود.
اگر LOG_CHAT_CONTENT=1 باشد، متن سوال و پاسخ هم (بریده‌شده و رمزنگاری‌شده با Fernet) ذخیره می‌شود
و لاگ‌های قدیمی‌تر از LOG_RETENTION_DAYS به‌صورت خودکار پاک می‌شوند.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.chat_log import ChatLog
from app.utils.security import decrypt_api_key, encrypt_api_key  # همان Fernet برنامه (نام تاریخی)

log = logging.getLogger("dana.chatlog")
_last_purge = 0.0
_PURGE_EVERY = 3600  # ثانیه


def _clip(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return text[: settings.LOG_CONTENT_MAX_CHARS]


def record(
    db: Session,
    user_id: int,
    source: str,
    ok: bool,
    sources_count: int = 0,
    question: Optional[str] = None,
    answer: Optional[str] = None,
    flagged: bool = False,
    flag_reason: Optional[str] = None,
) -> None:
    entry = ChatLog(user_id=user_id, source=source, ok=ok, sources_count=sources_count,
                    flagged=flagged, flag_reason=flag_reason if flagged else None)
    if settings.LOG_CHAT_CONTENT:
        if question:
            entry.question_enc = encrypt_api_key(_clip(question))
        if answer:
            entry.answer_enc = encrypt_api_key(_clip(answer))
    db.add(entry)
    db.commit()
    purge_old(db)


def purge_old(db: Session, force: bool = False) -> int:
    """حذف لاگ‌های منقضی‌شده (حداکثر ساعتی یک بار، مگر force). تعداد حذف‌شده را برمی‌گرداند."""
    global _last_purge
    days = settings.LOG_RETENTION_DAYS
    if days <= 0:
        return 0
    now = time.monotonic()
    if not force and _last_purge and now - _last_purge < _PURGE_EVERY:
        return 0
    _last_purge = now
    cutoff = datetime.utcnow() - timedelta(days=days)
    n = db.query(ChatLog).filter(ChatLog.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    if n:
        log.info("%d لاگ قدیمی‌تر از %d روز پاک شد.", n, days)
    return n


def read_content(entry: ChatLog) -> tuple[Optional[str], Optional[str]]:
    """متن رمزگشایی‌شده (یا None اگر ذخیره نشده / کلید عوض شده)."""
    def dec(v):
        if not v:
            return None
        try:
            return decrypt_api_key(v)
        except Exception:
            return None
    return dec(entry.question_enc), dec(entry.answer_enc)
