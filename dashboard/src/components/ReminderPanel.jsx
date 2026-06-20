import { useEffect, useMemo, useState } from "react";
import { deleteJson, getJson, postJson, putJson, notifyCalendarChanged } from "../lib/api";
import Card from "./Card";

const PRIORITIES = ["low", "medium", "high"];
const TYPES = ["reminder", "study", "assignment", "test", "quiz", "meeting", "personal"];
const MAX_HOURS_AHEAD = 24;

function toDateTimeParts(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return {
    date: `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
    time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
  };
}

function buildQuickOptions(now) {
  const candidates = [
    { id: "15m", label: "In 15 min", date: new Date(now.getTime() + 15 * 60000) },
    { id: "30m", label: "In 30 min", date: new Date(now.getTime() + 30 * 60000) },
    { id: "1h", label: "In 1 hour", date: new Date(now.getTime() + 60 * 60000) },
    { id: "3h", label: "In 3 hours", date: new Date(now.getTime() + 3 * 60 * 60000) },
  ];

  const tonight = new Date(now);
  tonight.setHours(20, 0, 0, 0);
  if (tonight > now) {
    candidates.push({ id: "tonight", label: "Tonight, 8:00 PM", date: tonight });
  }

  const tomorrowMorning = new Date(now);
  tomorrowMorning.setDate(tomorrowMorning.getDate() + 1);
  tomorrowMorning.setHours(9, 0, 0, 0);
  const maxAhead = new Date(now.getTime() + MAX_HOURS_AHEAD * 60 * 60000);
  if (tomorrowMorning <= maxAhead) {
    candidates.push({ id: "tomorrow_am", label: "Tomorrow, 9:00 AM", date: tomorrowMorning });
  }

  return candidates;
}

const EMPTY_FORM = { title: "", type: "reminder", priority: "medium" };

export default function ReminderPanel() {
  const [reminders, setReminders] = useState([]);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("reminder");
  const [priority, setPriority] = useState("medium");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [mode, setMode] = useState("quick"); // "quick" | "custom"
  const [quickId, setQuickId] = useState(null);
  const [customTime, setCustomTime] = useState("");
  const [customDay, setCustomDay] = useState("today"); // "today" | "tomorrow"

  const [editingId, setEditingId] = useState(null); // null = creating, otherwise editing this id

  const now = useMemo(() => new Date(), []);
  const quickOptions = useMemo(() => buildQuickOptions(now), [now]);
  const maxAhead = useMemo(() => new Date(now.getTime() + MAX_HOURS_AHEAD * 60 * 60000), [now]);

  async function loadReminders() {
    const data = await getJson("/api/reminders");
    setReminders(data);
  }

  useEffect(() => {
    loadReminders();
    const interval = window.setInterval(loadReminders, 4000);
    return () => window.clearInterval(interval);
  }, []);

  function resolveSelectedDate() {
    if (mode === "quick") {
      const option = quickOptions.find((o) => o.id === quickId);
      return option ? option.date : null;
    }
    if (!customTime) return null;
    const [hours, minutes] = customTime.split(":").map(Number);
    const candidate = new Date();
    if (customDay === "tomorrow") candidate.setDate(candidate.getDate() + 1);
    candidate.setHours(hours, minutes, 0, 0);
    return candidate;
  }

  function resetForm() {
    setTitle(EMPTY_FORM.title);
    setType(EMPTY_FORM.type);
    setPriority(EMPTY_FORM.priority);
    setMode("quick");
    setQuickId(null);
    setCustomTime("");
    setCustomDay("today");
    setEditingId(null);
    setError("");
  }

  function startEditing(reminder) {
    setEditingId(reminder.id);
    setTitle(reminder.title ?? "");
    setType(reminder.type ?? "reminder");
    setPriority(reminder.priority ?? "medium");
    setError("");

    // Quick-picks are relative to "now," so an existing reminder always
    // goes into custom mode, pre-filled with its actual date/time.
    setMode("custom");
    setCustomTime(reminder.time ?? "");

    if (reminder.date) {
      const todayParts = toDateTimeParts(now);
      setCustomDay(reminder.date === todayParts.date ? "today" : "tomorrow");
    } else {
      setCustomDay("today");
    }

    // Scroll the form into view so editing an item lower in the list is obvious
    document.getElementById("reminder-title")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function submitReminder(event) {
    event.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("Give the reminder a title first.");
      return;
    }

    const selectedDate = resolveSelectedDate();
    if (!selectedDate) {
      setError("Pick when this reminder should fire.");
      return;
    }
    // Only enforce "must be in the future" when creating — an existing
    // reminder being edited may legitimately keep a time that's already close.
    if (!editingId && selectedDate <= now) {
      setError("That time has already passed — pick something later.");
      return;
    }
    if (selectedDate > maxAhead) {
      setError("Reminders can only be set up to 24 hours ahead.");
      return;
    }

    const { date, time } = toDateTimeParts(selectedDate);
    const payload = { title: title.trim(), date, time, type, priority };

    setSaving(true);
    try {
      if (editingId) {
        await putJson(`/api/reminders/${editingId}`, payload);
      } else {
        await postJson("/api/reminders", payload);
      }
      resetForm();
      await loadReminders();
      notifyCalendarChanged(); 
    } finally {
      setSaving(false);
    }
  }

  async function removeReminder(itemId) {
    await deleteJson(`/api/reminders/${itemId}`);
    if (editingId === itemId) resetForm();
    await loadReminders();
    notifyCalendarChanged(); 
  }
  async function toggleCompleted(reminder) {
    await putJson(`/api/reminders/${reminder.id}`, {
      title: reminder.title,
      date: reminder.date,
      time: reminder.time,
      type: reminder.type,
      priority: reminder.priority,
      completed: !reminder.completed,
    });
    await loadReminders();
    notifyCalendarChanged();
  }

 

  useEffect(() => {
    loadReminders();
    // Voice-created reminders arrive through the backend/ROS loop, so poll
    // lightly to keep the dashboard list aligned with spoken commands.
    const interval = window.setInterval(loadReminders, 4000);
    return () => window.clearInterval(interval);
  }, []);

  const sortedReminders = [...reminders].sort((a, b) => Number(Boolean(a.completed)) - Number(Boolean(b.completed)));

  return (
    <Card title="Reminders">
      <form onSubmit={submitReminder} className="mb-5 rounded-[1.75rem] border border-white/20 bg-white/[0.08] p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium text-slate-200">
            {editingId ? "Edit reminder" : "Add a new reminder"}
          </p>
          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="text-xs font-medium text-slate-300/80 hover:text-white"
            >
              Cancel edit
            </button>
          )}
        </div>

        <label htmlFor="reminder-title" className="sr-only">Reminder title</label>
        <input
          id="reminder-title"
          className="input-glass mb-3 w-full rounded-2xl px-3 py-2 text-sm"
          placeholder="e.g. Submit lab report"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />

        <fieldset className="mb-3">
          <legend className="mb-2 text-sm font-medium text-slate-300/85">When (within 24 hours)</legend>

          <div role="radiogroup" aria-label="Quick time options" className="flex flex-wrap gap-2">
            {quickOptions.map((option) => {
              const selected = mode === "quick" && quickId === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => {
                    setMode("quick");
                    setQuickId(option.id);
                  }}
                  className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                    selected
                      ? "border-cyan-300/60 bg-cyan-400/20 text-white"
                      : "border-white/20 bg-white/[0.06] text-slate-200 hover:bg-white/[0.12]"
                  }`}
                >
                  {option.label}
                </button>
              );
            })}
            <button
              type="button"
              role="radio"
              aria-checked={mode === "custom"}
              onClick={() => setMode("custom")}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                mode === "custom"
                  ? "border-cyan-300/60 bg-cyan-400/20 text-white"
                  : "border-white/20 bg-white/[0.06] text-slate-200 hover:bg-white/[0.12]"
              }`}
            >
              Custom time…
            </button>
          </div>

          {mode === "custom" && (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <div role="radiogroup" aria-label="Day" className="flex gap-2">
                {[
                  { id: "today", label: "Today" },
                  { id: "tomorrow", label: "Tomorrow" },
                ].map((day) => (
                  <button
                    key={day.id}
                    type="button"
                    role="radio"
                    aria-checked={customDay === day.id}
                    onClick={() => setCustomDay(day.id)}
                    className={`rounded-full border px-3 py-1.5 text-sm font-medium ${
                      customDay === day.id
                        ? "border-cyan-300/60 bg-cyan-400/20 text-white"
                        : "border-white/20 bg-white/[0.06] text-slate-200"
                    }`}
                  >
                    {day.label}
                  </button>
                ))}
              </div>

              <label htmlFor="reminder-custom-time" className="sr-only">Custom time</label>
              <input
                id="reminder-custom-time"
                type="time"
                className="input-glass rounded-2xl px-3 py-2 text-sm"
                value={customTime}
                onChange={(event) => setCustomTime(event.target.value)}
                aria-describedby="reminder-time-hint"
              />
              <span id="reminder-time-hint" className="text-xs text-slate-300/70">
                Must be within the next 24 hours.
              </span>
            </div>
          )}
        </fieldset>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm text-slate-300/85">
            Type
            <select
              className="input-glass mt-1 w-full rounded-2xl px-3 py-2 text-sm"
              value={type}
              onChange={(event) => setType(event.target.value)}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300/85">
            Priority
            <select
              className="input-glass mt-1 w-full rounded-2xl px-3 py-2 text-sm"
              value={priority}
              onChange={(event) => setPriority(event.target.value)}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>{p} priority</option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <p role="alert" className="mt-3 text-sm font-medium text-rose-300">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="btn-primary mt-3 px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
        >
          {saving ? "Saving..." : editingId ? "Update Reminder" : "Add Reminder"}
        </button>
      </form>

      <div className="space-y-3">
        {sortedReminders.length === 0 ? (
          <p className="text-slate-300/75">No reminders added yet.</p>
        ) : (
          sortedReminders.map((reminder) => (
            <div
              key={reminder.id}
              className={`flex items-start justify-between gap-3 rounded-2xl border border-white/20 p-3 ${reminder.completed ? "bg-white/[0.04] opacity-60" : "bg-white/[0.08]"}`}
            >
              <div>
                <p className={`font-semibold text-white ${reminder.completed ? "line-through" : ""}`}>{reminder.title}</p>
                <p className={`text-sm capitalize text-slate-300/75 ${reminder.completed ? "line-through" : ""}`}>
                  {reminder.formatted_date || reminder.date || "No date"} · {reminder.time || "No time"} · {reminder.type || "reminder"} · {reminder.priority} priority
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => toggleCompleted(reminder)}
                  className={`rounded-full border px-3 py-1.5 text-sm font-medium ${reminder.completed ? "border-emerald-300/30 bg-emerald-400/10 text-emerald-100 hover:bg-emerald-400/20" : "border-white/20 bg-white/[0.08] text-slate-200 hover:bg-white/[0.15]"}`}
                >
                  {reminder.completed ? "Completed ✓" : "Mark done"}
                </button>
                <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => startEditing(reminder)}
                  className="rounded-full border border-cyan-300/30 bg-cyan-400/10 px-3 py-1.5 text-sm font-medium text-cyan-100 hover:bg-cyan-400/20"
                >
                  Edit
                </button>
                <button
                    onClick={() => removeReminder(reminder.id)}
                    className="rounded-full border border-rose-300/30 bg-rose-400/10 px-3 py-1.5 text-sm font-medium text-rose-100 hover:bg-rose-400/20"
                  >
                    Remove
                  </button>
              </div>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}