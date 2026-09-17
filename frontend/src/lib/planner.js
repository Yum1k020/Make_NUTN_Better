export const WEEKDAYS = [
  "週日",
  "週一",
  "週二",
  "週三",
  "週四",
  "週五",
  "週六",
];

export function parseDate(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function toIso(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function addDays(iso, count) {
  const date = parseDate(iso);
  date.setDate(date.getDate() + count);
  return toIso(date);
}

export function weekStart(iso) {
  const day = parseDate(iso).getDay();
  return addDays(iso, -((day + 6) % 7));
}

export function formatDate(iso, includeYear = false) {
  const date = parseDate(iso);
  return `${includeYear ? `${date.getFullYear()} 年 ` : ""}${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

export function weekdayLabel(iso) {
  return WEEKDAYS[parseDate(iso).getDay()];
}

export function minutes(time) {
  const [hour, minute] = time.split(":").map(Number);
  return hour * 60 + minute;
}

export function overlaps(left, right) {
  return (
    left.date === right.date &&
    minutes(left.start) < minutes(right.end) &&
    minutes(right.start) < minutes(left.end)
  );
}

export function eventsOnDate(
  date,
  weeklyClasses,
  personalEvents = [],
  studySessions = [],
) {
  const weekday = parseDate(date).getDay();
  return [
    ...weeklyClasses
      .filter((item) => item.weekday === weekday)
      .map((item) => ({ ...item, date, kind: "class" })),
    ...personalEvents
      .filter((item) => item.date === date)
      .map((item) => ({ ...item, kind: "personal" })),
    ...studySessions
      .filter((item) => item.date === date)
      .map((item) => ({ ...item, kind: "study", tone: "amber" })),
  ].sort((a, b) => minutes(a.start) - minutes(b.start));
}

export function findEventConflict(
  candidate,
  weeklyClasses,
  personalEvents,
  ignoredId,
) {
  return eventsOnDate(
    candidate.date,
    weeklyClasses,
    personalEvents.filter((item) => item.id !== ignoredId),
  ).find((event) => overlaps(candidate, event));
}

const PERIODS = {
  morning: [8 * 60, 12 * 60],
  afternoon: [13 * 60, 18 * 60],
  evening: [18 * 60, 22 * 60],
};

function asTime(value) {
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
}

export function planStudySessions({
  startDate,
  examDate,
  hours,
  sessionHours,
  allowedPeriods,
  courseName,
  weeklyClasses,
  personalEvents,
}) {
  const targetMinutes = Math.round(Number(hours) * 60);
  const usualSessionMinutes = Math.round(Number(sessionHours) * 60);
  if (
    !Number.isFinite(targetMinutes) ||
    targetMinutes <= 0 ||
    !Number.isFinite(usualSessionMinutes) ||
    usualSessionMinutes <= 0 ||
    examDate <= startDate
  ) {
    return {
      sessions: [],
      scheduledMinutes: 0,
      remainingMinutes: Math.max(0, targetMinutes || 0),
    };
  }

  const dates = [];
  for (
    let date = startDate;
    date < examDate && dates.length < 60;
    date = addDays(date, 1)
  )
    dates.push(date);
  const sessions = [];
  let remainingMinutes = targetMinutes;
  let foundSlot = true;

  while (remainingMinutes > 0 && foundSlot) {
    foundSlot = false;
    for (const date of dates) {
      if (remainingMinutes <= 0) break;
      const duration = Math.min(usualSessionMinutes, remainingMinutes);
      const occupied = eventsOnDate(
        date,
        weeklyClasses,
        personalEvents,
        sessions,
      );
      let selected;
      for (const period of allowedPeriods) {
        const limits = PERIODS[period];
        if (!limits) continue;
        for (
          let start = limits[0];
          start + duration <= limits[1];
          start += 30
        ) {
          const candidate = {
            date,
            start: asTime(start),
            end: asTime(start + duration),
          };
          if (occupied.every((event) => !overlaps(candidate, event))) {
            selected = candidate;
            break;
          }
        }
        if (selected) break;
      }
      if (selected) {
        sessions.push({
          ...selected,
          id: `study-${date}-${selected.start}`,
          title: `${courseName}複習`,
          location: "自行安排",
          tone: "amber",
        });
        remainingMinutes -= duration;
        foundSlot = true;
      }
    }
  }

  return {
    sessions,
    scheduledMinutes: targetMinutes - remainingMinutes,
    remainingMinutes,
  };
}
