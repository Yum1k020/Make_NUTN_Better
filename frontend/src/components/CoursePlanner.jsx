import React from "react";
import Icon from "./Icon.jsx";
import { courses } from "../data/demo.js";

export default function CoursePlanner({ plannedCourseIds, onToggleCourse }) {
  const enrolled = courses.filter((course) => course.status === "inProgress");
  const completed = courses.filter((course) => course.status === "completed");
  const candidates = courses.filter((course) => course.status === "available");
  const planned = candidates.filter((course) =>
    plannedCourseIds.includes(course.id),
  );
  const plannedCredits = planned.reduce(
    (sum, course) => sum + course.credits,
    0,
  );

  return (
    <>
      <header className="page-header">
        <div>
          <div className="title-line">
            <h1>修課規劃</h1>
            <span className="demo-badge">示範資料</span>
          </div>
          <p>檢視已修與規劃中的課程，提前留意先修條件和畢業缺項。</p>
        </div>
      </header>
      <div className="metric-strip">
        <div>
          <span>本學期修課</span>
          <strong>{enrolled.length} 門</strong>
          <small>
            {enrolled.reduce((sum, item) => sum + item.credits, 0)} 學分
          </small>
        </div>
        <div>
          <span>下學期規劃</span>
          <strong>{planned.length} 門</strong>
          <small>{plannedCredits} 學分</small>
        </div>
        <div>
          <span>尚缺必修</span>
          <strong>1 門</strong>
          <small>資料庫系統</small>
        </div>
      </div>
      <div className="feature-grid courses-grid">
        <div className="feature-left">
          <section className="panel">
            <div className="panel-heading">
              <h2>下學期選課建議</h2>
              <span className="subtle">依示範修課資料列出</span>
            </div>
            <div className="course-list">
              {candidates.map((course) => (
                <article className="course-row" key={course.id}>
                  <div className="course-icon">
                    <Icon name="book" size={20} />
                  </div>
                  <div className="course-main">
                    <div>
                      <h3>{course.name}</h3>
                      <span
                        className={`course-type ${course.type === "必修" ? "required" : ""}`}
                      >
                        {course.type}
                      </span>
                    </div>
                    <p>
                      {course.code}・{course.credits} 學分
                    </p>
                    <small>
                      先修：{course.prerequisite || "無"}
                      {course.prerequisite === "資料結構" && "（修習中）"}
                    </small>
                  </div>
                  <button
                    type="button"
                    className={
                      plannedCourseIds.includes(course.id)
                        ? "secondary-button small"
                        : "primary-button small"
                    }
                    onClick={() => onToggleCourse(course.id)}
                  >
                    {plannedCourseIds.includes(course.id)
                      ? "移出規劃"
                      : "加入規劃"}
                  </button>
                </article>
              ))}
            </div>
          </section>
          <section className="panel completed-panel">
            <div className="panel-heading">
              <h2>已修課程節錄</h2>
              <span className="subtle">示範資料</span>
            </div>
            <div className="completed-list">
              {completed.map((course) => (
                <div key={course.id}>
                  <strong>{course.name}</strong>
                  <span>
                    {course.code}・{course.credits} 學分
                  </span>
                </div>
              ))}
            </div>
            <p className="helper-text">
              此處僅列出部分示範課程；畢業進度使用 README 的 100 學分測試數值。
            </p>
          </section>
        </div>
        <div className="feature-right">
          <section className="panel">
            <div className="panel-heading">
              <h2>我的修課清單</h2>
              <span className="subtle">規劃不等於已取得學分</span>
            </div>
            {planned.length ? (
              <div className="planned-list">
                {planned.map((course) => (
                  <div key={course.id}>
                    <div>
                      <strong>{course.name}</strong>
                      <span>
                        {course.type}・{course.credits} 學分
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
                尚未加入下學期課程。從左側建議清單開始規劃。
              </p>
            )}
            <div className="panel-foot">
              <span>規劃學分</span>
              <strong>{plannedCredits} 學分</strong>
            </div>
          </section>
          <section className="panel soft-blue">
            <div className="panel-heading">
              <h2>先修提醒</h2>
              <Icon name="alert" size={19} />
            </div>
            <p>
              「資料庫系統」與「人工智慧導論」的先修課「資料結構」目前修習中。選課前請確認校方當學期規定與開課資訊。
            </p>
          </section>
        </div>
      </div>
    </>
  );
}
