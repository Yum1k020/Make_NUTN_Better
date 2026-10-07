from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.scheduler import build_study_plan


def preview_study_plan(**request: Any) -> dict[str, Any]:
    result = build_study_plan(**request)
    return {**result, "action": "preview_study_plan", "mutated": False, "source": "scheduler_v1"}


def _fingerprint(preview: dict[str, Any]) -> str:
    data = {
        "plan_id": preview["plan_id"],
        "suggested_sessions": preview["suggested_sessions"],
        "scheduled_minutes": preview["scheduled_minutes"],
        "remaining_minutes": preview["remaining_minutes"],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"requests": {}, "study_sessions": [], "audit": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("requests", {})
    data.setdefault("study_sessions", [])
    data.setdefault("audit", [])
    return data


def save_study_plan(
    *,
    preview: dict[str, Any],
    confirmed: bool,
    request_id: str,
    store_path: str | Path,
) -> dict[str, Any]:
    if not confirmed:
        return {
            "action": "save_study_plan",
            "accepted": False,
            "executed": False,
            "status": "confirmation_required",
            "request_id": request_id or None,
            "replayed": False,
        }

    if not request_id.strip():
        raise ValueError("request_id is required")
    if not preview.get("suggested_sessions"):
        raise ValueError("cannot save an empty study plan")

    path = Path(store_path)
    data = _load(path)
    fp = _fingerprint(preview)

    if request_id in data["requests"]:
        old = data["requests"][request_id]
        if old["fingerprint"] != fp:
            raise ValueError("request_id replay payload mismatch")
        return {**old["result"], "replayed": True}

    ids = []
    for i, session in enumerate(preview["suggested_sessions"], 1):
        sid = f"{request_id}-S{i:03d}"
        ids.append(sid)
        data["study_sessions"].append(
            {"session_id": sid, **session, "source_type": "generated"}
        )

    result = {
        "action": "save_study_plan",
        "accepted": True,
        "executed": True,
        "status": "saved",
        "plan_id": preview["plan_id"],
        "request_id": request_id,
        "saved_session_ids": ids,
        "replayed": False,
    }

    data["requests"][request_id] = {"fingerprint": fp, "result": result}
    data["audit"].append(
        {
            "request_id": request_id,
            "action": "save_study_plan",
            "plan_id": preview["plan_id"],
            "confirmed": True,
            "result_status": "saved",
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
