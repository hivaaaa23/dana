from datetime import datetime, timedelta

from app.models.chat_log import ChatLog
from app.services import chat_log_service


def widget_chat(client, key, msg="سوال خصوصی من"):
    return client.post("/api/widget/chat", json={"key": key, "message": msg})


def test_default_stores_metadata_only(client, user, widget_key, admin, db):
    widget_chat(client, widget_key)
    row = db.query(ChatLog).one()
    assert row.question_enc is None and row.answer_enc is None
    r = client.get("/api/admin/logs", headers=admin).json()
    assert r["content_logging"] is False
    assert "question" not in r["logs"][0] and r["logs"][0]["source"] == "widget"


def test_content_logging_opt_in_is_encrypted_at_rest(client, user, widget_key, admin, db, cfg):
    cfg(LOG_CHAT_CONTENT=True, LOG_RETENTION_DAYS=30)
    widget_chat(client, widget_key, "سوال خصوصی من")
    row = db.query(ChatLog).one()
    assert "سوال خصوصی" not in row.question_enc and "پاسخ آزمایشی" not in row.answer_enc
    r = client.get("/api/admin/logs", headers=admin).json()
    assert r["content_logging"] is True and r["retention_days"] == 30
    assert r["logs"][0]["question"] == "سوال خصوصی من" and r["logs"][0]["answer"] == "پاسخ آزمایشی"


def test_content_is_truncated(client, user, widget_key, db, cfg):
    cfg(LOG_CHAT_CONTENT=True, LOG_CONTENT_MAX_CHARS=5)
    widget_chat(client, widget_key, "abcdefghij")
    assert chat_log_service.read_content(db.query(ChatLog).one())[0] == "abcde"


def test_failed_chat_logged_without_answer(client, user, widget_key, db, cfg, monkeypatch):
    from app.services import rag_service
    cfg(LOG_CHAT_CONTENT=True)
    monkeypatch.setattr(rag_service, "answer_question", lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    widget_chat(client, widget_key)
    row = db.query(ChatLog).one()
    assert row.ok is False and row.answer_enc is None and row.question_enc is not None


def test_retention_purges_old_rows(db, user, cfg, client):
    cfg(LOG_RETENTION_DAYS=7)
    uid = client.get("/auth/me", headers=user).json()["id"]
    db.add_all([
        ChatLog(user_id=uid, source="widget", ok=True, created_at=datetime.utcnow() - timedelta(days=30)),
        ChatLog(user_id=uid, source="widget", ok=True, created_at=datetime.utcnow()),
    ])
    db.commit()
    assert chat_log_service.purge_old(db, force=True) == 1
    assert db.query(ChatLog).count() == 1


def test_retention_zero_keeps_everything(db, user, cfg, client):
    cfg(LOG_RETENTION_DAYS=0)
    uid = client.get("/auth/me", headers=user).json()["id"]
    db.add(ChatLog(user_id=uid, source="widget", ok=True, created_at=datetime.utcnow() - timedelta(days=900)))
    db.commit()
    assert chat_log_service.purge_old(db, force=True) == 0


def test_playground_chat_logged_too(client, user, admin, db, cfg):
    cfg(LOG_CHAT_CONTENT=True)
    client.post("/api/chat", json={"message": "تست"}, headers=user)
    assert chat_log_service.read_content(db.query(ChatLog).one()) == ("تست", "پاسخ آزمایشی")
