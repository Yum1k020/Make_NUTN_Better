import test from "node:test";
import assert from "node:assert/strict";
import { initialEvents } from "../src/data/demo.js";
import {
  runStudyPlanWorkflow,
  StudyPlanWorkflowError,
  WORKFLOW_STOP_REASONS,
} from "../server/studyPlanWorkflow.js";

function createRequest(overrides = {}) {
  return {
    startDate: "2026-09-17",
    examDate: "2026-09-24",
    hours: 6,
    sessionHours: 2,
    allowedPeriods: ["afternoon", "evening"],
    courseName: "資料結構",
    personalEvents: initialEvents.map(
      ({ id, title, date, start, end, location }) => ({
        id,
        title,
        date,
        start,
        end,
        location,
      }),
    ),
    ...overrides,
  };
}

function createExplanation() {
  return {
    summary: "已依規則完成學習規劃。",
    warnings: [],
    citations: ["planner-rule", "weekly-classes-fixture"],
    refused: false,
  };
}

test("week06 case 1: normal chaining completes every dependent stage", async () => {
  let agentCalls = 0;
  const result = await runStudyPlanWorkflow({
    request: createRequest(),
    explainPlan: async () => {
      agentCalls += 1;
      return createExplanation();
    },
    runIdFactory: () => "normal-case",
  });

  assert.equal(result.plan.scheduledMinutes, 360);
  assert.equal(result.plan.remainingMinutes, 0);
  assert.equal(result.workflow.runId, "week06-normal-case");
  assert.equal(result.workflow.status, "completed");
  assert.equal(result.workflow.stopReason, null);
  assert.deepEqual(
    result.workflow.stages.map(({ id, status }) => ({ id, status })),
    [
      { id: "validate-request", status: "completed" },
      { id: "build-plan", status: "completed" },
      { id: "verify-plan", status: "completed" },
      { id: "explain-plan", status: "completed" },
    ],
  );
  assert.equal(agentCalls, 1);
});

test("week06 case 2: invalid input stops before planner and agent", async () => {
  let plannerCalls = 0;
  let agentCalls = 0;

  await assert.rejects(
    runStudyPlanWorkflow({
      request: createRequest({ examDate: "2026-09-17" }),
      planBuilder: () => {
        plannerCalls += 1;
        return {};
      },
      explainPlan: async () => {
        agentCalls += 1;
        return createExplanation();
      },
      runIdFactory: () => "invalid-case",
    }),
    (error) => {
      assert.ok(error instanceof StudyPlanWorkflowError);
      assert.equal(error.code, WORKFLOW_STOP_REASONS.INVALID_REQUEST);
      assert.equal(error.workflow.status, "stopped");
      assert.equal(error.workflow.stages.length, 1);
      assert.equal(error.workflow.stages[0].status, "rejected");
      assert.equal(error.workflow.stages[0].evidence.downstreamCalls, 0);
      return true;
    },
  );

  assert.equal(plannerCalls, 0);
  assert.equal(agentCalls, 0);
});

test("week06 case 3: provider failure stops once and reports the source", async () => {
  let agentCalls = 0;

  await assert.rejects(
    runStudyPlanWorkflow({
      request: createRequest(),
      explainPlan: async () => {
        agentCalls += 1;
        throw new Error("Injected provider failure");
      },
      runIdFactory: () => "provider-failure",
    }),
    (error) => {
      assert.ok(error instanceof StudyPlanWorkflowError);
      assert.equal(error.code, WORKFLOW_STOP_REASONS.AGENT_STAGE_FAILED);
      assert.equal(error.workflow.status, "stopped");
      assert.equal(error.workflow.stopReason, "AGENT_STAGE_FAILED");
      assert.equal(error.workflow.stages.at(-1).id, "explain-plan");
      assert.equal(error.workflow.stages.at(-1).status, "failed");
      assert.equal(
        error.workflow.stages.at(-1).evidence.errorSource,
        "agent-provider-or-output",
      );
      return true;
    },
  );

  assert.equal(agentCalls, 1);
});

test("week06 case 4: conflict gate rejects a bad plan without calling agent", async () => {
  let agentCalls = 0;

  await assert.rejects(
    runStudyPlanWorkflow({
      request: createRequest(),
      planBuilder: () => ({
        sessions: [
          {
            id: "unsafe-overlap",
            title: "資料結構複習",
            date: "2026-09-17",
            start: "09:00",
            end: "15:00",
            location: "自行安排",
          },
        ],
        scheduledMinutes: 360,
        remainingMinutes: 0,
      }),
      explainPlan: async () => {
        agentCalls += 1;
        return createExplanation();
      },
      runIdFactory: () => "gate-rejection",
    }),
    (error) => {
      assert.ok(error instanceof StudyPlanWorkflowError);
      assert.equal(error.code, WORKFLOW_STOP_REASONS.PLAN_GATE_REJECTED);
      assert.equal(error.workflow.status, "stopped");
      assert.equal(error.workflow.stages.at(-1).id, "verify-plan");
      assert.equal(error.workflow.stages.at(-1).status, "rejected");
      assert.equal(error.workflow.stages.at(-1).evidence.downstreamCalls, 0);
      assert.ok(error.issues.some((issue) => /重疊/.test(issue.message)));
      return true;
    },
  );

  assert.equal(agentCalls, 0);
});
