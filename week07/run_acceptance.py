from __future__ import annotations

import json
import tempfile
from pathlib import Path

from backend.week07_memory import (
    preview_with_memory,
    read_preference,
    revoke_preference,
    save_confirmed_preference,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"
OUT = ROOT / "week07" / "evidence" / "offline_comparison.json"


def _request_without_session_minutes() -> dict:
    request = json.loads(FIXTURE.read_text(encoding="utf-8"))
    request["session_minutes"] = None
    return request


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="week07-") as temp:
        store = Path(temp) / "memory.json"

        baseline = {
            "memory_available": False,
            "behavior": "session_minutes must be supplied again in each new session",
        }

        unconfirmed = save_confirmed_preference(
            owner_id="U001",
            actor_id="U001",
            value=60,
            source_id="chat-proposal-001",
            request_id="REQ-W07-NO",
            confirmed=False,
            store_path=store,
            now="2026-10-28T10:00:00",
        )

        saved_v1 = save_confirmed_preference(
            owner_id="U001",
            actor_id="U001",
            value=60,
            source_id="chat-confirm-001",
            request_id="REQ-W07-SAVE-1",
            confirmed=True,
            store_path=store,
            now="2026-10-28T10:01:00",
            expires_at="2026-12-31T23:59:59",
        )
        new_session = preview_with_memory(
            request=_request_without_session_minutes(),
            owner_id="U001",
            reader_id="U001",
            store_path=store,
            now="2026-10-28T10:05:00",
        )
        cross_user = read_preference(
            owner_id="U001",
            reader_id="U002",
            store_path=store,
            now="2026-10-28T10:05:00",
        )

        saved_v2 = save_confirmed_preference(
            owner_id="U001",
            actor_id="U001",
            value=30,
            source_id="chat-confirm-002",
            request_id="REQ-W07-SAVE-2",
            confirmed=True,
            store_path=store,
            now="2026-10-28T11:00:00",
            expires_at="2026-12-31T23:59:59",
        )
        corrected_read = read_preference(
            owner_id="U001",
            reader_id="U001",
            store_path=store,
            now="2026-10-28T11:05:00",
        )

        replay = save_confirmed_preference(
            owner_id="U001",
            actor_id="U001",
            value=30,
            source_id="chat-confirm-002",
            request_id="REQ-W07-SAVE-2",
            confirmed=True,
            store_path=store,
            now="2026-10-28T11:00:00",
            expires_at="2026-12-31T23:59:59",
        )

        revoked = revoke_preference(
            owner_id="U001",
            actor_id="U001",
            request_id="REQ-W07-REVOKE",
            confirmed=True,
            store_path=store,
            now="2026-10-28T12:00:00",
        )
        after_revoke = read_preference(
            owner_id="U001",
            reader_id="U001",
            store_path=store,
            now="2026-10-28T12:01:00",
        )

        data = json.loads(store.read_text(encoding="utf-8"))
        checks = {
            "unconfirmed_did_not_write": unconfirmed["executed"] is False,
            "new_session_read_v1": (
                new_session["status"] == "ok"
                and new_session["memory_used"] is True
                and new_session["effective_session_minutes"] == 60
                and new_session["preview"]["scheduled_minutes"] == 180
            ),
            "cross_user_isolated": cross_user["status"] == "forbidden",
            "correction_reads_v2_only": (
                saved_v2["version"] == 2
                and corrected_read["memory"]["version"] == 2
                and corrected_read["memory"]["value"] == 30
            ),
            "same_request_id_no_duplicate": (
                replay["replayed"] is True and len(data["records"]) == 2
            ),
            "revocation_stops_future_reads": (
                revoked["status"] == "revoked" and after_revoke["found"] is False
            ),
        }

        artifact = {
            "route": "A_confirmed_preference",
            "baseline_sha": "9e2407a9a9a160b5ca5b51fc6e4a090ba077768e",
            "preference_type": "study_session_minutes",
            "baseline": baseline,
            "candidate": {
                "saved_v1": saved_v1,
                "new_session": new_session,
                "cross_user": cross_user,
                "saved_v2": saved_v2,
                "corrected_read": corrected_read,
                "replay": replay,
                "revoked": revoked,
                "after_revoke": after_revoke,
            },
            "checks": checks,
            "offline_all_pass": all(checks.values()),
            "live_status": "LIVE_NOT_RUN",
            "live_note": (
                "Week 07 requires current-version real Gemini evidence. "
                "CI has no private API key, so offline evidence does not claim LIVE_PASS."
            ),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    if not artifact["offline_all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
