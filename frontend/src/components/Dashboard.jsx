import React, { useState } from "react";
import Icon from "./Icon.jsx";
import {
  addDays,
  eventsOnDate,
  formatDate,
  minutes,
  parseDate,
  weekdayLabel,
  weekStart,
} from "../lib/planner.js";
import { DEMO_DATE } from "../data/demo.js";
import { downloadCalendar } from "../lib/calendarExport.js";

const ROW_HEIGHT = 38;

function CalendarEvent({
  event,
  startHour,
  onEditEvent,
  onOpenMap,
  onNavigate,
}) {
  const top = ((minutes(event.start) - startHour * 60) / 60) * ROW_HEIGHT;
  const height =
    ((minutes(event.end) - minutes(event.start)) / 60) * ROW_HEIGHT;
  const content = (
    <>
      <strong>{event.title}</strong>
      <span>
        {event.start}–{event.end}
      </span>
      {height > 54 && <small>{event.location}</small>}
    </>
  );
  const className = `calendar-event tone-${event.tone || "blue"}`;
  const style = { top: `${top}px`, height: `${Math.max(height - 2, 29)}px` };
  if (event.kind === "personal")
    return (
      <button
        type="button"
        className={className}
        style={style}
        onClick={() => onEditEvent(event)}
        aria-label={`編輯${event.title}，${event.start} 至 ${event.end}`}
      >
        {content}
      </button>
    );
  if (event.kind === "study")
    return (
      <button
        type="button"
        className={className}
        style={style}
        onClick={() => onNavigate("study")}
        aria-label={`查看${event.title}學習計畫`}
      >
        {content}
      </button>
    );
  return (
    <button
      type="button"
      className={className}
      style={style}
      onClick={() => onOpenMap(event.campus, event.location)}
      aria-label={`查看${event.title}上課地點：${event.location}`}
    >
      {content}
    </button>
  );
}

function WeekCalendar({
  selectedDate,
  dates,
  personalEvents,
  studySessions,
  weeklyClasses,
  onSelectDate,
  onEditEvent,
  onOpenMap,
  onNavigate,
}) {
  const days = dates.map((date) =>
    eventsOnDate(date, weeklyClasses, personalEvents, studySessions),
  );
  const startHour = days
    .flat()
    .reduce(
      (hour, event) => Math.min(hour, Math.floor(minutes(event.start) / 60)),
      8,
    );
  const endHour = days
    .flat()
    .reduce(
      (hour, event) => Math.max(hour, Math.ceil(minutes(event.end) / 60)),
      22,
    );
  const hours = Array.from(
    { length: endHour - startHour },
    (_, index) => startHour + index,
  );
  return (
    <div className="week-calendar" aria-label="本週課表與行程">
      <div className="calendar-corner" />
      {dates.map((date) => (
        <button
          type="button"
          key={date}
          className={`calendar-day-head ${date === selectedDate ? "selected" : ""}`}
          onClick={() => onSelectDate(date)}
        >
          <span>
            {parseDate(date).getMonth() + 1}/{parseDate(date).getDate()}
          </span>
          <strong>{weekdayLabel(date)}</strong>
        </button>
      ))}
      <div className="calendar-hours">
        {hours.map((hour) => (
          <span key={hour}>{String(hour).padStart(2, "0")}:00</span>
        ))}
      </div>
      {dates.map((date, index) => (
        <div
          className={`calendar-day ${date === selectedDate ? "selected" : ""}`}
          key={date}
        >
          {days[index].map((event) => (
            <CalendarEvent
              key={event.id}
              event={event}
              startHour={startHour}
              onEditEvent={onEditEvent}
              onOpenMap={onOpenMap}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function DayTimeline({
  date,
  personalEvents,
  studySessions,
  weeklyClasses,
  onEditEvent,
  onOpenMap,
  onNavigate,
}) {
  const events = eventsOnDate(
    date,
    weeklyClasses,
    personalEvents,
    studySessions,
  );
  return (
    <div className="day-timeline">
      <div className="panel-heading">
        <h2>
          {date === DEMO_DATE
            ? "今日課程與行程"
            : `${formatDate(date)}課程與行程`}
        </h2>
        <span className="subtle">{events.length} 項行程</span>
      </div>
      {events.length ? (
        <div className="timeline-list">
          {events.map((event) => {
            const content = (
              <>
                <div className="timeline-time">
                  <strong>{event.start}</strong>
                  <span>{event.end}</span>
                </div>
                <span className={`timeline-dot tone-${event.tone || "blue"}`} />
                <div
                  className={`timeline-content tone-${event.tone || "blue"}`}
                >
                  <strong>{event.title}</strong>
                  <span>{event.location || "自行安排"}</span>
                  <em>
                    {event.kind === "class"
                      ? "課程"
                      : event.kind === "study"
                        ? "複習"
                        : "個人"}
                  </em>
                </div>
              </>
            );
            return (
              <button
                type="button"
                className="timeline-row"
                key={event.id}
                onClick={() =>
                  event.kind === "study"
                    ? onNavigate("study")
                    : event.kind === "class"
                      ? onOpenMap(event.campus, event.location)
                      : onEditEvent(event)
                }
                aria-label={
                  event.kind === "class"
                    ? `查看${event.title}上課地點：${event.location}`
                    : undefined
                }
              >
                {content}
              </button>
            );
          })}
        </div>
      ) : (
        <p className="empty-state">
          這天沒有安排，選擇其他日期或新增私人行程。
        </p>
      )}
    </div>
  );
}

function TaskList({ tasks, showDeadline = false, onToggleTask, onEditTask }) {
  return (
    <ul className="task-list">
      {tasks.map((task) => (
        <li key={task.id}>
          <label className="task-check">
            <input
              type="checkbox"
              checked={task.completed}
              onChange={() => onToggleTask(task.id)}
            />
            <span className="custom-check">
              <Icon name="check" size={13} />
            </span>
            <span className={task.completed ? "completed" : ""}>
              {task.title}
            </span>
          </label>
          <span className="task-time">
            {showDeadline && task.date ? `${formatDate(task.date)} ` : ""}
            {task.time}
          </span>
          <button
            type="button"
            className="row-edit"
            onClick={() => onEditTask(task)}
            aria-label={`編輯${task.title}`}
          >
            <Icon name="edit" size={16} />
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function Dashboard({
  selectedDate,
  onSelectDate,
  tasks,
  personalEvents,
  studySessions,
  weeklyClasses,
  graduationProgress,
  academicYear,
  onToggleTask,
  onEditTask,
  onEditEvent,
  onAdd,
  onOpenMap,
  onNavigate,
}) {
  const [calendarMode, setCalendarMode] = useState("week");
  const start = weekStart(selectedDate);
  const dates = Array.from({ length: 7 }, (_, index) => addDays(start, index));
  const todayTasks = tasks
    .filter((item) => item.date === selectedDate)
    .sort((a, b) => a.time.localeCompare(b.time));
  const completedCount = todayTasks.filter((item) => item.completed).length;
  const overdue = tasks.filter(
    (item) => !item.completed && item.date && item.date < DEMO_DATE,
  );
  const undated = tasks.filter((item) => !item.completed && !item.date);
  const upcoming = tasks
    .filter(
      (item) =>
        !item.completed &&
        item.date >= DEMO_DATE &&
        ["作業", "報告", "考試"].includes(item.type),
    )
    .sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`))
    .slice(0, 4);
  const weekSessions = studySessions.filter(
    (item) => item.date >= start && item.date <= dates[6],
  );

  return (
    <>
      <header className="page-header">
        <div>
          <div className="title-line">
            <h1>今日／本週</h1>
            <span className="header-date">
              {formatDate(selectedDate)} {weekdayLabel(selectedDate)}
            </span>
            <span className="demo-badge">示範資料</span>
          </div>
        </div>
        <div className="header-actions">
          <button
            className="secondary-button header-action"
            type="button"
            onClick={() => onOpenMap("fucheng")}
          >
            <Icon name="map" size={18} />
            校區地圖
          </button>
          <button
            className="primary-button header-action"
            type="button"
            onClick={() => onAdd("task")}
          >
            <Icon name="plus" size={20} />
            新增事項
          </button>
        </div>
      </header>
      <div className="dashboard-grid">
        <section className="panel calendar-panel">
          <div className="calendar-jump">
            <label>
              <span className="sr-only">跳到指定日期</span>
              <input
                type="date"
                value={selectedDate}
                onChange={(event) => {
                  if (event.target.value) onSelectDate(event.target.value);
                }}
              />
            </label>
            <button
              className="secondary-button"
              type="button"
              onClick={() => onSelectDate(DEMO_DATE)}
            >
              回到今天
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                downloadCalendar({
                  dates,
                  weeklyClasses,
                  personalEvents,
                  studySessions,
                })
              }
            >
              匯出本週行事曆
            </button>
          </div>
          <div className="calendar-toolbar">
            <div className="calendar-range">
              <div className="calendar-arrows">
                <button
                  type="button"
                  className="icon-button"
                  onClick={() =>
                    onSelectDate(
                      addDays(selectedDate, calendarMode === "week" ? -7 : -1),
                    )
                  }
                  aria-label={calendarMode === "week" ? "上一週" : "前一天"}
                >
                  <Icon name="left" size={18} />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() =>
                    onSelectDate(
                      addDays(selectedDate, calendarMode === "week" ? 7 : 1),
                    )
                  }
                  aria-label={calendarMode === "week" ? "下一週" : "後一天"}
                >
                  <Icon name="right" size={18} />
                </button>
              </div>
              <strong>
                {calendarMode === "week"
                  ? `${formatDate(start, true)} – ${formatDate(dates[6])}`
                  : formatDate(selectedDate, true)}
              </strong>
            </div>
            <div className="segment" role="group" aria-label="課表檢視模式">
              <button
                type="button"
                className={calendarMode === "week" ? "selected" : ""}
                onClick={() => setCalendarMode("week")}
              >
                週檢視
              </button>
              <button
                type="button"
                className={calendarMode === "day" ? "selected" : ""}
                onClick={() => setCalendarMode("day")}
              >
                日檢視
              </button>
            </div>
          </div>
          <div className="mobile-week-picker" aria-label="選擇日期">
            {dates.map((date) => (
              <button
                type="button"
                className={date === selectedDate ? "selected" : ""}
                key={date}
                onClick={() => onSelectDate(date)}
              >
                <span>{weekdayLabel(date)}</span>
                <strong>
                  {parseDate(date).getMonth() + 1}/{parseDate(date).getDate()}
                </strong>
              </button>
            ))}
          </div>
          <div className="desktop-calendar">
            {calendarMode === "week" ? (
              <WeekCalendar
                selectedDate={selectedDate}
                dates={dates}
                personalEvents={personalEvents}
                studySessions={studySessions}
                weeklyClasses={weeklyClasses}
                onSelectDate={onSelectDate}
                onEditEvent={onEditEvent}
                onOpenMap={onOpenMap}
                onNavigate={onNavigate}
              />
            ) : (
              <DayTimeline
                date={selectedDate}
                personalEvents={personalEvents}
                studySessions={studySessions}
                weeklyClasses={weeklyClasses}
                onEditEvent={onEditEvent}
                onOpenMap={onOpenMap}
                onNavigate={onNavigate}
              />
            )}
          </div>
          <div className="mobile-timeline">
            <DayTimeline
              date={selectedDate}
              personalEvents={personalEvents}
              studySessions={studySessions}
              weeklyClasses={weeklyClasses}
              onEditEvent={onEditEvent}
              onOpenMap={onOpenMap}
              onNavigate={onNavigate}
            />
          </div>
        </section>
        <div className="dashboard-side">
          <section className="panel task-panel">
            <div className="panel-heading">
              <h2>
                {selectedDate === DEMO_DATE
                  ? "今日待辦"
                  : `${formatDate(selectedDate)}待辦`}
              </h2>
              <span className="subtle">
                {completedCount} / {todayTasks.length} 已完成
              </span>
            </div>
            {todayTasks.length ? (
              <TaskList
                tasks={todayTasks}
                onToggleTask={onToggleTask}
                onEditTask={onEditTask}
              />
            ) : (
              <p className="empty-state">
                這天沒有待辦事項。
                <button type="button" onClick={() => onAdd("task")}>
                  新增一項
                </button>
              </p>
            )}
          </section>
          {(overdue.length > 0 || undated.length > 0) && (
            <section className="panel task-panel backlog-panel">
              <div className="panel-heading">
                <h2>尚待處理</h2>
              </div>
              {overdue.length > 0 && (
                <details open>
                  <summary>已逾期（{overdue.length}）</summary>
                  <TaskList
                    tasks={overdue}
                    showDeadline
                    onToggleTask={onToggleTask}
                    onEditTask={onEditTask}
                  />
                </details>
              )}
              {undated.length > 0 && (
                <details open>
                  <summary>未設定截止日（{undated.length}）</summary>
                  <TaskList
                    tasks={undated}
                    onToggleTask={onToggleTask}
                    onEditTask={onEditTask}
                  />
                </details>
              )}
            </section>
          )}
          <section className="panel deadlines-panel">
            <div className="panel-heading">
              <h2>近期截止事項</h2>
              <button
                className="text-link"
                type="button"
                onClick={() => onAdd("task")}
              >
                新增待辦 <Icon name="plus" size={16} />
              </button>
            </div>
            {upcoming.length ? (
              <ul className="deadline-list">
                {upcoming.map((task) => (
                  <li key={task.id}>
                    <span className={`deadline-mark type-${task.type}`}></span>
                    <button type="button" onClick={() => onEditTask(task)}>
                      <strong>{task.title}</strong>
                      <small>{task.course || task.type}</small>
                    </button>
                    <span className="deadline-date">
                      {formatDate(task.date)}
                      <small>{task.type}</small>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-state">目前沒有未完成的截止事項。</p>
            )}
          </section>
        </div>
      </div>
      <div className="summary-grid">
        <button
          type="button"
          className="summary-card study-summary"
          onClick={() => onNavigate("study")}
        >
          <div>
            <span className="summary-icon">
              <Icon name="book" size={20} />
            </span>
            <h2>本週學習計畫</h2>
          </div>
          <strong>
            {weekSessions.length} <small>個複習時段</small>
          </strong>
          <p>
            {weekSessions.length
              ? `已安排 ${weekSessions.reduce((sum, item) => sum + minutes(item.end) - minutes(item.start), 0) / 60} 小時，點選查看與調整`
              : "尚未安排複習，點選開始規劃"}
          </p>
          <Icon name="right" size={18} className="summary-arrow" />
        </button>
        <button
          type="button"
          className="summary-card graduation-summary"
          onClick={() => onNavigate("graduation")}
        >
          <div>
            <span className="summary-icon">
              <Icon name="graduation" size={21} />
            </span>
            <h2>{academicYear} 學年度畢業進度</h2>
          </div>
          <strong>
            {graduationProgress?.earned_credits ?? "待確認"} /{" "}
            {graduationProgress?.checks?.find(
              (check) => check.check_id === "total_credits",
            )?.required_value ?? 133}{" "}
            <small>學分</small>
          </strong>
          <div className="progress-track">
            <span
              style={{
                width: `${Math.min(
                  100,
                  ((graduationProgress?.earned_credits || 0) /
                    (graduationProgress?.checks?.find(
                      (check) => check.check_id === "total_credits",
                    )?.required_value || 133)) *
                    100,
                )}%`,
              }}
            />
          </div>
          <p>
            {graduationProgress
              ? `後端規則：${graduationProgress.rule_set_id}・${
                  graduationProgress.overall_status === "met"
                    ? "已達標"
                    : graduationProgress.overall_status === "not_met"
                      ? "未達標"
                      : "待確認"
                }`
              : "正在從後端讀取畢業規則與已修紀錄"}
          </p>
          <Icon name="right" size={18} className="summary-arrow" />
        </button>
      </div>
    </>
  );
}
