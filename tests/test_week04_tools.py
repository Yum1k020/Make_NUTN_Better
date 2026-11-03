import json
from pathlib import Path

import pytest

from backend.week04_tools import preview_study_plan, save_study_plan

FIXTURE = Path(__file__).parent / "fixtures" / "week04_plan.json"


def load_case():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_read_preview_does_not_write(tmp_path):
    store = tmp_path / "study_sessions.json"
    preview = preview_study_plan(**load_case())
    assert preview["mutated"] is False
    assert preview["scheduled_minutes"] == 180
    assert preview["remaining_minutes"] == 0
    assert not store.exists()


def test_write_without_confirmation_is_blocked(tmp_path):
    preview = preview_study_plan(**load_case())
    store = tmp_path / "study_sessions.json"
    result = save_study_plan(
        preview=preview,
        confirmed=False,
        request_id="REQ-001",
        store_path=store,
    )
    assert result["accepted"] is False
    assert result["executed"] is False
    assert not store.exists()


def test_confirmed_write_persists(tmp_path):
    preview = preview_study_plan(**load_case())
    store = tmp_path / "study_sessions.json"
    result = save_study_plan(
        preview=preview,
        confirmed=True,
        request_id="REQ-001",
        store_path=store,
    )
    data = json.loads(store.read_text(encoding="utf-8"))
    assert result["status"] == "saved"
    assert len(data["study_sessions"]) == len(preview["suggested_sessions"])


def test_request_id_replay_is_idempotent(tmp_path):
    preview = preview_study_plan(**load_case())
    store = tmp_path / "study_sessions.json"
    first = save_study_plan(preview=preview, confirmed=True, request_id="REQ-SAME", store_path=store)
    second = save_study_plan(preview=preview, confirmed=True, request_id="REQ-SAME", store_path=store)
    data = json.loads(store.read_text(encoding="utf-8"))
    assert first["replayed"] is False
    assert second["replayed"] is True
    assert len(data["study_sessions"]) == len(preview["suggested_sessions"])


def test_replay_payload_mismatch_is_rejected(tmp_path):
    preview = preview_study_plan(**load_case())
    store = tmp_path / "study_sessions.json"
    save_study_plan(preview=preview, confirmed=True, request_id="REQ-X", store_path=store)
    changed = dict(preview)
    changed["scheduled_minutes"] -= 60
    with pytest.raises(ValueError, match="payload mismatch"):
        save_study_plan(preview=changed, confirmed=True, request_id="REQ-X", store_path=store)


def test_shortage_is_reported():
    request = load_case()
    request["target_minutes"] = 600
    preview = preview_study_plan(**request)
    assert preview["remaining_minutes"] > 0
    assert preview["reason"] == "insufficient_available_time_before_exam"
