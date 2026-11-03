"""Idempotent, synthetic catalog fixtures; never import real school records implicitly."""

import json
from pathlib import Path


def init_catalog(db):
    # Upgrade the original /me ID-only semester table without replacing any rows.
    columns = {row["name"] for row in db.execute("PRAGMA table_info(semesters)")}
    for name, kind in (("academic_year", "INTEGER"), ("term", "TEXT"),
                       ("starts_on", "TEXT"), ("ends_on", "TEXT"), ("timezone", "TEXT")):
        if name not in columns:
            db.execute(f"ALTER TABLE semesters ADD COLUMN {name} {kind}")
    for statement in (
        "CREATE TABLE IF NOT EXISTS campuses (id TEXT PRIMARY KEY)",
        """CREATE TABLE IF NOT EXISTS courses (
            course_id TEXT PRIMARY KEY, course_code TEXT, name TEXT NOT NULL,
            credits REAL NOT NULL, offering_department_id TEXT REFERENCES departments(id),
            prerequisite_status TEXT NOT NULL, prerequisite_mode TEXT, prerequisite_source TEXT)""",
        """CREATE TABLE IF NOT EXISTS course_classifications (
            course_id TEXT REFERENCES courses(course_id), rule_set_id TEXT REFERENCES rule_sets(id),
            credit_category TEXT NOT NULL, PRIMARY KEY(course_id, rule_set_id))""",
        """CREATE TABLE IF NOT EXISTS course_prerequisites (
            course_id TEXT REFERENCES courses(course_id), prerequisite_id TEXT REFERENCES courses(course_id),
            PRIMARY KEY(course_id, prerequisite_id))""",
        """CREATE TABLE IF NOT EXISTS course_offerings (
            offering_id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses(course_id),
            semester_id TEXT NOT NULL REFERENCES semesters(id), section_name TEXT,
            schedule_status TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS class_meetings (
            meeting_id TEXT PRIMARY KEY, offering_id TEXT NOT NULL REFERENCES course_offerings(offering_id),
            weekday INTEGER NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
            campus_id TEXT REFERENCES campuses(id), location TEXT)""",
        """CREATE TABLE IF NOT EXISTS ui_courses (
            course_id TEXT PRIMARY KEY, course_code TEXT, name TEXT NOT NULL,
            credits REAL NOT NULL)""",
    ):
        db.execute(statement)
    for semester in (
        ("semester-113-1", 113, "1", "2024-09-01", "2025-01-31", "Asia/Taipei"),
        ("semester-113-2", 113, "2", "2025-02-01", "2025-06-30", "Asia/Taipei"),
        ("semester-114-2", 114, "2", "2026-02-01", "2026-06-30", "Asia/Taipei"),
        ("semester-115-1", 115, "1", "2026-09-01", "2027-01-31", "Asia/Taipei"),
        ("semester-115-2", 115, "2", "2027-02-01", "2027-06-30", "Asia/Taipei"),
    ):
        db.execute("""INSERT OR IGNORE INTO semesters
                   (id, academic_year, term, starts_on, ends_on, timezone) VALUES (?,?,?,?,?,?)""", semester)
        db.execute("""UPDATE semesters SET academic_year=?, term=?, starts_on=?, ends_on=?, timezone=?
                   WHERE id=? AND academic_year IS NULL AND term IS NULL
                   AND starts_on IS NULL AND ends_on IS NULL AND timezone IS NULL""",
                   (*semester[1:], semester[0]))
    db.execute("INSERT OR IGNORE INTO campuses VALUES ('campus-demo')")
    # Does not add mappings for (dept-csie, 114) or (dept-demo, 115), used by /me tests.
    db.execute("INSERT OR IGNORE INTO rule_sets VALUES ('rules-demo-114-v1', 'dept-demo', 114)")
    source = "測試來源：合成先修規定，非校方正式規定"
    db.executemany("INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?,?,?,?)", [
        ("course-demo-001", None, "資料結構", 3, "dept-csie", "unknown", None, None),
        ("course-demo-002", "DEMO-PROG", "程式設計", 3, "dept-csie", "none", None, source),
        ("course-demo-003", "DEMO-MATH", "離散數學", 2.5, "dept-csie", "none", None, source),
        ("course-demo-004", None, "進階資料分析", 3, "dept-csie", "known", "all", source),
        ("course-demo-005", "DEMO-ANY", "跨域專題", 0, "dept-demo", "known", "any", source),
        ("course-demo-006", None, "探索課程", 1, None, "unknown", None, None),
    ])
    catalog_path = Path(__file__).with_name("data") / "nutn_csie_113_course_catalog_v1.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    integrated_path = Path(__file__).parents[2] / "nutn_csie_115_graduation_rules.json"
    integrated = json.loads(integrated_path.read_text(encoding="utf-8"))
    integrated_courses = (
        integrated["credit_requirements"]["department_required"]["courses"]
        + integrated["course_catalog"]["department_electives"]
    )
    db.executemany(
        "INSERT OR IGNORE INTO ui_courses VALUES (?,?,?,?)",
        [
            (course_id, code, name, credits)
            for course_id, code, name, credits in catalog["courses"]
        ] + [
            (f"nutn-115-{course['course_code'].lower()}", course["course_code"],
             course["name"], course["credits"])
            for course in integrated_courses
        ] + [
            ("ui-calculus", "MATH101", "微積分（一）", 3),
            ("ui-english", "ENG102", "英文閱讀與寫作", 2),
            ("ui-psychology", "GE210", "普通心理學", 2),
            ("ui-seminar", None, "專題討論", 0),
        ],
    )
    db.executemany("INSERT OR IGNORE INTO course_classifications VALUES (?,?,?)", [
        ("course-demo-001", "rules-csie-115-v1", "department_required"),
        ("course-demo-001", "rules-demo-114-v1", "free_elective"),
        ("course-demo-002", "rules-csie-115-v1", "department_required"),
    ])
    db.executemany("INSERT OR IGNORE INTO course_prerequisites VALUES (?,?)", [
        (course, pre) for course in ("course-demo-004", "course-demo-005")
        for pre in ("course-demo-002", "course-demo-003")
    ])
    db.executemany("INSERT OR IGNORE INTO course_offerings VALUES (?,?,?,?,?)", [
        ("offering-demo-001", "course-demo-001", "semester-115-1", "A班", "scheduled"),
        ("offering-demo-002", "course-demo-001", "semester-115-1", "B班", "scheduled"),
        ("offering-demo-003", "course-demo-002", "semester-115-1", None, "unknown"),
        ("offering-demo-004", "course-demo-004", "semester-115-1", "測試班", "scheduled"),
    ])
    db.executemany("INSERT OR IGNORE INTO class_meetings VALUES (?,?,?,?,?,?,?)", [
        ("meeting-demo-002", "offering-demo-001", 3, "10:00", "12:00", "campus-demo", "測試教室 A"),
        ("meeting-demo-001", "offering-demo-001", 1, "09:00", "10:00", "campus-demo", "測試教室 A"),
        ("meeting-demo-003", "offering-demo-002", 2, "13:00", "15:00", None, None),
        ("meeting-demo-004", "offering-demo-004", 4, "09:00", "10:00", "campus-demo", None),
        ("meeting-demo-005", "offering-demo-004", 4, "13:00", "15:00", "campus-demo", "測試教室 B"),
    ])
