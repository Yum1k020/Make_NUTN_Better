import { createStudyAgentService } from "../server/studyAgent.js";

const service = createStudyAgentService({
  apiKey: process.env.OPENAI_API_KEY,
  model: process.env.OPENAI_MODEL,
  tracingEnabled: process.env.OPENAI_AGENTS_TRACING === "true",
});

const result = await service.run({
  startDate: "2026-09-17",
  examDate: "2026-09-24",
  hours: 6,
  sessionHours: 2,
  allowedPeriods: ["afternoon", "evening"],
  courseName: "Smoke Test Course",
  personalEvents: [],
});

if (
  result.plan.scheduledMinutes !== 360 ||
  result.plan.remainingMinutes !== 0 ||
  result.plan.sessions.length !== 3
) {
  throw new Error("Agent smoke result did not preserve the baseline plan.");
}

console.log(
  JSON.stringify(
    {
      framework: result.agent.framework,
      tool: result.agent.tool,
      summary: result.agent.summary,
      warnings: result.agent.warnings,
      citations: result.agent.citations,
      comparison: result.comparison,
      workflow: result.workflow,
    },
    null,
    2,
  ),
);
