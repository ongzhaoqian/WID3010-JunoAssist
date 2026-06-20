import { useEffect, useState } from "react";
import { deleteJson, getJson, postJson, putJson } from "../lib/api";
import Card from "./Card";

const PRIORITIES = ["low", "medium", "high"];
const TYPES = ["reminder", "study", "assignment", "test", "quiz", "meeting", "personal"];

export default function ReminderPanel() {
  const [reminders, setReminders] = useState([]);
  const [form, setForm] = useState({
    title: "",
    date: "",
    time: "",
    type: "reminder",
    priority: "medium"
  });
  const [saving, setSaving] = useState(false);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function loadReminders() {
    const data = await getJson("/api/reminders");
    setReminders(data);
  }

  async function addReminder(event) {
    event.preventDefault();
    if (!form.title.trim()) return;

    setSaving(true);
    try {
      await postJson("/api/reminders", {
        ...form,
        title: form.title.trim(),
        date: form.date || null,
        time: form.time || null
      });
      setForm({ title: "", date: "", time: "", type: "reminder", priority: "medium" });
      await loadReminders();
    } finally {
      setSaving(false);
    }
  }

  async function removeReminder(itemId) {
    await deleteJson(`/api/reminders/${itemId}`);
    await loadReminders();
  }

  async function toggleCompleted(reminder) {
    await putJson(`/api/reminders/${reminder.id}`, { completed: !reminder.completed });
    await loadReminders();
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
      <form onSubmit={addReminder} className="mb-5 rounded-[1.75rem] border border-white/20 bg-white/[0.08] p-4">
        <p className="mb-3 text-sm font-medium text-slate-200">Add a new reminder</p>
        <div className="grid gap-3 md:grid-cols-2">
          <input
            className="input-glass rounded-2xl px-3 py-2 text-sm md:col-span-2"
            placeholder="e.g. Submit lab report"
            value={form.title}
            onChange={(event) => updateField("title", event.target.value)}
          />
          <input
            type="date"
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.date}
            onChange={(event) => updateField("date", event.target.value)}
          />
          <input
            type="time"
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.time}
            onChange={(event) => updateField("time", event.target.value)}
          />
          <select
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.type}
            onChange={(event) => updateField("type", event.target.value)}
          >
            {TYPES.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
          <select
            className="input-glass rounded-2xl px-3 py-2 text-sm"
            value={form.priority}
            onChange={(event) => updateField("priority", event.target.value)}
          >
            {PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>{priority} priority</option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={saving}
          className="btn-primary mt-3 px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
        >
          {saving ? "Adding..." : "Add Reminder"}
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
                <button
                  onClick={() => removeReminder(reminder.id)}
                  className="rounded-full border border-rose-300/30 bg-rose-400/10 px-3 py-1.5 text-sm font-medium text-rose-100 hover:bg-rose-400/20"
                >
                  Remove
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
