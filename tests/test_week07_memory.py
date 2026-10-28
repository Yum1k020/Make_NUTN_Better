from __future__ import annotations

import json
from pathlib import Path

from backend.week07_memory import (
    preview_with_memory,
    read_preference,
    revoke_preference,
    save_confirmed_preference,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"
NOW = "2026-10-28T10:00:00"


def _request_without_session_minutes() -> dict:
    request = json.loads(FIXTURE.read_text(encoding="utf-8"))
    request["session_minutes"] = None
    return request


def test_c01_confirmed_preference_is_read_in_new_session_and_used(tmp_path: Path):
    store = tmp_path / "memory.json"

    saved = save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-confirm-001",
        request_id="REQ-W07-SAVE-001",
        confirmed=True,
        store_path=store,
        now=NOW,
        expires_at="2026-12-31T23:59:59",
    )
    result = preview_with_memory(
        request=_request_without_session_minutes(),
        owner_id="U001",
        reader_id="U001",
        store_path=store,
        now="2026-10-28T10:05:00",
    )

    assert saved["version"] == 1
    assert result["status"] == "ok"
    assert result["memory_used"] is True
    assert result["effective_session_minutes"] == 60
    assert result["memory_read"]["memory"]["source"]["source_id"] == "chat-confirm-001"
    assert result["preview"]["scheduled_minutes"] == 180


def test_c02_cross_user_cannot_read_or_use_another_users_memory(tmp_path: Path):
    store = tmp_path / "memory.json"
    save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-confirm-001",
        request_id="REQ-W07-SAVE-001",
        confirmed=True,
        store_path=store,
        now=NOW,
    )

    direct = read_preference(
        owner_id="U001",
        reader_id="U002",
        store_path=store,
        now="2026-10-28T10:05:00",
    )
    plan = preview_with_memory(
        request=_request_without_session_minutes(),
        owner_id="U001",
        reader_id="U002",
        store_path=store,
        now="2026-10-28T10:05:00",
    )

    assert direct["status"] == "forbidden"
    assert direct["found"] is False
    assert plan["status"] == "memory_not_available"
    assert plan["preview"] is None


def test_route_a_correction_creates_v2_and_new_session_reads_only_v2(tmp_path: Path):
    store = tmp_path / "memory.json"
    save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-confirm-001",
        request_id="REQ-W07-SAVE-001",
        confirmed=True,
        store_path=store,
        now=NOW,
    )
    corrected = save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=30,
        source_id="chat-confirm-002",
        request_id="REQ-W07-SAVE-002",
        confirmed=True,
        store_path=store,
        now="2026-10-28T11:00:00",
    )
    readback = read_preference(
        owner_id="U001",
        reader_id="U001",
        store_path=store,
        now="2026-10-28T11:05:00",
    )

    assert corrected["version"] == 2
    assert readback["memory"]["version"] == 2
    assert readback["memory"]["value"] == 30
    assert readback["memory"]["source"]["source_id"] == "chat-confirm-002"


def test_route_a_revocation_makes_memory_unavailable(tmp_path: Path):
    store = tmp_path / "memory.json"
    save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-confirm-001",
        request_id="REQ-W07-SAVE-001",
        confirmed=True,
        store_path=store,
        now=NOW,
    )
    revoked = revoke_preference(
        owner_id="U001",
        actor_id="U001",
        request_id="REQ-W07-REVOKE-001",
        confirmed=True,
        store_path=store,
        now="2026-10-28T12:00:00",
    )
    readback = read_preference(
        owner_id="U001",
        reader_id="U001",
        store_path=store,
        now="2026-10-28T12:01:00",
    )

    assert revoked["status"] == "revoked"
    assert readback["found"] is False


def test_w01_unconfirmed_save_does_not_write(tmp_path: Path):
    store = tmp_path / "memory.json"
    result = save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-proposal-001",
        request_id="REQ-W07-NO-001",
        confirmed=False,
        store_path=store,
        now=NOW,
    )

    assert result["status"] == "confirmation_required"
    assert result["executed"] is False
    assert not store.exists()


def test_w02_same_request_id_is_idempotent(tmp_path: Path):
    store = tmp_path / "memory.json"
    first = save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-confirm-001",
        request_id="REQ-W07-IDEMP-001",
        confirmed=True,
        store_path=store,
        now=NOW,
    )
    replay = save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-confirm-001",
        request_id="REQ-W07-IDEMP-001",
        confirmed=True,
        store_path=store,
        now=NOW,
    )
    data = json.loads(store.read_text(encoding="utf-8"))

    assert first["replayed"] is False
    assert replay["replayed"] is True
    assert len(data["records"]) == 1


def test_illegal_preference_value_fails_without_write(tmp_path: Path):
    store = tmp_path / "memory.json"

    try:
        save_confirmed_preference(
            owner_id="U001",
            actor_id="U001",
            value=0,
            source_id="chat-confirm-bad",
            request_id="REQ-W07-BAD-001",
            confirmed=True,
            store_path=store,
            now=NOW,
        )
    except ValueError as exc:
        assert "between 15 and 240" in str(exc)
    else:
        raise AssertionError("expected ValueError")

    assert not store.exists()


def test_expired_memory_is_not_returned(tmp_path: Path):
    store = tmp_path / "memory.json"
    save_confirmed_preference(
        owner_id="U001",
        actor_id="U001",
        value=60,
        source_id="chat-confirm-expiring",
        request_id="REQ-W07-EXP-001",
        confirmed=True,
        store_path=store,
        now="2026-10-28T10:00:00",
        expires_at="2026-10-28T10:30:00",
    )

    result = read_preference(
        owner_id="U001",
        reader_id="U001",
        store_path=store,
        now="2026-10-28T10:31:00",
    )

    assert result["status"] == "not_found"
    assert result["found"] is False
