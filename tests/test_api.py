"""API tests. They need a real PostgreSQL reachable via DATABASE_URL."""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        with db.connection() as conn:
            conn.execute("TRUNCATE tasks RESTART IDENTITY")
        yield c


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_create_and_list(client):
    created = client.post("/api/tasks", json={"title": "write a Dockerfile"})
    assert created.status_code == 201
    assert created.json()["done"] is False

    tasks = client.get("/api/tasks").json()
    assert [t["title"] for t in tasks] == ["write a Dockerfile"]


def test_mark_done(client):
    task_id = client.post("/api/tasks", json={"title": "x"}).json()["id"]
    updated = client.patch(f"/api/tasks/{task_id}", json={"done": True})
    assert updated.json()["done"] is True


def test_delete(client):
    task_id = client.post("/api/tasks", json={"title": "x"}).json()["id"]
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204
    assert client.delete(f"/api/tasks/{task_id}").status_code == 404


def test_rejects_empty_title(client):
    assert client.post("/api/tasks", json={"title": ""}).status_code == 422


def test_metrics(client):
    client.post("/api/tasks", json={"title": "x"})
    body = client.get("/metrics").text
    assert 'taskboard_tasks{state="open"} 1.0' in body
    assert 'http_requests_total{method="POST",path="/api/tasks",status="201"}' in body
