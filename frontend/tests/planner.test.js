import test from "node:test";
import assert from "node:assert/strict";
import { initialEvents, weeklyClasses } from "../src/data/demo.js";
import {
  eventsOnDate,
  findEventConflict,
  overlaps,
  planStudySessions,
  weekStart,
} from "../src/lib/planner.js";

test("a Thursday resolves to the Monday of the same week", () => {
  assert.equal(weekStart("2026-09-17"), "2026-09-14");
});

test("weekly classes and personal events appear together", () => {
  const events = eventsOnDate("2026-09-17", weeklyClasses, initialEvents);
  assert.ok(events.some((event) => event.title === "資料結構"));
  assert.ok(events.some((event) => event.title === "社團會議"));
});

test("a private event overlapping a class is reported", () => {
  const conflict = findEventConflict(
    { date: "2026-09-17", start: "09:30", end: "10:30" },
    weeklyClasses,
    initialEvents,
  );
  assert.equal(conflict?.title, "資料結構");
});

test("study sessions fit before the exam without overlapping existing events", () => {
  const result = planStudySessions({
    startDate: "2026-09-17",
    examDate: "2026-09-24",
    hours: 6,
    sessionHours: 2,
    allowedPeriods: ["afternoon", "evening"],
    courseName: "資料結構",
    weeklyClasses,
    personalEvents: initialEvents,
  });
  assert.equal(result.scheduledMinutes, 360);
  assert.equal(result.remainingMinutes, 0);
  assert.equal(result.sessions.length, 3);
  for (const session of result.sessions) {
    assert.ok(session.date < "2026-09-24");
    const occupied = eventsOnDate(session.date, weeklyClasses, initialEvents);
    assert.ok(occupied.every((event) => !overlaps(session, event)));
    assert.ok(
      result.sessions
        .filter((other) => other.id !== session.id)
        .every((other) => !overlaps(session, other)),
    );
  }
});

test("insufficient available time is reported instead of creating conflicts", () => {
  const result = planStudySessions({
    startDate: "2026-09-17",
    examDate: "2026-09-18",
    hours: 10,
    sessionHours: 2,
    allowedPeriods: ["morning"],
    courseName: "資料結構",
    weeklyClasses,
    personalEvents: initialEvents,
  });
  assert.equal(result.scheduledMinutes, 0);
  assert.equal(result.remainingMinutes, 600);
});
