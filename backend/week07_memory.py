from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.week04_tools import preview_study_plan

PREFERENCE_TYPE = "study_session_minutes"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"records": [], "requests": {}, "audit": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("records", [])
    data.setdefault("requests", {})
    data.setdefault("audit", [])
    return data


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _request_replay(data: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    prior = data["requests"].get(request_id)
    if prior is None:
        return None
    return {**prior, "replayed": True}


def _validate_minutes(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("study_session_minutes must be an integer")
    if value < 15 or value > 240:
        raise ValueError("study_session_minutes must be between 15 and 240")
    return value


def _parse_optional_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _active_record(
    data: dict[str, Any],
    *,
    owner_id: str,
    now: datetime,
) -> dict[str, Any] | None:
    candidates = [
        item
        for item in data["records"]
        if item.get("owner_id") == owner_id
        and item.get("preference_type") == PREFERENCE_TYPE
        and item.get("revoked_at") is None
        and item.get("superseded_at") is None
    ]
    if not candidates:
        return None

    record = max(candidates, key=lambda item: int(item["version"]))
    expires_at = _parse_optional_time(record.get("expires_at"))
    if expires_at is not None and now >= expires_at:
        return None
    return record


def save_confirmed_preference(
    *,
    owner_id: str,
    actor_id: str,
    value: int,
    source_id: str,
    request_id: str,
    confirmed: bool,
    store_path: str | Path,
    now: str,
    expires_at: str | None = None,
) -> dict[str, Any]:
    path = Path(store_path)
    data = _load(path)

    if not request_id.strip():
        raise ValueError("request_id is required")

    replay = _request_replay(data, request_id)
    if replay is not None:
        return replay

    if actor_id != owner_id:
        result = {
            "action": "save_preference",
            "accepted": False,
            "executed": False,
            "status": "forbidden",
            "request_id": request_id,
            "owner_id": owner_id,
            "replayed": False,
        }
        return result

    if not confirmed:
        result = {
            "action": "save_preference",
            "accepted": False,
            "executed": False,
            "status": "confirmation_required",
            "request_id": request_id,
            "owner_id": owner_id,
            "replayed": False,
        }
        return result

    minutes = _validate_minutes(value)
    now_dt = datetime.fromisoformat(now)
    expiry_dt = _parse_optional_time(expires_at)
    if expiry_dt is not None and expiry_dt <= now_dt:
        raise ValueError("expires_at must be later than now")

    current = _active_record(data, owner_id=owner_id, now=now_dt)
    version = 1 if current is None else int(current["version"]) + 1

    if current is not None:
        current["superseded_at"] = now

    memory_id = f"{owner_id}:{PREFERENCE_TYPE}:v{version}"
    record = {
        "memory_id": memory_id,
        "owner_id": owner_id,
        "preference_type": PREFERENCE_TYPE,
        "value": minutes,
        "source": {
            "source_type": "user_confirmation",
            "source_id": source_id,
        },
        "version": version,
        "created_at": now,
        "expires_at": expires_at,
        "superseded_at": None,
        "revoked_at": None,
    }
    data["records"].append(record)

    result = {
        "action": "save_preference",
        "accepted": True,
        "executed": True,
        "status": "saved",
        "request_id": request_id,
        "memory_id": memory_id,
        "owner_id": owner_id,
        "preference_type": PREFERENCE_TYPE,
        "value": minutes,
        "version": version,
        "expires_at": expires_at,
        "replayed": False,
    }
    data["requests"][request_id] = result
    data["audit"].append({
        "request_id": request_id,
        "action": "save_preference",
        "owner_id": owner_id,
        "memory_id": memory_id,
        "version": version,
        "source_id": source_id,
        "at": now,
    })
    _save(path, data)
    return result


def read_preference(
    *,
    owner_id: str,
    reader_id: str,
    store_path: str | Path,
    now: str,
) -> dict[str, Any]:
    if reader_id != owner_id:
        return {
            "action": "read_preference",
            "status": "forbidden",
            "found": False,
            "owner_id": owner_id,
            "reader_id": reader_id,
            "memory": None,
        }

    data = _load(Path(store_path))
    record = _active_record(data, owner_id=owner_id, now=datetime.fromisoformat(now))
    if record is None:
        return {
            "action": "read_preference",
            "status": "not_found",
            "found": False,
            "owner_id": owner_id,
            "reader_id": reader_id,
            "memory": None,
        }

    return {
        "action": "read_preference",
        "status": "ok",
        "found": True,
        "owner_id": owner_id,
        "reader_id": reader_id,
        "memory": {
            "memory_id": record["memory_id"],
            "preference_type": record["preference_type"],
            "value": record["value"],
            "source": record["source"],
            "version": record["version"],
            "expires_at": record["expires_at"],
        },
    }


def revoke_preference(
    *,
    owner_id: str,
    actor_id: str,
    request_id: str,
    confirmed: bool,
    store_path: str | Path,
    now: str,
) -> dict[str, Any]:
    path = Path(store_path)
    data = _load(path)

    if not request_id.strip():
        raise ValueError("request_id is required")

    replay = _request_replay(data, request_id)
    if replay is not None:
        return replay

    if actor_id != owner_id:
        return {
            "action": "revoke_preference",
            "accepted": False,
            "executed": False,
            "status": "forbidden",
            "request_id": request_id,
            "owner_id": owner_id,
            "replayed": False,
        }

    if not confirmed:
        return {
            "action": "revoke_preference",
            "accepted": False,
            "executed": False,
            "status": "confirmation_required",
            "request_id": request_id,
            "owner_id": owner_id,
            "replayed": False,
        }

    now_dt = datetime.fromisoformat(now)
    current = _active_record(data, owner_id=owner_id, now=now_dt)
    if current is None:
        result = {
            "action": "revoke_preference",
            "accepted": True,
            "executed": False,
            "status": "not_found",
            "request_id": request_id,
            "owner_id": owner_id,
            "replayed": False,
        }
        data["requests"][request_id] = result
        _save(path, data)
        return result

    current["revoked_at"] = now
    result = {
        "action": "revoke_preference",
        "accepted": True,
        "executed": True,
        "status": "revoked",
        "request_id": request_id,
        "owner_id": owner_id,
        "memory_id": current["memory_id"],
        "version": current["version"],
        "replayed": False,
    }
    data["requests"][request_id] = result
    data["audit"].append({
        "request_id": request_id,
        "action": "revoke_preference",
        "owner_id": owner_id,
        "memory_id": current["memory_id"],
        "version": current["version"],
        "at": now,
    })
    _save(path, data)
    return result


def preview_with_memory(
    *,
    request: dict[str, Any],
    owner_id: str,
    reader_id: str,
    store_path: str | Path,
    now: str,
) -> dict[str, Any]:
    effective_request = dict(request)
    memory_read = None

    if effective_request.get("session_minutes") is None:
        memory_read = read_preference(
            owner_id=owner_id,
            reader_id=reader_id,
            store_path=store_path,
            now=now,
        )
        if not memory_read["found"]:
            return {
                "action": "preview_with_memory",
                "status": "memory_not_available",
                "memory_used": False,
                "memory_read": memory_read,
                "preview": None,
            }
        effective_request["session_minutes"] = memory_read["memory"]["value"]

    preview = preview_study_plan(**effective_request)
    return {
        "action": "preview_with_memory",
        "status": "ok",
        "memory_used": memory_read is not None,
        "memory_read": memory_read,
        "effective_session_minutes": effective_request["session_minutes"],
        "preview": preview,
    }
