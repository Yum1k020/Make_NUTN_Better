import test from "node:test";
import assert from "node:assert/strict";
import { buildCalendar } from "../src/lib/calendarExport.js";

test("exports only the requested dates with Taipei times and escaped calendar text", () => {
  const calendar = buildCalendar(
    {
      dates: ["2026-11-29"],
      weeklyClasses: [
        {
          id: "class-1",
          weekday: 0,
          title: "週日課程",
          start: "07:30",
          end: "08:30",
          location: "教室,二樓",
        },
      ],
      personalEvents: [
        { id: "other", date: "2026-11-28", title: "不在匯出範圍" },
        {
          id: "event-1",
          date: "2026-11-29",
          title: "個人;行程\n下一行",
          start: "19:00",
          end: "20:00",
        },
      ],
      studySessions: [
        {
          id: "study-1",
          date: "2026-11-29",
          title: "複習".repeat(30),
          start: "20:00",
          end: "21:00",
        },
      ],
    },
    new Date("2026-11-25T12:00:00Z"),
  );
  assert.equal(calendar.match(/BEGIN:VEVENT/g).length, 3);
  assert.match(calendar, /DTSTART:20261128T233000Z\r\n/);
  assert.match(calendar, /DTEND:20261129T003000Z\r\n/);
  assert.match(calendar, /DTSTAMP:20261125T120000Z\r\n/);
  assert.ok(calendar.includes("LOCATION:教室\\,二樓\r\n"));
  assert.ok(calendar.includes("SUMMARY:個人\\;行程\\n下一行\r\n"));
  assert.ok(!calendar.includes("不在匯出範圍"));
  assert.ok(
    calendar.split("\r\n").every((line) => Buffer.byteLength(line) <= 75),
  );
  assert.ok(calendar.replaceAll("\r\n ", "").includes("複習".repeat(30)));
});
