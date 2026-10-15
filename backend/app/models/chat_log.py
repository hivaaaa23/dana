"""
لاگ مکالمات برای آمار داشبورد و پنل ادمین.
پیش‌فرض فقط متادیتا ذخیره می‌شود. متن سوال/پاسخ فقط وقتی LOG_CHAT_CONTENT=1 باشد ذخیره می‌شود
(رمزنگاری‌شده، با مدت نگهداری LOG_RETENTION_DAYS) — این یک تصمیم حریم خصوصی است؛ README را ببین.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(20), nullable=False, default="playground")  # playground | widget
    ok = Column(Boolean, nullable=False, default=True)
    sources_count = Column(Integer, nullable=False, default=0)
    # تشخیص Prompt Injection: پیام مشکوک بود؟ و به چه دلیلی (کد کوتاه، نه متن پیام)
    flagged = Column(Boolean, nullable=False, default=False, server_default="0", index=True)
    flag_reason = Column(String(40), nullable=True)
    # فقط وقتی LOG_CHAT_CONTENT=1: متن رمزنگاری‌شده (Fernet)
    question_enc = Column(Text, nullable=True)
    answer_enc = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
