"""
مدل‌های Pydantic برای ورودی/خروجی مربوط به مخزن دانش
مسئول: نفر ۲
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """آپلود سند به‌صورت متن خام (برای فایل، از یک endpoint جدای multipart استفاده کنید)"""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)


class DocumentOut(BaseModel):
    id: int
    title: str
    original_filename: Optional[str] = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # pydantic v2 (معادل orm_mode در v1)


class DocumentDetail(DocumentOut):
    """همان DocumentOut + متن کامل (برای فرم ویرایش)"""
    content: str


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentOut]
