import React from "react";
import Icon from "./Icon.jsx";
import { courses, graduationRule } from "../data/demo.js";

export default function GraduationProgress({
  plannedCourseIds,
  onNavigate,
  onToggleCourse,
}) {
  const {
    requiredCredits,
    earnedCredits,
    requiredLectures,
    completedLectures,
    missingRequiredCourses,
  } = graduationRule;
  const plannedCredits = courses
    .filter((course) => plannedCourseIds.includes(course.id))
    .reduce((sum, course) => sum + course.credits, 0);
  const databasePlanned = plannedCourseIds.includes("database");
  return (
    <>
      <header className="page-header">
        <div>
          <div className="title-line">
            <h1>畢業進度</h1>
            <span className="demo-badge">示範資料</span>
          </div>
          <p>將已取得的學分與示範畢業條件逐項比對，提早看見缺項。</p>
        </div>
      </header>
      <div className="graduation-hero">
        <div>
          <span className="grad-hero-icon">
            <Icon name="graduation" size={25} />
          </span>
          <h2>距離畢業，還有幾步？</h2>
          <p>目前已取得 {earnedCredits} 學分，仍需確認必修與講座條件。</p>
        </div>
        <div className="grad-score">
          <strong>
            {earnedCredits} <span>/ {requiredCredits}</span>
          </strong>
          <small>已取得學分</small>
        </div>
      </div>
      <div className="graduation-grid">
        <section className="panel requirement-panel">
          <div className="panel-heading">
            <h2>畢業條件</h2>
            <span className="subtle">示範規則</span>
          </div>
          <div className="requirement-row">
            <div className="requirement-title">
              <span className="requirement-icon blue">
                <Icon name="book" size={20} />
              </span>
              <div>
                <strong>總學分</strong>
                <small>至少 {requiredCredits} 學分</small>
              </div>
            </div>
            <div className="requirement-value">
              <strong>
                {earnedCredits} / {requiredCredits}
              </strong>
              <span>尚缺 {requiredCredits - earnedCredits} 學分</span>
            </div>
            <div className="progress-track">
              <span
                style={{ width: `${(earnedCredits / requiredCredits) * 100}%` }}
              />
            </div>
          </div>
          <div className="requirement-row">
            <div className="requirement-title">
              <span className="requirement-icon lavender">
                <Icon name="calendar" size={20} />
              </span>
              <div>
                <strong>講座場次</strong>
                <small>至少 {requiredLectures} 場</small>
              </div>
            </div>
            <div className="requirement-value">
              <strong>
                {completedLectures} / {requiredLectures}
              </strong>
              <span>尚缺 {requiredLectures - completedLectures} 場</span>
            </div>
            <div className="progress-track lavender">
              <span
                style={{
                  width: `${(completedLectures / requiredLectures) * 100}%`,
                }}
              />
            </div>
          </div>
          <div className="requirement-row">
            <div className="requirement-title">
              <span className="requirement-icon mint">
                <Icon name="list" size={20} />
              </span>
              <div>
                <strong>指定必修</strong>
                <small>依示範規則核對</small>
              </div>
            </div>
            <div className="requirement-value">
              <strong>尚缺 {missingRequiredCourses.length} 門</strong>
              <span>{missingRequiredCourses.join("、")}</span>
            </div>
          </div>
        </section>
        <div className="feature-right">
          <section className="panel missing-panel">
            <div className="panel-heading">
              <h2>待完成項目</h2>
            </div>
            <ul>
              <li>
                <Icon name="alert" size={18} />
                <span>
                  尚缺 <strong>{requiredCredits - earnedCredits} 學分</strong>
                </span>
              </li>
              <li>
                <Icon name="alert" size={18} />
                <span>
                  必修：<strong>{missingRequiredCourses[0]}</strong>
                  {databasePlanned && (
                    <small> 已加入規劃，完成後才能採計</small>
                  )}
                </span>
              </li>
              <li>
                <Icon name="alert" size={18} />
                <span>
                  講座：尚缺{" "}
                  <strong>{requiredLectures - completedLectures} 場</strong>
                </span>
              </li>
            </ul>
            {!databasePlanned && (
              <button
                type="button"
                className="secondary-button full-width"
                onClick={() => onToggleCourse("database")}
              >
                將資料庫系統加入修課規劃
              </button>
            )}
          </section>
          <section className="panel forecast-panel">
            <div className="panel-heading">
              <h2>修課模擬</h2>
            </div>
            <p>
              下學期已規劃 <strong>{plannedCredits} 學分</strong>
              。規劃中的學分尚未計入已取得學分。
            </p>
            <button
              type="button"
              className="text-link"
              onClick={() => onNavigate("courses")}
            >
              查看修課規劃 <Icon name="right" size={17} />
            </button>
          </section>
        </div>
      </div>
      <p className="graduation-disclaimer">
        本頁使用 README
        所列的測試條件；正式畢業資格仍應以學校、系所公告及實際修課紀錄為準。
      </p>
    </>
  );
}
