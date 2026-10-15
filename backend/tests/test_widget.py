import pytest

from app.services import rag_service


def chat(client, key, msg="سلام", **headers):
    return client.post("/api/widget/chat", json={"key": key, "message": msg}, headers=headers)


def test_invalid_key(client):
    assert client.get("/api/widget/config?key=gk_nope").status_code == 401
    assert chat(client, "gk_nope").status_code == 401


def test_widget_chat_works_and_cors_open(client, user, widget_key):
    r = chat(client, widget_key, Origin="https://shop.example.com")
    assert r.status_code == 200 and r.json() == {"answer": "پاسخ آزمایشی"}
    assert r.headers["access-control-allow-origin"] == "*"


def test_allowed_origins_enforced(client, user, widget_key):
    client.put("/api/settings", json={"allowed_origins": "shop.example.com, www.example.com"}, headers=user)
    assert chat(client, widget_key, Origin="https://shop.example.com").status_code == 200
    assert chat(client, widget_key, Referer="https://www.example.com/page").status_code == 200
    assert chat(client, widget_key, Origin="https://evil.com").status_code == 403
    assert chat(client, widget_key).status_code == 403  # بدون Origin/Referer


def test_production_closes_widget_without_allowed_origins(client, user, widget_key, cfg):
    cfg(APP_ENV="production")
    assert chat(client, widget_key, Origin="https://shop.example.com").status_code == 403
    client.put("/api/settings", json={"allowed_origins": "shop.example.com"}, headers=user)
    assert chat(client, widget_key, Origin="https://shop.example.com").status_code == 200


def test_explicit_flag_overrides_environment(client, user, widget_key, cfg):
    cfg(APP_ENV="production", WIDGET_REQUIRE_ALLOWED_ORIGINS=False)
    assert chat(client, widget_key).status_code == 200


def test_rate_limit_per_key_and_ip(client, user, widget_key, cfg):
    cfg(WIDGET_RATE_LIMIT=3)
    assert [chat(client, widget_key).status_code for _ in range(4)] == [200, 200, 200, 429]


def test_forwarded_header_ignored_unless_proxy_trusted(client, user, widget_key, cfg):
    cfg(WIDGET_RATE_LIMIT=1)
    assert chat(client, widget_key, **{"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    # جعل هدر نباید شمارنده‌ی تازه بدهد
    assert chat(client, widget_key, **{"X-Forwarded-For": "2.2.2.2"}).status_code == 429


def test_forwarded_header_used_behind_trusted_proxy(client, user, widget_key, cfg):
    cfg(WIDGET_RATE_LIMIT=1, TRUSTED_PROXY_COUNT=1)
    assert chat(client, widget_key, **{"X-Forwarded-For": "9.9.9.9, 1.1.1.1"}).status_code == 200
    assert chat(client, widget_key, **{"X-Forwarded-For": "9.9.9.9, 2.2.2.2"}).status_code == 200  # IP دیگر
    assert chat(client, widget_key, **{"X-Forwarded-For": "8.8.8.8, 1.1.1.1"}).status_code == 429  # همان IP پشت proxy


def test_ai_error_details_hidden_from_visitor(client, user, widget_key, monkeypatch):
    def boom(**kw):
        raise RuntimeError("secret account detail sk-123")
    monkeypatch.setattr(rag_service, "answer_question", boom)
    r = chat(client, widget_key)
    assert r.status_code == 502 and "sk-123" not in r.text


def test_message_length_limit(client, user, widget_key):
    assert chat(client, widget_key, "x" * 1001).status_code == 422
