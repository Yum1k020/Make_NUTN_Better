import sqlite3

import pytest

from app import create_app
from app.db import DEMO_USER_ID, init_db


@pytest.fixture
def memory_app(tmp_path):
    path = tmp_path / "memory.sqlite3"
    app = create_app({"TESTING": True, "DATABASE": str(path)})
    with app.app_context():
        init_db()
    return app, path


def save_payload(**overrides):
    return {
        "operationId": "operation-save-001",
        "expectedVersion": 0,
        "value": 60,
        "expiresInDays": 30,
        "confirmed": True,
        **overrides,
    }


def test_confirmed_preference_persists_in_sqlite(memory_app):
    app, path = memory_app
    client = app.test_client()

    empty = client.get("/api/v1/study-memory/preference")
    assert empty.status_code == 200
    assert empty.json == {"record": None, "latestVersion": 0}

    saved = client.put(
        "/api/v1/study-memory/preference", json=save_payload()
    )
    assert saved.status_code == 200
    assert saved.json["record"]["owner"] == DEMO_USER_ID
    assert saved.json["record"]["value"] == 60
    assert saved.json["record"]["version"] == 1
    assert saved.json["replayed"] is False

    restarted = create_app({"TESTING": True, "DATABASE": str(path)}).test_client()
    recalled = restarted.get("/api/v1/study-memory/preference")
    assert recalled.status_code == 200
    assert recalled.json["record"]["id"] == saved.json["record"]["id"]
    assert recalled.json["latestVersion"] == 1

    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM study_preferences").fetchone()[0] == 60


def test_memory_version_replay_withdrawal_and_operation_conflict(memory_app):
    client = memory_app[0].test_client()
    first = client.put("/api/v1/study-memory/preference", json=save_payload())
    replay = client.put("/api/v1/study-memory/preference", json=save_payload())
    assert first.status_code == replay.status_code == 200
    assert replay.json["record"]["version"] == 1
    assert replay.json["replayed"] is True

    reused = client.put(
        "/api/v1/study-memory/preference",
        json=save_payload(value=90),
    )
    assert reused.status_code == 409
    assert reused.json["code"] == "MEMORY_OPERATION_CONFLICT"

    stale = client.put(
        "/api/v1/study-memory/preference",
        json=save_payload(
            operationId="operation-save-002", expectedVersion=0, value=90
        ),
    )
    assert stale.status_code == 409
    assert stale.json["code"] == "MEMORY_VERSION_CONFLICT"

    withdrawn = client.delete(
        "/api/v1/study-memory/preference",
        json={
            "operationId": "operation-withdraw-001",
            "expectedVersion": 1,
            "confirmed": True,
        },
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json["record"] is None
    assert withdrawn.json["latestVersion"] == 2
    assert client.get("/api/v1/study-memory/preference").json == {
        "record": None,
        "latestVersion": 2,
    }


@pytest.mark.parametrize(
    "payload",
    [
        save_payload(confirmed=False),
        save_payload(value=10),
        save_payload(expiresInDays=0),
        save_payload(operationId="short"),
    ],
)
def test_unconfirmed_or_invalid_memory_input_does_not_write(memory_app, payload):
    app, path = memory_app
    response = app.test_client().put(
        "/api/v1/study-memory/preference", json=payload
    )
    assert response.status_code == 422
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM study_preferences").fetchone()[0] == 0


def test_memory_rejects_a_different_demo_identity(memory_app):
    response = memory_app[0].test_client().get(
        "/api/v1/study-memory/preference",
        headers={"X-Demo-User-Id": "another-student"},
    )
    assert response.status_code == 401
    assert response.json["code"] == "MEMORY_IDENTITY_REQUIRED"
