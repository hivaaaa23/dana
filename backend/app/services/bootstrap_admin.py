import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.services import auth_service
from app.utils.security import hash_password

log = logging.getLogger("dana")


def ensure_admin(db: Session) -> str | None:
    """ادمین اولیه را از ADMIN_EMAIL/ADMIN_PASSWORD می‌سازد. رمز کاربر موجود هیچ‌وقت عوض نمی‌شود.
    خروجی: "created" | "promoted" | None (کاری لازم نبود)."""
    email, password = settings.ADMIN_EMAIL.strip().lower(), settings.ADMIN_PASSWORD
    if not email or not password:
        return None
    user = auth_service.get_user_by_email(db, email)
    if user is None:
        db.add(User(email=email, password_hash=hash_password(password), role="admin"))
        db.commit()
        log.warning("ادمین اولیه ساخته شد: %s", email)
        return "created"
    if user.role != "admin":
        user.role = "admin"
        db.commit()
        log.warning("کاربر موجود به ادمین ارتقا یافت: %s", email)
        return "promoted"
    return None
