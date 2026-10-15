from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    # "user" یا "admin"
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
