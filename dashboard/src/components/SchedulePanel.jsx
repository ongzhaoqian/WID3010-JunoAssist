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
      <form onSubmit={addItem} className="mb-5 rounded-[1.75rem] border border-white/20 bg-white/[0.08] p-4">
        <p className="mb-3 text-sm font-medium text-slate-200">Add a new schedule item</p>
        <div className="grid gap-3 md:grid-cols-2">
          <input
            className="input-glass rounded-2xl px-3 py-2 text-sm md:col-span-2"
            placeholder="e.g. Deep Learning revision"
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
          {saving ? "Adding..." : "Add Schedule Item"}
        </button>
      </form>

      <div className="space-y-3">
        {schedule.length === 0 ? (
          <p className="text-slate-300/75">No schedule items loaded.</p>
        ) : (
          schedule.map((item) => (
            <div key={item.id} className="flex items-start justify-between gap-3 rounded-2xl border border-white/20 bg-white/[0.08] p-3">
              <div>
                <p className="font-semibold text-white">{item.title}</p>
                <p className="text-sm capitalize text-slate-300/75">
                  {item.formatted_date || item.date || "No date"} · {item.time || "No time"} · {item.type || "schedule"} · {item.priority} priority
                </p>
              </div>
              <button
                onClick={() => removeItem(item.id)}
                className="rounded-full border border-rose-300/30 bg-rose-400/10 px-3 py-1.5 text-sm font-medium text-rose-100 hover:bg-rose-400/20"
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
