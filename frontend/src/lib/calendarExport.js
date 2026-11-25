import { eventsOnDate } from "./planner.js";

const encoder = new TextEncoder();

function escapeText(value) {
  return value
    .replaceAll("\\", "\\\\")
    .replace(/\r\n|\r|\n/g, "\\n")
    .replaceAll(",", "\\,")
    .replaceAll(";", "\\;");
}

function foldLine(line) {
  let result = "";
  let bytes = 0;
  for (const character of line) {
    const size = encoder.encode(character).length;
    if (bytes + size > 75) {
      result += "\r\n ";
      bytes = 1;
    }
    result += character;
    bytes += size;
  }
  return result;
}

function utcTimestamp(date) {
  return date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

export function buildCalendar(
  { dates, weeklyClasses, personalEvents, studySessions },
  now = new Date(),
) {
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Make NUTN Better//Campus Planner//ZH-TW",
    "CALSCALE:GREGORIAN",
  ];
  const timestamp = utcTimestamp(now);
  for (const date of dates) {
    const events = eventsOnDate(date, weeklyClasses, personalEvents, studySessions);
    for (const event of events) {
      const start = new Date(`${date}T${event.start}:00+08:00`);
      const end = new Date(`${date}T${event.end}:00+08:00`);
      lines.push(
        "BEGIN:VEVENT",
        `UID:${event.kind}-${date}-${encodeURIComponent(event.id)}@make-nutn-better`,
        `DTSTAMP:${timestamp}`,
        `DTSTART:${utcTimestamp(start)}`,
        `DTEND:${utcTimestamp(end)}`,
        `SUMMARY:${escapeText(event.title)}`,
      );
      if (event.location) lines.push(`LOCATION:${escapeText(event.location)}`);
      lines.push("END:VEVENT");
    }
  }
  lines.push("END:VCALENDAR");
  return `${lines.map(foldLine).join("\r\n")}\r\n`;
}

export function downloadCalendar(data) {
  const file = new Blob([buildCalendar(data)], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = `nutn-calendar-${data.dates[0]}.ics`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
