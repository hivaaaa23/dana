from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import hash_password, verify_password
def get_user_by_email(db: Session, email: str): return db.scalar(select(User).where(User.email == email.lower()))
def register_user(db: Session, email: str, password: str):
    user = User(email=email.lower(), password_hash=hash_password(password)); db.add(user); db.commit(); db.refresh(user); return user
def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    return user if user and user.is_active and verify_password(password, user.password_hash) else None
