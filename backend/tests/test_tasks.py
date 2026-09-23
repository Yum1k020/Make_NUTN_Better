import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite3")) as client:
        yield client


def test_crud_and_filters(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    response = client.post("/api/v1/tasks", json={
        "title": "完成資料庫作業", "due_at": "2026-10-01T18:00:00+08:00",
        "priority": "high",
    })
    assert response.status_code == 201
    task = response.json()
    url = f"/api/v1/tasks/{task['id']}"
    assert task["completed"] is False
    assert client.get(url).json() == task
    assert len(client.get("/api/v1/tasks?completed=false").json()) == 1
    response = client.patch(url, json={"completed": True, "due_at": None})
    assert response.status_code == 200
    assert response.json()["due_at"] is None
    assert response.json()["title"] == task["title"]
    assert client.get("/api/v1/tasks?completed=false").json() == []
    assert len(client.get("/api/v1/tasks?completed=true").json()) == 1
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.patch(url, json={"title": "不存在"}).status_code == 404


@pytest.mark.parametrize("payload", [
    {}, {"title": "   "}, {"title": "x" * 201},
    {"title": "a", "priority": "urgent"},
    {"title": "a", "due_at": "invalid"}, {"title": "a", "unknown": 1},
])
def test_invalid_create(client, payload):
    assert client.post("/api/v1/tasks", json=payload).status_code == 422
    assert client.get("/api/v1/tasks").json() == []


@pytest.mark.parametrize("payload", [{}, {"title": None}, {"completed": None},
                                        {"title": " "}, {"unknown": "x"}])
def test_invalid_patch_does_not_change_data(client, payload):
    task = client.post("/api/v1/tasks", json={"title": "keep"}).json()
    url = f"/api/v1/tasks/{task['id']}"
    assert client.patch(url, json=payload).status_code == 422
    assert client.get(url).json() == task


def test_persistence_and_parameterized_sql(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    title = "'); DROP TABLE tasks; --"
    with TestClient(create_app(path)) as client:
        task = client.post("/api/v1/tasks", json={"title": title}).json()
    with TestClient(create_app(path)) as client:
        assert client.get(f"/api/v1/tasks/{task['id']}").json()["title"] == title
        assert len(client.get("/api/v1/tasks").json()) == 1


def test_pagination(client):
    for title in ("first", "second", "third"):
        assert client.post("/api/v1/tasks", json={"title": title}).status_code == 201
    first = client.get("/api/v1/tasks?limit=2").json()
    second = client.get("/api/v1/tasks?limit=2&offset=2").json()
    assert len(first) == 2 and len(second) == 1
    assert len({task["id"] for task in first + second}) == 3
    assert client.get("/api/v1/tasks?limit=0").status_code == 422
    assert client.get("/api/v1/tasks?offset=-1").status_code == 422
