const API_ROOT = "/api/v1";
export const TARGET_SEMESTER_113 = "semester-113-2";
export const TARGET_SEMESTER_115 = "semester-115-1";

const taskTypesToApi = {
  待辦: "todo",
  作業: "assignment",
  報告: "report",
  考試: "exam",
  複習: "review",
};
const taskTypesFromApi = Object.fromEntries(
  Object.entries(taskTypesToApi).map(([label, value]) => [value, label]),
);

const courseNameToApiId = {
  "微積分（一）": "ui-calculus",
  英文閱讀與寫作: "ui-english",
  "程式設計（一）": "course-demo-002",
  計算機程式設計: "course-demo-002",
  資料結構: "course-demo-001",
  普通心理學: "ui-psychology",
  離散數學: "course-demo-003",
  專題討論: "ui-seminar",
};
const courseIdToName = Object.fromEntries(
  Object.entries(courseNameToApiId).map(([name, id]) => [id, name]),
);
const studyCourseToApiId = {
  calculus: "ui-calculus",
  english: "ui-english",
  programming: "course-demo-002",
  "data-structures": "course-demo-001",
  psychology: "ui-psychology",
};

const periodWindows = {
  morning: ["08:00", "12:00"],
  afternoon: ["13:00", "18:00"],
  evening: ["18:00", "22:00"],
};

export class PlannerApiError extends Error {
  constructor(message, { code, status, fields, conflicts } = {}) {
    super(message);
    this.name = "PlannerApiError";
    this.code = code;
    this.status = status;
    this.fields = fields || [];
    this.conflicts = conflicts || [];
  }
}

async function requestData(
  path,
  { method = "GET", body, fetchImpl = globalThis.fetch } = {},
) {
  if (typeof fetchImpl !== "function")
    throw new PlannerApiError("目前無法連線後端。", {
      code: "FETCH_UNAVAILABLE",
    });
  const response = await fetchImpl(`${API_ROOT}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const problem = payload.error || {};
    throw new PlannerApiError(
      problem.message || problem || `後端回傳 HTTP ${response.status}`,
      {
        code: problem.code,
        status: response.status,
        fields: problem.fields,
        conflicts: problem.conflicts,
      },
    );
  }
  return payload.data;
}

function uiCourseDescription(course) {
  return course ? `ui-course:${course}` : "";
}

function courseFromTask(task) {
  if (task.description?.startsWith("ui-course:"))
    return task.description.slice("ui-course:".length);
  return courseIdToName[task.course_id] || "";
}

function taskFromApi(task) {
  return {
    id: task.task_id,
    backendId: task.task_id,
    title: task.title,
    course: courseFromTask(task),
    date: task.due_date || "",
    time: task.due_time || "",
    type: taskTypesFromApi[task.type] || "待辦",
    completed: task.completed,
  };
}

function taskToApi(task) {
  return {
    title: task.title,
    type: taskTypesToApi[task.type] || "todo",
    course_id: courseNameToApiId[task.course] || null,
    due_date: task.date || null,
    due_time: task.date && task.time ? task.time : null,
    description: uiCourseDescription(task.course),
    priority: "medium",
    completed: Boolean(task.completed),
    event_id: null,
  };
}

function localParts(value) {
  return { date: value.slice(0, 10), time: value.slice(11, 16) };
}

function eventFromApi(event) {
  const start = localParts(event.starts_at);
  const end = localParts(event.ends_at);
  return {
    id: event.event_id,
    backendId: event.event_id,
    title: event.title,
    date: start.date,
    start: start.time,
    end: end.time,
    location: event.location || "",
    tone: "mint",
  };
}

function eventToApi(event) {
  return {
    title: event.title,
    starts_at: `${event.date}T${event.start}:00+08:00`,
    ends_at: `${event.date}T${event.end}:00+08:00`,
    location: event.location || null,
  };
}

function sessionFromApi(session, planVersion) {
  const start = localParts(session.starts_at);
  const end = localParts(session.ends_at);
  return {
    id: session.session_id,
    backendId: session.session_id,
    planId: session.plan_id,
    planVersion,
    title: session.title,
    date: start.date,
    start: start.time,
    end: end.time,
    location: "自行安排",
    tone: "amber",
  };
}

function scheduleFromApi(schedule) {
  if (!schedule) return { plan: null, sessions: [] };
  return {
    plan: schedule.plan,
    sessions: schedule.sessions.map((session) =>
      sessionFromApi(session, schedule.plan_version),
    ),
  };
}

export async function loadPlannerState({
  fetchImpl = globalThis.fetch,
  targetSemesterId = TARGET_SEMESTER_115,
} = {}) {
  const [tasks, personalEvents, studySchedule, plannedCourses] =
    await Promise.all([
      requestData("/tasks?limit=200", { fetchImpl }),
      requestData("/personal-events", { fetchImpl }),
      requestData("/study-schedule", { fetchImpl }),
      requestData(`/planned-courses?target_semester_id=${targetSemesterId}`, {
        fetchImpl,
      }),
    ]);
  const schedule = scheduleFromApi(studySchedule);
  return {
    tasks: tasks.map(taskFromApi),
    personalEvents: personalEvents.map(eventFromApi),
    studyPlan: schedule.plan,
    studySessions: schedule.sessions,
    plannedCourses,
  };
}

function academicCourseFromApi(course, enrollments) {
  const enrollment = enrollments.find(
    (item) => item.course_id === course.course_id,
  );
  return {
    id: course.course_id,
    name: course.name,
    code: course.course_code,
    credits: course.credits,
    type: course.type,
    category: course.credit_category,
    recommendedTerm: course.recommended_term || "未指定",
    status:
      enrollment?.enrollment_status === "finished"
        ? "completed"
        : enrollment?.enrollment_status === "in_progress"
          ? "inProgress"
          : "available",
  };
}

function weeklyClassesFromApi(entries, courses, enrollments) {
  const names = new Map(courses.map((course) => [course.id, course.name]));
  enrollments.forEach((enrollment) =>
    names.set(enrollment.course_id, enrollment.course_snapshot?.name),
  );
  return entries.flatMap((entry) =>
    entry.meetings.map((meeting, index) => ({
      id: `${entry.entry_id}:${index}`,
      courseId: entry.course_id,
      title: names.get(entry.course_id) || "未命名課程",
      weekday: meeting.weekday,
      start: meeting.start_time,
      end: meeting.end_time,
      location: meeting.location || "地點待確認",
      campus: meeting.campus_id || "fucheng",
      tone: "blue",
    })),
  );
}

export async function loadAcademicState({
  fetchImpl = globalThis.fetch,
  profile: suppliedProfile,
} = {}) {
  const profile = suppliedProfile || (await requestData("/me", { fetchImpl }));
  if (!profile.rule_set_id) {
    return {
      profile,
      rule: null,
      programs: [],
      enrollments: [],
      timetableEntries: [],
      courses: [],
      weeklyClasses: [],
      graduationProgress: null,
    };
  }
  const semesterId = profile.current_semester_id || TARGET_SEMESTER_115;
  const [rule, programs, enrollments, timetableEntries, graduationProgress] =
    await Promise.all([
      requestData(`/graduation-rules/${profile.rule_set_id}`, { fetchImpl }),
      requestData(`/programs?rule_set_id=${profile.rule_set_id}`, {
        fetchImpl,
      }),
      requestData("/enrollments", { fetchImpl }),
      requestData(`/timetable-entries?semester_id=${semesterId}`, {
        fetchImpl,
      }),
      requestData("/graduation-progress", { fetchImpl }),
    ]);
  const courses = (rule.planning_courses || []).map((course) =>
    academicCourseFromApi(course, enrollments),
  );
  return {
    profile,
    rule,
    programs,
    enrollments,
    timetableEntries,
    courses,
    weeklyClasses: weeklyClassesFromApi(timetableEntries, courses, enrollments),
    graduationProgress,
  };
}

export async function loadApplicationState({
  fetchImpl = globalThis.fetch,
} = {}) {
  const profile = await requestData("/me", { fetchImpl });
  const targetSemesterId = profile.current_semester_id || TARGET_SEMESTER_115;
  const [planner, academic] = await Promise.all([
    loadPlannerState({ fetchImpl, targetSemesterId }),
    loadAcademicState({ fetchImpl, profile }),
  ]);
  return { ...planner, academic };
}

export async function saveTask(item, options = {}) {
  const path = item.backendId ? `/tasks/${item.backendId}` : "/tasks";
  const method = item.backendId ? "PATCH" : "POST";
  return taskFromApi(
    await requestData(path, { ...options, method, body: taskToApi(item) }),
  );
}

export async function deleteTask(item, options = {}) {
  await requestData(`/tasks/${item.backendId || item.id}`, {
    ...options,
    method: "DELETE",
  });
}

export async function setTaskCompleted(item, completed, options = {}) {
  return taskFromApi(
    await requestData(`/tasks/${item.backendId || item.id}`, {
      ...options,
      method: "PATCH",
      body: { completed },
    }),
  );
}

export async function savePersonalEvent(item, options = {}) {
  const path = item.backendId
    ? `/personal-events/${item.backendId}`
    : "/personal-events";
  const method = item.backendId ? "PATCH" : "POST";
  return eventFromApi(
    await requestData(path, { ...options, method, body: eventToApi(item) }),
  );
}

export async function deletePersonalEvent(item, options = {}) {
  await requestData(`/personal-events/${item.backendId || item.id}`, {
    ...options,
    method: "DELETE",
  });
}

export async function addPlannedCourse(
  courseId,
  targetSemesterId = TARGET_SEMESTER_115,
  options = {},
) {
  return requestData("/planned-courses", {
    ...options,
    method: "POST",
    body: {
      target_semester_id: targetSemesterId,
      course_id: courseId,
      offering_id: null,
    },
  });
}

export async function deletePlannedCourse(record, options = {}) {
  await requestData(`/planned-courses/${record.planned_course_id}`, {
    ...options,
    method: "DELETE",
  });
}

function allowedWindows(periods) {
  return Array.from({ length: 7 }, (_, index) => index + 1).flatMap((weekday) =>
    periods.map((period) => ({
      weekday,
      start_time: periodWindows[period][0],
      end_time: periodWindows[period][1],
    })),
  );
}

export async function replaceStudySchedule(
  { request, sessions },
  options = {},
) {
  const courseId = studyCourseToApiId[request.courseId] || request.courseId;
  if (!courseId)
    throw new PlannerApiError("這門示範課程尚未對應到後端課程資料。", {
      code: "COURSE_MAPPING_MISSING",
    });
  const schedule = await requestData("/study-schedule", {
    ...options,
    method: "PUT",
    body: {
      plan: {
        course_id: courseId,
        exam_task_id: null,
        start_date: request.startDate,
        exam_date: request.examDate,
        target_minutes: Math.round(Number(request.hours) * 60),
        session_minutes: Math.round(Number(request.sessionHours) * 60),
        allowed_windows: allowedWindows(request.allowedPeriods),
      },
      sessions: sessions.map((session) => ({
        title: session.title,
        starts_at: `${session.date}T${session.start}:00+08:00`,
        ends_at: `${session.date}T${session.end}:00+08:00`,
      })),
    },
  });
  return scheduleFromApi(schedule);
}

export async function updateStudySession(session, draft, options = {}) {
  const result = await requestData(`/study-sessions/${session.backendId}`, {
    ...options,
    method: "PATCH",
    body: {
      plan_version: session.planVersion,
      starts_at: `${draft.date}T${draft.start}:00+08:00`,
      ends_at: `${draft.date}T${draft.end}:00+08:00`,
    },
  });
  return {
    plan: null,
    sessions: result.sessions.map((item) =>
      sessionFromApi(item, result.plan_version),
    ),
  };
}

export async function deleteStudySession(session, options = {}) {
  await requestData(
    `/study-sessions/${session.backendId}?plan_version=${session.planVersion}`,
    { ...options, method: "DELETE" },
  );
  const schedule = await requestData("/study-schedule", options);
  return scheduleFromApi(schedule);
}

function readLegacyArray(storage, key) {
  try {
    const value = JSON.parse(storage.getItem(key));
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export async function migrateLegacyPlannerState(
  backendState,
  {
    storage = globalThis.localStorage,
    fetchImpl = globalThis.fetch,
    targetSemesterId = TARGET_SEMESTER_115,
  } = {},
) {
  if (!storage) return backendState;
  const migrationWarnings = [];
  const migrations = [];
  const completedKeys = [];
  const migrateGroup = async (key, operation) => {
    try {
      await operation();
      storage.removeItem(key);
      completedKeys.push(key);
    } catch (error) {
      migrationWarnings.push({
        key,
        message: error instanceof Error ? error.message : String(error),
      });
    }
  };
  if (!backendState.tasks.length) {
    const tasks = readLegacyArray(storage, "nutn-tasks-v2");
    if (tasks.length) {
      migrations.push(
        migrateGroup("nutn-tasks-v2", () =>
          Promise.all(tasks.map((task) => saveTask(task, { fetchImpl }))),
        ),
      );
    }
  }
  if (!backendState.personalEvents.length) {
    const events = readLegacyArray(storage, "nutn-events-v1");
    if (events.length) {
      migrations.push(
        migrateGroup("nutn-events-v1", () =>
          Promise.all(
            events.map((event) => savePersonalEvent(event, { fetchImpl })),
          ),
        ),
      );
    }
  }
  if (!backendState.plannedCourses.length) {
    const courseIds = readLegacyArray(storage, "nutn-courses-v1");
    if (courseIds.length) {
      migrations.push(
        migrateGroup("nutn-courses-v1", () =>
          Promise.all(
            courseIds.map((courseId) =>
              addPlannedCourse(courseId, targetSemesterId, { fetchImpl }),
            ),
          ),
        ),
      );
    }
  }
  await Promise.all(migrations);

  if (!backendState.studySessions.length) {
    const sessions = readLegacyArray(storage, "nutn-study-v1");
    if (sessions.length) {
      const totalMinutes = sessions.reduce(
        (sum, item) =>
          sum +
          (Number(item.end.slice(0, 2)) * 60 + Number(item.end.slice(3, 5))) -
          (Number(item.start.slice(0, 2)) * 60 +
            Number(item.start.slice(3, 5))),
        0,
      );
      await migrateGroup("nutn-study-v1", () =>
        replaceStudySchedule(
          {
            request: {
              courseId: "data-structures",
              startDate: "2026-09-17",
              examDate: "2026-09-24",
              hours: Math.max(totalMinutes / 60, 0.5),
              sessionHours: 2,
              allowedPeriods: ["morning", "afternoon", "evening"],
            },
            sessions,
          },
          { fetchImpl },
        ),
      );
    }
  }
  const state = completedKeys.length
    ? await loadPlannerState({ fetchImpl, targetSemesterId })
    : backendState;
  return { ...state, migrationWarnings };
}
