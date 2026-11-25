import test from "node:test";
import assert from "node:assert/strict";
import { weeklyClasses } from "../src/data/demo.js";

import {
  requestStudyAgentPlan,
  requestStudyContextComparison,
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
    weeklyClasses: [],
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

test("week09 frontend calls same-case context comparison endpoint", async () => {
  const payload = {
    startDate: "2026-09-17",
    examDate: "2026-09-24",
    hours: 6,
    sessionHours: 2,
    allowedPeriods: ["afternoon", "evening"],
    courseName: "資料結構",
    weeklyClasses: [],
    personalEvents: [],
  };
  let request;
  const fetchImpl = async (url, options) => {
    request = { url, options };
    return jsonResponse({
      runId: "week09-compare-test",
      method: "few-shot prompting",
      sameCase: true,
      expectedAssessment: "balanced",
      versions: {
        baseline: {
          contextVersion: "week08-instruction-v1",
          output: { assessment: "concentrated" },
          evaluation: {
            pass: false,
            expectedAssessment: "balanced",
            actualAssessment: "concentrated",
          },
        },
        candidate: {
          contextVersion: "week09-few-shot-v1",
          output: { assessment: "balanced" },
          evaluation: {
            pass: true,
            expectedAssessment: "balanced",
            actualAssessment: "balanced",
          },
        },
      },
      observation: "Candidate 在固定評估規則下由未通過變為通過。",
    });
  };

  const result = await requestStudyContextComparison({ payload, fetchImpl });

  assert.equal(request.url, "/api/v1/study-agent/context-comparison");
  assert.equal(request.options.method, "POST");
  assert.deepEqual(JSON.parse(request.options.body), payload);
  assert.equal(result.sameCase, true);
  assert.equal(result.versions.baseline.evaluation.pass, false);
  assert.equal(result.versions.candidate.evaluation.pass, true);
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

test("frontend client sends the current timetable without credentials", async () => {
  const payload = {
    startDate: "2026-11-25",
    examDate: "2026-12-02",
    hours: 2,
    sessionHours: 2,
    allowedPeriods: ["afternoon"],
    courseName: "資料結構",
    weeklyClasses: weeklyClasses.map(
      ({ id, title, weekday, start, end, location }) => ({
        id,
        title,
        weekday,
        start,
        end,
        location,
      }),
    ),
    personalEvents: [],
  };
  const responseBody = {
    plan: {
      sessions: [],
      scheduledMinutes: 0,
      remainingMinutes: 120,
    },
    agent: {
      summary: "尚缺 120 分鐘。",
      warnings: ["請增加可安排時段。"],
      citations: ["planner-rule"],
      refused: false,
      framework: "OpenAI Responses API",
      tool: "get_validated_study_plan",
      model: "gpt-test",
    },
  };
  let captured;

  const response = await requestStudyAgentPlan({
    payload,
    endpoint: "/api/v1/study-agent/run",
    fetchImpl: async (url, options) => {
      captured = { url, options };
      return {
        ok: true,
        json: async () => responseBody,
      };
    },
  });

  assert.deepEqual(response, responseBody);
  assert.equal(captured.url, "/api/v1/study-agent/run");
  assert.equal(captured.options.headers.Authorization, undefined);
  assert.doesNotMatch(captured.options.body, /test-api-key|OPENAI_API_KEY/);
  const sent = JSON.parse(captured.options.body);
  assert.equal(sent.weeklyClasses.length, weeklyClasses.length);
  assert.deepEqual(sent.weeklyClasses[0], {
    id: "class-calculus-mon",
    title: "微積分（一）",
    weekday: 1,
    start: "09:00",
    end: "10:50",
    location: "文薈樓 J101",
  });
});
