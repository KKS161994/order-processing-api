from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status":"OK"}

def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "version" in body
    assert "environment" in body