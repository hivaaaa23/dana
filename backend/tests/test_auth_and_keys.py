from conftest import register


def test_register_login_me(client):
    h = register(client)
    me = client.get("/auth/me", headers=h).json()
    assert me["email"] == "a@example.com" and me["role"] == "user"


def test_duplicate_email_and_short_password(client):
    register(client)
    assert client.post("/auth/register", json={"email": "a@example.com", "password": "password123"}).status_code == 409
    assert client.post("/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 400


def test_wrong_password_rejected(client):
    register(client)
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "nope-nope"}).status_code == 401


def test_protected_routes_need_token(client):
    for path in ("/auth/me", "/api/settings", "/api/knowledge-base", "/api/stats", "/api-keys"):
        assert client.get(path).status_code == 401, path


def test_api_key_never_returned_and_stored_encrypted(client, db):
    h = register(client)
    client.put("/api-keys", json={"api_key": "sk-secret-123"}, headers=h)
    r = client.get("/api-keys", headers=h)
    assert r.json() == {"configured": True} and "sk-secret-123" not in r.text
    from app.models.user import User
    assert "sk-secret-123" not in db.query(User).first().api_key_encrypted
    assert client.delete("/api-keys", headers=h).status_code == 204
    assert client.get("/api-keys", headers=h).json() == {"configured": False}


def test_blocked_user_cannot_use_token(client, db):
    h = register(client)
    from app.models.user import User
    db.query(User).first().is_active = False
    db.commit()
    assert client.get("/auth/me", headers=h).status_code == 403
