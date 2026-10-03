"""Resource relationships and mutations. Caller owns a single SQLite transaction."""

from datetime import timedelta

from .planner_core import (
    RESOURCE, Problem, at, conflict, course_snapshot, day, invalid, moment, offering,
    owned, records, reference, remove, shape, stage, store_resource,
)
from .planner_schedule import (
    available, check, expand, merge, minutes, overlap, plan_windows, reject_conflicts, semester_dates,
)


def plan_sessions(db, plan_id):
    return sorted([s for s in records(db, "study-sessions") if s["plan_id"] == plan_id], key=lambda s: (s["starts_at"], s["session_id"]))


def summary(plan, sessions):
    scheduled = sum(minutes(moment(s["starts_at"]), moment(s["ends_at"])) for s in sessions)
    if scheduled < 0 or scheduled > plan["target_minutes"]:
        raise ValueError("Invalid stored session totals")
    return {"scheduled_minutes": scheduled, "remaining_minutes": plan["target_minutes"] - scheduled}


def output(db, kind, value):
    if kind == "study-plans":
        return {**value, **summary(value, plan_sessions(db, value["plan_id"]))}
    return value


def sessions_valid(db, plan, sessions, scheduling=True):
    stage("L4")
    windows = plan_windows(plan)
    total, short, previous = 0, 0, None
    for s in sorted(sessions, key=lambda row: row["starts_at"]):
        start, end = moment(s["starts_at"]), moment(s["ends_at"])
        duration = (end - start).total_seconds() / 60
        if duration <= 0 or not duration.is_integer() or duration > plan["session_minutes"]:
            invalid("sessions", "時段須為正整數分鐘且不得超過單次時長")
        if not any(a <= start and end <= b for a, b in windows):
            invalid("sessions", "時段不在計畫日期或可用視窗內")
        if previous and start < previous:
            conflict("複習時段彼此衝突", "SCHEDULE_CONFLICT")
        previous = end
        short += duration < plan["session_minutes"]
        total += int(duration)
        if scheduling:
            result = check(db, start, end, ignore_plan=plan.get("plan_id"))
            if not result["check_complete"]:
                conflict("存在未知課表時間", "SCHEDULE_INCOMPLETE")
            if result["has_conflict"]:
                conflict("複習安排與最新行程衝突", "SCHEDULE_CONFLICT", result["conflicts"])
    ordered = sorted(sessions, key=lambda row: row["starts_at"])
    if short > 1 or total > plan["target_minutes"]:
        invalid("sessions", "總分鐘超過目標或有多個非標準時段")
    if short and minutes(moment(ordered[-1]["starts_at"]), moment(ordered[-1]["ends_at"])) == plan["session_minutes"]:
        invalid("sessions", "較短時段僅能放在最後")


def validate_plan(plan):
    days = (day(plan["exam_date"]) - day(plan["start_date"])).days
    if not 1 <= days <= 60:
        invalid("exam_date", "考試日期須晚於開始日期且範圍最多 60 天")


def exam_matches(plan, task):
    return (task["type"] == "exam" and task["due_date"] == plan["exam_date"]
            and (task["course_id"] is None or task["course_id"] == plan["course_id"]))


def save(db, kind, payload, old=None):
    key, fields, required, defaults = RESOURCE[kind]
    if old is not None and not payload:
        invalid("body", "PATCH 至少提供一個可修改欄位")
    parsed = shape(payload, fields, required if old is None else (), defaults if old is None else None)
    data = {k: v for k, v in (old or {}).items() if k in fields}
    data.update(parsed)
    shape(data, fields, required)
    # Format/cross-field validation precedes lookups or writes.
    if kind == "personal-events" and moment(data["ends_at"]) <= moment(data["starts_at"]):
        invalid("ends_at", "結束時間必須晚於開始時間")
    if kind == "study-plans":
        validate_plan(data)
    stage("L3")
    if data.get("course_id"):
        reference(db, "courses", "course_id", data["course_id"], "course_id")
    sem = data.get("semester_id", data.get("target_semester_id"))
    if sem:
        reference(db, "semesters", "id", sem, "semester_id")
    if data.get("offering_id"):
        catalog, meetings = offering(db, data["offering_id"], data["course_id"], sem)
    same = [r for r in records(db, kind) if old is None or r[key] != old[key]]
    if kind in ("enrollments", "planned-courses", "timetable-entries"):
        for r in same:
            if r["course_id"] == data["course_id"] and (kind == "enrollments" or r.get("semester_id", r.get("target_semester_id")) == sem):
                conflict("課程紀錄重複；baseline 不支援重修建檔", "DUPLICATE_COURSE")
    if kind == "enrollments":
        if data["enrollment_status"] == "in_progress":
            if data["passed"] is not None or data["grade"] is not None:
                invalid("passed", "修習中不接受成績或通過狀態")
        elif type(data["passed"]) is not bool:
            invalid("passed", "finished 必須明確提供通過狀態")
        if data["grade"] is not None and data["passed"] != (data["grade"] >= 60):
            invalid("grade", "成績與通過狀態矛盾")
        if old:
            for entry in records(db, "timetable-entries"):
                if entry["enrollment_id"] == old[key] and any(data[f] != old[f] for f in ("course_id", "semester_id", "offering_id")):
                    conflict("修課紀錄已有課表引用，請先移除課表", "RELATED_RESOURCE")
        data["course_snapshot"] = old["course_snapshot"] if old and old["course_id"] == data["course_id"] else course_snapshot(db, data["course_id"])
    elif kind == "tasks":
        if data["due_date"] is None:
            if payload.get("due_time") is not None:
                invalid("due_time", "截止時間需要截止日期")
            data["due_time"] = None
        if data["event_id"] is not None:
            try:
                owned(db, "personal-events", data["event_id"])
            except Problem:
                invalid("event_id", "非本人的有效行程")
        for plan in records(db, "study-plans"):
            if old and plan["exam_task_id"] == old[key] and not exam_matches(plan, data):
                conflict("修改會破壞複習計畫的考試關聯", "RELATED_RESOURCE")
    elif kind == "personal-events":
        data["warnings"] = reject_conflicts(db, moment(data["starts_at"]), moment(data["ends_at"]),
                                             exclude={("personal_event", old[key])} if old else ())
    elif kind == "study-plans":
        if data["exam_task_id"] is not None:
            try:
                task = owned(db, "tasks", data["exam_task_id"])
            except Problem:
                invalid("exam_task_id", "非本人的有效考試待辦")
            if not exam_matches(data, task):
                invalid("exam_task_id", "考試類型、日期或課程不一致")
        if old:
            try:
                sessions_valid(db, dict(data, plan_id=old[key]), plan_sessions(db, old[key]))
            except Problem as error:
                raise Problem(409, "SESSIONS_REQUIRE_ADJUSTMENT", "請先調整或清空既有複習安排") from error
        data["plan_version"] = old["plan_version"] + 1 if old else 1
    elif kind == "timetable-entries":
        if data["offering_id"]:
            if "meetings" in payload or "section_name" in payload:
                invalid("meetings", "共用開課模式不可覆寫時段或班別")
            data.update(meetings=meetings, section_name=catalog["section_name"], source_type="catalog")
        else:
            if "meetings" not in data or old and old["offering_id"] and "meetings" not in payload:
                invalid("meetings", "手動模式須提供至少一筆時段")
            data["source_type"] = "manual"
        for meeting in data["meetings"]:
            if meeting["campus_id"]:
                reference(db, "campuses", "id", meeting["campus_id"], "campus_id")
        enrollments = records(db, "enrollments")
        enrollment = next((e for e in enrollments if e["course_id"] == data["course_id"]), None)
        if enrollment and enrollment["semester_id"] != sem:
            conflict("已有其他學期修課紀錄；baseline 不支援重修", "DUPLICATE_COURSE")
        ignore_enroll = {enrollment["enrollment_id"]} if enrollment else set()
        first, last = semester_dates(db, sem)
        events = expand(data["meetings"], first, last, "candidate", course_snapshot(db, data["course_id"])["name"])
        warnings = []
        for i, e in enumerate(events):
            a, b = moment(e["starts_at"]), moment(e["ends_at"])
            if any(overlap(a, b, moment(other["starts_at"]), moment(other["ends_at"])) for other in events[:i]):
                conflict("課表自身時段重疊", "SCHEDULE_CONFLICT")
            warnings.extend(reject_conflicts(db, a, b, ignore_entries={old[key]} if old else (), ignore_enrollments=ignore_enroll))
        if not data["meetings"]:
            warnings.append({"code": "UNKNOWN_CLASS_TIME", "source_type": "class", "source_id": data["offering_id"]})
        data["warnings"] = list({str(w): w for w in warnings}.values())
        # All validation precedes relationship writes; failure in the final INSERT rolls both back.
        if enrollment is None:
            enrollment = save(db, "enrollments", {"course_id": data["course_id"], "semester_id": sem,
                "offering_id": data["offering_id"], "enrollment_status": "in_progress"})
        data["enrollment_id"] = enrollment["enrollment_id"]
    return output(db, kind, store_resource(db, kind, data, old))


def delete(db, kind, old):
    key = RESOURCE[kind][0]
    if kind == "enrollments" and any(e["enrollment_id"] == old[key] for e in records(db, "timetable-entries")):
        conflict("請先移除課表關聯", "RELATED_RESOURCE")
    if kind == "tasks" and any(p["exam_task_id"] == old[key] for p in records(db, "study-plans")):
        conflict("請先解除複習計畫引用", "RELATED_RESOURCE")
    if kind == "personal-events":
        for task in records(db, "tasks"):
            if task["event_id"] == old[key]:
                store_resource(db, "tasks", dict(task, event_id=None), task)
    if kind == "study-plans":
        for s in plan_sessions(db, old[key]):
            remove(db, "study-sessions", s["session_id"])
    remove(db, kind, old[key])


def generate(db, plan):
    stage("L4")
    result = available(db, at(day(plan["start_date"])), at(day(plan["exam_date"])), plan_windows(plan), ignore_plan=plan["plan_id"])
    if not result["check_complete"]:
        conflict("存在未知課表時間", "SCHEDULE_INCOMPLETE")
    remaining, candidates = plan["target_minutes"], []
    for slot in result["free_slots"]:
        cursor, end = moment(slot["starts_at"]), moment(slot["ends_at"])
        while remaining:
            duration = min(plan["session_minutes"], remaining)
            if minutes(cursor, end) < duration:
                break
            finish = cursor + timedelta(minutes=duration)
            candidates.append({"title": "複習：" + course_snapshot(db, plan["course_id"])["name"],
                               "starts_at": cursor.isoformat(), "ends_at": finish.isoformat()})
            remaining -= duration
            cursor = finish
    sessions_valid(db, plan, candidates)
    return {"plan_id": plan["plan_id"], "plan_version": plan["plan_version"], "candidates": candidates,
            "scheduled_minutes": plan["target_minutes"] - remaining, "remaining_minutes": remaining,
            "generation_status": "complete" if remaining == 0 else "partial", "warnings": result["warnings"]}


def version_matches(plan, version):
    if version != plan["plan_version"]:
        conflict("計畫版本已過期", "STALE_PLAN_VERSION")


def session_result(db, plan):
    sessions = plan_sessions(db, plan["plan_id"])
    return {"plan_id": plan["plan_id"], "plan_version": plan["plan_version"], "sessions": sessions, **summary(plan, sessions)}


def replace_sessions(db, plan, sessions, version):
    version_matches(plan, version)
    sessions_valid(db, plan, sessions)
    for old in plan_sessions(db, plan["plan_id"]):
        remove(db, "study-sessions", old["session_id"])
    for session in sessions:
        store_resource(db, "study-sessions", dict(session, plan_id=plan["plan_id"]))
    plan = store_resource(db, "study-plans", dict(plan, plan_version=plan["plan_version"] + 1), plan)
    return session_result(db, plan)
