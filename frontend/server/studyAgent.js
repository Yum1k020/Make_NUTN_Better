import {
  Agent,
  run,
  setDefaultOpenAIKey,
  setTracingDisabled,
  tool,
} from "@openai/agents";
import { z } from "zod";
import { weeklyClasses } from "../src/data/demo.js";
import { planStudySessions } from "../src/lib/planner.js";

const DEFAULT_MODEL = "gpt-5-mini";
const STUDY_PLAN_TOOL_NAME = "get_validated_study_plan";
const PERIODS = ["morning", "afternoon", "evening"];

const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "日期格式必須是 YYYY-MM-DD。");
const timeSchema = z
  .string()
  .regex(/^([01]\d|2[0-3]):[0-5]\d$/, "時間格式必須是 HH:MM。");

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

const agentOutputSchema = z
  .object({
    summary: z.string().min(1).max(600),
    warnings: z.array(z.string().min(1).max(240)).max(3),
    citations: z
      .array(
        z.enum([
          "planner-rule",
          "weekly-classes-fixture",
          "tasks-events-local",
        ]),
      )
      .min(1)
      .max(3),
    refused: z.boolean(),
  })
  .strict();

export function buildValidatedStudyPlan(request) {
  const input = studyPlanRequestSchema.parse(request);
  return planStudySessions({
    ...input,
    weeklyClasses,
  });
}

const getValidatedStudyPlan = tool({
  name: STUDY_PLAN_TOOL_NAME,
  description:
    "取得由既有規則引擎計算並驗證過的複習計畫。只能說明工具結果，不得自行改寫時段。",
  parameters: z.object({}).strict(),
  async execute(_input, runContext) {
    const context = runContext?.context;
    if (!context?.plan || !context?.request) {
      throw new Error("Validated study-plan context is missing.");
    }

    return {
      plan: context.plan,
      evidence: {
        courseName: context.request.courseName,
        weeklyClassCount: weeklyClasses.length,
        personalEventCount: context.request.personalEvents.length,
        sources: [
          "planner-rule",
          "weekly-classes-fixture",
          "tasks-events-local",
        ],
      },
    };
  },
});

function createAgent(model) {
  return new Agent({
    name: "NUTN Study Planning Agent",
    model,
    instructions: [
      "你是學生個人安排系統中的學習規劃說明 Agent。",
      `你必須先呼叫 ${STUDY_PLAN_TOOL_NAME}，而且只能根據工具回傳的 validated plan 回答。`,
      "排程日期、時間、scheduledMinutes 與 remainingMinutes 都由既有規則引擎決定，不得自行新增、刪除或改寫。",
      "若 remainingMinutes 大於 0，warnings 必須明確說明尚缺時數；若為 0，warnings 必須是空陣列，並在 summary 說明時數已完整安排。",
      "回答使用繁體中文，summary 適合直接顯示在學生介面。",
      "citations 只能使用工具提供的 source id。這個流程不查詢即時校務資料。",
      "輸入已由伺服器驗證，正常情況 refused 必須是 false。",
    ].join("\n"),
    tools: [getValidatedStudyPlan],
    outputType: agentOutputSchema,
    modelSettings: {
      toolChoice: "required",
      parallelToolCalls: false,
      maxTokens: 1200,
      store: false,
    },
  });
}

export function createStudyAgentService({
  apiKey,
  model = DEFAULT_MODEL,
  tracingEnabled = false,
  runAgent = run,
} = {}) {
  const normalizedKey = apiKey?.trim() || "";
  const normalizedModel = model?.trim() || DEFAULT_MODEL;
  if (!normalizedKey) {
    throw new Error("Missing server-side OPENAI_API_KEY.");
  }

  setDefaultOpenAIKey(normalizedKey);
  setTracingDisabled(!tracingEnabled);
  const agent = createAgent(normalizedModel);

  return {
    model: normalizedModel,
    async run(request) {
      const normalizedRequest = studyPlanRequestSchema.parse(request);
      const plan = buildValidatedStudyPlan(normalizedRequest);
      const result = await runAgent(
        agent,
        `請說明「${normalizedRequest.courseName}」在 ${normalizedRequest.examDate} 前的複習安排。`,
        {
          context: { request: normalizedRequest, plan },
          maxTurns: 4,
        },
      );
      const explanation = agentOutputSchema.parse(result.finalOutput);

      if (explanation.refused) {
        throw new Error("Agent refused a validated study-plan request.");
      }

      return {
        plan,
        agent: {
          ...explanation,
          warnings:
            plan.remainingMinutes > 0
              ? explanation.warnings.length
                ? explanation.warnings
                : [`尚缺 ${plan.remainingMinutes} 分鐘，請增加可安排時段。`]
              : [],
          framework: "OpenAI Agents SDK",
          tool: STUDY_PLAN_TOOL_NAME,
          model: normalizedModel,
        },
        comparison: {
          rulePreserved: true,
          scheduledMinutes: plan.scheduledMinutes,
          remainingMinutes: plan.remainingMinutes,
          sessionCount: plan.sessions.length,
        },
      };
    },
  };
}

export { DEFAULT_MODEL, STUDY_PLAN_TOOL_NAME };
