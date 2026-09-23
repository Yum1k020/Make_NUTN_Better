import React, { useEffect, useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import { findEventConflict, minutes } from "../lib/planner.js";
import { weeklyClasses } from "../data/demo.js";

export default function ItemDialog({
  initial,
  initialKind = "task",
  selectedDate,
  personalEvents,
  onClose,
  onSave,
  onDelete,
}) {
  const [kind, setKind] = useState(initialKind);
  const [form, setForm] = useState({
    title: initial?.title || "",
    date: initial?.date || selectedDate,
    time: initial?.time || "18:00",
    start: initial?.start || "16:00",
    end: initial?.end || "17:00",
    course: initial?.course || "",
    location: initial?.location || "",
    type: initial?.type || "待辦",
  });
  const [error, setError] = useState("");
  const conflict = useMemo(
    () =>
      kind === "event" &&
      form.date &&
      form.start &&
      form.end &&
      minutes(form.end) > minutes(form.start)
        ? findEventConflict(form, weeklyClasses, personalEvents, initial?.id)
        : null,
    [kind, form, personalEvents, initial?.id],
  );

  useEffect(() => {
    function handleKey(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setError("");
  }

  function submit(event) {
    event.preventDefault();
    if (!form.title.trim()) return setError("請輸入名稱。");
    if (!form.date) return setError("請選擇日期。");
    if (kind === "event" && minutes(form.end) <= minutes(form.start))
      return setError("結束時間需晚於開始時間。");
    if (conflict)
      return setError(`與「${conflict.title}」時間重疊，請調整時間。`);
    onSave({
      ...form,
      title: form.title.trim(),
      course: form.course.trim(),
      location: form.location.trim(),
      kind,
      id: initial?.id || `${kind}-${Date.now()}`,
    });
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
      >
        <div className="dialog-heading">
          <div>
            <h2 id="dialog-title">{initial ? "編輯事項" : "新增事項"}</h2>
            <p>把課業與生活安排在同一處。</p>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="關閉"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="segment full-width" role="group" aria-label="事項類型">
          <button
            type="button"
            className={kind === "task" ? "selected" : ""}
            onClick={() => setKind("task")}
            disabled={Boolean(initial)}
          >
            待辦事項
          </button>
          <button
            type="button"
            className={kind === "event" ? "selected" : ""}
            onClick={() => setKind("event")}
            disabled={Boolean(initial)}
          >
            私人行程
          </button>
        </div>
        <form onSubmit={submit} className="form-stack">
          <label className="field">
            <span>
              名稱 <em>*</em>
            </span>
            <input
              autoFocus
              value={form.title}
              onChange={(event) => update("title", event.target.value)}
              placeholder={
                kind === "task" ? "例如：繳交報告" : "例如：社團會議"
              }
            />
          </label>
          <label className="field">
            <span>
              日期 <em>*</em>
            </span>
            <input
              type="date"
              value={form.date}
              onChange={(event) => update("date", event.target.value)}
            />
          </label>
          {kind === "task" ? (
            <>
              <div className="form-row">
                <label className="field">
                  <span>時間</span>
                  <input
                    type="time"
                    value={form.time}
                    onChange={(event) => update("time", event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>類型</span>
                  <select
                    value={form.type}
                    onChange={(event) => update("type", event.target.value)}
                  >
                    <option>待辦</option>
                    <option>作業</option>
                    <option>報告</option>
                    <option>考試</option>
                    <option>複習</option>
                  </select>
                </label>
              </div>
              <label className="field">
                <span>相關課程</span>
                <input
                  value={form.course}
                  onChange={(event) => update("course", event.target.value)}
                  placeholder="選填"
                />
              </label>
            </>
          ) : (
            <>
              <div className="form-row">
                <label className="field">
                  <span>
                    開始時間 <em>*</em>
                  </span>
                  <input
                    type="time"
                    value={form.start}
                    onChange={(event) => update("start", event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>
                    結束時間 <em>*</em>
                  </span>
                  <input
                    type="time"
                    value={form.end}
                    onChange={(event) => update("end", event.target.value)}
                  />
                </label>
              </div>
              <label className="field">
                <span>地點</span>
                <input
                  value={form.location}
                  onChange={(event) => update("location", event.target.value)}
                  placeholder="選填"
                />
              </label>
            </>
          )}
          {conflict && (
            <p className="inline-alert" role="alert">
              <Icon name="alert" size={18} />
              與「{conflict.title}」時間重疊，請調整時間。
            </p>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="dialog-actions">
            {initial && (
              <button
                className="danger-button"
                type="button"
                onClick={() => onDelete(initial)}
              >
                <Icon name="trash" size={17} />
                刪除
              </button>
            )}
            <span className="action-spacer" />
            <button
              className="secondary-button"
              type="button"
              onClick={onClose}
            >
              取消
            </button>
            <button className="primary-button" type="submit">
              儲存事項
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
