import React, { useEffect, useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import { findEventConflict, minutes } from "../lib/planner.js";

function moveTime(start, end) {
  return `${start.slice(0, 10)} ${start.slice(11, 16)}–${end.slice(11, 16)}`;
}

export default function ItemDialog({
  initial,
  initialKind = "task",
  selectedDate,
  personalEvents,
  weeklyClasses,
  onClose,
  onSave,
  onDelete,
}) {
  const [kind, setKind] = useState(initialKind);
  const [form, setForm] = useState({
    title: initial?.title || "",
    date: initial?.date ?? selectedDate,
    time: initial?.time ?? "18:00",
    start: initial?.start || "16:00",
    end: initial?.end || "17:00",
    course: initial?.course || "",
    location: initial?.location || "",
    type: initial?.type || "待辦",
  });
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [preview, setPreview] = useState(null);
  const conflict = useMemo(
    () =>
      kind === "event" &&
      form.date &&
      form.start &&
      form.end &&
      minutes(form.end) > minutes(form.start)
        ? findEventConflict(form, weeklyClasses, personalEvents, initial?.id)
        : null,
    [kind, form, personalEvents, weeklyClasses, initial?.id],
  );

  useEffect(() => {
    function handleKey(event) {
      if (event.key === "Escape" && !isSaving) onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isSaving, onClose]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setError("");
    setPreview(null);
  }

  function changeKind(nextKind) {
    setKind(nextKind);
    setError("");
    setPreview(null);
  }

  async function submit(event) {
    event.preventDefault();
    if (isSaving) return;
    if (!form.title.trim()) return setError("請輸入名稱。");
    if (kind === "event") {
      if (!form.date) return setError("請選擇日期。");
      if (!form.start || !form.end || minutes(form.end) <= minutes(form.start))
        return setError("請輸入起訖時間，結束時間需晚於開始時間。");
    }
    if (conflict)
      return setError(`與「${conflict.title}」時間重疊，請調整時間。`);
    setIsSaving(true);
    setError("");
    try {
      const result = await onSave(
        {
          ...form,
          title: form.title.trim(),
          course: form.course.trim(),
          location: form.location.trim(),
          kind,
          id: initial?.id || `${kind}-${Date.now()}`,
        },
        preview?.preview_token,
      );
      setPreview(result || null);
    } catch (saveError) {
      if (saveError?.status === 409) setPreview(null);
      setError(
        saveError instanceof Error ? saveError.message : String(saveError),
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function remove() {
    if (
      typeof globalThis.confirm === "function" &&
      !globalThis.confirm(`確定要刪除「${initial?.title || "這筆資料"}」嗎？`)
    ) {
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      await onDelete(initial);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : String(deleteError),
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSaving) onClose();
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
            disabled={isSaving}
            aria-label="關閉"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="segment full-width" role="group" aria-label="事項類型">
          <button
            type="button"
            className={kind === "task" ? "selected" : ""}
            onClick={() => changeKind("task")}
            disabled={Boolean(initial) || isSaving}
          >
            待辦事項
          </button>
          <button
            type="button"
            className={kind === "event" ? "selected" : ""}
            onClick={() => changeKind("event")}
            disabled={Boolean(initial) || isSaving}
          >
            私人行程
          </button>
        </div>
        <form onSubmit={submit} className="form-stack" aria-busy={isSaving}>
          <label className="field">
            <span>
              名稱 <em>*</em>
            </span>
            <input
              autoFocus
              disabled={isSaving}
              value={form.title}
              onChange={(event) => update("title", event.target.value)}
              placeholder={
                kind === "task" ? "例如：繳交報告" : "例如：社團會議"
              }
            />
          </label>
          <label className="field">
            <span>
              {kind === "event" ? (
                <>
                  日期 <em>*</em>
                </>
              ) : (
                "截止日期（選填）"
              )}
            </span>
            <input
              type="date"
              disabled={isSaving}
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
                    disabled={isSaving || !form.date}
                    value={form.time}
                    onChange={(event) => update("time", event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>類型</span>
                  <select
                    disabled={isSaving}
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
                  disabled={isSaving}
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
                    disabled={isSaving}
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
                    disabled={isSaving}
                    value={form.end}
                    onChange={(event) => update("end", event.target.value)}
                  />
                </label>
              </div>
              <label className="field">
                <span>地點</span>
                <input
                  disabled={isSaving}
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
          {preview && (
            <section className="study-adjustment-preview" aria-live="polite">
              <strong>複習時段調整預覽</strong>
              <p>確認後會一併儲存這筆行程與以下調整。</p>
              <ul>
                {preview.moves.map((move) => (
                  <li key={move.session_id}>
                    <strong>{move.title}</strong>
                    <span>原 {moveTime(move.from_start, move.from_end)}</span>
                    <span>改為 {moveTime(move.to_start, move.to_end)}</span>
                  </li>
                ))}
              </ul>
            </section>
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
                onClick={remove}
                disabled={isSaving}
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
              disabled={isSaving}
            >
              取消
            </button>
            <button
              className="primary-button"
              type="submit"
              disabled={isSaving}
            >
              {isSaving ? "處理中" : preview ? "確認行程與重排" : "儲存事項"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
