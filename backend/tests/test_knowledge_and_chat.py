from conftest import register


def test_document_crud_and_chat(client, user):
    r = client.post("/api/knowledge-base", json={"title": "قوانین", "content": "ساعت کاری ما ۹ تا ۱۷ است. " * 5}, headers=user)
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]
    assert client.get(f"/api/knowledge-base/{doc_id}", headers=user).json()["title"] == "قوانین"
    assert client.get("/api/knowledge-base", headers=user).json()["total"] == 1

    chat = client.post("/api/chat", json={"message": "ساعت کاری؟"}, headers=user)
    assert chat.status_code == 200
    body = chat.json()
    assert body["answer"] == "پاسخ آزمایشی" and body["sources"][0]["document_id"] == doc_id

    assert client.put(f"/api/knowledge-base/{doc_id}", json={"title": "عنوان جدید"}, headers=user).json()["title"] == "عنوان جدید"
    assert client.delete(f"/api/knowledge-base/{doc_id}", headers=user).status_code == 204
    assert client.get("/api/knowledge-base", headers=user).json()["total"] == 0


def test_user_cannot_see_other_users_documents(client, user):
    doc = client.post("/api/knowledge-base", json={"title": "خصوصی", "content": "راز " * 20}, headers=user).json()
    other = register(client, "b@example.com")
    assert client.get("/api/knowledge-base", headers=other).json()["total"] == 0
    assert client.get(f"/api/knowledge-base/{doc['id']}", headers=other).status_code == 404
    assert client.delete(f"/api/knowledge-base/{doc['id']}", headers=other).status_code == 404


def test_chat_requires_api_key(client):
    h = register(client)
    assert client.post("/api/chat", json={"message": "سلام"}, headers=h).status_code == 400


def test_upload_txt_and_bad_type(client, user):
    ok = client.post("/api/knowledge-base/upload", files={"file": ("a.txt", "متن آزمایشی " * 30, "text/plain")}, headers=user)
    assert ok.status_code == 201, ok.text
    bad = client.post("/api/knowledge-base/upload", files={"file": ("a.exe", b"MZ", "application/octet-stream")}, headers=user)
    assert bad.status_code == 400


def test_stats_count_chats(client, user):
    client.post("/api/knowledge-base", json={"title": "t", "content": "x " * 30}, headers=user)
    client.post("/api/chat", json={"message": "سلام"}, headers=user)
    s = client.get("/api/stats", headers=user).json()
    assert s["documents"] == 1 and s["chats_7d"] == 1 and s["widget_chats_7d"] == 0


def test_settings_update_validation_and_widget_key_rotation(client, user):
    assert client.put("/api/settings", json={"temperature": 5}, headers=user).status_code == 422
    assert client.put("/api/settings", json={"widget_color": "red"}, headers=user).status_code == 422
    assert client.put("/api/settings", json={"temperature": 0.2, "top_k": 3}, headers=user).json()["top_k"] == 3
    old = client.get("/api/settings", headers=user).json()["widget_key"]
    new = client.post("/api/settings/widget-key/regenerate", headers=user).json()["widget_key"]
    assert old != new and new.startswith("gk_")
    assert client.get(f"/api/widget/config?key={old}").status_code == 401
    assert client.get(f"/api/widget/config?key={new}").status_code == 200
