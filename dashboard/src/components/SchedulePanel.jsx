import { useState } from "react";
import { deleteJson, postJson, putJson } from "../lib/api";
import Card from "./Card";

const PRIORITIES = ["low", "medium", "high"];
const TYPES = ["class", "meeting", "study", "assignment", "test", "quiz", "personal"];

const EMPTY_FORM = {
  title: "",
  date: "",
  time: "",
  type: "study",
  priority: "medium"
};

export default function SchedulePanel({ schedule, onScheduleChanged }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      title: item.title || "",
      date: item.date || "",
      time: item.time || "",
      type: item.type || "study",
      priority: item.priority || "medium"
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function submitForm(event) {
    event.preventDefault();
    if (!form.title.trim()) return;

    const payload = {
      ...form,
      title: form.title.trim(),
      date: form.date || null,
      time: form.time || null
    };

    setSaving(true);
    try {
      if (editingId) {
        await putJson(`/api/schedule/${editingId}`, payload);
      } else {
        await postJson("/api/schedule", payload);
      }
      setEditingId(null);
      setForm(EMPTY_FORM);
      await onScheduleChanged?.();
    } finally {
      setSaving(false);
    }
  }

  async function removeItem(itemId) {
    await deleteJson(`/api/schedule/${itemId}`);
    if (editingId === itemId) {
      cancelEdit();
    }
    await onScheduleChanged?.();
  }

  async function toggleCompleted(item) {
    await putJson(`/api/schedule/${item.id}`, { completed: !item.completed });
    await onScheduleChanged?.();
  }

  const sortedSchedule = [...schedule].sort((a, b) => Number(Boolean(a.completed)) - Number(Boolean(b.completed)));

  return (
    <Card title="Upcoming Schedule">
      <form onSubmit={submitForm} className="mb-5 rounded-[1.75rem] border border-white/20 bg-white/[0.08] p-4">
        <p className="mb-3 text-sm font-medium text-slate-200">
          {editingId ? "Edit schedule item" : "Add a new schedule item"}
        </p>
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
        <div className="mt-3 flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="btn-primary px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
          >
            {saving ? "Saving..." : editingId ? "Save changes" : "Add Schedule Item"}
          </button>
          {editingId ? (
            <button
              type="button"
              onClick={cancelEdit}
              className="rounded-full border border-white/20 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-slate-200 hover:bg-white/[0.15]"
            >
              Cancel
            </button>
          ) : null}
        </div>
      </form>

      <div className="space-y-3">
        {sortedSchedule.length === 0 ? (
          <p className="text-slate-300/75">No schedule items loaded.</p>
        ) : (
          sortedSchedule.map((item) => (
            <div
              key={item.id}
              className={`flex items-start justify-between gap-3 rounded-2xl border border-white/20 p-3 ${item.completed ? "bg-white/[0.04] opacity-60" : "bg-white/[0.08]"}`}
            >
              <div>
                <p className={`font-semibold text-white ${item.completed ? "line-through" : ""}`}>{item.title}</p>
                <p className={`text-sm capitalize text-slate-300/75 ${item.completed ? "line-through" : ""}`}>
                  {item.formatted_date || item.date || "No date"} · {item.time || "No time"} · {item.type || "schedule"} · {item.priority} priority
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => toggleCompleted(item)}
                  className={`rounded-full border px-3 py-1.5 text-sm font-medium ${item.completed ? "border-emerald-300/30 bg-emerald-400/10 text-emerald-100 hover:bg-emerald-400/20" : "border-white/20 bg-white/[0.08] text-slate-200 hover:bg-white/[0.15]"}`}
                >
                  {item.completed ? "Completed ✓" : "Mark done"}
                </button>
                <button
                  onClick={() => startEdit(item)}
                  className="rounded-full border border-sky-300/30 bg-sky-400/10 px-3 py-1.5 text-sm font-medium text-sky-100 hover:bg-sky-400/20"
                >
                  Edit
                </button>
                <button
                  onClick={() => removeItem(item.id)}
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
