import React, { useCallback, useState } from "react";
import Icon from "./Icon.jsx";
import StudyMemoryPanel from "./StudyMemoryPanel.jsx";
import { DEFAULT_EXAM_DATE, DEMO_DATE } from "../data/demo.js";
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
import {
  requestStudyAgentPlan,
  requestStudyContextComparison,
  studyPlansMatch,
} from "../lib/studyAgentClient.js";

const periodOptions = [
  { id: "morning", label: "上午", start: "08:00", end: "12:00" },
  { id: "afternoon", label: "下午", start: "13:00", end: "18:00" },
  { id: "evening", label: "晚上", start: "18:00", end: "22:00" },
];

const workflowStatusLabels = {
  completed: "通過",
  rejected: "拒絕",
  failed: "失敗",
};

function formatStageEvidence(stage) {
  const evidence = stage.evidence || {};
  if (stage.id === "validate-request") {
    return stage.status === "completed"
      ? `${evidence.fieldCount} 個欄位・${evidence.personalEventCount} 筆私人行程`
      : `${evidence.issueCount} 項問題・下游 ${evidence.downstreamCalls} 次`;
  }
  if (stage.id === "build-plan") {
    return stage.status === "completed"
      ? `${evidence.sessionCount} 個時段・已安排 ${evidence.scheduledMinutes} 分鐘・尚缺 ${evidence.remainingMinutes} 分鐘`
      : `${evidence.errorSource}・嘗試 ${evidence.attemptCount} 次`;
  }
  if (stage.id === "verify-plan") {
    return stage.status === "completed"
      ? `檢查 ${evidence.checkedSessionCount} 個時段・${evidence.issueCount} 項問題`
      : `${evidence.issueCount} 項問題・下游 ${evidence.downstreamCalls} 次`;
  }
  if (stage.id === "model-tool-call") {
    return `${evidence.provider}・${evidence.model}・tool ${evidence.tool}`;
  }
  if (stage.id === "validate-tool-args") {
    return `${evidence.issueCount} 項問題・${evidence.confirmationRequired ? "需要人工確認" : "唯讀預覽免確認"}`;
  }
  if (stage.id === "execute-tool") {
    return `${evidence.sessionCount} 個時段・已安排 ${evidence.scheduledMinutes} 分鐘・尚缺 ${evidence.remainingMinutes} 分鐘`;
  }
  if (stage.id === "return-tool-result") {
    return `${evidence.functionResponseCount} 筆工具結果・${evidence.citationCount} 個來源`;
  }
  if (stage.id === "delegate-study-load-expert") {
    return stage.status === "completed"
      ? `${evidence.role}・tool ${evidence.toolCalls} 次・${evidence.assessment}`
      : `${evidence.role}・tool ${evidence.toolCalls} 次`;
  }
  if (stage.id === "integrate-expert-review") {
    return `${evidence.returnedBy} → ${evidence.caller}・${evidence.recommendationCount} 項建議`;
  }
  return stage.status === "completed"
    ? `${evidence.provider}・${evidence.citationCount} 個來源・嘗試 ${evidence.attemptCount} 次`
    : `${evidence.errorSource}・嘗試 ${evidence.attemptCount} 次`;
}

function WorkflowTrace({ workflow }) {
  if (!workflow) return null;
  return (
    <div className="workflow-trace" aria-label="Prompt chaining 執行軌跡">
      <div className="workflow-trace-heading">
        <strong>Prompt chaining 執行軌跡</strong>
        <span className={`workflow-state is-${workflow.status}`}>
          {workflow.status === "completed" ? "完成" : "已停止"}
        </span>
      </div>
      <ol>
        {workflow.stages.map((stage) => (
          <li className={`is-${stage.status}`} key={stage.id}>
            <span className="workflow-step-marker" aria-hidden="true" />
            <div>
              <strong>{stage.label}</strong>
              <small>{formatStageEvidence(stage)}</small>
            </div>
            <span className="workflow-step-status">
              {workflowStatusLabels[stage.status] || stage.status}
            </span>
          </li>
        ))}
      </ol>
      {workflow.stopReason && (
        <p className="workflow-stop-reason">
          停止原因：<code>{workflow.stopReason}</code>
        </p>
      )}
      <small className="workflow-run-id">
        workflow：{workflow.name}・version：{workflow.version}
        {workflow.runId ? `・run ID：${workflow.runId}` : ""}
      </small>
    </div>
  );
}

function MultiAgentTrace({ multiAgent }) {
  if (!multiAgent) return null;
  const expert = multiAgent.expertReview;
  return (
    <div className="workflow-trace" aria-label="多代理協作軌跡">
      <div className="workflow-trace-heading">
        <strong>Multi-Agent Route A</strong>
        <span className="workflow-state is-completed">2 個角色</span>
      </div>
      <ol>
        {multiAgent.roles.map((role) => (
          <li className="is-completed" key={role.id}>
            <span className="workflow-step-marker" aria-hidden="true" />
            <div>
              <strong>{role.label}</strong>
              <small>
                {role.id === "study-coordinator"
                  ? `保留主控制權・tool：${role.tools.join("、")}`
                  : "受限專家・無 Tool／無資料庫寫入權限"}
              </small>
            </div>
            <span className="workflow-step-status">完成</span>
          </li>
        ))}
      </ol>
      {expert && (
        <div className="agent-result">
          <div className="agent-result-tags">
            <span>專家評估：{expert.assessment}</span>
            <span>最小共享 context</span>
          </div>
          <p>{expert.summary}</p>
          {expert.recommendations.length > 0 && (
            <ul>
              {expert.recommendations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <small className="workflow-run-id">
        Coordinator → Study Load Review Expert → Coordinator
      </small>
    </div>
  );
}

function ContextOptimizationPanel({
  result,
  error,
  isLoading,
  onCompare,
  canCompare,
}) {
  const baseline = result?.versions?.baseline;
  const candidate = result?.versions?.candidate;
  return (
    <section className="panel agent-explanation-panel">
      <div className="panel-heading">
        <div>
          <h2>Week 09 上下文優化</h2>
          <p className="subtle">
            同一案例比較 Week 08 指令版與 Week 09 few-shot 版。
          </p>
        </div>
        <span className="agent-framework-badge">Few-shot</span>
      </div>

      <button
        type="button"
        className="primary-button full-width"
        onClick={onCompare}
        disabled={!canCompare || isLoading}
      >
        {isLoading ? "比較中" : "用同一案例比較 Baseline / Candidate"}
      </button>

      {!canCompare && (
        <p className="helper-text">請先成功執行一次智慧學習主流程。</p>
      )}
      {error && (
        <p className="notice notice-warning" role="alert">
          <Icon name="alert" size={18} />
          {error}
        </p>
      )}
      {result && (
        <div className="agent-result">
          <div className="agent-result-tags">
            <span>固定案例</span>
            <span>固定模型</span>
            <span>固定評估規則</span>
          </div>
          <p>
            預期 assessment：<strong>{result.expectedAssessment}</strong>
          </p>
          <div className="workflow-trace">
            <ol>
              {[
                ["Baseline", baseline],
                ["Candidate", candidate],
              ].map(([label, version]) => (
                <li
                  className={
                    version?.evaluation?.pass ? "is-completed" : "is-rejected"
                  }
                  key={label}
                >
                  <span className="workflow-step-marker" aria-hidden="true" />
                  <div>
                    <strong>{label}</strong>
                    <small>
                      {version?.contextVersion}・輸出：
                      {version?.evaluation?.actualAssessment || "無"}・
                      {version?.evaluation?.pass ? "PASS" : "FAIL"}
                    </small>
                  </div>
                  <span className="workflow-step-status">
                    {version?.evaluation?.pass ? "通過" : "未通過"}
                  </span>
                </li>
              ))}
            </ol>
          </div>
          <p>{result.observation}</p>
          <small>
            method：{result.method}・run ID：{result.runId}
          </small>
        </div>
      )}
    </section>
  );
}

function AgentDataPackagePanel({ dataPackage }) {
  if (!dataPackage) return null;
  const environment = dataPackage.environment || {};
  const verifier = dataPackage.verifier || {};
  const trajectory = dataPackage.trajectory || {};
  return (
    <div className="workflow-trace" aria-label="Week 10 Agent Data Package">
      <div className="workflow-trace-heading">
        <strong>Week 10 Agent Data Package</strong>
        <span
          className={`workflow-state is-${
            verifier.passed ? "completed" : "rejected"
          }`}
        >
          {verifier.passed ? "可核對" : "需檢查"}
        </span>
      </div>
      <div className="agent-result">
        <div className="agent-result-tags">
          <span>Task</span>
          <span>Environment</span>
          <span>Trajectory</span>
          <span>Verifier</span>
        </div>
        <p>
          {dataPackage.task.courseName}・目標 {dataPackage.task.targetMinutes} 分鐘・
          每次 {dataPackage.task.sessionMinutes} 分鐘
        </p>
        <ul>
          <li>
            課表：{environment.weeklyClasses?.count ?? 0} 筆・
            {environment.weeklyClasses?.source}
          </li>
          <li>
            私人行程：{environment.personalEvents?.count ?? 0} 筆・只保留
            ID／日期／時間
          </li>
          <li>
            軌跡：{trajectory.stepCount ?? 0} 步・來源 {trajectory.source}
          </li>
          <li>
            驗證：{verifier.planIssueCount ?? 0} 項排程問題・assessment{" "}
            {verifier.actualAssessment} / {verifier.expectedAssessment}
          </li>
        </ul>
        <div className="workflow-trace">
          <ol>
            {(trajectory.steps || []).map((step) => (
              <li
                className={`is-${
                  step.status === "completed" ? "completed" : "rejected"
                }`}
                key={`${step.step}-${step.action}`}
              >
                <span className="workflow-step-marker" aria-hidden="true" />
                <div>
                  <strong>{step.action}</strong>
                  <small>{step.actor}</small>
                </div>
                <span className="workflow-step-status">{step.status}</span>
              </li>
            ))}
          </ol>
        </div>
        <small className="workflow-run-id">
          package：{dataPackage.packageId}・不含 credentials／私人行程文字
        </small>
      </div>
    </div>
  );
}

function AgentExplanationPanel({ result, error, isLoading, workflow }) {
  return (
    <section className="panel agent-explanation-panel">
      <div className="panel-heading">
        <div>
          <h2>Agent 規劃說明</h2>
          <p className="subtle">框架負責工具協調與說明，排程仍由原規則計算。</p>
        </div>
        <span className="agent-framework-badge">
          {result?.framework || "後端 Agent"}
        </span>
      </div>

      {isLoading ? (
        <p className="agent-state" role="status">
          <Icon name="check" size={18} />
          Agent 正在呼叫規則工具並整理說明。
        </p>
      ) : error ? (
        <p className="notice notice-warning" role="alert">
          <Icon name="alert" size={18} />
          {error} 已保留原本規則產生的安全排程。
        </p>
      ) : result ? (
        <div className="agent-result">
          <div className="agent-result-tags">
            <span>function tool</span>
            <span>2-Agent Route A</span>
            <span>規則結果一致</span>
          </div>
          <p>{result.summary}</p>
          {result.warnings.length > 0 && (
            <ul>
              {result.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}
          <div className="agent-citations" aria-label="Agent 使用資料來源">
            {result.citations.map((citation) => (
              <span key={citation}>{citation}</span>
            ))}
          </div>
          <small>
            tool：{result.tool}・model：{result.model}・排程規則未交由 LLM
          </small>
          <MultiAgentTrace multiAgent={result.multiAgent} />
          <AgentDataPackagePanel dataPackage={result.dataPackage} />
        </div>
      ) : (
        <p className="empty-state">
          按下「用 Agent 產生學習計畫」，可查看框架如何呼叫既有排程工具。
        </p>
      )}
      <WorkflowTrace workflow={workflow} />
    </section>
  );
}

export default function StudyPlanner({
  studyPlan,
  personalEvents,
  studySessions,
  courses,
  weeklyClasses,
  onReplaceSchedule,
  onUpdateSession,
  onDeleteSession,
}) {
  const [courseId, setCourseId] = useState("");
  const [examDate, setExamDate] = useState(DEFAULT_EXAM_DATE);
  const [hours, setHours] = useState(6);
  const [sessionHours, setSessionHours] = useState(2);
  const [allowedPeriods, setAllowedPeriods] = useState([
    "afternoon",
    "evening",
  ]);
  const [planMessage, setPlanMessage] = useState("");
  const [agentResult, setAgentResult] = useState(null);
  const [agentError, setAgentError] = useState("");
  const [agentWorkflow, setAgentWorkflow] = useState(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [lastAgentRequest, setLastAgentRequest] = useState(null);
  const [contextComparison, setContextComparison] = useState(null);
  const [contextComparisonError, setContextComparisonError] = useState("");
  const [contextComparisonLoading, setContextComparisonLoading] =
    useState(false);
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState(null);
  const [editError, setEditError] = useState("");
  const enrolledCourses = courses.filter((course) =>
    ["inProgress", "completed"].includes(course.status),
  );
  const planCourse = courses.find(
    (course) => course.id === studyPlan?.course_id,
  );
  const selectableCourses = enrolledCourses.length
    ? [
        ...enrolledCourses,
        ...(planCourse &&
        !enrolledCourses.some((course) => course.id === planCourse.id)
          ? [planCourse]
          : []),
      ]
    : courses;
  const activeCourseId = selectableCourses.some(
    (course) => course.id === courseId,
  )
    ? courseId
    : planCourse?.id || selectableCourses[0]?.id || "";
  const courseName =
    courses.find((course) => course.id === activeCourseId)?.name || "課程";
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
  const applyRememberedSessionMinutes = useCallback((minutes) => {
    setSessionHours(minutes / 60);
  }, []);

  function togglePeriod(period) {
    setAllowedPeriods((current) =>
      current.includes(period)
        ? current.filter((item) => item !== period)
        : [...current, period],
    );
  }

  async function generatePlan(event) {
    event.preventDefault();
    if (
      !Number.isFinite(Number(hours)) ||
      Number(hours) <= 0 ||
      Number(hours) > 100
    )
      return setPlanMessage("請輸入 0.5 至 100 小時的複習時數。");
    if (!allowedPeriods.length)
      return setPlanMessage("請至少選擇一個可安排時段。");
    if (!activeCourseId)
      return setPlanMessage("後端目前沒有可用課程，請先設定 115 示範身分。");
    if (examDate <= DEMO_DATE)
      return setPlanMessage(`考試日期需晚於今天 ${formatDate(DEMO_DATE)}。`);
    const planningWeeklyClasses = weeklyClasses.map(
      ({ id, title, weekday, start, end, location }) => ({
        id,
        title,
        weekday,
        start,
        end,
        location: location || "",
      }),
    );
    const request = {
      startDate: DEMO_DATE,
      examDate,
      hours: Number(hours),
      sessionHours,
      allowedPeriods,
      courseName,
      weeklyClasses: planningWeeklyClasses,
      personalEvents: personalEvents.map(
        ({ id, title, date, start, end, location }) => ({
          id,
          title,
          date,
          start,
          end,
          location,
        }),
      ),
    };
    const baseline = planStudySessions(request);
    setLastAgentRequest(request);
    setContextComparison(null);
    setContextComparisonError("");

    setPlanMessage(
      baseline.remainingMinutes > 0
        ? `可安排時間不足，尚缺 ${baseline.remainingMinutes / 60} 小時。請增加可安排時段或調整複習需求。`
        : `已在考試前安排 ${baseline.scheduledMinutes / 60} 小時，正在請 Agent 說明結果。`,
    );
    setAgentResult(null);
    setAgentError("");
    setAgentWorkflow(null);
    setAgentLoading(true);
    setEditingId(null);

    try {
      await onReplaceSchedule({
        request: { ...request, courseId: activeCourseId },
        sessions: baseline.sessions,
      });
    } catch (error) {
      setAgentError(
        `後端儲存失敗：${error instanceof Error ? error.message : String(error)}`,
      );
      setPlanMessage("學習計畫未寫入後端，請修正錯誤後再試一次。");
      setAgentLoading(false);
      return;
    }

    try {
      const response = await requestStudyAgentPlan({
        payload: request,
        signal:
          typeof AbortSignal !== "undefined" &&
          typeof AbortSignal.timeout === "function"
            ? AbortSignal.timeout(45_000)
            : undefined,
      });
      if (!studyPlansMatch(baseline, response.plan)) {
        throw new Error("框架回傳排程與原規則不一致。");
      }

      setAgentResult({
        ...response.agent,
        comparison: response.comparison,
        multiAgent: response.multiAgent,
        optimization: response.optimization,
        dataPackage: response.dataPackage,
      });
      setAgentWorkflow(response.workflow);
      setPlanMessage(
        response.plan.remainingMinutes > 0
          ? `規則與 Agent 結果一致；目前尚缺 ${response.plan.remainingMinutes / 60} 小時。`
          : `規則與 Agent 結果一致，已安排 ${response.plan.scheduledMinutes / 60} 小時。`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setAgentError(error?.code ? `${message}（${error.code}）` : message);
      setAgentWorkflow(error?.workflow || null);
    } finally {
      setAgentLoading(false);
    }
  }

  async function compareContexts() {
    if (!lastAgentRequest) return;
    setContextComparison(null);
    setContextComparisonError("");
    setContextComparisonLoading(true);
    try {
      const response = await requestStudyContextComparison({
        payload: lastAgentRequest,
        signal:
          typeof AbortSignal !== "undefined" &&
          typeof AbortSignal.timeout === "function"
            ? AbortSignal.timeout(45_000)
            : undefined,
      });
      setContextComparison(response);
    } catch (error) {
      setContextComparisonError(
        error instanceof Error ? error.message : String(error),
      );
    } finally {
      setContextComparisonLoading(false);
    }
  }

  function startEdit(session) {
    setEditingId(session.id);
    setDraft({ date: session.date, start: session.start, end: session.end });
    setEditError("");
  }

  async function saveEdit(session) {
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
    try {
      await onUpdateSession(session, draft);
      setAgentResult(null);
      setAgentError("");
      setAgentWorkflow(null);
      setEditingId(null);
      setPlanMessage("已手動調整複習時段並同步到後端。");
    } catch (error) {
      setEditError(error instanceof Error ? error.message : String(error));
    }
  }

  async function removeSession(session) {
    if (
      typeof globalThis.confirm === "function" &&
      !globalThis.confirm(`確定要刪除「${session.title}」這個複習時段嗎？`)
    ) {
      return;
    }
    try {
      await onDeleteSession(session);
      setAgentResult(null);
      setAgentError("");
      setAgentWorkflow(null);
      setPlanMessage("已從後端移除複習時段；需要時可重新產生計畫。");
    } catch (error) {
      setPlanMessage(
        `無法刪除複習時段：${error instanceof Error ? error.message : String(error)}`,
      );
    }
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
                  value={activeCourseId}
                  onChange={(event) => setCourseId(event.target.value)}
                  disabled={!selectableCourses.length}
                >
                  {selectableCourses.map((course) => (
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
                  min={addDays(DEMO_DATE, 1)}
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
              <button
                className="primary-button full-width"
                type="submit"
                disabled={agentLoading}
              >
                {agentLoading ? "Agent 規劃中" : "用 Agent 產生學習計畫"}
              </button>
              <p className="agent-disclosure">
                按下後會將課名、日期、可用時段、目前示範課表與私人行程送至 Flask
                後端。Coordinator 先呼叫確定性排程工具，再把去識別的時段結果交給
                Study Load Review Expert 檢查，最後由 Coordinator 整合回答。Week
                09 主流程使用 few-shot context；Week 10 會把同學後端課表、私人行程、
                Agent 軌跡與 verifier 整理成可核對 Data Package。專家沒有 Tool 或
                資料庫寫入權限；API key 僅存在 Flask 後端。
              </p>
            </form>
          </section>
          <StudyMemoryPanel onApplyPreference={applyRememberedSessionMinutes} />
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
                          onClick={() => removeSession(session)}
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
          <AgentExplanationPanel
            result={agentResult}
            error={agentError}
            isLoading={agentLoading}
            workflow={agentWorkflow}
          />
          <ContextOptimizationPanel
            result={contextComparison}
            error={contextComparisonError}
            isLoading={contextComparisonLoading}
            onCompare={compareContexts}
            canCompare={Boolean(lastAgentRequest && agentResult)}
          />
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
