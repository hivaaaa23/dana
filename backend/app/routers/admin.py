"""
پنل ادمین (فاز ۲). همه‌ی مسیرها با require_admin محافظت می‌شوند.

متن مکالمات فقط وقتی برگردانده می‌شود که LOG_CHAT_CONTENT=1 باشد؛ در حالت پیش‌فرض فقط متادیتا
(زمان، منبع، موفق/ناموفق).
"""
from datetime import datetime, timedelta
from typing import Literal, Optional

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_admin
from app.models.audit_log import AdminAuditLog
from app.models.chat_log import ChatLog
from app.models.document import Document
from app.models.settings import UserSettings
from app.models.user import User
from app.schemas.user import ImpersonationResponse
from app.services import chat_log_service
from app.services.rate_limit import client_ip
from app.utils.security import create_impersonation_token

audit_log = logging.getLogger("dana.audit")

router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


def _user_row(db: Session, u: User) -> dict:
    docs, chunks = db.query(
        func.count(Document.id), func.coalesce(func.sum(Document.chunk_count), 0)
    ).filter(Document.user_id == u.id).one()
    return {
        "id": u.id, "email": u.email, "role": u.role, "is_active": u.is_active,
        "created_at": u.created_at, "documents": docs, "chunks": int(chunks),
        "api_key_configured": u.api_key_encrypted is not None,
    }


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=7)
    active = db.query(func.count(func.distinct(ChatLog.user_id))).filter(ChatLog.created_at >= since).scalar()
    recent = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    return {
        "users": db.query(func.count(User.id)).scalar(),
        "active_users_7d": active,
        "documents": db.query(func.count(Document.id)).scalar(),
        "chats_total": db.query(func.count(ChatLog.id)).scalar(),
        "injection_flagged_7d": db.query(func.count(ChatLog.id)).filter(ChatLog.created_at >= since, ChatLog.flagged.is_(True)).scalar(),
        "chats_failed_7d": db.query(func.count(ChatLog.id)).filter(ChatLog.created_at >= since, ChatLog.ok.is_(False)).scalar(),
        "recent_users": [{"id": u.id, "email": u.email, "created_at": u.created_at} for u in recent],
    }


@router.get("/users")
def list_users(
    q: Optional[str] = None,
    status: Optional[Literal["active", "blocked"]] = None,
    role: Optional[Literal["user", "admin"]] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        query = query.filter(User.email.ilike(f"%{q.strip().lower()}%"))
    if status:
        query = query.filter(User.is_active.is_(status == "active"))
    if role:
        query = query.filter(User.role == role)
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "users": [_user_row(db, u) for u in users]}


@router.get("/users/{user_id}")
def user_detail(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "کاربر یافت نشد.")
    # System Prompt فقط‌خواندنی است و هر بار دیدنش در لاگ حسابرسی ثبت می‌شود (حریم خصوصی)
    st = db.query(UserSettings).filter(UserSettings.user_id == u.id).first()
    ip = client_ip(request)
    db.add(AdminAuditLog(admin_id=admin.id, admin_email=admin.email, action="view_system_prompt",
                         target_user_id=u.id, target_email=u.email, ip=ip))
    db.commit()
    audit_log.info("view_system_prompt admin=%s(%s) target=%s(%s) ip=%s", admin.id, admin.email, u.id, u.email, ip)
    docs = db.query(Document).filter(Document.user_id == u.id).order_by(Document.created_at.desc()).all()
    return {
        **_user_row(db, u),
        "chats_total": db.query(func.count(ChatLog.id)).filter(ChatLog.user_id == u.id).scalar(),
        "system_prompt": st.system_prompt if st else None,
        "document_list": [{"id": d.id, "title": d.title, "chunk_count": d.chunk_count} for d in docs],
    }


class UserPatch(BaseModel):
    role: Optional[Literal["user", "admin"]] = None
    is_active: Optional[bool] = None


@router.patch("/users/{user_id}")
def patch_user(user_id: int, payload: UserPatch, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "کاربر یافت نشد.")
    if u.id == admin.id:
        raise HTTPException(400, "نقش یا وضعیت حساب خودت را نمی‌توانی تغییر بدهی.")
    if payload.role is not None:
        u.role = payload.role
    if payload.is_active is not None:
        u.is_active = payload.is_active
    db.commit()
    return _user_row(db, u)


@router.post("/users/{user_id}/impersonate", response_model=ImpersonationResponse)
def impersonate_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """توکن کوتاه‌مدتِ علامت‌دار («impersonated») برای کار به‌جای یک کاربر عادی. هر صدور در لاگ حسابرسی ثبت می‌شود."""
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "کاربر یافت نشد.")
    if u.id == admin.id:
        raise HTTPException(400, "به‌جای خودت نمی‌توانی وارد شوی.")
    if u.role == "admin":
        raise HTTPException(403, "ورود به جای ادمین دیگر مجاز نیست.")
    if not u.is_active:
        raise HTTPException(400, "این حساب مسدود است.")
    ip = client_ip(request)
    # اول لاگ، بعد توکن: اگر ثبت لاگ شکست بخورد توکنی صادر نمی‌شود
    db.add(AdminAuditLog(admin_id=admin.id, admin_email=admin.email, action="impersonate_start",
                         target_user_id=u.id, target_email=u.email, ip=ip))
    db.commit()
    audit_log.warning("impersonate_start admin=%s(%s) target=%s(%s) ip=%s", admin.id, admin.email, u.id, u.email, ip)
    token, seconds = create_impersonation_token(u.id, admin.id)
    return ImpersonationResponse(access_token=token, expires_in=seconds, target_email=u.email)


@router.get("/audit-logs")
def audit_logs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    rows = db.query(AdminAuditLog).order_by(AdminAuditLog.id.desc()).limit(limit).all()
    return {"logs": [{"id": r.id, "admin_id": r.admin_id, "admin_email": r.admin_email, "action": r.action,
                      "target_user_id": r.target_user_id, "target_email": r.target_email, "ip": r.ip,
                      "created_at": r.created_at} for r in rows]}


@router.get("/logs")
def chat_logs(
    limit: int = Query(50, ge=1, le=200),
    only_failed: bool = False,
    only_flagged: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(ChatLog, User.email).join(User, User.id == ChatLog.user_id)
    if only_failed:
        query = query.filter(ChatLog.ok.is_(False))
    if only_flagged:
        query = query.filter(ChatLog.flagged.is_(True))
    rows = query.order_by(ChatLog.created_at.desc()).limit(limit).all()
    logs = []
    for l, email in rows:
        item = {"id": l.id, "email": email, "source": l.source, "ok": l.ok,
                "sources_count": l.sources_count, "created_at": l.created_at,
                "flagged": bool(l.flagged), "flag_reason": l.flag_reason}
        if settings.LOG_CHAT_CONTENT:
            item["question"], item["answer"] = chat_log_service.read_content(l)
        logs.append(item)
    return {
        "content_logging": settings.LOG_CHAT_CONTENT,
        "retention_days": settings.LOG_RETENTION_DAYS,
        "logs": logs,
    }
