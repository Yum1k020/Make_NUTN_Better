import React, { useState } from "react";
import Icon from "./Icon.jsx";
import { DEMO_DATE, courses, weeklyClasses } from "../data/demo.js";
import {
  addDays,
  eventsOnDate,
  formatDate,
  minutes,
  overlaps,
  planStudySessions,
  weekStart,
  weekdayLabel,
} from "../lib/planner.js";

const periodOptions = [
  { id: "morning", label: "上午", start: "08:00", end: "12:00" },
  { id: "afternoon", label: "下午", start: "13:00", end: "18:00" },
  { id: "evening", label: "晚上", start: "18:00", end: "22:00" },
];

export default function StudyPlanner({
  personalEvents,
  studySessions,
  onUpdateSessions,
}) {
  const [courseId, setCourseId] = useState("data-structures");
  const [examDate, setExamDate] = useState("2026-09-24");
  const [hours, setHours] = useState(6);
  const [sessionHours, setSessionHours] = useState(2);
  const [allowedPeriods, setAllowedPeriods] = useState([
    "afternoon",
    "evening",
  ]);
  const [planMessage, setPlanMessage] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState(null);
  const [editError, setEditError] = useState("");
  const courseName =
    courses.find((course) => course.id === courseId)?.name || "課程";
  const scheduledHours =
    studySessions.reduce(
      (sum, item) => sum + minutes(item.end) - minutes(item.start),
      0,
    ) / 60;
  const upcomingClasses = eventsOnDate(
    DEMO_DATE,
    weeklyClasses,
    personalEvents,
  ).filter((item) => item.kind !== "study");
  const firstDay = weekStart(DEMO_DATE);
  const weekDates = Array.from({ length: 7 }, (_, index) =>
    addDays(firstDay, index),
  );
  const weekEvents = Object.fromEntries(
    weekDates.map((date) => [
      date,
      eventsOnDate(date, weeklyClasses, personalEvents),
    ]),
  );

  function togglePeriod(period) {
    setAllowedPeriods((current) =>
      current.includes(period)
        ? current.filter((item) => item !== period)
        : [...current, period],
    );
  }

  function generatePlan(event) {
    event.preventDefault();
    if (
      !Number.isFinite(Number(hours)) ||
      Number(hours) <= 0 ||
      Number(hours) > 100
    )
      return setPlanMessage("請輸入 0.5 至 100 小時的複習時數。");
    if (!allowedPeriods.length)
      return setPlanMessage("請至少選擇一個可安排時段。");
    if (examDate <= DEMO_DATE)
      return setPlanMessage("考試日期需晚於示範起始日 9 月 17 日。");
    const result = planStudySessions({
      startDate: DEMO_DATE,
      examDate,
      hours,
      sessionHours,
      allowedPeriods,
      courseName,
      weeklyClasses,
      personalEvents,
    });
    onUpdateSessions(result.sessions);
    setPlanMessage(
      result.remainingMinutes > 0
        ? `可安排時間不足，尚缺 ${result.remainingMinutes / 60} 小時。請增加可安排時段或調整複習需求。`
        : `已在考試前安排 ${result.scheduledMinutes / 60} 小時，請檢視後自行調整。`,
    );
    setEditingId(null);
  }

  function startEdit(session) {
    setEditingId(session.id);
    setDraft({ date: session.date, start: session.start, end: session.end });
    setEditError("");
  }

  function saveEdit(session) {
    if (!draft?.date || minutes(draft.end) <= minutes(draft.start))
      return setEditError("請輸入有效的日期與時間。");
    if (draft.date < DEMO_DATE || draft.date >= examDate)
      return setEditError("複習時段需在示範起始日與考試日期之間。");
    const occupied = eventsOnDate(
      draft.date,
      weeklyClasses,
      personalEvents,
      studySessions.filter((item) => item.id !== session.id),
    );
    const conflict = occupied.find((item) => overlaps(draft, item));
    if (conflict)
      return setEditError(`與「${conflict.title}」重疊，請調整時間。`);
    onUpdateSessions(
      studySessions.map((item) =>
        item.id === session.id ? { ...item, ...draft } : item,
      ),
    );
    setEditingId(null);
    setPlanMessage("已手動調整複習時段。");
  }

  function removeSession(sessionId) {
    onUpdateSessions(studySessions.filter((item) => item.id !== sessionId));
    setPlanMessage("已移除複習時段；需要時可重新產生計畫。");
  }

  return (
    <>
      <header className="page-header">
        <div>
          <div className="title-line">
            <h1>智慧學習</h1>
            <span className="demo-badge">示範資料</span>
          </div>
          <p>依課表與行程找出空閒時段，產生可檢視、可調整的複習建議。</p>
        </div>
        <button
          className="primary-button header-action"
          type="button"
          onClick={() => document.getElementById("study-course")?.focus()}
        >
          <Icon name="plus" size={20} />
          安排複習
        </button>
      </header>
      <div className="feature-grid study-grid">
        <div className="feature-left">
          <section className="panel form-panel">
            <div className="panel-heading">
              <h2>規劃考試複習</h2>
            </div>
            <form onSubmit={generatePlan} className="form-stack">
              <label className="field">
                <span>課程</span>
                <select
                  id="study-course"
                  value={courseId}
                  onChange={(event) => setCourseId(event.target.value)}
                >
                  {courses
                    .filter((course) =>
                      ["inProgress", "completed"].includes(course.status),
                    )
                    .map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.name}（{course.code}）
                      </option>
                    ))}
                </select>
              </label>
              <label className="field">
                <span>考試日期</span>
                <input
                  type="date"
                  min="2026-09-18"
                  value={examDate}
                  onChange={(event) => setExamDate(event.target.value)}
                />
              </label>
              <div className="form-row">
                <label className="field">
                  <span>所需複習時數</span>
                  <div className="input-suffix">
                    <input
                      type="number"
                      min="0.5"
                      max="100"
                      step="0.5"
                      value={hours}
                      onChange={(event) => setHours(event.target.value)}
                    />
                    <span>小時</span>
                  </div>
                </label>
                <label className="field">
                  <span>每次安排時長</span>
                  <select
                    value={sessionHours}
                    onChange={(event) =>
                      setSessionHours(Number(event.target.value))
                    }
                  >
                    <option value="1">1 小時</option>
                    <option value="1.5">1.5 小時</option>
                    <option value="2">2 小時</option>
                  </select>
                </label>
              </div>
              <fieldset className="period-field">
                <legend>可安排時段</legend>
                {periodOptions.map((period) => (
                  <label key={period.id}>
                    <input
                      type="checkbox"
                      checked={allowedPeriods.includes(period.id)}
                      onChange={() => togglePeriod(period.id)}
                    />
                    <span>
                      {period.label}{" "}
                      <small>
                        ({period.start}–{period.end})
                      </small>
                    </span>
                  </label>
                ))}
              </fieldset>
              <button className="primary-button full-width" type="submit">
                產生學習計畫
              </button>
            </form>
          </section>
          <section className="panel availability-panel">
            <div className="panel-heading">
              <h2>本週時間預覽</h2>
              <span className="subtle">
                {formatDate(firstDay)}–{formatDate(weekDates[6])}
              </span>
            </div>
            <div className="availability-week" aria-label="本週課程與個人行程">
              <div className="availability-week-corner">時段</div>
              {weekDates.map((date) => (
                <div
                  className={`availability-week-day${date === DEMO_DATE ? " is-today" : ""}${date < DEMO_DATE ? " is-past" : ""}`}
                  key={date}
                >
                  <strong>{weekdayLabel(date)}</strong>
                  <small>{date.slice(5).replace("-", "/")}</small>
                </div>
              ))}
              {periodOptions.map((period) => (
                <React.Fragment key={period.id}>
                  <div className="availability-week-period">
                    <strong>{period.label}</strong>
                    <small>{period.start}</small>
                  </div>
                  {weekDates.map((date) => {
                    const occupied = weekEvents[date].filter((item) =>
                      overlaps(
                        { date, start: period.start, end: period.end },
                        item,
                      ),
                    );
                    return (
                      <div
                        className={`availability-slot${date < DEMO_DATE ? " is-past" : ""}`}
                        key={`${period.id}-${date}`}
                        aria-label={`${formatDate(date)}${period.label}：${occupied.length ? occupied.map((item) => `${item.title} ${item.start} 至 ${item.end}`).join("、") : date < DEMO_DATE ? "已過" : "無固定行程"}`}
                      >
                        {occupied.length ? (
                          occupied.map((item) => (
                            <span
                              className={`availability-event tone-${item.tone || "blue"}`}
                              key={item.id}
                              title={`${item.title} ${item.start}–${item.end}`}
                            >
                              <strong>{item.title}</strong>
                              <small>{item.start}</small>
                            </span>
                          ))
                        ) : (
                          <span className="availability-free">
                            {date < DEMO_DATE ? "已過" : "無固定行程"}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
            <p className="availability-mobile-caption">
              {formatDate(DEMO_DATE)}課程與行程
            </p>
            <div className="availability-list">
              {upcomingClasses.map((item) => (
                <div key={item.id}>
                  <span
                    className={`availability-marker tone-${item.tone || "blue"}`}
                  />
                  <strong>
                    {item.start}–{item.end}
                  </strong>
                  <span>{item.title}</span>
                  <small>{item.location}</small>
                </div>
              ))}
            </div>
            <p className="helper-text">
              產生計畫會避開課程與個人行程；手動調整時也會檢查其他複習時段。
            </p>
          </section>
        </div>
        <div className="feature-right">
          <section className="panel plan-panel">
            <div className="panel-heading">
              <h2>建議學習計畫</h2>
              <span className="subtle">可逐項調整</span>
            </div>
            {planMessage && (
              <p
                className={`notice ${planMessage.includes("不足") || planMessage.includes("請") ? "notice-warning" : "notice-info"}`}
                role="status"
              >
                <Icon name="alert" size={18} />
                {planMessage}
              </p>
            )}
            {studySessions.length ? (
              <div className="study-session-list">
                {studySessions
                  .slice()
                  .sort((a, b) =>
                    `${a.date}${a.start}`.localeCompare(`${b.date}${b.start}`),
                  )
                  .map((session, index) => (
                    <div className="study-session" key={session.id}>
                      <span className="session-number">{index + 1}</span>
                      <div className="session-main">
                        <strong>
                          {formatDate(session.date)}（
                          {weekdayLabel(session.date)}）
                        </strong>
                        <span>
                          {session.start}–{session.end}・
                          {(minutes(session.end) - minutes(session.start)) / 60}{" "}
                          小時
                        </span>
                        {editingId === session.id && (
                          <div className="session-edit">
                            <label>
                              日期
                              <input
                                type="date"
                                value={draft.date}
                                onChange={(event) =>
                                  setDraft({
                                    ...draft,
                                    date: event.target.value,
                                  })
                                }
                              />
                            </label>
                            <label>
                              開始
                              <input
                                type="time"
                                value={draft.start}
                                onChange={(event) =>
                                  setDraft({
                                    ...draft,
                                    start: event.target.value,
                                  })
                                }
                              />
                            </label>
                            <label>
                              結束
                              <input
                                type="time"
                                value={draft.end}
                                onChange={(event) =>
                                  setDraft({
                                    ...draft,
                                    end: event.target.value,
                                  })
                                }
                              />
                            </label>
                            <button
                              type="button"
                              className="primary-button small"
                              onClick={() => saveEdit(session)}
                            >
                              儲存
                            </button>
                            <button
                              type="button"
                              className="secondary-button small"
                              onClick={() => setEditingId(null)}
                            >
                              取消
                            </button>
                            {editError && (
                              <p className="form-error" role="alert">
                                {editError}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                      <span className="session-label">{session.title}</span>
                      <div className="session-actions">
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => startEdit(session)}
                          aria-label={`調整第 ${index + 1} 個複習時段`}
                        >
                          <Icon name="edit" size={17} />
                        </button>
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => removeSession(session.id)}
                          aria-label={`移除第 ${index + 1} 個複習時段`}
                        >
                          <Icon name="trash" size={17} />
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="empty-state">
                尚未排定複習。填寫左側條件後產生建議時段。
              </p>
            )}
          </section>
          <section className="panel study-summary-panel">
            <div className="panel-heading">
              <h2>時數摘要</h2>
            </div>
            <div className="study-numbers">
              <div>
                <span>已安排</span>
                <strong>
                  {scheduledHours} <small>小時</small>
                </strong>
              </div>
              <div>
                <span>目標</span>
                <strong>
                  {hours || 0} <small>小時</small>
                </strong>
              </div>
            </div>
            <div className="progress-track">
              <span
                style={{
                  width: `${Math.min(100, hours > 0 ? (scheduledHours / Number(hours)) * 100 : 0)}%`,
                }}
              />
            </div>
            <p className="helper-text">
              這是根據示範課表計算的建議。請確認安排是否符合實際情況。
            </p>
          </section>
        </div>
      </div>
    </>
  );
}
