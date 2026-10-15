from conftest import register


def test_admin_routes_forbidden_for_normal_user(client, user):
    for path in ("/api/admin/stats", "/api/admin/users", "/api/admin/logs"):
        assert client.get(path, headers=user).status_code == 403, path
        assert client.get(path).status_code == 401, path


def test_admin_lists_and_blocks_users(client, admin):
    other = register(client, "b@example.com")
    users = client.get("/api/admin/users", headers=admin).json()
    assert users["total"] == 2
    uid = next(u["id"] for u in users["users"] if u["email"] == "b@example.com")
    assert client.patch(f"/api/admin/users/{uid}", json={"is_active": False}, headers=admin).json()["is_active"] is False
    assert client.get("/auth/me", headers=other).status_code == 403


def test_admin_cannot_demote_or_block_self(client, admin):
    me = client.get("/auth/me", headers=admin).json()["id"]
    assert client.patch(f"/api/admin/users/{me}", json={"role": "user"}, headers=admin).status_code == 400
    assert client.patch(f"/api/admin/users/{me}", json={"is_active": False}, headers=admin).status_code == 400


def test_admin_stats_shape(client, admin):
    s = client.get("/api/admin/stats", headers=admin).json()
    assert {"users", "active_users_7d", "documents", "chats_total", "chats_failed_7d", "recent_users"} <= s.keys()


def test_bootstrap_admin_creates_and_logs_in(client, monkeypatch):
    from app.config import settings
    from app.database import SessionLocal
    from app.services import bootstrap_admin
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "Boss@Example.com")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "a-long-test-password")
    with SessionLocal() as db:
        assert bootstrap_admin.ensure_admin(db) == "created"
        assert bootstrap_admin.ensure_admin(db) is None  # دوباره چیزی نمی‌سازد
    r = client.post("/auth/login", json={"email": "boss@example.com", "password": "a-long-test-password"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/admin/users", headers=h).status_code == 200


def test_bootstrap_admin_promotes_without_changing_password(client, monkeypatch):
    from app.config import settings
    from app.database import SessionLocal
    from app.services import bootstrap_admin
    register(client, "boss@example.com")
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "another-long-password")
    with SessionLocal() as db:
        assert bootstrap_admin.ensure_admin(db) == "promoted"
    assert client.post("/auth/login", json={"email": "boss@example.com", "password": "another-long-password"}).status_code == 401


def test_bootstrap_admin_noop_when_unset(client):
    from app.database import SessionLocal
    from app.services import bootstrap_admin
    with SessionLocal() as db:
        assert bootstrap_admin.ensure_admin(db) is None


# ---------- ورود به جای کاربر (impersonation) ----------
def _uid(client, admin, email):
    users = client.get("/api/admin/users", headers=admin).json()["users"]
    return next(u["id"] for u in users if u["email"] == email)


def test_impersonation_issues_marked_short_token_and_logs(client, admin, db):
    import jwt
    from app.config import settings
    from app.models.audit_log import AdminAuditLog
    register(client, "b@example.com")
    uid = _uid(client, admin, "b@example.com")
    r = client.post(f"/api/admin/users/{uid}/impersonate", headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    payload = jwt.decode(body["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["impersonated"] is True and payload["sub"] == str(uid) and "imp" in payload
    assert payload["exp"] - __import__("time").time() <= settings.IMPERSONATION_TOKEN_MINUTES * 60 + 5
    h = {"Authorization": f"Bearer {body['access_token']}"}
    me = client.get("/auth/me", headers=h).json()
    assert me["email"] == "b@example.com" and me["impersonated"] is True and me["impersonated_by"] == int(payload["imp"])
    row = db.query(AdminAuditLog).one()
    assert row.action == "impersonate_start" and row.admin_email == "admin@example.com" and row.target_user_id == uid
    logs = client.get("/api/admin/audit-logs", headers=admin).json()["logs"]
    assert logs[0]["target_email"] == "b@example.com"


def test_normal_login_is_not_impersonated(client, admin):
    assert client.get("/auth/me", headers=admin).json()["impersonated"] is False


def test_impersonation_admin_only_and_guards(client, admin, user):
    register(client, "c@example.com")
    uid = _uid(client, admin, "c@example.com")
    assert client.post(f"/api/admin/users/{uid}/impersonate", headers=user).status_code == 403
    assert client.post(f"/api/admin/users/{uid}/impersonate").status_code == 401
    assert client.post("/api/admin/users/9999/impersonate", headers=admin).status_code == 404
    me = client.get("/auth/me", headers=admin).json()["id"]
    assert client.post(f"/api/admin/users/{me}/impersonate", headers=admin).status_code == 400
    client.patch(f"/api/admin/users/{uid}", json={"is_active": False}, headers=admin)
    assert client.post(f"/api/admin/users/{uid}/impersonate", headers=admin).status_code == 400


def test_cannot_impersonate_another_admin(client, admin, db):
    from app.models.user import User
    register(client, "boss2@example.com")
    db.query(User).filter(User.email == "boss2@example.com").update({"role": "admin"}); db.commit()
    uid = _uid(client, admin, "boss2@example.com")
    assert client.post(f"/api/admin/users/{uid}/impersonate", headers=admin).status_code == 403


def test_impersonated_token_cannot_reach_admin_or_change_api_key(client, admin, db):
    from app.models.user import User
    register(client, "d@example.com")
    uid = _uid(client, admin, "d@example.com")
    tok = client.post(f"/api/admin/users/{uid}/impersonate", headers=admin).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/admin/users", headers=h).status_code == 403
    assert client.put("/api-keys", json={"api_key": "sk-x"}, headers=h).status_code == 403
    assert client.delete("/api-keys", headers=h).status_code == 403
    assert client.get("/api-keys", headers=h).status_code == 200
    # حتی اگر بعداً کاربر هدف ادمین شود، توکن جایگزین به پنل ادمین نمی‌رسد
    db.query(User).filter(User.id == uid).update({"role": "admin"}); db.commit()
    assert client.get("/api/admin/users", headers=h).status_code == 403


def test_impersonated_token_dies_when_admin_loses_access(client, admin, db):
    from app.models.user import User
    register(client, "e@example.com")
    uid = _uid(client, admin, "e@example.com")
    tok = client.post(f"/api/admin/users/{uid}/impersonate", headers=admin).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/auth/me", headers=h).status_code == 200
    db.query(User).filter(User.email == "admin@example.com").update({"role": "user"}); db.commit()
    assert client.get("/auth/me", headers=h).status_code == 401


def test_impersonated_token_expires(client, admin):
    from app.config import settings
    register(client, "f@example.com")
    uid = _uid(client, admin, "f@example.com")
    import jwt, time
    tok = jwt.encode({"sub": str(uid), "exp": int(time.time()) - 5, "impersonated": True, "imp": "1"},
                     settings.SECRET_KEY, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


# ---------- دیدن System Prompt کاربر توسط ادمین ----------
def test_admin_sees_system_prompt_readonly_and_access_is_logged(client, admin, db):
    from app.models.audit_log import AdminAuditLog
    h = register(client, "g@example.com")
    client.put("/api/settings", json={"system_prompt": "فقط درباره‌ی دانا جواب بده"}, headers=h)
    uid = _uid(client, admin, "g@example.com")
    d = client.get(f"/api/admin/users/{uid}", headers=admin).json()
    assert d["system_prompt"] == "فقط درباره‌ی دانا جواب بده"
    row = db.query(AdminAuditLog).filter(AdminAuditLog.action == "view_system_prompt").one()
    assert row.target_user_id == uid and row.admin_email == "admin@example.com"
    # PATCH نباید system_prompt را برگرداند یا تغییر دهد
    assert "system_prompt" not in client.patch(f"/api/admin/users/{uid}", json={"is_active": True}, headers=admin).json()


def test_system_prompt_hidden_from_non_admin(client, user):
    assert client.get("/api/admin/users/1", headers=user).status_code == 403
