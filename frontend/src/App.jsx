import React, { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard.jsx";
import StudyPlanner from "./components/StudyPlanner.jsx";
import CoursePlanner from "./components/CoursePlanner.jsx";
import GraduationProgress from "./components/GraduationProgress.jsx";
import GateEvidence from "./components/GateEvidence.jsx";
import ItemDialog from "./components/ItemDialog.jsx";
import CampusMapDialog from "./components/CampusMapDialog.jsx";
import Icon from "./components/Icon.jsx";
import { MobileNav, Sidebar } from "./components/Navigation.jsx";
import { DEMO_DATE } from "./data/demo.js";
import {
  addPlannedCourse,
  deletePersonalEvent,
  deletePlannedCourse,
  deleteStudySession,
  deleteTask,
  loadApplicationState,
  migrateLegacyPlannerState,
  replaceStudySchedule,
  savePersonalEvent,
  saveTask,
  setTaskCompleted,
  updateStudySession,
} from "./lib/plannerApiClient.js";

let plannerInitialization;

function initializePlannerState() {
  if (!plannerInitialization) {
    plannerInitialization = loadApplicationState()
      .then(async (state) => ({
        ...state,
        ...(await migrateLegacyPlannerState(state, {
          targetSemesterId:
            state.academic.profile.current_semester_id || "semester-115-1",
        })),
      }))
      .catch((error) => {
        plannerInitialization = undefined;
        throw error;
      });
  }
  return plannerInitialization;
}

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [selectedDate, setSelectedDate] = useState(DEMO_DATE);
  const [tasks, setTasks] = useState([]);
  const [personalEvents, setPersonalEvents] = useState([]);
  const [studyPlan, setStudyPlan] = useState(null);
  const [studySessions, setStudySessions] = useState([]);
  const [plannedCourses, setPlannedCourses] = useState([]);
  const [academic, setAcademic] = useState({
    profile: {},
    rule: null,
    programs: [],
    enrollments: [],
    timetableEntries: [],
    courses: [],
    weeklyClasses: [],
    graduationProgress: null,
  });
  const [backendState, setBackendState] = useState({
    status: "loading",
    message: "正在從後端讀取個人安排。",
  });
  const [dialog, setDialog] = useState(null);
  const [mapDialog, setMapDialog] = useState(null);
  const plannedCourseIds = plannedCourses.map((item) => item.course_id);

  useEffect(() => {
    let active = true;
    initializePlannerState()
      .then((state) => {
        if (!active) return;
        setTasks(state.tasks);
        setPersonalEvents(state.personalEvents);
        setStudyPlan(state.studyPlan);
        setStudySessions(state.studySessions);
        setPlannedCourses(state.plannedCourses);
        setAcademic(state.academic);
        const integrated =
          state.academic.rule?.rule_set_id === "nutn-csie-115-integrated-v2";
        const migrationWarnings = state.migrationWarnings || [];
        setBackendState({
          status: integrated && !migrationWarnings.length ? "ready" : "error",
          message: !integrated
            ? "後端尚未選用 115 整合規格，請執行 scripts/select-demo-profile-115.sh。"
            : migrationWarnings.length
              ? `115 後端資料已載入；${migrationWarnings.length} 組舊版瀏覽器資料因衝突而保留，未覆寫 SQLite。`
              : "待辦、行程、讀書時段、課表、課程、修課紀錄與畢業規則已由 Flask／SQLite 管理。",
        });
      })
      .catch((error) => {
        if (!active) return;
        setBackendState({
          status: "error",
          message: error instanceof Error ? error.message : String(error),
        });
      });
    return () => {
      active = false;
    };
  }, []);

  function reportBackendError(error) {
    const message = error instanceof Error ? error.message : String(error);
    setBackendState({ status: "error", message });
    return error instanceof Error ? error : new Error(message);
  }

  function reportBackendReady(message) {
    setBackendState({ status: "ready", message });
  }

  async function saveItem(item) {
    try {
      if (item.kind === "event") {
        const original = personalEvents.find((event) => event.id === item.id);
        const saved = await savePersonalEvent({
          ...item,
          backendId: original?.backendId,
        });
        setPersonalEvents((current) =>
          current.some((event) => event.id === saved.id)
            ? current.map((event) => (event.id === saved.id ? saved : event))
            : [...current, saved],
        );
      } else {
        const original = tasks.find((task) => task.id === item.id);
        const saved = await saveTask({
          ...item,
          backendId: original?.backendId,
          completed: original?.completed || false,
        });
        setTasks((current) =>
          current.some((task) => task.id === saved.id)
            ? current.map((task) => (task.id === saved.id ? saved : task))
            : [...current, saved],
        );
      }
      reportBackendReady("已儲存到後端 SQLite。");
      setDialog(null);
    } catch (error) {
      throw reportBackendError(error);
    }
  }

  async function removeItem(item) {
    try {
      if (dialog?.kind === "event") {
        await deletePersonalEvent(item);
        setPersonalEvents((current) =>
          current.filter((event) => event.id !== item.id),
        );
      } else {
        await deleteTask(item);
        setTasks((current) => current.filter((task) => task.id !== item.id));
      }
      reportBackendReady("已從後端刪除資料。");
      setDialog(null);
    } catch (error) {
      throw reportBackendError(error);
    }
  }

  async function toggleTask(taskId) {
    const task = tasks.find((item) => item.id === taskId);
    if (!task) return;
    try {
      const saved = await setTaskCompleted(task, !task.completed);
      setTasks((current) =>
        current.map((item) => (item.id === saved.id ? saved : item)),
      );
      reportBackendReady("待辦狀態已同步到後端。");
    } catch (error) {
      reportBackendError(error);
    }
  }

  async function toggleCourse(courseId) {
    const existing = plannedCourses.find((item) => item.course_id === courseId);
    try {
      if (existing) {
        const courseName =
          academic.courses.find((course) => course.id === courseId)?.name ||
          "這門課程";
        if (
          typeof globalThis.confirm === "function" &&
          !globalThis.confirm(`確定要把「${courseName}」移出修課規劃嗎？`)
        ) {
          return;
        }
        await deletePlannedCourse(existing);
        setPlannedCourses((current) =>
          current.filter(
            (item) => item.planned_course_id !== existing.planned_course_id,
          ),
        );
      } else {
        const saved = await addPlannedCourse(
          courseId,
          academic.profile.current_semester_id || "semester-115-1",
        );
        setPlannedCourses((current) => [...current, saved]);
      }
      reportBackendReady("115 修課規劃已同步到後端。");
    } catch (error) {
      reportBackendError(error);
    }
  }

  async function replaceSchedule(payload) {
    try {
      const saved = await replaceStudySchedule(payload);
      setStudyPlan(saved.plan);
      setStudySessions(saved.sessions);
      reportBackendReady("讀書計畫與時段已儲存到後端。");
      return saved.sessions;
    } catch (error) {
      throw reportBackendError(error);
    }
  }

  async function editStudySession(session, draft) {
    try {
      const saved = await updateStudySession(session, draft);
      setStudySessions(saved.sessions);
      reportBackendReady("讀書時段已更新到後端。");
      return saved.sessions;
    } catch (error) {
      throw reportBackendError(error);
    }
  }

  async function removeStudySession(session) {
    try {
      const saved = await deleteStudySession(session);
      setStudyPlan(saved.plan || studyPlan);
      setStudySessions(saved.sessions);
      reportBackendReady("讀書時段已從後端刪除。");
      return saved.sessions;
    } catch (error) {
      throw reportBackendError(error);
    }
  }

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className="mobile-topbar">
        <button
          type="button"
          className="mobile-brand"
          onClick={() => setActivePage("dashboard")}
        >
          <Icon name="calendar" size={25} />
          <span>校園日程・115</span>
        </button>
        <div className="mobile-top-actions">
          <button
            type="button"
            className="icon-button"
            onClick={() => setMapDialog({ campus: "fucheng" })}
            aria-label="查看校區地圖"
          >
            <Icon name="map" size={19} />
          </button>
          <button
            type="button"
            className="primary-button mobile-add"
            onClick={() => setDialog({ kind: "task" })}
          >
            <Icon name="plus" size={19} />
            新增
          </button>
        </div>
      </div>
      <main className="main-content">
        <div
          className={`notice ${backendState.status === "error" ? "notice-warning" : "notice-info"}`}
          role={backendState.status === "error" ? "alert" : "status"}
        >
          <Icon
            name={backendState.status === "error" ? "alert" : "check"}
            size={18}
          />
          {backendState.message}
        </div>
        {activePage === "dashboard" && (
          <Dashboard
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            tasks={tasks}
            personalEvents={personalEvents}
            studySessions={studySessions}
            weeklyClasses={academic.weeklyClasses}
            graduationProgress={academic.graduationProgress}
            academicYear={academic.rule?.admission_year || 115}
            onToggleTask={toggleTask}
            onEditTask={(item) => setDialog({ kind: "task", initial: item })}
            onEditEvent={(item) => setDialog({ kind: "event", initial: item })}
            onAdd={(kind) => setDialog({ kind })}
            onOpenMap={(campus, location) => setMapDialog({ campus, location })}
            onNavigate={setActivePage}
          />
        )}
        {activePage === "study" && (
          <StudyPlanner
            personalEvents={personalEvents}
            studySessions={studySessions}
            courses={academic.courses}
            weeklyClasses={academic.weeklyClasses}
            onReplaceSchedule={replaceSchedule}
            onUpdateSession={editStudySession}
            onDeleteSession={removeStudySession}
          />
        )}
        {activePage === "courses" && (
          <CoursePlanner
            plannedCourseIds={plannedCourseIds}
            onToggleCourse={toggleCourse}
            academic={academic}
          />
        )}
        {activePage === "graduation" && (
          <GraduationProgress
            plannedCourseIds={plannedCourseIds}
            onToggleCourse={toggleCourse}
            onNavigate={setActivePage}
            initialAcademic={academic}
          />
        )}
        {activePage === "evidence" && (
          <GateEvidence onNavigate={setActivePage} />
        )}
      </main>
      <MobileNav activePage={activePage} onNavigate={setActivePage} />
      {dialog && (
        <ItemDialog
          key={`${dialog.kind}-${dialog.initial?.id || "new"}`}
          initial={dialog.initial}
          initialKind={dialog.kind}
          selectedDate={selectedDate}
          personalEvents={personalEvents}
          weeklyClasses={academic.weeklyClasses}
          onClose={() => setDialog(null)}
          onSave={saveItem}
          onDelete={removeItem}
        />
      )}
      {mapDialog && (
        <CampusMapDialog
          initialCampus={mapDialog.campus}
          location={mapDialog.location}
          onClose={() => setMapDialog(null)}
        />
      )}
    </div>
  );
}
