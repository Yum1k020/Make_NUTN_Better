import React, { useMemo, useState } from "react";
import Icon from "./Icon.jsx";

function RequirementOverview({ rule }) {
  const requirements = rule?.credit_requirements;
  if (!requirements) return null;
  return (
    <section className="curriculum-overview" aria-label="115 學年度畢業門檻">
      <div>
        <span>最低畢業學分</span>
        <strong>{requirements.minimum_total_credits}</strong>
        <small>學分</small>
      </div>
      <div>
        <span>通識課程</span>
        <strong>{requirements.general_education.minimum_total_credits}</strong>
        <small>核心與選修分別檢核</small>
      </div>
      <div>
        <span>系專業必選修</span>
        <strong>
          {requirements.department_required.required_credits +
            requirements.department_elective.minimum_credits}
        </strong>
        <small>
          必修 {requirements.department_required.required_credits}＋選修至少{" "}
          {requirements.department_elective.minimum_credits}
        </small>
      </div>
      <div>
        <span>領域學程</span>
        <strong>{rule.program_requirements.minimum_completed_programs}</strong>
        <small>至少完成的學程數</small>
      </div>
    </section>
  );
}

function ProgramCard({ program, plannedCourseNames }) {
  const names = program.unmapped_course_names || [];
  const selectedCount = names.filter((name) =>
    plannedCourseNames.has(name),
  ).length;
  return (
    <article className="program-card">
      <div className="program-card-head">
        <div>
          <h3>{program.name}</h3>
          <span>已通過且已認列 3 門</span>
        </div>
        <strong>
          {Math.min(selectedCount, program.minimum_passed_courses)} /{" "}
          {program.minimum_passed_courses}
        </strong>
      </div>
      <div className="program-course-tags">
        {names.map((name) => (
          <span
            className={plannedCourseNames.has(name) ? "selected" : ""}
            key={name}
          >
            {name}
          </span>
        ))}
      </div>
      <small>
        {program.data_status === "complete" ? "對照完成" : "正式課程 ID 待確認"}
      </small>
    </article>
  );
}

export default function CoursePlanner({
  plannedCourseIds,
  onToggleCourse,
  academic,
}) {
  const [catalog, setCatalog] = useState("department_required");
  const [query, setQuery] = useState("");
  const courses = academic.courses || [];
  const rule = academic.rule;
  const programs = academic.programs || [];
  const enrollments = academic.enrollments || [];
  const plannedIdSet = useMemo(
    () => new Set(plannedCourseIds),
    [plannedCourseIds],
  );
  const planned = useMemo(
    () => courses.filter((course) => plannedIdSet.has(course.id)),
    [courses, plannedIdSet],
  );
  const plannedCourseNames = useMemo(
    () => new Set(planned.map((course) => course.name)),
    [planned],
  );
  const normalizedQuery = query.trim().toLocaleLowerCase("zh-TW");
  const visibleCourses = courses.filter(
    (course) =>
      course.category === catalog &&
      (!normalizedQuery ||
        `${course.code} ${course.name} ${course.recommendedTerm}`
          .toLocaleLowerCase("zh-TW")
          .includes(normalizedQuery)),
  );
  const plannedCredits = planned.reduce(
    (sum, course) => sum + course.credits,
    0,
  );
  const requiredCount = courses.filter(
    (course) => course.category === "department_required",
  ).length;
  const electiveCount = courses.filter(
    (course) => course.category === "department_elective",
  ).length;

  return (
    <>
      <header className="page-header curriculum-header">
        <div>
          <div className="title-line">
            <h1>115 學年度修課規劃</h1>
            <span className="academic-year-badge">
              {rule?.rule_set_id || "規則載入中"}
            </span>
          </div>
          <p>課程資料、規劃清單與已修紀錄都由 Flask／SQLite 提供。</p>
        </div>
      </header>

      <div className="curriculum-source-banner">
        <Icon name="check" size={20} />
        <div>
          <strong>後端整合規格：{rule?.backend_status || "讀取中"}</strong>
          <p>規劃課程不等於已取得或已認列學分。</p>
        </div>
      </div>

      <RequirementOverview rule={rule} />

      <div className="feature-grid courses-grid curriculum-grid">
        <div className="feature-left">
          <section className="panel course-catalog-panel">
            <div className="course-catalog-heading">
              <div>
                <h2>115 後端課程目錄</h2>
                <span>
                  必修 {requiredCount} 門；專業選修 {electiveCount} 門
                </span>
              </div>
              <label className="course-search">
                <span className="sr-only">搜尋課程名稱或代碼</span>
                <Icon name="search" size={17} />
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="搜尋課名、代碼或年級"
                />
              </label>
            </div>
            <div className="catalog-tabs" role="tablist" aria-label="課程類別">
              {[
                ["department_required", "專業必修", requiredCount],
                ["department_elective", "專業選修", electiveCount],
              ].map(([id, label, count]) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={catalog === id}
                  className={catalog === id ? "selected" : ""}
                  onClick={() => setCatalog(id)}
                  key={id}
                >
                  {label}
                  <span>{count}</span>
                </button>
              ))}
            </div>
            <div className="course-list" role="tabpanel">
              {visibleCourses.map((course) => {
                const selected = plannedIdSet.has(course.id);
                return (
                  <article className="course-row" key={course.id}>
                    <div className="course-icon">
                      <Icon name="book" size={20} />
                    </div>
                    <div className="course-main">
                      <div>
                        <h3>{course.name}</h3>
                        <span
                          className={`course-type ${catalog === "department_required" ? "required" : ""}`}
                        >
                          {course.type}
                        </span>
                      </div>
                      <p>
                        {course.code}・{course.credits} 學分・
                        {course.recommendedTerm}
                      </p>
                      <small>來源：{rule?.rule_set_id}</small>
                    </div>
                    <button
                      type="button"
                      className={
                        selected
                          ? "secondary-button small"
                          : "primary-button small"
                      }
                      aria-pressed={selected}
                      onClick={() => onToggleCourse(course.id)}
                    >
                      {selected ? "移出規劃" : "加入規劃"}
                    </button>
                  </article>
                );
              })}
              {!visibleCourses.length && (
                <p className="empty-state">後端沒有符合條件的 115 課程。</p>
              )}
            </div>
          </section>

          <section className="panel program-panel">
            <div className="panel-heading">
              <div>
                <h2>115 專業領域學程</h2>
                <span className="subtle">課程完成與證書推定分開顯示</span>
              </div>
            </div>
            <div className="program-grid">
              {programs.map((program) => (
                <ProgramCard
                  program={program}
                  plannedCourseNames={plannedCourseNames}
                  key={program.program_id}
                />
              ))}
            </div>
          </section>
        </div>

        <div className="feature-right curriculum-side">
          <section className="panel planned-panel">
            <div className="panel-heading">
              <h2>我的 115 修課清單</h2>
              <span className="subtle">後端 SQLite</span>
            </div>
            {planned.length ? (
              <div className="planned-list">
                {planned.map((course) => (
                  <div key={course.id}>
                    <div>
                      <strong>{course.name}</strong>
                      <span>
                        {course.code}・{course.type}・{course.credits} 學分
                      </span>
                    </div>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => onToggleCourse(course.id)}
                      aria-label={`移除${course.name}`}
                    >
                      <Icon name="close" size={17} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">尚未加入課程。</p>
            )}
            <div className="panel-foot">
              <span>{planned.length} 門課</span>
              <strong>{plannedCredits} 規劃學分</strong>
            </div>
          </section>

          <section className="panel requirement-detail-panel">
            <div className="panel-heading">
              <h2>後端已修紀錄</h2>
              <span className="academic-year-mini">115</span>
            </div>
            {enrollments.length ? (
              <ul className="requirement-list">
                {enrollments.map((enrollment) => (
                  <li key={enrollment.enrollment_id}>
                    {enrollment.course_snapshot.name}・
                    {enrollment.enrollment_status === "finished"
                      ? "已完成"
                      : "修習中"}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-state">目前沒有後端已修紀錄。</p>
            )}
          </section>

          <section className="panel source-panel">
            <div className="panel-heading">
              <h2>資料界線</h2>
            </div>
            <p>{rule?.verification_scope}</p>
            <p>
              共同認列範圍尚未提供時，已修課程會保留為待確認，不會自動算入畢業學分。
            </p>
          </section>
        </div>
      </div>
    </>
  );
}
