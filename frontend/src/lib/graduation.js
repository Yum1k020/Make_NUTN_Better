export const GRADUATION_STATUS = {
  met: "已達標",
  not_met: "未達標",
  needs_confirmation: "待確認",
};
export const CHECK_NAMES = {
  general_core: "通識核心",
  general_domain: "通識領域學分",
  college_required: "院核心",
  department_required: "專業必修學分",
  department_elective: "專業選修",
  free_elective: "自由選修",
};
export const DATA_MESSAGES = {
  CLASSIFICATION_UNKNOWN: "部分課程的學分類別尚待確認。",
  REQUIRED_COURSES_UNMAPPED: "部分必修課程尚未完成課程對照。",
  GENERAL_DOMAIN_UNKNOWN: "部分通識課程的領域尚待確認。",
  DUPLICATE_COURSE: "發現重複課程紀錄，請確認採計方式。",
  RULE_UNAVAILABLE: "尚無適用且完整的畢業規則。",
};
const apiBase = (import.meta.env?.VITE_GRADUATION_API_BASE || "").replace(
  /\/$/,
  "",
);
export async function graduationRequest(path, options = {}) {
  const response = await fetch(`${apiBase}/api/v1/${path}`, options);
  const payload = await response.json();
  if (!response.ok)
    throw new Error(payload.error?.message || "無法讀取畢業進度");
  return payload.data;
}
export function displayValue(value) {
  return value === null || value === undefined ? "待確認" : String(value);
}
export function workflowMessage(workflow) {
  if (workflow.status === "verified") return "說明已通過數字、狀態與來源檢查。";
  if (workflow.stop_reason === "RULE_UNAVAILABLE")
    return "尚無適用規則，請先確認系所與入學年度。";
  if (workflow.stop_reason === "PROVIDER_NOT_CONFIGURED")
    return "說明服務尚未設定，以下顯示基本進度。";
  if (workflow.stop_reason === "REVISION_LIMIT")
    return "說明修正後仍未通過檢查，以下顯示基本進度。";
  return "說明服務暫時無法使用，以下顯示基本進度。";
}
