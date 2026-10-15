from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.security import decode_token_payload
bearer_scheme = HTTPBearer(auto_error=False)
def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: Session = Depends(get_db)) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer": raise HTTPException(status_code=401, detail="Authentication required")
    try: payload = decode_token_payload(credentials.credentials)
    except Exception: raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if user is None: raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active: raise HTTPException(status_code=403, detail="Account is disabled")
    request.state.impersonated_by = None
    if payload.get("impersonated"):
        # اعتبار توکن به ادمینِ صادرکننده بسته است: اگر ادمین دیگر فعال/ادمین نیست، توکن بی‌اثر می‌شود
        admin = db.get(User, int(payload["imp"]))
        if admin is None or not admin.is_active or admin.role != "admin":
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        request.state.impersonated_by = admin.id
    return user
def require_admin(request: Request, user: User = Depends(get_current_user)) -> User:
    if user.role != "admin": raise HTTPException(status_code=403, detail="Admin access required")
    # توکن «ورود به جای کاربر» هرگز نباید به پنل ادمین برسد (حتی اگر کاربر هدف بعداً ادمین شود)
    if getattr(request.state, "impersonated_by", None) is not None:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
def forbid_when_impersonating(request: Request, _user: User = Depends(get_current_user)) -> None:
    """برای کارهای حساس حساب (مثل تغییر API Key کاربر) که ادمینِ جایگزین نباید انجام دهد."""
    if getattr(request.state, "impersonated_by", None) is not None:
        raise HTTPException(status_code=403, detail="این کار در حالت «ورود به جای کاربر» مجاز نیست.")
