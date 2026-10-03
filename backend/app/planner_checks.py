"""Non-mutating course planning checks and summaries using the same detail calculations."""

from collections import Counter
from datetime import timedelta

from .catalog_schemas import PrerequisiteSchema
from .planner_core import at, day, moment, offering, records, reference
from .planner_schedule import calendar, check, expand, minutes, occupied, overlap, semester_dates
from .planner_graduation import progress


def planned_check(db, semester_id, items):
    first, last = semester_dates(db, semester_id)
    counts = Counter(item["course_id"] for item in items)
    duplicate = sorted(cid for cid, count in counts.items() if count > 1)
    passed = {e["course_id"] for e in records(db, "enrollments") if e["enrollment_status"] == "finished" and e["passed"] is True}
    prereqs, warnings, events = [], [], {}
    complete = True
    for item in items:
        course = reference(db, "courses", "course_id", item["course_id"], "course_id")
        ids = [r[0] for r in db.execute("SELECT prerequisite_id FROM course_prerequisites WHERE course_id=? ORDER BY prerequisite_id", (item["course_id"],))]
        if course["prerequisite_status"] != "known" and ids:
            raise ValueError("Invalid stored prerequisite relationship")
        PrerequisiteSchema().load({"status": course["prerequisite_status"], "mode": course["prerequisite_mode"],
                                   "course_ids": ids if course["prerequisite_status"] != "unknown" else None,
                                   "source": course["prerequisite_source"]})
        for cid in ids:
            reference(db, "courses", "course_id", cid, "course_id")
        status = "needs_confirmation" if course["prerequisite_status"] == "unknown" else "passed"
        if course["prerequisite_status"] == "known":
            satisfied = all(cid in passed for cid in ids) if course["prerequisite_mode"] == "all" else any(cid in passed for cid in ids)
            status = "passed" if satisfied else "not_met"
        prereqs.append({"course_id": item["course_id"], "status": status, "mode": course["prerequisite_mode"],
                        "required_course_ids": ids if course["prerequisite_status"] != "unknown" else None,
                        "missing_course_ids": [cid for cid in ids if cid not in passed], "source": course["prerequisite_source"]})
        if item["course_id"] in passed:
            warnings.append({"code": "ALREADY_PASSED", "course_id": item["course_id"]})
        meetings = offering(db, item["offering_id"], item["course_id"], semester_id)[1] if item.get("offering_id") else []
        if not meetings:
            complete = False
            warnings.append({"code": "UNKNOWN_CLASS_TIME", "course_id": item["course_id"]})
        for event in expand(meetings, first, last, item.get("offering_id"), course["name"]):
            events[event["event_key"]] = event
    conflicts, prior = [], []
    for event in events.values():
        a, b = moment(event["starts_at"]), moment(event["ends_at"])
        result = check(db, a, b)
        complete &= result["check_complete"]
        warnings.extend(result["warnings"])
        for existing in result["conflicts"]:
            conflicts.append({"candidate_source_id": event["source_id"], **existing})
        for other in prior:
            c, d = moment(other["starts_at"]), moment(other["ends_at"])
            if overlap(a, b, c, d):
                conflicts.append({"candidate_source_id": event["source_id"], "source_type": "candidate_class",
                                  "source_id": other["source_id"], "overlap_starts_at": max(a, c).isoformat(), "overlap_ends_at": min(b, d).isoformat()})
        prior.append(event)
    # Even without any known candidate meetings, report unknown saved timetable data.
    _, unknown = occupied(db, at(first), at(last + timedelta(days=1)))
    warnings.extend(unknown)
    complete &= not unknown
    issues = bool(duplicate or conflicts or any(p["status"] == "not_met" for p in prereqs))
    status = "issues_found" if issues else "needs_confirmation" if not complete or any(p["status"] == "needs_confirmation" for p in prereqs) else "passed"
    return {"overall_status": status, "duplicate_courses": duplicate, "prerequisite_checks": prereqs,
            "schedule_conflicts": conflicts, "schedule_check_complete": complete,
            "warnings": list({str(w): w for w in warnings}.values())}


def dashboard(db, date):
    today = calendar(db, date, date)
    tasks = records(db, "tasks")
    upcoming = [t for t in tasks if t["due_date"] is not None and date <= day(t["due_date"]) < date + timedelta(days=7) and not t["completed"]]
    upcoming.sort(key=lambda t: (t["due_date"], t["due_time"] is None, t["due_time"] or "", t["task_id"]))
    monday = date - timedelta(days=date.weekday())
    start, end = at(monday), at(monday + timedelta(days=7))
    count, total = 0, 0
    for s in records(db, "study-sessions"):
        a, b = max(start, moment(s["starts_at"])), min(end, moment(s["ends_at"]))
        if b > a:
            count += 1
            total += minutes(a, b)
    graduation = progress(db)
    unresolved = any(e["code"] in ("RULE_UNAVAILABLE", "REQUIRED_COURSES_UNMAPPED") for e in graduation["data_errors"])
    return {"date": date.isoformat(), "timezone": "Asia/Taipei",
            "today_task_summary": {"total": len(today["task_deadlines"]), "completed": sum(t["completed"] for t in today["task_deadlines"])},
            "upcoming_tasks": upcoming, "week_study_summary": {"scheduled_minutes": total, "session_count": count},
            "graduation_summary": {"rule_set_id": graduation["rule_set_id"], "earned_credits": graduation["earned_credits"],
                                   "missing_required_courses_count": None if unresolved else len(graduation["missing_required_courses"]),
                                   "overall_status": graduation["overall_status"]},
            "warnings": today["warnings"] + graduation["data_errors"]}
