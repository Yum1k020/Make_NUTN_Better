import React, { useEffect, useState, useRef } from "react";
import {
  GRADUATION_STATUS,
  CHECK_NAMES,
  DATA_MESSAGES,
  displayValue,
  graduationRequest,
  workflowMessage,
} from "../lib/graduation.js";
import "./GraduationProgress.css";
import {
  GraduationMemory,
  VALIDITY_MESSAGES,
} from "../lib/graduationMemory.js";

export default function GraduationProgress({ onNavigate }) {
  const [progress, setProgress] = useState(null);
  const [planned, setPlanned] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [error, setError] = useState("");
  const [plannedError, setPlannedError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const [memoryReason, setMemoryReason] = useState("");
  const [fixtureMode, setFixtureMode] = useState(false);
  const memory = useRef(null);
  useEffect(() => {
    const store = new GraduationMemory({
      request: (path, options = {}) =>
        graduationRequest(path, {
          ...options,
          cache: "no-store",
          signal: AbortSignal.timeout(
            path === "graduation-explanation" ? 60000 : 5000,
          ),
        }),
      update: (state) => {
        setWorkflow(state.workflow);
        setMemoryReason(state.reason);
        setBusy(state.busy);
        if (state.progress) setProgress(state.progress);
      },
    });
    memory.current = store;
    let seconds = 0;
    const timer = setInterval(() => {
      store.tick();
      if (++seconds % 15 === 0) void store.verify();
    }, 1000);
    const focus = () => void store.verify();
    const visibility = () => {
      if (document.visibilityState === "visible") focus();
      else setWorkflow(null);
    };
    window.addEventListener("focus", focus);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      store.dispose();
      clearInterval(timer);
      window.removeEventListener("focus", focus);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    memory.current?.clear();
    graduationRequest("graduation-context", {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((context) => {
        if (!controller.signal.aborted)
          setFixtureMode(context.execution_mode === "synthetic_fixture");
      })
      .catch(() => {
        if (!controller.signal.aborted) setFixtureMode(false);
      });
    setLoading(true);
    setProgress(null);
    setPlanned(null);
    setWorkflow(null);
    setError("");
    setPlannedError("");
    graduationRequest("graduation-progress", { signal: controller.signal })
      .then(setProgress)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    graduationRequest("planned-courses", { signal: controller.signal })
      .then(setPlanned)
      .catch(() => {
        if (!controller.signal.aborted)
          setPlannedError("修課規劃暫時無法讀取，不能當作零門。");
      });
    return () => controller.abort();
  }, [reload]);

  function generateExplanation() {
    void memory.current?.generate();
  }

  return (
    <div className="graduation-live">
      <header className="page-header">
        <div>
          <h1>畢業進度</h1>
          <p>
            依目前使用者紀錄與啟用規則，逐項確認已完成、未完成與待確認事項。
          </p>
        </div>
        <button
          className="secondary-button"
          disabled={loading || busy}
          onClick={() => setReload((n) => n + 1)}
        >
          重新整理
        </button>
      </header>
      <button
        className="text-link"
        disabled={busy || loading}
        onClick={() => void memory.current?.reset()}
      >
        開始新的說明工作階段
      </button>
      {loading && <p role="status">正在讀取畢業進度…</p>}
      {error && (
        <p role="alert" className="graduation-notice">
          {error}
        </p>
      )}
      {progress && (
        <>
          <section className="graduation-hero">
            <div>
              <h2>{GRADUATION_STATUS[progress.overall_status]}</h2>
              <p>已取得 {displayValue(progress.earned_credits)} 學分</p>
            </div>
            <div>
              <strong>目前適用規則</strong>
              <p>{progress.rule_set_id || "尚未選定"}</p>
              <small>{progress.verification_scope}</small>
            </div>
          </section>
          <section className="panel graduation-checks">
            <h2>畢業條件</h2>
            {!progress.checks.length && (
              <p>尚無可檢查的規則，請確認系所、入學年度及規則資料。</p>
            )}
            {progress.checks.map((check) => (
              <article key={check.check_id} className="graduation-check">
                <div>
                  <strong>{CHECK_NAMES[check.check_id] || check.name}</strong>
                  <small>{GRADUATION_STATUS[check.status]}</small>
                </div>
                <p>
                  已採計 {displayValue(check.actual_value)} ／ 要求{" "}
                  {displayValue(check.required_value)}
                  <br />
                  尚缺 {displayValue(check.remaining_value)}（
                  {{
                    credits: "學分",
                    courses: "門",
                    lectures: "場",
                    programs: "個學程",
                    domains: "個領域",
                  }[check.unit] || check.unit}
                  ）
                </p>
                <small>
                  依據：{progress.rule_set_id}:{check.check_id}
                </small>
              </article>
            ))}
          </section>
          {!!progress.data_errors.length && (
            <section className="panel graduation-section">
              <h2>資料待確認</h2>
              <ul>
                {progress.data_errors.map((item, i) => (
                  <li key={i}>
                    {DATA_MESSAGES[item.code] ||
                      item.message ||
                      "有資料需要確認，請檢查修課與認列紀錄。"}
                  </li>
                ))}
              </ul>
            </section>
          )}
          <section className="panel graduation-section">
            <h2>規劃中的課程</h2>
            <p>
              {plannedError ||
                (planned === null
                  ? "正在讀取修課規劃…"
                  : `後端紀錄有 ${planned.length} 門規劃課程。`)}
              規劃中或修習中課程不計入已取得學分。
            </p>
            <p>修課規劃頁目前另使用本機示範資料；此處以後端紀錄為準。</p>
            <button className="text-link" onClick={() => onNavigate("courses")}>
              查看修課規劃
            </button>
          </section>
          <section className="panel graduation-section" aria-live="polite">
            <h2>缺項說明與下一步</h2>
            <p>
              {fixtureMode
                ? "合成測試模式：使用虛構資料與固定測試回應，不連線 Gemini，不傳送學業資料。"
                : "按下後會將去識別的規則版本、學分／場次及達標狀態送至 Google Gemini，不傳姓名、學號或成績明細。"}
            </p>
            <button
              className="primary-button"
              disabled={busy || loading || !progress.checks.length}
              onClick={generateExplanation}
            >
              {busy
                ? "正在產生並檢查說明…"
                : fixtureMode
                  ? "產生合成測試說明"
                  : "產生說明"}
            </button>
            <p>
              說明最多保留 5 分鐘；每 15
              秒及回到頁面時重查來源。重新整理或新工作階段會清除說明。
            </p>
            {memoryReason && (
              <p role="status">{VALIDITY_MESSAGES[memoryReason]}</p>
            )}
            {workflow && (
              <>
                <p role="status">{workflowMessage(workflow)}</p>
                <p>
                  產生時間：
                  {new Date(workflow.validity.issued_at_ms).toLocaleString()}
                  ；到期時間：
                  {new Date(workflow.validity.expires_at_ms).toLocaleString()}
                </p>
                <ul className="graduation-explanations">
                  {workflow.explanation.map((item) => (
                    <li key={item.check_id}>
                      <strong>{item.name}</strong>
                      <p>{item.text}</p>
                      <p>{item.next_step}</p>
                      <small>依據：{item.source_ids.join("、")}</small>
                    </li>
                  ))}
                </ul>
                <details>
                  <summary>本次處理紀錄</summary>
                  <p>識別碼：{workflow.run_id}</p>
                  <p>
                    停止原因：{workflow.stop_reason}；模型呼叫：
                    {workflow.model_calls} 次
                  </p>
                  <ol>
                    {workflow.attempts.map((attempt) => (
                      <li key={attempt.label}>
                        版本 {attempt.label}：
                        {attempt.passed ? "通過" : attempt.errors.join("、")}
                      </li>
                    ))}
                  </ol>
                </details>
              </>
            )}
          </section>
          <p className="graduation-disclaimer">
            本頁呈現本次啟用的專案規則檢查結果，正式畢業資格以校方審核為準。待確認資料不視為零或已達標。
          </p>
        </>
      )}
    </div>
  );
}
