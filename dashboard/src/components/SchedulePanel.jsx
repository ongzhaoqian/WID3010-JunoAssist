import { useState } from "react";
import { deleteJson, postJson } from "../lib/api";
import Card from "./Card";

const PRIORITIES = ["low", "medium", "high"];
const TYPES = ["class", "meeting", "study", "assignment", "test", "quiz", "personal"];

export default function SchedulePanel({ schedule, onScheduleChanged }) {
  const [form, setForm] = useState({
    title: "",
    date: "",
    time: "",
    type: "study",
    priority: "medium"
  });
  const [saving, setSaving] = useState(false);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function addItem(event) {
    event.preventDefault();
    if (!form.title.trim()) return;

    setSaving(true);
    try {
      await postJson("/api/schedule", {
        ...form,
        title: form.title.trim(),
        date: form.date || null,
        time: form.time || null
      });
      setForm({ title: "", date: "", time: "", type: "study", priority: "medium" });
      await onScheduleChanged?.();
    } finally {
      setSaving(false);
    }
  }

  async function removeItem(itemId) {
    await deleteJson(`/api/schedule/${itemId}`);
    await onScheduleChanged?.();
  }

  return (
    <Card title="Upcoming Schedule">
      <form onSubmit={addItem} className="mb-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <p className="mb-3 text-sm font-medium text-slate-700">Add a new schedule item</p>
        <div className="grid gap-3 md:grid-cols-2">
          <input
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300 md:col-span-2"
            placeholder="e.g. Deep Learning revision"
            value={form.title}
            onChange={(event) => updateField("title", event.target.value)}
          />
          <input
            type="date"
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
            value={form.date}
            onChange={(event) => updateField("date", event.target.value)}
          />
          <input
            type="time"
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
            value={form.time}
            onChange={(event) => updateField("time", event.target.value)}
          />
          <select
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
            value={form.type}
            onChange={(event) => updateField("type", event.target.value)}
          >
            {TYPES.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
          <select
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
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
          className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? "Adding..." : "Add Schedule Item"}
        </button>
      </form>

      <div className="space-y-3">
        {schedule.length === 0 ? (
          <p className="text-slate-500">No schedule items loaded.</p>
        ) : (
          schedule.map((item) => (
            <div key={item.id} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 p-3">
              <div>
                <p className="font-semibold text-slate-900">{item.title}</p>
                <p className="text-sm capitalize text-slate-500">
                  {item.date || "No date"} · {item.time || "No time"} · {item.type || "schedule"} · {item.priority} priority
                </p>
              </div>
              <button
                onClick={() => removeItem(item.id)}
                className="rounded-xl border border-rose-200 px-3 py-1.5 text-sm font-medium text-rose-700 hover:bg-rose-50"
              >
                Remove
              </button>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
