import { randomUUID } from "node:crypto";
import { z } from "zod";
import { weeklyClasses } from "../src/data/demo.js";
import {
  eventsOnDate,
  minutes,
  overlaps,
  planStudySessions,
} from "../src/lib/planner.js";

const PERIODS = ["morning", "afternoon", "evening"];
const PERIOD_LIMITS = {
  morning: [8 * 60, 12 * 60],
  afternoon: [13 * 60, 18 * 60],
  evening: [18 * 60, 22 * 60],
};
const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "日期格式必須是 YYYY-MM-DD。");
const timeSchema = z.string().regex(TIME_PATTERN, "時間格式必須是 HH:MM。");

const personalEventSchema = z
  .object({
    id: z.string().min(1).max(120),
    title: z.string().min(1).max(200),
    date: isoDateSchema,
    start: timeSchema,
    end: timeSchema,
    location: z.string().max(200).default(""),
  })
  .strict()
  .refine((event) => event.end > event.start, {
    message: "私人行程的結束時間必須晚於開始時間。",
  });

export const studyPlanRequestSchema = z
  .object({
    startDate: isoDateSchema,
    examDate: isoDateSchema,
    hours: z.number().min(0.5).max(100),
    sessionHours: z.number().min(0.5).max(4),
    allowedPeriods: z.array(z.enum(PERIODS)).min(1),
    courseName: z.string().trim().min(1).max(120),
    personalEvents: z.array(personalEventSchema).max(200),
  })
  .strict()
  .refine((request) => request.examDate > request.startDate, {
    message: "考試日期必須晚於規劃起始日。",
    path: ["examDate"],
  });

export const WORKFLOW_NAME = "study-plan-prompt-chaining";
export const WORKFLOW_VERSION = "week06-v1";
export const WORKFLOW_STOP_REASONS = {
  INVALID_REQUEST: "INVALID_REQUEST",
  RULE_ENGINE_FAILED: "RULE_ENGINE_FAILED",
  PLAN_GATE_REJECTED: "PLAN_GATE_REJECTED",
  AGENT_STAGE_FAILED: "AGENT_STAGE_FAILED",
};

export class StudyPlanWorkflowError extends Error {
  constructor({ code, message, statusCode, workflow, issues = [], cause }) {
    super(message, cause ? { cause } : undefined);
    this.name = "StudyPlanWorkflowError";
    this.code = code;
    this.statusCode = statusCode;
    this.workflow = workflow;
    this.issues = issues;
  }
}

function createWorkflow(runIdFactory) {
  return {
    name: WORKFLOW_NAME,
    version: WORKFLOW_VERSION,
    runId: `week06-${runIdFactory()}`,
    status: "running",
    stopReason: null,
    stages: [],
  };
}

function addStage(workflow, { id, label, status, evidence = {} }) {
  workflow.stages.push({ id, label, status, evidence });
}

function stoppedWorkflow(workflow, stopReason) {
  return {
    ...workflow,
    status: "stopped",
    stopReason,
  };
}

function completedWorkflow(workflow) {
  return {
    ...workflow,
    status: "completed",
    stopReason: null,
  };
}

function schemaIssues(error) {
  return error.issues.map((issue) => ({
    path: issue.path.join("."),
    message: issue.message,
  }));
}

export function buildDeterministicStudyPlan(request) {
  return planStudySessions({
    ...request,
    weeklyClasses,
  });
}

export function verifyStudyPlan(request, plan) {
  const issues = [];
  if (!plan || !Array.isArray(plan.sessions)) {
    return ["排程結果缺少 sessions。"];
  }

  const targetMinutes = Math.round(request.hours * 60);
  const acceptedSessions = [];
  const sessionIds = new Set();
  let calculatedMinutes = 0;

  for (const session of plan.sessions) {
    if (
      !session?.id ||
      !session?.date ||
      !TIME_PATTERN.test(session.start || "") ||
      !TIME_PATTERN.test(session.end || "")
    ) {
      issues.push("複習時段缺少可驗證的日期、時間或識別碼。");
      continue;
    }
    if (sessionIds.has(session.id)) {
      issues.push(`複習時段識別碼重複：${session.id}。`);
    }
    sessionIds.add(session.id);

    const startMinutes = minutes(session.start);
    const endMinutes = minutes(session.end);
    if (endMinutes <= startMinutes) {
      issues.push(`複習時段 ${session.id} 的結束時間未晚於開始時間。`);
      continue;
    }
    if (session.date < request.startDate || session.date >= request.examDate) {
      issues.push(`複習時段 ${session.id} 不在規劃日期範圍內。`);
    }

    const insideAllowedPeriod = request.allowedPeriods.some((period) => {
      const limits = PERIOD_LIMITS[period];
      return limits && startMinutes >= limits[0] && endMinutes <= limits[1];
    });
    if (!insideAllowedPeriod) {
      issues.push(`複習時段 ${session.id} 不在允許的時段內。`);
    }

    const occupied = eventsOnDate(
      session.date,
      weeklyClasses,
      request.personalEvents,
      acceptedSessions,
    );
    const conflict = occupied.find((event) => overlaps(session, event));
    if (conflict) {
      issues.push(`複習時段 ${session.id} 與既有行程重疊。`);
    }

    calculatedMinutes += endMinutes - startMinutes;
    acceptedSessions.push(session);
  }

  if (
    !Number.isFinite(plan.scheduledMinutes) ||
    !Number.isFinite(plan.remainingMinutes) ||
    plan.scheduledMinutes < 0 ||
    plan.remainingMinutes < 0
  ) {
    issues.push("排程結果的時數摘要無效。");
  } else {
    if (plan.scheduledMinutes !== calculatedMinutes) {
      issues.push("scheduledMinutes 與時段加總不一致。");
    }
    if (plan.scheduledMinutes + plan.remainingMinutes !== targetMinutes) {
      issues.push("已安排與尚缺時數不等於目標時數。");
    }
  }

  return issues;
}

export async function runStudyPlanWorkflow({
  request,
  planBuilder = buildDeterministicStudyPlan,
  explainPlan,
  runIdFactory = randomUUID,
} = {}) {
  const workflow = createWorkflow(runIdFactory);
  const parsed = studyPlanRequestSchema.safeParse(request);

  if (!parsed.success) {
    const issues = schemaIssues(parsed.error);
    addStage(workflow, {
      id: "validate-request",
      label: "需求驗證",
      status: "rejected",
      evidence: { issueCount: issues.length, downstreamCalls: 0 },
    });
    throw new StudyPlanWorkflowError({
      code: WORKFLOW_STOP_REASONS.INVALID_REQUEST,
      message: "學習規劃資料格式不正確。",
      statusCode: 422,
      workflow: stoppedWorkflow(
        workflow,
        WORKFLOW_STOP_REASONS.INVALID_REQUEST,
      ),
      issues,
    });
  }

  const normalizedRequest = parsed.data;
  addStage(workflow, {
    id: "validate-request",
    label: "需求驗證",
    status: "completed",
    evidence: {
      fieldCount: Object.keys(normalizedRequest).length,
      personalEventCount: normalizedRequest.personalEvents.length,
    },
  });

  let plan;
  try {
    plan = await planBuilder(normalizedRequest);
  } catch (error) {
    addStage(workflow, {
      id: "build-plan",
      label: "規則排程",
      status: "failed",
      evidence: { errorSource: "rule-engine", attemptCount: 1 },
    });
    throw new StudyPlanWorkflowError({
      code: WORKFLOW_STOP_REASONS.RULE_ENGINE_FAILED,
      message: "規則排程執行失敗。",
      statusCode: 500,
      workflow: stoppedWorkflow(
        workflow,
        WORKFLOW_STOP_REASONS.RULE_ENGINE_FAILED,
      ),
      cause: error,
    });
  }

  addStage(workflow, {
    id: "build-plan",
    label: "規則排程",
    status: "completed",
    evidence: {
      sessionCount: plan.sessions.length,
      scheduledMinutes: plan.scheduledMinutes,
      remainingMinutes: plan.remainingMinutes,
    },
  });

  const gateIssues = verifyStudyPlan(normalizedRequest, plan);
  if (gateIssues.length) {
    addStage(workflow, {
      id: "verify-plan",
      label: "衝突與完整性 Gate",
      status: "rejected",
      evidence: { issueCount: gateIssues.length, downstreamCalls: 0 },
    });
    throw new StudyPlanWorkflowError({
      code: WORKFLOW_STOP_REASONS.PLAN_GATE_REJECTED,
      message: "排程結果未通過衝突與完整性檢查。",
      statusCode: 409,
      workflow: stoppedWorkflow(
        workflow,
        WORKFLOW_STOP_REASONS.PLAN_GATE_REJECTED,
      ),
      issues: gateIssues.map((message) => ({
        path: "plan",
        message,
      })),
    });
  }

  addStage(workflow, {
    id: "verify-plan",
    label: "衝突與完整性 Gate",
    status: "completed",
    evidence: {
      checkedSessionCount: plan.sessions.length,
      issueCount: 0,
    },
  });

  try {
    if (typeof explainPlan !== "function") {
      throw new Error("Agent explanation stage is not configured.");
    }
    const explanation = await explainPlan({
      request: normalizedRequest,
      plan,
    });
    addStage(workflow, {
      id: "explain-plan",
      label: "Agent 說明",
      status: "completed",
      evidence: {
        provider: "OpenAI Agents SDK",
        citationCount: explanation.citations?.length || 0,
        attemptCount: 1,
      },
    });
    return {
      request: normalizedRequest,
      plan,
      explanation,
      workflow: completedWorkflow(workflow),
    };
  } catch (error) {
    addStage(workflow, {
      id: "explain-plan",
      label: "Agent 說明",
      status: "failed",
      evidence: {
        errorSource: "agent-provider-or-output",
        attemptCount: 1,
      },
    });
    throw new StudyPlanWorkflowError({
      code: WORKFLOW_STOP_REASONS.AGENT_STAGE_FAILED,
      message: "Agent 執行失敗，請稍後再試；原本的規則排程仍可使用。",
      statusCode: 502,
      workflow: stoppedWorkflow(
        workflow,
        WORKFLOW_STOP_REASONS.AGENT_STAGE_FAILED,
      ),
      cause: error,
    });
  }
}
