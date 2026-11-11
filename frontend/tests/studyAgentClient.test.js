import test from "node:test";
import assert from "node:assert/strict";

import {
  requestStudyAgentPlan,
  studyPlansMatch,
} from "../src/lib/studyAgentClient.js";

function jsonResponse(body, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    async json() {
      return body;
    },
  };
}

test("week08 frontend contract keeps backend multi-agent trace", async () => {
  const payload = {
    startDate: "2026-09-17",
    examDate: "2026-09-24",
    hours: 6,
    sessionHours: 2,
    allowedPeriods: ["afternoon", "evening"],
    courseName: "資料結構",
    personalEvents: [],
  };
  const plan = {
    sessions: [
      {
        id: "study-1",
        date: "2026-09-17",
        start: "18:00",
        end: "20:00",
      },
    ],
    scheduledMinutes: 120,
    remainingMinutes: 240,
  };
  let request;
  const fetchImpl = async (url, options) => {
    request = { url, options };
    return jsonResponse({
      plan,
      agent: {
        summary: "已完成排程並整合專家回報。",
        warnings: ["尚缺 240 分鐘。"],
        citations: ["planner-rule"],
        refused: false,
        tool: "get_validated_study_plan",
        model: "gpt-test",
      },
      multiAgent: {
        route: "A",
        pattern: "bounded-specialist",
        status: "completed",
        roles: [
          {
            id: "study-coordinator",
            label: "Study Coordinator",
            tools: ["get_validated_study_plan"],
          },
          {
            id: "study-load-reviewer",
            label: "Study Load Review Expert",
            tools: [],
            writeAccess: false,
          },
        ],
        expertReview: {
          assessment: "insufficient",
          summary: "仍有未排時數。",
          recommendations: ["增加可安排時段。"],
          citations: ["planner-rule", "study-load-review"],
        },
      },
      comparison: { rulePreserved: true, agentCount: 2 },
      workflow: {
        name: "study-plan-multi-agent",
        version: "week08-route-a-v1",
        status: "completed",
        stages: [],
      },
    });
  };

  const result = await requestStudyAgentPlan({ payload, fetchImpl });

  assert.equal(request.url, "/api/v1/study-agent/run");
  assert.equal(request.options.method, "POST");
  assert.deepEqual(JSON.parse(request.options.body), payload);
  assert.equal(result.multiAgent.pattern, "bounded-specialist");
  assert.equal(result.multiAgent.roles[1].tools.length, 0);
  assert.equal(result.multiAgent.expertReview.assessment, "insufficient");
  assert.equal(result.comparison.agentCount, 2);
});

test("week08 frontend still compares deterministic plan independent of key order", () => {
  const left = {
    sessions: [{ id: "s1", date: "2026-09-17", start: "18:00", end: "20:00" }],
    scheduledMinutes: 120,
    remainingMinutes: 0,
  };
  const right = {
    remainingMinutes: 0,
    scheduledMinutes: 120,
    sessions: [{ end: "20:00", start: "18:00", date: "2026-09-17", id: "s1" }],
  };

  assert.equal(studyPlansMatch(left, right), true);
});
