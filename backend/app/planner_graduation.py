"""Versioned team draft rules. Unmapped requirements remain explicitly unresolved."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from .db import DEMO_USER_ID
from .planner_core import Problem, dump, records, reference, timestamp

RULE_FILE = Path(__file__).parent / "data" / "nutn_csie_115_graduation_rules_v1.json"


def init_graduation(db):
    db.execute("""CREATE TABLE IF NOT EXISTS graduation_rule_documents (
        rule_set_id TEXT PRIMARY KEY REFERENCES rule_sets(id), document TEXT NOT NULL, digest TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS graduation_course_mappings (
        rule_set_id TEXT REFERENCES graduation_rule_documents(rule_set_id), source_key TEXT,
        course_id TEXT NOT NULL REFERENCES courses(course_id), PRIMARY KEY(rule_set_id,source_key))""")
    db.execute("""CREATE TABLE IF NOT EXISTS graduation_course_domains (
        rule_set_id TEXT REFERENCES graduation_rule_documents(rule_set_id),
        course_id TEXT REFERENCES courses(course_id), domain TEXT NOT NULL,
        PRIMARY KEY(rule_set_id,course_id))""")
    document = json.loads(RULE_FILE.read_text())
    db.execute("INSERT OR IGNORE INTO departments VALUES ('dept-nutn-csie')")
    db.execute("INSERT OR IGNORE INTO rule_sets VALUES (?, 'dept-nutn-csie', 115)", (document["rule_set_id"],))
    encoded = dump(document)
    digest = sha256(encoded.encode()).hexdigest()
    old = db.execute("SELECT digest FROM graduation_rule_documents WHERE rule_set_id=?", (document["rule_set_id"],)).fetchone()
    if old and old["digest"] != digest:
        raise ValueError("Rule content changed without a new rule version")
    db.execute("INSERT OR IGNORE INTO graduation_rule_documents VALUES (?,?,?)", (document["rule_set_id"], encoded, digest))
    db.executemany("INSERT OR IGNORE INTO campuses VALUES (?)", [("fucheng",), ("rongyu",)])


def document(db, rule_id):
    row = db.execute("SELECT * FROM graduation_rule_documents WHERE rule_set_id=?", (rule_id,)).fetchone()
    if row is None:
        raise Problem(404, "RULE_NOT_FOUND", "此規則沒有可供審核的規則文件")
    if sha256(row["document"].encode()).hexdigest() != row["digest"]:
        raise ValueError("Rule document checksum mismatch")
    return json.loads(row["document"])


def mappings(db, rule_id):
    return {r["source_key"]: r["course_id"] for r in db.execute(
        "SELECT * FROM graduation_course_mappings WHERE rule_set_id=?", (rule_id,))}


def rules(db, rule_id):
    d = document(db, rule_id)
    ref = reference(db, "rule_sets", "id", rule_id, "rule_set_id")
    mapped = mappings(db, rule_id)
    required = d["credit_requirements"]["department_required"]["courses"]
    ids = [mapped["required:" + c["course_code"]] for c in required if "required:" + c["course_code"] in mapped]
    for course_id in ids:
        reference(db, "courses", "course_id", course_id, "course_id")
    return {"rule_set_id": rule_id, "version": rule_id.rsplit("-", 1)[-1],
            "department_id": ref["department_id"], "admission_year": ref["admission_year"],
            "sources": d["sources"], "total_credits_required": d["credit_requirements"]["minimum_total_credits"],
            "credit_requirements": d["credit_requirements"], "required_course_ids": ids,
            "unmapped_required_courses": [c for c in required if "required:" + c["course_code"] not in mapped],
            "general_education_requirements": d["credit_requirements"]["general_education"],
            "program_requirements": d["program_requirements"], "lecture_requirements": d["lecture_requirements"],
            "excluded_conditions": d["excluded_from_v1"], "verification_scope": d["scope"]["authority"]}


def programs(db, rule_id):
    reference(db, "rule_sets", "id", rule_id, "rule_set_id")
    try:
        d = document(db, rule_id)
    except Problem:
        # Synthetic catalog rules have no program requirements.
        return []
    mapped = mappings(db, rule_id)
    result = []
    for p in d["program_requirements"]["programs"]:
        keys = [f"program:{p['id']}:{i}" for i in range(len(p["courses"]))]
        ids = [mapped[k] for k in keys if k in mapped]
        for course_id in ids:
            reference(db, "courses", "course_id", course_id, "course_id")
        result.append({"program_id": p["id"], "name": p["name"], "rule_set_id": rule_id,
                       "list_year": d["scope"]["program_catalog_academic_year_roc"], "course_ids": ids,
                       "minimum_passed_courses": p["minimum_distinct_passed_courses"], "sources": d["sources"],
                       "data_status": "complete" if len(ids) == len(keys) else "needs_confirmation",
                       "unmapped_course_names": [name for name, key in zip(p["courses"], keys) if key not in mapped]})
    return result


def lectures(db):
    row = db.execute("SELECT * FROM lecture_progress WHERE user_id=?", (DEMO_USER_ID,)).fetchone()
    result = dict(row) if row else {"user_id": DEMO_USER_ID, "professional_count": None, "general_count": None, "updated_at": None}
    for key in ("professional_count", "general_count"):
        if result[key] is not None and (type(result[key]) is not int or result[key] < 0):
            raise ValueError("Invalid stored lecture count")
    return result


def make_check(key, name, required, actual, unit="credits", reason=None):
    status = "needs_confirmation" if actual is None else "met" if actual >= required else "not_met"
    remaining = None if actual is None else max(0, required - actual)
    return {"check_id": key, "name": name, "required_value": required, "actual_value": actual,
            "remaining_value": remaining, "unit": unit, "status": status,
            "message": reason or ("資料待確認" if actual is None else "已達第一版門檻" if remaining == 0 else f"尚缺 {remaining:g} {unit}")}


def progress(db):
    profile = db.execute("SELECT * FROM user_profiles WHERE user_id=?", (DEMO_USER_ID,)).fetchone()
    if profile is None:
        raise ValueError("Missing current user")
    rule_id = profile["rule_set_id"]
    result = {"user_id": DEMO_USER_ID, "rule_set_id": rule_id, "evaluated_at": timestamp(),
              "overall_status": "needs_confirmation", "checks": [], "credit_allocation": [],
              "missing_required_courses": [], "program_progress": [], "lecture_progress": lectures(db),
              "data_errors": [], "verification_scope": "第一版設定，非校方正式認證"}
    try:
        rule = rules(db, rule_id) if rule_id else None
    except Problem:
        rule = None
    if rule is None:
        result["data_errors"] = [{"code": "RULE_UNAVAILABLE", "message": "尚無適用且有完整文件的畢業規則"}]
        result["earned_credits"] = None
        return result
    d = document(db, rule_id)
    result["verification_scope"] = rule["verification_scope"]
    passed, seen, earned, groups = set(), set(), 0, defaultdict(float)
    unknown = False
    for enrollment in records(db, "enrollments"):
        if enrollment["enrollment_status"] != "finished" or enrollment["passed"] is not True:
            continue
        cid = enrollment["course_id"]
        if cid in seen:
            result["data_errors"].append({"code": "DUPLICATE_COURSE", "course_id": cid})
            unknown = True
            continue
        seen.add(cid)
        passed.add(cid)
        credits = enrollment["course_snapshot"]["credits"]
        if type(credits) not in (int, float) or credits < 0:
            raise ValueError("Invalid credit snapshot")
        earned += credits
        row = db.execute("SELECT credit_category FROM course_classifications WHERE course_id=? AND rule_set_id=?", (cid, rule_id)).fetchone()
        category = row[0] if row else None
        if category not in ("general_core", "general_domain", "general_diverse", "college_required", "department_required", "department_elective", "free_elective"):
            unknown = True
            result["data_errors"].append({"code": "CLASSIFICATION_UNKNOWN", "course_id": cid})
        else:
            groups[category] += credits
        result["credit_allocation"].append({"enrollment_id": enrollment["enrollment_id"], "course_id": cid,
                                            "credits": credits, "category": category, "allocations": []})
    # Allocate each earned credit once; professional elective overflow transfers to free elective.
    elective_left = d["credit_requirements"]["department_elective"]["minimum_credits"]
    diverse_left = d["credit_requirements"]["general_education"]["elective"]["diverse_courses"]["maximum_counted_credits"]
    totals = defaultdict(float)
    for row in result["credit_allocation"]:
        category, credits = row["category"], row["credits"]
        parts = []
        if category == "department_elective":
            count = min(elective_left, credits)
            elective_left -= count
            parts = [(category, count), ("free_elective", credits - count)]
        elif category == "general_diverse":
            count = min(diverse_left, credits)
            diverse_left -= count
            parts = [(category, count)]
        elif category is not None and category in groups:
            parts = [(category, credits)]
        for cat, amount in parts:
            if amount:
                row["allocations"].append({"category": cat, "credits": amount})
                totals[cat] += amount
    result["earned_credits"] = earned
    checks = [make_check("total_credits", "總學分", rule["total_credits_required"], earned)]
    cr = d["credit_requirements"]
    for key, needed in (("general_core", cr["general_education"]["core"]["required_credits"]),
                        ("general_domain", cr["general_education"]["elective"]["domain_courses"]["minimum_credits"]),
                        ("college_required", cr["college_core"]["required_credits"]),
                        ("department_required", cr["department_required"]["required_credits"]),
                        ("department_elective", cr["department_elective"]["minimum_credits"]),
                        ("free_elective", cr["free_elective"]["minimum_credits"])):
        checks.append(make_check(key, key, needed, None if unknown else totals[key]))
    checks.append(make_check("general_elective", "通識選修", cr["general_education"]["elective"]["minimum_credits"],
                             None if unknown else totals["general_domain"] + totals["general_diverse"]))
    domains, missing_domain = set(), unknown
    for allocation in result["credit_allocation"]:
        if allocation["category"] == "general_domain":
            row = db.execute("SELECT domain FROM graduation_course_domains WHERE rule_set_id=? AND course_id=?",
                             (rule_id, allocation["course_id"])).fetchone()
            if row is None or row[0] not in cr["general_education"]["elective"]["domain_courses"]["domains"]:
                missing_domain = True
                result["data_errors"].append({"code": "GENERAL_DOMAIN_UNKNOWN", "course_id": allocation["course_id"]})
            else:
                domains.add(row[0])
    checks.append(make_check("general_domains", "通識領域數", cr["general_education"]["elective"]["domain_courses"]["minimum_distinct_domains"],
                             None if missing_domain else len(domains), "domains"))
    mapped = mappings(db, rule_id)
    for i, requirement in enumerate(cr["general_education"]["core"]["requirements"]):
        cid = mapped.get(f"general_core:{i}")
        amount = next((e["credits"] for e in result["credit_allocation"] if e["course_id"] == cid), 0) if cid else None
        checks.append(make_check(f"general_core_{i}", requirement["name"], requirement["required_credits"], amount))
    for i, course in enumerate(cr["college_core"]["required_courses"]):
        cid = mapped.get(f"college:{i}")
        checks.append(make_check(f"college_course_{i}", course["name"], 1, int(cid in passed) if cid else None, "courses"))
    result["missing_required_courses"] = [cid for cid in rule["required_course_ids"] if cid not in passed]
    unresolved = rule["unmapped_required_courses"]
    if unresolved:
        result["data_errors"].append({"code": "REQUIRED_COURSES_UNMAPPED", "courses": unresolved})
    checks.append(make_check("required_courses", "指定必修", len(cr["department_required"]["courses"]),
                             None if unresolved else len(rule["required_course_ids"]) - len(result["missing_required_courses"]), "courses"))
    complete_programs, unresolved_programs = 0, False
    for p in programs(db, rule_id):
        actual = len(set(p["course_ids"]) & passed)
        status = "met" if actual >= p["minimum_passed_courses"] else "needs_confirmation" if p["data_status"] != "complete" else "not_met"
        complete_programs += status == "met"
        unresolved_programs |= status == "needs_confirmation"
        result["program_progress"].append({**p, "passed_courses": actual, "status": status})
    needed_programs = d["program_requirements"]["minimum_completed_programs"]
    checks.append(make_check("programs", "完成學程", needed_programs,
                             None if unresolved_programs and complete_programs < needed_programs else complete_programs, "programs"))
    for key in ("professional", "general"):
        checks.append(make_check("lecture_" + key, d["lecture_requirements"][key]["name"],
                                 d["lecture_requirements"][key]["minimum_count"], result["lecture_progress"][key + "_count"], "lectures"))
    result["checks"] = checks
    statuses = {c["status"] for c in checks}
    result["overall_status"] = "not_met" if "not_met" in statuses else "needs_confirmation" if "needs_confirmation" in statuses else "met"
    return result


MAPS = [
    {"map_id": "fucheng-campus", "campus_id": "fucheng", "campus_name": "府城校區", "view_name": "校區總覽",
     "image_url": "/maps/fucheng-campus.png", "alt_text": "臺南大學府城校區平面圖，顯示建築、出入口與設施", "sort_order": 1},
    {"map_id": "fucheng-rooms", "campus_id": "fucheng", "campus_name": "府城校區", "view_name": "教室配置",
     "image_url": "/maps/fucheng-rooms.png", "alt_text": "臺南大學府城校區各棟建築的教室與處室配置圖", "sort_order": 2},
    {"map_id": "rongyu-rooms", "campus_id": "rongyu", "campus_name": "榮譽校區", "view_name": "教學中心配置",
     "image_url": "/maps/rongyu-rooms.png", "alt_text": "臺南大學榮譽校區教學中心各棟建築與教室配置圖", "sort_order": 3},
]
