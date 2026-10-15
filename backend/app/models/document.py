"""
مدل دیتابیس برای اسناد مخزن دانش (Knowledge Base)
مسئول: نفر ۲

نکته مهم جداسازی داده:
هر رکورد سند حتماً باید ستون user_id داشته باشد تا در تمام Queryها
فیلتر روی کاربر لاگین‌شده اعمال شود (طبق نیازمندی «جداسازی داده بین کاربران»).
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # جداسازی داده بین کاربران - این ستون اجباری و حیاتی است
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)  # در صورت آپلود فایل
    content = Column(Text, nullable=False)  # متن کامل سند، قبل از chunk شدن

    # نام Collection مربوط به این کاربر در ChromaDB (برای رهگیری/حذف بردارها)
    chroma_collection_name = Column(String(255), nullable=False)
    chunk_count = Column(Integer, default=0)  # تعداد تکه‌های ساخته‌شده از این سند

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Document id={self.id} user_id={self.user_id} title={self.title!r}>"
