import { useEffect, useMemo, useState } from "react";
import { getJson, notifyCalendarChanged, onCalendarChanged } from "../lib/api";
import Card from "./Card";

const SCALES = [
  { id: "today", label: "Today" },
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
];

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const TYPE_COLOR = {
  study: "bg-cyan-300",
  assignment: "bg-amber-300",
  test: "bg-rose-400",
  quiz: "bg-fuchsia-300",
  meeting: "bg-violet-300",
  personal: "bg-emerald-300",
  reminder: "bg-slate-300",
};

function dateKey(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function startOfDay(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function addMonths(date, months) {
  const d = new Date(date);
  d.setMonth(d.getMonth() + months);
  return d;
}

function isSameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function startOfWeek(date) {
  const d = startOfDay(date);
  d.setDate(d.getDate() - d.getDay());
  return d;
}

function buildMonthGrid(anchorDate) {
  const firstOfMonth = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
  const gridStart = startOfWeek(firstOfMonth);
  const weeks = [];
  let cursor = gridStart;
  for (let week = 0; week < 6; week++) {
    const days = [];
    for (let day = 0; day < 7; day++) {
      days.push(cursor);
      cursor = addDays(cursor, 1);
    }
    weeks.push(days);
  }
  return weeks;
}

function buildWeekRow(anchorDate) {
  const start = startOfWeek(anchorDate);
  return Array.from({ length: 7 }, (_, i) => addDays(start, i));
}

function parseItemDate(item) {
  if (!item.date) return null;
  const time = item.time || "00:00";
  const parsed = new Date(`${item.date}T${time}`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatTime(date) {
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export default function CalendarPanel() {
  const [scheduleItems, setScheduleItems] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [scale, setScale] = useState("today");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [anchorDate, setAnchorDate] = useState(() => startOfDay(new Date()));
  const [selectedDate, setSelectedDate] = useState(() => startOfDay(new Date()));

  async function loadAll() {
    setError("");
    try {
      const [schedule, reminderList] = await Promise.all([
        getJson("/api/schedule/today"),
        getJson("/api/reminders"),
      ]);
      setScheduleItems(schedule ?? []);
      setReminders(reminderList ?? []);
    } catch (err) {
      setError("Could not load your calendar right now. Try refreshing.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    const interval = window.setInterval(loadAll, 30000);
    const unsubscribe = onCalendarChanged(loadAll);
    return () => {
    window.clearInterval(interval);
    unsubscribe();
  };
  }, []);

  function selectScale(nextScale) {
    setScale(nextScale);
    const today = startOfDay(new Date());
    setAnchorDate(today);
    setSelectedDate(today);
  }

  const itemsByDate = useMemo(() => {
    const tagged = [
      ...scheduleItems.map((item) => ({ ...item, source: "schedule" })),
      ...reminders.map((item) => ({ ...item, source: "reminder" })),
    ];
    const map = new Map();
    for (const item of tagged) {
      const when = parseItemDate(item);
      if (!when) continue;
      const key = dateKey(when);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push({ ...item, _when: when });
    }
    for (const list of map.values()) {
      list.sort((a, b) => a._when - b._when);
    }
    return map;
  }, [scheduleItems, reminders]);

  const today = useMemo(() => startOfDay(new Date()), []);
  const monthGrid = useMemo(() => buildMonthGrid(anchorDate), [anchorDate]);
  const weekRow = useMemo(() => buildWeekRow(anchorDate), [anchorDate]);
  const selectedItems = itemsByDate.get(dateKey(selectedDate)) ?? [];

  function goPrev() {
    if (scale === "month") setAnchorDate((d) => addMonths(d, -1));
    else if (scale === "week") setAnchorDate((d) => addDays(d, -7));
  }
  function goNext() {
    if (scale === "month") setAnchorDate((d) => addMonths(d, 1));
    else if (scale === "week") setAnchorDate((d) => addDays(d, 7));
  }
  function goToday() {
    setAnchorDate(today);
    setSelectedDate(today);
  }

  const periodLabel = useMemo(() => {
    if (scale === "month") {
      return anchorDate.toLocaleDateString(undefined, { month: "long", year: "numeric" });
    }
    if (scale === "week") {
      const start = weekRow[0];
      const end = weekRow[6];
      const sameMonth = start.getMonth() === end.getMonth();
      const startLabel = start.toLocaleDateString(undefined, { month: "short", day: "numeric" });
      const endLabel = end.toLocaleDateString(undefined, sameMonth ? { day: "numeric" } : { month: "short", day: "numeric" });
      return `${startLabel} – ${endLabel}`;
    }
    return today.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
  }, [scale, anchorDate, weekRow, today]);

  function renderDayCell(date) {
    const key = dateKey(date);
    const items = itemsByDate.get(key) ?? [];
    const isToday = isSameDay(date, today);
    const isSelected = isSameDay(date, selectedDate);
    const inAnchorMonth = scale !== "month" || date.getMonth() === anchorDate.getMonth();

    return (
      <button
        key={key}
        type="button"
        onClick={() => setSelectedDate(startOfDay(date))}
        aria-pressed={isSelected}
        aria-label={`${date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}${
          items.length ? `, ${items.length} item${items.length > 1 ? "s" : ""}` : ""
        }`}
        className={`relative flex min-h-14 flex-col items-center justify-start gap-1 rounded-xl py-2 transition ${
          isSelected
            ? "bg-cyan-400/20 ring-1 ring-cyan-300/50"
            : isToday
            ? "bg-white/[0.08]"
            : "hover:bg-white/[0.05]"
        } ${inAnchorMonth ? "" : "opacity-35"}`}
      >
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-full text-sm font-semibold ${
            isToday ? "bg-cyan-400 text-slate-950" : "text-white"
          }`}
        >
          {date.getDate()}
        </span>
        {items.length > 0 && (
          <span className="flex gap-0.5">
            {items.slice(0, 3).map((item, i) => (
              <span
                key={i}
                aria-hidden="true"
                className={`h-1.5 w-1.5 rounded-full ${TYPE_COLOR[item.type] ?? "bg-slate-400"}`}
              />
            ))}
          </span>
        )}
      </button>
    );
  }

  return (
    <Card title="Calendar">
      <div className="rounded-[1.75rem] border border-white/20 bg-white/[0.08] p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="section-kicker text-xs font-semibold">Upcoming tasks &amp; reminders</p>
          <div role="radiogroup" aria-label="Time scale" className="flex gap-1.5 rounded-full border border-white/15 bg-white/[0.05] p-1">
            {SCALES.map((s) => (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={scale === s.id}
                onClick={() => selectScale(s.id)}
                className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                  scale === s.id ? "bg-cyan-400/25 text-white" : "text-slate-300/75 hover:text-white"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <p role="alert" className="mb-3 text-sm font-medium text-rose-300">
            {error}
          </p>
        )}

        {loading ? (
          <p className="text-slate-300/75">Loading your calendar…</p>
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between">
              {scale !== "today" ? (
                <button
                  type="button"
                  onClick={goPrev}
                  aria-label={scale === "month" ? "Previous month" : "Previous week"}
                  className="rounded-full border border-white/15 bg-white/[0.05] px-3 py-1.5 text-sm text-slate-200 hover:bg-white/[0.12]"
                >
                  ‹
                </button>
              ) : (
                <span />
              )}
              <div className="flex items-center gap-3">
                <p className="text-sm font-semibold text-white">{periodLabel}</p>
                {scale !== "today" && !isSameDay(anchorDate, today) && (
                  <button
                    type="button"
                    onClick={goToday}
                    className="rounded-full border border-white/15 bg-white/[0.05] px-2.5 py-1 text-xs font-medium text-slate-300/80 hover:text-white"
                  >
                    Today
                  </button>
                )}
              </div>
              {scale !== "today" ? (
                <button
                  type="button"
                  onClick={goNext}
                  aria-label={scale === "month" ? "Next month" : "Next week"}
                  className="rounded-full border border-white/15 bg-white/[0.05] px-3 py-1.5 text-sm text-slate-200 hover:bg-white/[0.12]"
                >
                  ›
                </button>
              ) : (
                <span />
              )}
            </div>

            {(scale === "month" || scale === "week") && (
              <div className="rounded-2xl border border-white/15 bg-white/[0.04] p-2">
                <div className="grid grid-cols-7 gap-1 pb-1 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-300/60">
                  {WEEKDAY_LABELS.map((label) => (
                    <span key={label}>{label}</span>
                  ))}
                </div>
                <div className="grid grid-cols-7 gap-1">
                  {(scale === "month" ? monthGrid.flat() : weekRow).map((date) => renderDayCell(date))}
                </div>
              </div>
            )}

            <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1.5">
              {Object.entries(TYPE_COLOR).map(([type, colorClass]) => (
                <span key={type} className="flex items-center gap-1.5 text-[11px] text-slate-300/70">
                  <span aria-hidden="true" className={`h-2 w-2 rounded-full ${colorClass}`} />
                  <span className="capitalize">{type}</span>
                </span>
              ))}
            </div>

            <div className="mt-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-300/60">
                {scale === "today" || isSameDay(selectedDate, today)
                  ? "Today"
                  : selectedDate.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
              </p>
              {selectedItems.length === 0 ? (
                <div className="flex min-h-20 flex-col items-center justify-center rounded-2xl border border-white/15 bg-white/[0.05] p-4 text-center">
                  <p className="text-sm text-slate-300/70">Nothing on this day.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {selectedItems.map((entry) => (
                    <div
                      key={`${entry.source}-${entry.id}`}
                      className="flex items-center justify-between gap-3 rounded-2xl border border-white/15 bg-white/[0.06] px-3 py-2.5"
                    >
                      <div className="flex min-w-0 items-center gap-2.5">
                        <span
                          aria-hidden="true"
                          className={`h-2 w-2 shrink-0 rounded-full ${TYPE_COLOR[entry.type] ?? "bg-slate-400"}`}
                        />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-white">{entry.title}</p>
                          <p className="text-xs text-slate-300/65">
                            {formatTime(entry._when)} · {entry.source === "reminder" ? "Reminder" : entry.type || "Schedule"}
                          </p>
                        </div>
                      </div>
                      {entry.priority && (
                        <span className="shrink-0 rounded-full border border-white/15 px-2 py-0.5 text-[11px] font-medium capitalize text-slate-300/75">
                          {entry.priority}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Card>
  );
}