"""Preview and apply a personal event that displaces saved study sessions."""

from datetime import datetime, timedelta
from hashlib import sha256

from .planner_core import TZ, at, conflict, day, dump, invalid, moment, owned, store_resource
from .planner_logic import plan_sessions, save, sessions_valid
from .planner_schedule import available, check, minutes, plan_windows


def _interval(row):
    return moment(row["starts_at"]), moment(row["ends_at"])


def _replacements(db, plan, affected, excluded, busy, now):
    sessions = plan_sessions(db, plan["plan_id"])
    kept = [session for session in sessions if session["session_id"] not in affected]
    moving = [session for session in sessions if session["session_id"] in affected]
    kept_full_ends = []
    kept_short_start = None
    for session in kept:
        start, end = _interval(session)
        if minutes(start, end) < plan["session_minutes"]:
            kept_short_start = start
        else:
            kept_full_ends.append(end)

    start = at(day(plan["start_date"]))
    end = at(day(plan["exam_date"]))
    slots = available(
        db, start, end, plan_windows(plan), exclude=excluded, extra_busy=busy
    )
    if not slots["check_complete"]:
        conflict("課表有未知時段，暫時無法安全重排。", "SCHEDULE_INCOMPLETE")

    placements = []
    floor = max(start, now)
    for session in moving:
        previous_start, previous_end = _interval(session)
        duration = previous_end - previous_start
        short = duration < timedelta(minutes=plan["session_minutes"])
        earliest = floor
        latest = kept_short_start if not short and kept_short_start else end
        if short and kept_full_ends:
            earliest = max(earliest, max(kept_full_ends))
        for slot in slots["free_slots"]:
            begins = max(earliest, moment(slot["starts_at"]))
            finishes = begins + duration
            if finishes <= min(latest, moment(slot["ends_at"])):
                placements.append((session, begins, finishes))
                floor = finishes
                break
        else:
            conflict(
                "考試前的可用時段不足，請調整私人行程或複習計畫。",
                "STUDY_ADJUSTMENT_NO_SLOT",
            )
    return placements


def preview_adjustment(db, event, old=None, *, now=None):
    start, end = _interval(event)
    if end <= start:
        invalid("ends_at", "結束時間必須晚於開始時間")
    excluded = {("personal_event", old["event_id"])} if old else set()
    result = check(db, start, end, exclude=excluded)
    if any(item["source_type"] != "study_session" for item in result["conflicts"]):
        conflict("行程與課程或其他私人行程重疊。", "SCHEDULE_CONFLICT", result["conflicts"])
    if not result["conflicts"]:
        conflict("這筆行程目前沒有需要重排的複習時段，請重新儲存。", "STUDY_ADJUSTMENT_STALE")
    if not result["check_complete"]:
        conflict("課表有未知時段，暫時無法安全重排。", "SCHEDULE_INCOMPLETE")

    affected = {}
    for item in result["conflicts"]:
        session = owned(db, "study-sessions", item["source_id"])
        affected.setdefault(session["plan_id"], set()).add(session["session_id"])
        excluded.add(("study_session", session["session_id"]))

    plans = sorted(
        (owned(db, "study-plans", plan_id) for plan_id in affected),
        key=lambda plan: (plan["exam_date"], plan["plan_id"]),
    )
    now = now if now is not None else datetime.now(TZ)
    if now.second or now.microsecond:
        now = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    busy = [(start, end)]
    placements = []
    for plan in plans:
        moves = _replacements(db, plan, affected[plan["plan_id"]], excluded, busy, now)
        placements.extend(moves)
        busy.extend((begins, finishes) for _, begins, finishes in moves)

    moves = [
        {
            "session_id": session["session_id"],
            "title": session["title"],
            "from_start": session["starts_at"],
            "from_end": session["ends_at"],
            "to_start": begins.isoformat(),
            "to_end": finishes.isoformat(),
        }
        for session, begins, finishes in placements
    ]
    snapshot = {
        "event": event,
        "previous_event": old,
        "plan_versions": [(p["plan_id"], p["plan_version"]) for p in plans],
        "moves": moves,
    }
    token = sha256(dump(snapshot).encode()).hexdigest()
    return {"preview_token": token, "moves": moves}, plans, placements


def apply_adjustment(db, event, old, preview_token):
    preview, plans, placements = preview_adjustment(db, event, old)
    if preview["preview_token"] != preview_token:
        conflict("課表或複習計畫已更新，請重新預覽。", "STUDY_ADJUSTMENT_STALE")
    for session, begins, finishes in placements:
        store_resource(
            db,
            "study-sessions",
            dict(session, starts_at=begins.isoformat(), ends_at=finishes.isoformat()),
            session,
        )
    saved = save(db, "personal-events", event, old)
    for plan in plans:
        sessions_valid(db, plan, plan_sessions(db, plan["plan_id"]))
        store_resource(
            db, "study-plans", dict(plan, plan_version=plan["plan_version"] + 1), plan
        )
    return saved
