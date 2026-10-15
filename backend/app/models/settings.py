"""
مدل دیتابیس برای تنظیمات شخصی‌سازی هر کاربر (System Prompt + Temperature + ...)
مسئول: نفر ۲ (رابط کاربری‌اش با نفر ۳ هماهنگ می‌شود)
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey

from app.database import Base


class UserSettings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)

    # رابطه یک‌به‌یک: هر کاربر دقیقاً یک رکورد تنظیمات دارد
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    system_prompt = Column(Text, nullable=False, default="You are a helpful assistant.")
    temperature = Column(Float, nullable=False, default=0.7)

    # انتخاب مدل توسط کاربر - نیازمندی فایل نهایی: امکان انتخاب مدل چت و مدل embedding
    chat_model = Column(String(100), nullable=True, default="gpt-4o-mini")
    embedding_model = Column(String(100), nullable=True, default="text-embedding-3-small")

    # آدرس Base URL برای سرویس‌های Compatible با OpenAI
    api_base_url = Column(String(500), nullable=True, default="https://api.openai.com/v1")

    # تنظیمات ظاهری ویجت (رنگ، عنوان، پیام خوش‌آمد) - برای Embed Code Generator نفر ۳
    widget_title = Column(String(200), nullable=True, default="دستیار هوشمند")
    widget_welcome_message = Column(Text, nullable=True, default="سلام! چطور می‌توانم کمک کنم؟")
    widget_color = Column(String(20), nullable=True, default="#6D28D9")

    widget_position = Column(String(20), nullable=False, default="bottom-left", server_default="bottom-left")

    # تعداد تکه‌متن‌های بازیابی‌شده در RAG
    top_k = Column(Integer, nullable=False, default=5, server_default="5")

    # کلید عمومی ویجت: روی سایت‌های دیگر به‌جای لاگین استفاده می‌شود (قابل چرخش/تعویض)
    widget_key = Column(String(64), nullable=True, unique=True, index=True)
    # دامنه‌های مجاز برای ویجت، با کاما جدا می‌شوند؛ خالی = همه
    allowed_origins = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserSettings user_id={self.user_id}>"
