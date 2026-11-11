"use strict";
const $ = (id) => document.getElementById(id);
const state = {
  run: null,
  verification: null,
  examples: [],
  config: null,
  busy: false,
};
const labels = {
  assistant: "學生助理",
  scheduler: "排程專家",
  single: "單一助理",
  completed: "已完成",
  partial: "時數不足",
  failed: "執行失敗",
  working: "執行中",
};
const events = {
  role_started: "開始處理",
  delegation: "委派專家",
  tool_validated: "工具通過權限檢查",
  tool_result: "取得工具事實",
  role_completed: "完成交付",
  offline_step: "離線模擬步驟",
  model_request: "提出模型請求",
  model_response: "取得模型回應",
  tool_rejected: "拒絕越權工具",
  run_failed: "流程中止",
};
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function message(text, error = false) {
  $("message").textContent = text;
  $("message").className = `message${error ? " error" : ""}`;
  $("message").hidden = !text;
}
function busy(value) {
  state.busy = value;
  $("run-button").disabled = value;
  $("run-button").textContent = value
    ? "執行中，正在取得與驗證結果…"
    : "產生並驗證 ↗";
  for (const id of ["commit", "verify", "refresh"]) $(id).disabled = value;
  updateCommit();
}
async function api(path, options = {}) {
  const response = await fetch(`/api/v1/agent${path}`, {
    ...options,
    headers: options.body ? { "Content-Type": "application/json" } : {},
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error?.message || `HTTP ${response.status}`);
  return data.data;
}
function details(title, data, open = false) {
  const d = node("details");
  d.open = open;
  d.append(node("summary", title), node("pre", JSON.stringify(data, null, 2)));
  return d;
}
function time(value) {
  return new Date(value).toLocaleTimeString("zh-TW", {
    timeZone: "Asia/Taipei",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
function date(value) {
  return new Date(value).toLocaleDateString("zh-TW", {
    timeZone: "Asia/Taipei",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  });
}
function hours(minutes) {
  return `${Number((minutes / 60).toFixed(2))} h`;
}
function selectTab(key) {
  document.querySelectorAll("[data-tab]").forEach((b) => {
    b.setAttribute("aria-selected", String(b.dataset.tab === key));
    b.tabIndex = b.dataset.tab === key ? 0 : -1;
  });
  for (const tab of ["plan", "trace", "verify", "json"])
    $(`pane-${tab}`).hidden = tab !== key;
}
function updateCommit() {
  $("commit").disabled =
    state.busy ||
    !state.run?.result?.candidates?.length ||
    !state.verification?.passed ||
    !!state.run?.commit;
}
function renderVerification(v) {
  state.verification = v;
  $("checks").replaceChildren();
  for (const c of v.checks) {
    const row = node("div", undefined, `check${c.passed ? "" : " failed"}`);
    const content = node("div", c.detail);
    content.append(node("small", c.id));
    row.append(node("span", c.passed ? "✓" : "!"), content);
    $("checks").append(row);
  }
  $("verified-at").textContent =
    `${v.passed ? "驗證通過" : "驗證未通過"} · ${new Date(v.checked_at).toLocaleString("zh-TW", { timeZone: "Asia/Taipei" })}。自由文字說明不在程式驗證範圍內。`;
  updateCommit();
}
function render(run) {
  state.run = run;
  $("empty").hidden = true;
  $("result").hidden = false;
  $("run-status").textContent = labels[run.status] || run.status;
  $("run-status").className =
    `badge${run.status === "failed" ? " error" : run.status === "partial" ? " warn" : ""}`;
  $("scheduled").textContent = run.result
    ? hours(run.result.scheduled_minutes)
    : "—";
  $("remaining").textContent = run.result
    ? hours(run.result.remaining_minutes)
    : "—";
  $("calls").textContent = run.metrics.model_calls;
  $("latency").textContent = `${(run.metrics.latency_ms / 1000).toFixed(2)} s`;
  $("run-meta").textContent =
    `${run.provider.name === "offline" ? `離線固定流程 · ${run.metrics.simulated_turns} 個模擬回合，非模型效能測試` : `OpenAI · ${run.provider.model} · ${run.metrics.input_tokens} 輸入 / ${run.metrics.output_tokens} 輸出 tokens${run.metrics.usage_complete ? "" : "（用量不完整）"}`}\nRun ${run.run_id}`;
  $("sessions").replaceChildren();
  const sessions = run.result?.candidates || [];
  $("session-count").textContent = `${sessions.length} 個時段`;
  $("plan-note").textContent = run.error
    ? `${run.error.code}：${run.error.message}`
    : run.status === "partial"
      ? `可用時間不足，還缺 ${run.result.remaining_minutes} 分鐘。調整允許時段後重新產生；也可先儲存目前候選。`
      : "以下時段由後端排程引擎計算，模型不能自行改寫。";
  sessions.forEach((s, i) => {
    const row = node("div", undefined, "session");
    const content = node("div");
    content.append(
      node(
        "b",
        `${date(s.starts_at)}　${time(s.starts_at)} – ${time(s.ends_at)}`,
      ),
      node("small", s.title),
    );
    row.append(
      node("span", String(i + 1).padStart(2, "0"), "session-number"),
      content,
      node(
        "span",
        `${Math.round((new Date(s.ends_at) - new Date(s.starts_at)) / 60000)} 分鐘`,
      ),
    );
    $("sessions").append(row);
  });
  if (!sessions.length)
    $("sessions").append(
      node("p", "沒有可顯示的候選時段。請查看驗證與執行紀錄。", "hint"),
    );
  $("narration").textContent = run.narration || "本次未取得可採用的助理說明。";
  $("commit-status").textContent = run.commit
    ? `已儲存 · 計畫 ${run.commit.plan_id}`
    : "尚未寫入行事曆";
  $("ledger").replaceChildren(
    ...run.ledger.map((task) =>
      node(
        "span",
        `${labels[task.owner]} · ${labels[task.status]} · v${task.version}`,
      ),
    ),
  );
  $("events").replaceChildren();
  for (const e of run.events) {
    const item = node("div", undefined, "event");
    item.append(
      node(
        "b",
        `${String(e.seq).padStart(2, "0")}　${labels[e.role] || e.role} · ${events[e.type] || e.type}`,
      ),
      node("small", `${time(e.at)}${e.tool ? ` / ${e.tool}` : ""}`),
      details("查看事件內容", e),
    );
    $("events").append(item);
  }
  $("sources").replaceChildren(
    ...run.sources.map((s) => details(`${s.source_id} · ${s.kind}`, s)),
  );
  $("request-json").textContent = JSON.stringify(run.request, null, 2);
  $("result-json").textContent = JSON.stringify(run, null, 2);
  renderVerification(run.verification);
  selectTab("plan");
}
function payload() {
  const days = [...document.querySelectorAll("#weekdays input:checked")].map(
    (x) => Number(x.value),
  );
  if (!days.length) throw new Error("請至少選擇一個可安排日。");
  if ($("window-end").value <= $("window-start").value)
    throw new Error("結束時間必須晚於開始時間。");
  return {
    provider: $("provider").value,
    architecture: $("architecture").value,
    plan: {
      course_id: $("course").value,
      start_date: $("start").value,
      exam_date: $("exam").value,
      target_minutes: Math.round(Number($("hours").value) * 60),
      session_minutes: Number($("session").value),
      allowed_windows: days.map((d) => ({
        weekday: d,
        start_time: $("window-start").value,
        end_time: $("window-end").value,
      })),
    },
  };
}
function example(id) {
  const p = state.examples.find((x) => x.id === id)?.request.plan;
  if (!p) return;
  $("course").value = p.course_id;
  $("start").value = p.start_date;
  $("exam").value = p.exam_date;
  $("hours").value = p.target_minutes / 60;
  $("session").value = p.session_minutes;
  $("window-start").value = p.allowed_windows[0].start_time;
  $("window-end").value = p.allowed_windows[0].end_time;
  document.querySelectorAll("#weekdays input").forEach((box) => {
    box.checked = p.allowed_windows.some(
      (w) => w.weekday === Number(box.value),
    );
  });
}
async function history() {
  const runs = await api("/runs");
  $("history-list").replaceChildren();
  if (!runs.length) $("history-list").textContent = "尚無執行紀錄";
  for (const r of runs) {
    const b = node("button", undefined, "history-item");
    b.type = "button";
    const text = node(
      "span",
      `${r.request.architecture === "multi" ? "多 Agent" : "單 Agent"} · ${r.provider.name} · ${labels[r.status]}`,
    );
    text.append(
      node(
        "small",
        `${r.created_at.slice(0, 16).replace("T", " ")} · 目標 ${hours(r.request.plan.target_minutes)} · ${r.metrics.model_calls} 次模型呼叫`,
      ),
    );
    b.append(text, node("span", "查看 ↗"));
    b.onclick = async () => {
      if (state.busy) return;
      busy(true);
      try {
        const run = await api(`/runs/${r.run_id}`);
        render(run);
        renderVerification(
          await api(`/runs/${r.run_id}/verify`, { method: "POST" }),
        );
        message("已載入執行紀錄，並依目前資料重新查證。");
      } catch (e) {
        message(e.message, true);
      } finally {
        busy(false);
      }
    };
    $("history-list").append(b);
  }
}
$("request-form").onsubmit = async (event) => {
  event.preventDefault();
  if (state.busy) return;
  let p;
  try {
    p = payload();
  } catch (e) {
    message(e.message, true);
    return;
  }
  busy(true);
  message(
    p.provider === "openai"
      ? "OpenAI 執行中，將傳送本次複習需求及必要空檔資料；最多 120 秒執行預算。"
      : "正在執行固定流程、產生候選並查證…",
  );
  try {
    const r = await api("/runs", { method: "POST", body: JSON.stringify(p) });
    render(r);
    message(
      r.status === "failed"
        ? r.error.message
        : "候選已產生。請檢視時段與證據，確認後才會儲存。",
      r.status === "failed",
    );
    await history();
  } catch (e) {
    message(e.message, true);
  } finally {
    busy(false);
  }
};
$("verify").onclick = async () => {
  if (!state.run || state.busy) return;
  busy(true);
  try {
    const v = await api(`/runs/${state.run.run_id}/verify`, { method: "POST" });
    renderVerification(v);
    message(
      v.passed
        ? "重新查證通過，結果符合目前資料。"
        : "重新查證未通過，請檢視檢查項目並重新產生。",
      !v.passed,
    );
  } catch (e) {
    message(e.message, true);
  } finally {
    busy(false);
  }
};
$("commit").onclick = async () => {
  if (!state.run || state.busy) return;
  busy(true);
  try {
    await api(`/runs/${state.run.run_id}/commit`, {
      method: "POST",
      body: JSON.stringify({ confirmed: true }),
    });
    const r = await api(`/runs/${state.run.run_id}`);
    render(r);
    renderVerification(
      await api(`/runs/${r.run_id}/verify`, { method: "POST" }),
    );
    message("已儲存至後端複習計畫。重複確認不會建立第二份。");
    await history();
  } catch (e) {
    message(e.message, true);
    state.verification = { passed: false };
  } finally {
    busy(false);
  }
};
$("export").onclick = () => {
  if (!state.run) return;
  const data = { ...state.run, latest_verification: state.verification };
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = node("a");
  a.href = url;
  a.download = `agent-run-${state.run.run_id}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
$("refresh").onclick = () => {
  if (!state.busy) history().catch((e) => message(e.message, true));
};
document.querySelectorAll("[data-tab]").forEach((b) => {
  b.onclick = () => selectTab(b.dataset.tab);
  b.onkeydown = (e) => {
    if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    e.preventDefault();
    const tabs = [...document.querySelectorAll("[data-tab]")];
    const next = tabs[(tabs.indexOf(b) + (e.key === "ArrowRight" ? 1 : 3)) % 4];
    selectTab(next.dataset.tab);
    next.focus();
  };
});
document.querySelectorAll("[data-example]").forEach((b) => {
  b.onclick = () => example(b.dataset.example);
});
["一", "二", "三", "四", "五", "六", "日"].forEach((name, i) => {
  const label = node("label");
  const input = node("input");
  input.type = "checkbox";
  input.value = i + 1;
  input.setAttribute("aria-label", `星期${name}`);
  label.append(input, node("span", name));
  $("weekdays").append(label);
});
async function init() {
  busy(true);
  try {
    const [config, examples, response] = await Promise.all([
      api("/config"),
      api("/examples"),
      fetch("/api/v1/courses"),
    ]);
    if (!response.ok) throw new Error("課程載入失敗，請先執行 init-db。");
    const courses = await response.json();
    state.config = config;
    state.examples = examples;
    $("course").replaceChildren(
      ...courses.data.map((c) => {
        const o = node("option", c.name);
        o.value = c.course_id;
        return o;
      }),
    );
    const live = $("provider").querySelector('[value="openai"]');
    live.disabled = !config.openai.configured;
    $("provider-status").textContent = config.openai.configured
      ? `OpenAI 已設定：${config.openai.model}。離線驗證不使用額度。`
      : "OpenAI 尚未設定。後端設定 OPENAI_API_KEY、OPENAI_MODEL 後重啟；現在可使用離線驗證。";
    example("normal");
    await history();
  } catch (e) {
    message(e.message, true);
  } finally {
    busy(false);
  }
}
init();
