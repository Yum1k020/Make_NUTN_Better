import React, { useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import {
  curriculumMeta113,
  graduationRequirements113,
  legacySyllabusHighlights,
  professionalElectives113,
  programNamesForCourse113,
  programs113,
  requiredCourses113,
  sourceDocuments113,
} from "../data/curriculum113.js";

const CATALOGS = {
  required: { label: "專業必修", courses: requiredCourses113 },
  elective: { label: "專業選修", courses: professionalElectives113 },
};

function RequirementOverview() {
  const rules = graduationRequirements113;
  return (
    <section className="curriculum-overview" aria-label="113 學年度畢業門檻">
      <div>
        <span>最低畢業學分</span>
        <strong>{rules.minimumTotalCredits}</strong>
        <small>學分</small>
      </div>
      <div>
        <span>通識課程</span>
        <strong>{rules.generalEducationCredits}</strong>
        <small>核心 10＋領域／多元 18</small>
      </div>
      <div>
        <span>系專業必選修</span>
        <strong>{rules.minimumDepartmentCredits}</strong>
        <small>必修 70＋選修至少 12</small>
      </div>
      <div>
        <span>領域學程</span>
        <strong>{rules.minimumCompletedPrograms}</strong>
        <small>至少 2 個；每個通過 3 門</small>
      </div>
    </section>
  );
}

function ProgramCard({ program, plannedCourseNames }) {
  const selectedCount = program.courses.filter((name) =>
    plannedCourseNames.has(name),
  ).length;
  return (
    <article className="program-card">
      <div className="program-card-head">
        <div>
          <h3>{program.name}</h3>
          <span>{program.requirement}</span>
        </div>
        <strong>{Math.min(selectedCount, 3)} / 3</strong>
      </div>
      <div className="program-course-tags">
        {program.courses.map((name) => (
          <span
            className={plannedCourseNames.has(name) ? "selected" : ""}
            key={name}
          >
            {name}
          </span>
        ))}
      </div>
    </article>
  );
}

export default function CoursePlanner({ plannedCourseIds, onToggleCourse }) {
  const [catalog, setCatalog] = useState("required");
  const [query, setQuery] = useState("");
  const plannedIdSet = useMemo(
    () => new Set(plannedCourseIds),
    [plannedCourseIds],
  );
  const allCourses = useMemo(
    () => [...requiredCourses113, ...professionalElectives113],
    [],
  );
  const planned = useMemo(
    () => allCourses.filter((course) => plannedIdSet.has(course.id)),
    [allCourses, plannedIdSet],
  );
  const plannedCourseNames = useMemo(
    () => new Set(planned.map((course) => course.name)),
    [planned],
  );
  const normalizedQuery = query.trim().toLocaleLowerCase("zh-TW");
  const visibleCourses = CATALOGS[catalog].courses.filter((course) =>
    normalizedQuery
      ? `${course.code} ${course.name} ${course.recommendedTerm}`
          .toLocaleLowerCase("zh-TW")
          .includes(normalizedQuery)
      : true,
  );
  const plannedCredits = planned.reduce(
    (sum, course) => sum + course.credits,
    0,
  );

  return (
    <>
      <header className="page-header curriculum-header">
        <div>
          <div className="title-line">
            <h1>113 學年度修課規劃</h1>
            <span className="academic-year-badge">資料基準：113 學年度</span>
          </div>
          <p>
            {curriculumMeta113.institution} {curriculumMeta113.department}
            {curriculumMeta113.degree}課程規劃；可搜尋課程並加入個人清單。
          </p>
        </div>
      </header>

      <div className="curriculum-source-banner">
        <Icon name="check" size={20} />
        <div>
          <strong>已依兩份 113 學年度文件整理</strong>
          <p>{curriculumMeta113.verificationNote}</p>
        </div>
      </div>

      <RequirementOverview />

      <div className="feature-grid courses-grid curriculum-grid">
        <div className="feature-left">
          <section className="panel course-catalog-panel">
            <div className="course-catalog-heading">
              <div>
                <h2>113 課程目錄</h2>
                <span>必修 25 門；專業選修表列 35 門</span>
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
              {Object.entries(CATALOGS).map(([id, item]) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={catalog === id}
                  className={catalog === id ? "selected" : ""}
                  onClick={() => setCatalog(id)}
                  key={id}
                >
                  {item.label}
                  <span>{item.courses.length}</span>
                </button>
              ))}
            </div>
            <div className="course-list" role="tabpanel">
              {visibleCourses.map((course) => {
                const programNames = programNamesForCourse113(course.name);
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
                          className={`course-type ${catalog === "required" ? "required" : ""}`}
                        >
                          {course.type}
                        </span>
                      </div>
                      <p>
                        {course.code}・{course.credits} 學分・
                        {course.recommendedTerm}
                      </p>
                      <small>
                        {programNames.length
                          ? `可採計：${programNames.join("、")}學程`
                          : "依 113 學年度課程規劃表列示"}
                      </small>
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
                <p className="empty-state">找不到符合條件的 113 課程。</p>
              )}
            </div>
          </section>

          <section className="panel program-panel">
            <div className="panel-heading">
              <div>
                <h2>113 專業領域學程</h2>
                <span className="subtle">
                  每個學程通過 3 門；畢業至少取得 2 個學程證書
                </span>
              </div>
            </div>
            <div className="program-grid">
              {programs113.map((program) => (
                <ProgramCard
                  program={program}
                  plannedCourseNames={plannedCourseNames}
                  key={program.id}
                />
              ))}
            </div>
            <p className="helper-text program-helper">
              課程地圖中的部分學程課名未列於本份專業選修表；實際選課前仍需確認當學期開課與認列方式。
            </p>
          </section>

          <section className="panel syllabus-reference-panel">
            <div className="panel-heading">
              <div>
                <h2>課程內容參考</h2>
                <span className="subtle">舊版課程大綱；不是 113 畢業規定</span>
              </div>
            </div>
            <div className="syllabus-highlight-grid">
              {legacySyllabusHighlights.map((item) => (
                <article key={item.course}>
                  <strong>{item.course}</strong>
                  <p>{item.topics}</p>
                </article>
              ))}
            </div>
          </section>
        </div>

        <div className="feature-right curriculum-side">
          <section className="panel planned-panel">
            <div className="panel-heading">
              <h2>我的 113 修課清單</h2>
              <span className="subtle">規劃不等於已取得學分</span>
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
              <p className="empty-state">
                尚未加入課程。從左側 113 課程目錄開始規劃。
              </p>
            )}
            <div className="panel-foot">
              <span>{planned.length} 門課</span>
              <strong>{plannedCredits} 規劃學分</strong>
            </div>
          </section>

          <section className="panel requirement-detail-panel">
            <div className="panel-heading">
              <h2>畢業條件摘要</h2>
              <span className="academic-year-mini">113</span>
            </div>
            <dl className="requirement-list">
              <div>
                <dt>院核心必修</dt>
                <dd>4 學分</dd>
              </div>
              <div>
                <dt>自由選修</dt>
                <dd>至少 20 學分</dd>
              </div>
              <div>
                <dt>相關學術講座</dt>
                <dd>10 場＋心得報告</dd>
              </div>
              <div>
                <dt>通識領域</dt>
                <dd>4 大領域至少修 3 領域</dd>
              </div>
            </dl>
          </section>

          <section className="panel source-panel">
            <div className="panel-heading">
              <h2>資料來源與界線</h2>
            </div>
            <div className="source-document-list">
              {sourceDocuments113.map((source) => (
                <article key={source.title}>
                  <div>
                    <strong>{source.title}</strong>
                    <span>{source.status}</span>
                  </div>
                  <p>{source.usage}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
