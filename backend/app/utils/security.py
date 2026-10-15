from datetime import datetime, timedelta, timezone
import jwt
from cryptography.fernet import Fernet
from pwdlib import PasswordHash
from app.config import settings
password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"
def hash_password(password: str) -> str: return password_hash.hash(password)
def verify_password(password: str, hashed_password: str) -> bool: return password_hash.verify(password, hashed_password)
def create_access_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.SECRET_KEY, algorithm=ALGORITHM)
def create_impersonation_token(user_id: int, admin_id: int) -> tuple[str, int]:
    """توکن کوتاه‌مدت «ورود به جای کاربر». claim های impersonated و imp (شناسه‌ی ادمین) دارد. (توکن، ثانیه‌ی اعتبار)"""
    seconds = max(1, settings.IMPERSONATION_TOKEN_MINUTES) * 60
    exp = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    token = jwt.encode({"sub": str(user_id), "exp": exp, "impersonated": True, "imp": str(admin_id)},
                       settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, seconds
def decode_token_payload(token: str) -> dict:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("sub") is None: raise ValueError("Token subject is missing")
    int(payload["sub"])
    if payload.get("impersonated"): int(payload["imp"])  # بدون ادمین معتبر، توکن جعلی/ناقص است
    return payload
def decode_access_token(token: str) -> int:
    return int(decode_token_payload(token)["sub"])
def _fernet(): return Fernet(settings.APP_ENCRYPTION_KEY.encode())
def encrypt_api_key(api_key: str) -> str: return _fernet().encrypt(api_key.encode()).decode()
def decrypt_api_key(encrypted_api_key: str) -> str: return _fernet().decrypt(encrypted_api_key.encode()).decode()
