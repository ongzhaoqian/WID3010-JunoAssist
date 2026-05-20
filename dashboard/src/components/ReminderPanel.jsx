import { useEffect, useState } from "react";
import { getJson, postJson } from "../lib/api";
import Card from "./Card";

export default function ReminderPanel() {
  const [reminders, setReminders] = useState([]);
  const [title, setTitle] = useState("");

  async function loadReminders() {
    const data = await getJson("/api/reminders");
    setReminders(data);
  }

  async function addReminder(event) {
    event.preventDefault();
    if (!title.trim()) return;

    await postJson("/api/reminders", {
      title,
      priority: "medium"
    });
    setTitle("");
    await loadReminders();
  }

  useEffect(() => {
    loadReminders();
  }, []);

  return (
    <Card title="Reminders">
      <form onSubmit={addReminder} className="mb-4 flex gap-2">
        <input
          className="input-glass min-w-0 flex-1 rounded-2xl px-3 py-2 text-sm"
          placeholder="Add reminder"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <button className="btn-primary px-5 py-2.5 text-sm font-semibold">
          Add
        </button>
      </form>

      <div className="space-y-2">
        {reminders.length === 0 ? (
          <p className="text-slate-300/75">No reminders added yet.</p>
        ) : (
          reminders.map((reminder) => (
            <div key={reminder.id} className="rounded-2xl border border-white/20 bg-white/[0.08] p-3">
              <p className="font-medium text-white">{reminder.title}</p>
              <p className="text-sm text-slate-300/75">{reminder.priority} priority</p>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
