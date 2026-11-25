import test from "node:test";
import assert from "node:assert/strict";
import {
  confirmEventAdjustment,
  loadAcademicState,
  loadPlannerState,
  migrateLegacyPlannerState,
  previewEventAdjustment,
  replaceStudySchedule,
  saveTask,
} from "../src/lib/plannerApiClient.js";

function response(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

test("planner API loads the four backend-owned state groups", async () => {
  const fetchImpl = async (url) => {
    if (url.includes("/tasks?"))
      return response({
        data: [
          {
            task_id: "task-1",
            title: "後端待辦",
            type: "assignment",
            course_id: "course-demo-001",
            due_date: "2026-09-20",
            due_time: "10:00",
            description: "ui-course:資料結構",
            completed: false,
          },
        ],
      });
    if (url.endsWith("/personal-events")) return response({ data: [] });
    if (url.endsWith("/study-schedule")) return response({ data: null });
    if (url.includes("/planned-courses?"))
      return response({
        data: [
          {
            planned_course_id: "planned-1",
            course_id: "elective-NN1194",
            target_semester_id: "semester-113-2",
          },
        ],
      });
    throw new Error(`Unexpected URL ${url}`);
  };

  const state = await loadPlannerState({ fetchImpl });
  assert.equal(state.tasks[0].title, "後端待辦");
  assert.equal(state.tasks[0].course, "資料結構");
  assert.equal(state.tasks[0].type, "作業");
  assert.equal(state.plannedCourses[0].course_id, "elective-NN1194");
  assert.deepEqual(state.studySessions, []);
});

test("academic state loads 115 rules, courses, records and timetable from Flask", async () => {
  const fetchImpl = async (url) => {
    if (url.endsWith("/me"))
      return response({
        data: {
          rule_set_id: "nutn-csie-115-integrated-v2",
          current_semester_id: "semester-115-1",
        },
      });
    if (url.includes("/graduation-rules/"))
      return response({
        data: {
          rule_set_id: "nutn-csie-115-integrated-v2",
          planning_courses: [
            {
              course_id: "nutn-115-nn1018",
              course_code: "NN1018",
              name: "資料結構",
              credits: 3,
              type: "專業必修",
              credit_category: "department_required",
              recommended_term: "大二上",
            },
          ],
        },
      });
    if (url.includes("/programs?")) return response({ data: [] });
    if (url.endsWith("/enrollments"))
      return response({
        data: [
          {
            enrollment_id: "enrollment-1",
            course_id: "nutn-115-nn1018",
            enrollment_status: "in_progress",
            course_snapshot: { name: "資料結構" },
          },
        ],
      });
    if (url.includes("/timetable-entries?"))
      return response({
        data: [
          {
            entry_id: "entry-1",
            course_id: "nutn-115-nn1018",
            meetings: [
              {
                weekday: 4,
                start_time: "09:00",
                end_time: "10:50",
                campus_id: "fucheng",
                location: "J201",
              },
              {
                weekday: 7,
                start_time: "09:00",
                end_time: "10:50",
                campus_id: "fucheng",
                location: "J201",
              },
            ],
          },
        ],
      });
    if (url.endsWith("/graduation-progress"))
      return response({
        data: { rule_set_id: "nutn-csie-115-integrated-v2" },
      });
    throw new Error(`Unexpected URL ${url}`);
  };

  const state = await loadAcademicState({ fetchImpl });
  assert.equal(state.rule.rule_set_id, "nutn-csie-115-integrated-v2");
  assert.equal(state.courses[0].status, "inProgress");
  assert.deepEqual(state.weeklyClasses[0], {
    id: "entry-1:0",
    courseId: "nutn-115-nn1018",
    title: "資料結構",
    weekday: 4,
    start: "09:00",
    end: "10:50",
    location: "J201",
    campus: "fucheng",
    tone: "blue",
  });
  assert.equal(state.weeklyClasses[1].weekday, 0);
});

test("task loading follows server pagination so older tasks remain accessible", async () => {
  const task = { title: "待辦", type: "todo", completed: false };
  const fetchImpl = async (url) => {
    if (url.endsWith("offset=0")) {
      return response({
        data: Array.from({ length: 200 }, (_, index) => ({
          ...task,
          task_id: `task-${index}`,
        })),
        meta: { total: 201 },
      });
    }
    if (url.endsWith("offset=200")) {
      return response({
        data: [{ ...task, task_id: "task-200" }],
        meta: { total: 201 },
      });
    }
    if (url.endsWith("/study-schedule")) return response({ data: null });
    return response({ data: [] });
  };
  const state = await loadPlannerState({ fetchImpl });
  assert.equal(state.tasks.length, 201);
  assert.equal(state.tasks.at(-1).id, "task-200");
});

test("editing an undated task preserves notes, priority, completion and linked records", async () => {
  const fetchImpl = async (url, init) => {
    assert.equal(url, "/api/v1/tasks/task-1");
    assert.equal(init.method, "PATCH");
    assert.deepEqual(JSON.parse(init.body), {
      title: "更新後的待辦",
      type: "todo",
      due_date: null,
      due_time: null,
    });
    return response({ data: { task_id: "task-1", title: "更新後的待辦" } });
  };
  await saveTask(
    {
      backendId: "task-1",
      title: "更新後的待辦",
      course: "資料結構",
      date: "",
      time: "15:00",
      previous: { course: "資料結構", description: "已存在的筆記" },
    },
    { fetchImpl },
  );
});

test("event adjustment preview and confirmation share the event and update the saved schedule", async () => {
  const item = {
    backendId: "event-1",
    title: "聚會",
    date: "2026-11-29",
    start: "18:00",
    end: "19:00",
  };
  const requests = [];
  const fetchImpl = async (url, init) => {
    const body = JSON.parse(init.body);
    requests.push({ url, body });
    if (url.endsWith("/preview"))
      return response({ data: { preview_token: "snapshot", moves: [] } });
    return response({
      data: {
        event: { event_id: "event-1", ...body.event },
        study_schedule: {
          plan: { plan_id: "plan-1" },
          plan_version: 4,
          sessions: [
            {
              session_id: "session-1",
              plan_id: "plan-1",
              title: "移動後的複習",
              starts_at: "2026-11-29T19:00:00+08:00",
              ends_at: "2026-11-29T20:00:00+08:00",
            },
          ],
        },
      },
    });
  };
  const preview = await previewEventAdjustment(item, { fetchImpl });
  const saved = await confirmEventAdjustment(item, preview.preview_token, {
    fetchImpl,
  });
  assert.equal(
    requests[0].url,
    "/api/v1/personal-events/study-adjustment/preview",
  );
  assert.equal(
    requests[1].url,
    "/api/v1/personal-events/study-adjustment/commit",
  );
  assert.deepEqual(requests[1].body, {
    ...requests[0].body,
    preview_token: "snapshot",
  });
  assert.equal(saved.event.backendId, "event-1");
  assert.equal(saved.sessions[0].start, "19:00");
  assert.equal(saved.sessions[0].planVersion, 4);
});

test("task writes use the Flask task contract instead of localStorage", async () => {
  let captured;
  const saved = await saveTask(
    {
      id: "task-local",
      title: "整理筆記",
      course: "資料結構",
      date: "2026-09-17",
      time: "20:00",
      type: "待辦",
      completed: false,
    },
    {
      fetchImpl: async (url, init) => {
        captured = { url, init, body: JSON.parse(init.body) };
        return response({
          data: {
            task_id: "task-backend",
            ...captured.body,
          },
        });
      },
    },
  );

  assert.equal(captured.url, "/api/v1/tasks");
  assert.equal(captured.init.method, "POST");
  assert.equal(captured.body.course_id, "course-demo-001");
  assert.equal(captured.body.description, "ui-course:資料結構");
  assert.equal(saved.backendId, "task-backend");
});

test("study schedule replacement sends plan and sessions in one request", async () => {
  let captured;
  const result = await replaceStudySchedule(
    {
      request: {
        courseId: "data-structures",
        startDate: "2026-09-17",
        examDate: "2026-09-24",
        hours: 2,
        sessionHours: 2,
        allowedPeriods: ["evening"],
      },
      sessions: [
        {
          title: "資料結構複習",
          date: "2026-09-17",
          start: "18:00",
          end: "20:00",
        },
      ],
    },
    {
      fetchImpl: async (url, init) => {
        captured = { url, body: JSON.parse(init.body) };
        return response({
          data: {
            plan: { plan_id: "plan-1" },
            plan_id: "plan-1",
            plan_version: 2,
            sessions: [
              {
                session_id: "session-1",
                plan_id: "plan-1",
                title: "資料結構複習",
                starts_at: "2026-09-17T18:00:00+08:00",
                ends_at: "2026-09-17T20:00:00+08:00",
              },
            ],
          },
        });
      },
    },
  );

  assert.equal(captured.url, "/api/v1/study-schedule");
  assert.equal(captured.body.plan.course_id, "course-demo-001");
  assert.equal(captured.body.plan.allowed_windows.length, 7);
  assert.equal(result.sessions[0].planVersion, 2);
  assert.equal(result.sessions[0].date, "2026-09-17");
});

test("a conflicting legacy study schedule does not block backend initialization", async () => {
  const values = new Map([
    [
      "nutn-study-v1",
      JSON.stringify([
        {
          title: "舊版複習時段",
          date: "2026-09-17",
          start: "09:00",
          end: "11:00",
        },
      ]),
    ],
  ]);
  const storage = {
    getItem: (key) => values.get(key) || null,
    removeItem: (key) => values.delete(key),
  };
  const backendState = {
    tasks: [],
    personalEvents: [],
    studyPlan: null,
    studySessions: [],
    plannedCourses: [],
  };

  const state = await migrateLegacyPlannerState(backendState, {
    storage,
    fetchImpl: async (url) => {
      assert.equal(url, "/api/v1/study-schedule");
      return response(
        {
          error: {
            code: "SCHEDULE_CONFLICT",
            message: "讀書時段和課表衝突。",
          },
        },
        409,
      );
    },
  });

  assert.deepEqual(state.tasks, []);
  assert.equal(state.migrationWarnings.length, 1);
  assert.equal(state.migrationWarnings[0].key, "nutn-study-v1");
  assert.ok(values.has("nutn-study-v1"));
});
