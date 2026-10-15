"""
لاگ حسابرسی (audit) اقدام‌های حساس ادمین؛ فعلاً «ورود به جای کاربر».
ایمیل‌ها هم کنار شناسه‌ها ذخیره می‌شود تا با حذف کاربر، ردّ ماجرا از بین نرود (FK عمداً ندارد).
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    admin_email = Column(String(320), nullable=False)
    action = Column(String(40), nullable=False, index=True)  # مثلاً impersonate_start
    target_user_id = Column(Integer, nullable=True, index=True)
    target_email = Column(String(320), nullable=True)
    ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
