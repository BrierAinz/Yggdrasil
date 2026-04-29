from fastapi.testclient import TestClient
from lilith_api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat():
    response = client.post("/chat", json={"message": "Hola"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


def test_list_tools():
    response = client.get("/tools")
    assert response.status_code == 200
    assert "system_info" in response.json()
