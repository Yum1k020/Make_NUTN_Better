"""A single Taipei-time interval engine shared by calendar, checks and scheduling."""

from datetime import timedelta

from .planner_core import (
    TZ, Problem, at, checked, clock, conflict, day, interval, moment, offering,
    owned, records, reference, stage, weekly,
)


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def subtract(windows, busy):
    result = []
    busy = merge(busy)
    for start, end in merge(windows):
        cursor = start
        for a, b in busy:
            if b <= cursor or a >= end:
                continue
            if a > cursor:
                result.append((cursor, min(a, end)))
            cursor = max(cursor, b)
            if cursor >= end:
                break
        if cursor < end:
            result.append((cursor, end))
    return result


def minutes(start, end):
    return int((end - start).total_seconds() // 60)


def overlap(a, b, c, d):
    return a < d and c < b


def semester_dates(db, semester_id):
    row = reference(db, "semesters", "id", semester_id, "semester_id")
    try:
        start, end = day(row["starts_on"]), day(row["ends_on"])
        if end < start or row["timezone"] != "Asia/Taipei":
            raise ValueError("Invalid semester")
        return start, end
    except (ValueError, TypeError, KeyError) as error:
        raise ValueError("Semester data is invalid") from error


def expand(meetings, first, last, prefix, title):
    events = []
    d = first
    while d <= last:
        for i, m in enumerate(meetings):
            if d.isoweekday() == m["weekday"]:
                source = f"{prefix}:{i}"
                events.append({"event_key": f"class:{source}:{d.isoformat()}", "source_type": "class",
                               "source_id": source, "title": title, "starts_at": at(d, m["start_time"]).isoformat(),
                               "ends_at": at(d, m["end_time"]).isoformat(), "location": m.get("location")})
        d += timedelta(days=1)
    return events


def occupied(db, start, end, exclude=(), ignore_entries=(), ignore_enrollments=(), ignore_plan=None):
    """Return unique occupied events intersecting [start,end), plus unresolved classes."""
    events, warnings = [], []
    entries = records(db, "timetable-entries")
    covered = {e["enrollment_id"] for e in entries if e["entry_id"] not in ignore_entries}
    classes = []
    for e in entries:
        if e["entry_id"] not in ignore_entries:
            classes.append((e["entry_id"], e["course_id"], e["semester_id"], e["meetings"]))
    for e in records(db, "enrollments"):
        if e["enrollment_id"] in covered or e["enrollment_id"] in ignore_enrollments:
            continue
        meetings = offering(db, e["offering_id"], e["course_id"], e["semester_id"])[1] if e["offering_id"] else []
        classes.append((e["enrollment_id"], e["course_id"], e["semester_id"], meetings))
    for source_id, course_id, semester_id, meetings in classes:
        first, last = semester_dates(db, semester_id)
        first, last = max(first, start.astimezone(TZ).date()), min(last, (end - timedelta(microseconds=1)).astimezone(TZ).date())
        if first > last:
            continue
        course = reference(db, "courses", "course_id", course_id, "course_id")
        if not meetings:
            warnings.append({"code": "UNKNOWN_CLASS_TIME", "source_type": "class", "source_id": source_id})
        else:
            try:
                weekly(meetings, True)
            except Problem as error:
                raise ValueError("Invalid stored timetable") from error
            events.extend(expand(meetings, first, last, source_id, course["name"]))
    for kind, source_type, key in (("personal-events", "personal_event", "event_id"), ("study-sessions", "study_session", "session_id")):
        for row in records(db, kind):
            if kind == "study-sessions" and row["plan_id"] == ignore_plan:
                continue
            a, b = moment(row["starts_at"]), moment(row["ends_at"])
            if b <= a:
                raise ValueError("Invalid stored event interval")
            events.append({"event_key": f"{source_type}:{row[key]}", "source_type": source_type,
                           "source_id": row[key], "title": row["title"], "starts_at": row["starts_at"],
                           "ends_at": row["ends_at"], "location": row.get("location")})
    unique = {e["event_key"]: e for e in events if (e["source_type"], e["source_id"]) not in exclude
              and overlap(start, end, moment(e["starts_at"]), moment(e["ends_at"]))}
    return sorted(unique.values(), key=lambda e: (moment(e["starts_at"]), e["event_key"])), warnings


def check(db, start, end, **kwargs):
    stage("L4")
    events, warnings = occupied(db, start, end, **kwargs)
    conflicts = [{"source_type": e["source_type"], "source_id": e["source_id"], "title": e["title"],
                  "overlap_starts_at": max(start, moment(e["starts_at"])).isoformat(),
                  "overlap_ends_at": min(end, moment(e["ends_at"])).isoformat()} for e in events]
    return {"has_conflict": bool(conflicts), "check_complete": not warnings, "conflicts": conflicts, "warnings": warnings}


def reject_conflicts(db, start, end, **kwargs):
    result = check(db, start, end, **kwargs)
    if result["has_conflict"]:
        conflict("與既有安排衝突", "SCHEDULE_CONFLICT", result["conflicts"])
    return result["warnings"]


def validate_exclude(db, data, start, end):
    if not data:
        return ()
    source_type, source_id = data["source_type"], data["source_id"]
    if source_type in ("personal_event", "study_session"):
        owned(db, "personal-events" if source_type == "personal_event" else "study-sessions", source_id)
    else:
        prefix, _, index = source_id.rpartition(":")
        entries = records(db, "timetable-entries") + records(db, "enrollments")
        record = next((e for e in entries if e.get("entry_id", e.get("enrollment_id")) == prefix), None)
        if record is None or not index.isdigit():
            raise Problem(404, "RESOURCE_NOT_FOUND", "排除來源不存在")
        meetings = record.get("meetings")
        if meetings is None:
            meetings = offering(db, record["offering_id"], record["course_id"], record["semester_id"])[1] if record["offering_id"] else []
        if int(index) >= len(meetings):
            raise Problem(404, "RESOURCE_NOT_FOUND", "排除來源不存在")
    return {(source_type, source_id)}


def calendar(db, first, last):
    events, warnings = occupied(db, at(first), at(last + timedelta(days=1)))
    tasks = [t for t in records(db, "tasks") if first <= day(t["due_date"]) <= last]
    tasks.sort(key=lambda t: (t["due_date"], t["due_time"] is None, t["due_time"] or "", t["task_id"]))
    return {"from": first.isoformat(), "to": last.isoformat(), "timezone": "Asia/Taipei", "events": events,
            "task_deadlines": [{k: t[k] for k in ("task_id", "title", "type", "due_date", "due_time", "completed")} for t in tasks],
            "warnings": warnings}


def available(db, start, end, windows, minimum=1, ignore_plan=None):
    stage("L4")
    events, warnings = occupied(db, start, end, ignore_plan=ignore_plan)
    slots = subtract(windows, [(moment(e["starts_at"]), moment(e["ends_at"])) for e in events])
    free = []
    for a, b in slots:
        # Minute-based slots round inward; no partly occupied minute is declared free.
        if a.second or a.microsecond:
            a = a.replace(second=0, microsecond=0) + timedelta(minutes=1)
        b = b.replace(second=0, microsecond=0)
        duration = minutes(a, b)
        if duration >= minimum:
            free.append({"starts_at": a.isoformat(), "ends_at": b.isoformat(), "duration_minutes": duration})
    return {"free_slots": free, "total_free_minutes": sum(s["duration_minutes"] for s in free),
            "check_complete": not warnings, "warnings": warnings}


def plan_windows(plan):
    windows = []
    d, final = day(plan["start_date"]), day(plan["exam_date"])
    while d < final:
        for w in plan["allowed_windows"]:
            if d.isoweekday() == w["weekday"]:
                windows.append((at(d, w["start_time"]), at(d, w["end_time"])))
        d += timedelta(days=1)
    return merge(windows)
