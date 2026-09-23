import React, { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard.jsx";
import StudyPlanner from "./components/StudyPlanner.jsx";
import CoursePlanner from "./components/CoursePlanner.jsx";
import GraduationProgress from "./components/GraduationProgress.jsx";
import ItemDialog from "./components/ItemDialog.jsx";
import CampusMapDialog from "./components/CampusMapDialog.jsx";
import Icon from "./components/Icon.jsx";
import { MobileNav, Sidebar } from "./components/Navigation.jsx";
import {
  DEMO_DATE,
  initialEvents,
  initialTasks,
  weeklyClasses,
} from "./data/demo.js";
import { planStudySessions } from "./lib/planner.js";

function loadStored(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return Array.isArray(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

const initialStudyPlan = planStudySessions({
  startDate: DEMO_DATE,
  examDate: "2026-09-24",
  hours: 6,
  sessionHours: 2,
  allowedPeriods: ["afternoon", "evening"],
  courseName: "資料結構",
  weeklyClasses,
  personalEvents: initialEvents,
}).sessions;

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [selectedDate, setSelectedDate] = useState(DEMO_DATE);
  const [tasks, setTasks] = useState(() =>
    loadStored("nutn-tasks-v2", initialTasks),
  );
  const [personalEvents, setPersonalEvents] = useState(() =>
    loadStored("nutn-events-v1", initialEvents),
  );
  const [studySessions, setStudySessions] = useState(() =>
    loadStored("nutn-study-v1", initialStudyPlan),
  );
  const [plannedCourseIds, setPlannedCourseIds] = useState(() =>
    loadStored("nutn-courses-v1", []),
  );
  const [dialog, setDialog] = useState(null);
  const [mapDialog, setMapDialog] = useState(null);

  useEffect(() => {
    localStorage.setItem("nutn-tasks-v2", JSON.stringify(tasks));
  }, [tasks]);
  useEffect(() => {
    localStorage.setItem("nutn-events-v1", JSON.stringify(personalEvents));
  }, [personalEvents]);
  useEffect(() => {
    localStorage.setItem("nutn-study-v1", JSON.stringify(studySessions));
  }, [studySessions]);
  useEffect(() => {
    localStorage.setItem("nutn-courses-v1", JSON.stringify(plannedCourseIds));
  }, [plannedCourseIds]);

  function saveItem(item) {
    if (item.kind === "event") {
      setPersonalEvents((current) =>
        current.some((event) => event.id === item.id)
          ? current.map((event) => (event.id === item.id ? item : event))
          : [...current, item],
      );
    } else {
      setTasks((current) =>
        current.some((task) => task.id === item.id)
          ? current.map((task) =>
              task.id === item.id
                ? { ...item, completed: task.completed }
                : task,
            )
          : [...current, { ...item, completed: false }],
      );
    }
    setDialog(null);
  }

  function deleteItem(item) {
    if (dialog?.kind === "event")
      setPersonalEvents((current) =>
        current.filter((event) => event.id !== item.id),
      );
    else setTasks((current) => current.filter((task) => task.id !== item.id));
    setDialog(null);
  }

  function toggleCourse(courseId) {
    setPlannedCourseIds((current) =>
      current.includes(courseId)
        ? current.filter((id) => id !== courseId)
        : [...current, courseId],
    );
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
          <span>校園日程</span>
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
        {activePage === "dashboard" && (
          <Dashboard
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            tasks={tasks}
            personalEvents={personalEvents}
            studySessions={studySessions}
            onToggleTask={(taskId) =>
              setTasks((current) =>
                current.map((task) =>
                  task.id === taskId
                    ? { ...task, completed: !task.completed }
                    : task,
                ),
              )
            }
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
            onUpdateSessions={setStudySessions}
          />
        )}
        {activePage === "courses" && (
          <CoursePlanner
            plannedCourseIds={plannedCourseIds}
            onToggleCourse={toggleCourse}
          />
        )}
        {activePage === "graduation" && (
          <GraduationProgress
            plannedCourseIds={plannedCourseIds}
            onToggleCourse={toggleCourse}
            onNavigate={setActivePage}
          />
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
          onClose={() => setDialog(null)}
          onSave={saveItem}
          onDelete={deleteItem}
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
