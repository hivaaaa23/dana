"""آمار داشبورد کاربر (فقط داده‌های خود او)"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.chat_log import ChatLog
from app.models.document import Document

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("")
def my_stats(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    docs, chunks, chars = db.query(
        func.count(Document.id),
        func.coalesce(func.sum(Document.chunk_count), 0),
        func.coalesce(func.sum(func.length(Document.content)), 0),
    ).filter(Document.user_id == current_user.id).one()

    since = datetime.utcnow() - timedelta(days=7)
    base = db.query(ChatLog).filter(ChatLog.user_id == current_user.id, ChatLog.created_at >= since)
    return {
        "documents": docs,
        "chunks": int(chunks),
        "content_chars": int(chars),  # حجم متن خام مخزن (نه حجم دیسک Chroma)
        "chats_7d": base.count(),
        "widget_chats_7d": base.filter(ChatLog.source == "widget").count(),
    }
