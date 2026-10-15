"""
تست‌ها روی دیتابیس SQLite موقت و Chroma موقت اجرا می‌شوند و هیچ‌وقت به OpenAI وصل نمی‌شوند
(embedding و مدل زبانی mock هستند). متغیرهای محیطی باید قبل از import برنامه ست شوند.
"""
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="dana-test-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "CHROMA_PERSIST_DIR": f"{_tmp}/chroma",
    "SECRET_KEY": "test-secret-key-test-secret-key-test-secret-key",
    "APP_ENCRYPTION_KEY": "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=",
    "APP_ENV": "development",
    "CORS_ORIGINS": "*",
    "REDIS_URL": "",
    "LOG_CHAT_CONTENT": "0",
    "LOG_RETENTION_DAYS": "0",
    "TRUSTED_PROXY_COUNT": "0",
    "FRONTEND_DIR": f"{_tmp}/no-frontend",
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import embedding_service, llm_client, rate_limit, vector_store  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """هر تست با دیتابیس خالی، شمارنده‌ی تازه و سرویس‌های AI جعلی شروع می‌شود."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    rate_limit.reset_for_tests()
    monkeypatch.setattr(embedding_service, "get_embedding", lambda text, **kw: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        embedding_service, "get_embeddings_batch", lambda texts, **kw: [[0.1, 0.2, 0.3] for _ in texts]
    )
    monkeypatch.setattr(llm_client, "get_chat_completion", lambda **kw: "پاسخ آزمایشی")
    yield
    for uid in range(1, 6):
        vector_store.delete_all_documents(uid)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    with SessionLocal() as s:
        yield s


def register(client, email="a@example.com", password="password123"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    t = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture()
def user(client):
    """کاربر لاگین‌شده با API Key ذخیره‌شده؛ هدر احراز هویت را برمی‌گرداند."""
    h = register(client)
    assert client.put("/api-keys", json={"api_key": "sk-test"}, headers=h).status_code == 200
    return h


@pytest.fixture()
def widget_key(client, user):
    return client.get("/api/settings", headers=user).json()["widget_key"]


@pytest.fixture()
def admin(client, db):
    h = register(client, "admin@example.com")
    from app.models.user import User
    u = db.query(User).filter(User.email == "admin@example.com").first()
    u.role = "admin"
    db.commit()
    return h


@pytest.fixture()
def cfg(monkeypatch):
    """تغییر موقت تنظیمات: cfg(LOG_CHAT_CONTENT=True)"""
    def _set(**kw):
        for k, v in kw.items():
            monkeypatch.setattr(settings, k, v)
    return _set
