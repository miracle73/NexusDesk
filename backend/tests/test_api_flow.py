from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def signup(email: str, company: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"company_name": company, "email": email, "password": "StrongPass123!"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_signup_login_and_tenant_isolation(aws_backend) -> None:
    first = signup("one@example.com", "Acme Support")
    second = signup("two@example.com", "Globex Support")
    assert first["tenant_id"] != second["tenant_id"]

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"company_name": "Acme", "email": "one@example.com", "password": "StrongPass123!"},
    )
    assert duplicate.status_code == 409

    login = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "StrongPass123!"})
    assert login.status_code == 200
    assert login.json()["tenant_id"] == first["tenant_id"]
    assert client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "wrong"}).status_code == 401

    upload = client.post(
        "/api/v1/documents",
        headers=auth(first["access_token"]),
        files={"file": ("faq.md", b"Support hours are Monday to Friday, 9 to 17 UK time.", "text/markdown")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["chunk_count"] >= 1

    assert len(client.get("/api/v1/documents", headers=auth(first["access_token"])).json()) == 1
    assert client.get("/api/v1/documents", headers=auth(second["access_token"])).json() == []

    chat = client.post(
        "/api/v1/chat",
        headers=auth(first["access_token"]),
        json={"message": "What are the support hours for customers?"},
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["sources"] == ["faq.md"]
    conversation_id = body["conversation_id"]

    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=auth(first["access_token"]))
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2

    # The other tenant must not reach this conversation.
    assert client.get(f"/api/v1/conversations/{conversation_id}", headers=auth(second["access_token"])).status_code == 404
    assert client.get("/api/v1/conversations", headers=auth(second["access_token"])).json() == []

    escalated = client.post(
        "/api/v1/chat",
        headers=auth(first["access_token"]),
        json={"message": "I want a refund from a human agent"},
    )
    assert escalated.json()["decision"] == "escalate"

    metrics = client.get("/api/v1/conversations/metrics", headers=auth(first["access_token"])).json()
    assert metrics["total"] == 2
    assert metrics["escalated"] == 1
    assert metrics["knowledge_gaps"]

    patched = client.patch(
        f"/api/v1/conversations/{conversation_id}/status",
        headers=auth(first["access_token"]),
        params={"status": "resolved"},
    )
    assert patched.json()["status"] == "resolved"


def test_requires_token() -> None:
    assert client.get("/api/v1/conversations").status_code == 401
