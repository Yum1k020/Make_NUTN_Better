import React, { useState } from "react";
import { graduationRequest } from "../lib/graduation.js";

const fields = [
  ["professional_count", "professional", "專業講座"],
  ["general_count", "general", "一般講座"],
];

export default function LectureProgressForm({
  lectureProgress,
  requirements,
  onSaved,
}) {
  const [counts, setCounts] = useState(() =>
    Object.fromEntries(
      fields.map(([key]) => [key, lectureProgress[key] ?? ""]),
    ),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save(event) {
    event.preventDefault();
    if (saving) return;
    const values = Object.fromEntries(
      fields.map(([key]) => [
        key,
        counts[key] === "" ? null : Number(counts[key]),
      ]),
    );
    if (
      Object.values(values).some(
        (value) =>
          value !== null && (!Number.isSafeInteger(value) || value < 0),
      )
    ) {
      setError("場次請輸入非負整數，尚待確認可留白。");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await graduationRequest("lecture-progress", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      onSaved();
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel graduation-section">
      <h2>更新已通過的講座場次</h2>
      <p>場次未確認時可留白。填入 0 表示已確認目前沒有通過的場次。</p>
      <form className="form-stack" onSubmit={save} aria-busy={saving}>
        <div className="form-row">
          {fields.map(([key, category, label]) => (
            <label className="field" key={key}>
              <span>
                {label}
                {requirements?.[category]?.minimum_count != null &&
                  `（需 ${requirements[category].minimum_count} 場）`}
              </span>
              <input
                type="number"
                min="0"
                step="1"
                placeholder="待確認"
                value={counts[key]}
                disabled={saving}
                onChange={(event) => {
                  setCounts((current) => ({
                    ...current,
                    [key]: event.target.value,
                  }));
                  setError("");
                }}
              />
            </label>
          ))}
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div>
          <button type="submit" className="primary-button" disabled={saving}>
            {saving ? "儲存中" : "儲存場次"}
          </button>
        </div>
      </form>
    </section>
  );
}
