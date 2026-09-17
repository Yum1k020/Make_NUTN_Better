import React, { useState } from "react";
import Icon from "./Icon.jsx";
import { graduationRule, weeklyClasses } from "../data/demo.js";
import {
  addDays,
  eventsOnDate,
  formatDate,
  minutes,
  parseDate,
  weekdayLabel,
  weekStart,
} from "../lib/planner.js";

const HOURS = Array.from({ length: 14 }, (_, index) => index + 8);
const ROW_HEIGHT = 38;

function CalendarEvent({ event, onEditEvent, onOpenMap, onNavigate }) {
  const top = ((minutes(event.start) - 8 * 60) / 60) * ROW_HEIGHT;
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
  onSelectDate,
  onEditEvent,
  onOpenMap,
  onNavigate,
}) {
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
        {HOURS.map((hour) => (
          <span key={hour}>{String(hour).padStart(2, "0")}:00</span>
        ))}
      </div>
      {dates.map((date) => (
        <div
          className={`calendar-day ${date === selectedDate ? "selected" : ""}`}
          key={date}
        >
          {eventsOnDate(date, weeklyClasses, personalEvents, studySessions).map(
            (event) => (
              <CalendarEvent
                key={event.id}
                event={event}
                onEditEvent={onEditEvent}
                onOpenMap={onOpenMap}
                onNavigate={onNavigate}
              />
            ),
          )}
        </div>
      ))}
    </div>
  );
}

function DayTimeline({
  date,
  personalEvents,
  studySessions,
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
          {date === "2026-09-17"
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

export default function Dashboard({
  selectedDate,
  onSelectDate,
  tasks,
  personalEvents,
  studySessions,
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
  const upcoming = tasks
    .filter(
      (item) =>
        !item.completed &&
        item.date >= selectedDate &&
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
          <p>把每一個今天，累積成更好的未來。</p>
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
          <div className="calendar-toolbar">
            <div className="calendar-range">
              <div className="calendar-arrows">
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => onSelectDate(addDays(selectedDate, -7))}
                  aria-label="上一週"
                >
                  <Icon name="left" size={18} />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => onSelectDate(addDays(selectedDate, 7))}
                  aria-label="下一週"
                >
                  <Icon name="right" size={18} />
                </button>
              </div>
              <strong>
                {formatDate(start, true)} – {formatDate(dates[6])}
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
                {selectedDate === "2026-09-17"
                  ? "今日待辦"
                  : `${formatDate(selectedDate)}待辦`}
              </h2>
              <span className="subtle">
                {completedCount} / {todayTasks.length} 已完成
              </span>
            </div>
            {todayTasks.length ? (
              <ul className="task-list">
                {todayTasks.map((task) => (
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
                    <span className="task-time">{task.time}</span>
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
            ) : (
              <p className="empty-state">
                這天沒有待辦事項。
                <button type="button" onClick={() => onAdd("task")}>
                  新增一項
                </button>
              </p>
            )}
          </section>
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
            <h2>畢業進度</h2>
          </div>
          <strong>
            {graduationRule.earnedCredits} / {graduationRule.requiredCredits}{" "}
            <small>學分</small>
          </strong>
          <div className="progress-track">
            <span
              style={{
                width: `${(graduationRule.earnedCredits / graduationRule.requiredCredits) * 100}%`,
              }}
            />
          </div>
          <p>
            尚缺 {graduationRule.requiredCredits - graduationRule.earnedCredits}{" "}
            學分・缺少 1 門必修
          </p>
          <Icon name="right" size={18} className="summary-arrow" />
        </button>
      </div>
    </>
  );
}
