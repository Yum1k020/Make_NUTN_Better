import { useEffect, useState } from "react";
import Icon from "./Icon.jsx";
import {
  loadStudyPreference,
  saveStudyPreference,
  withdrawStudyPreference,
} from "../lib/studyMemoryClient.js";

const preferenceOptions = [
  { id: "morning", label: "上午（08:00–12:00）" },
  { id: "afternoon", label: "下午（13:00–18:00）" },
  { id: "evening", label: "晚上（18:00–22:00）" },
];

const preferenceLabels = Object.fromEntries(
  preferenceOptions.map((option) => [option.id, option.label]),
);

function formatExpiry(value) {
  if (!value) return "未設定";
  return new Intl.DateTimeFormat("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function StudyMemoryPanel({ onApplyPreference }) {
  const [memoryState, setMemoryState] = useState({
    record: null,
    latestVersion: 0,
  });
  const [draftValue, setDraftValue] = useState("afternoon");
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("正在讀取已確認的學習偏好。");

  useEffect(() => {
    let active = true;
    loadStudyPreference()
      .then((result) => {
        if (!active) return;
        setMemoryState(result);
        if (result.record) {
          setDraftValue(result.record.value);
          onApplyPreference(result.record.value);
          setMessage(
            `已從新 session 讀回 ${preferenceLabels[result.record.value]}。`,
          );
        } else {
          setMessage("目前沒有有效的長期偏好；本次條件不會自動保存。");
        }
        setStatus("ready");
      })
      .catch((error) => {
        if (!active) return;
        setStatus("error");
        setMessage(error instanceof Error ? error.message : String(error));
      });
    return () => {
      active = false;
    };
  }, [onApplyPreference]);

  async function savePreference() {
    setStatus("saving");
    setMessage("正在保存已確認偏好。");
    try {
      const result = await saveStudyPreference({
        value: draftValue,
        expectedVersion: memoryState.latestVersion,
      });
      setMemoryState(result);
      onApplyPreference(result.record.value);
      setStatus("ready");
      setMessage(
        `${result.replayed ? "已確認先前操作" : "已保存"} ${preferenceLabels[result.record.value]}，版本 v${result.record.version}。`,
      );
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function withdrawPreference() {
    setStatus("saving");
    setMessage("正在撤回長期偏好。");
    try {
      const result = await withdrawStudyPreference({
        expectedVersion: memoryState.latestVersion,
      });
      setMemoryState(result);
      setStatus("ready");
      setMessage("已撤回；之後的新 session 不會再讀到這筆偏好。");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  const isBusy = status === "loading" || status === "saving";
  const record = memoryState.record;

  return (
    <section className="panel memory-panel">
      <div className="panel-heading">
        <div>
          <h2>學習偏好記憶</h2>
          <p className="subtle">只保存你明確確認的常用時段，30 天後到期。</p>
        </div>
        <span className={`memory-state is-${record ? "active" : "empty"}`}>
          {record ? `v${record.version} 有效` : "未保存"}
        </span>
      </div>
      <div className="memory-controls">
        <label className="field">
          <span>常用學習時段</span>
          <select
            value={draftValue}
            onChange={(event) => setDraftValue(event.target.value)}
            disabled={isBusy}
          >
            {preferenceOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <div className="memory-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={savePreference}
            disabled={isBusy}
          >
            <Icon name="check" size={17} />
            確認並保存
          </button>
          <button
            type="button"
            className="danger-button"
            onClick={withdrawPreference}
            disabled={isBusy || !record}
          >
            <Icon name="trash" size={17} />
            撤回記憶
          </button>
        </div>
      </div>
      {record && (
        <dl className="memory-evidence">
          <div>
            <dt>來源</dt>
            <dd>使用者於智慧學習頁確認</dd>
          </div>
          <div>
            <dt>Owner</dt>
            <dd>{record.owner}</dd>
          </div>
          <div>
            <dt>到期</dt>
            <dd>{formatExpiry(record.expiresAt)}</dd>
          </div>
          <div>
            <dt>ID</dt>
            <dd>{record.id}</dd>
          </div>
        </dl>
      )}
      <p
        className={`memory-message${status === "error" ? " is-error" : ""}`}
        role={status === "error" ? "alert" : "status"}
      >
        {message}
      </p>
      <p className="memory-boundary">
        讀回偏好只會預選時段；仍會重新檢查課表、私人行程與本次輸入，不代表同意建立任何預約。
      </p>
    </section>
  );
}
