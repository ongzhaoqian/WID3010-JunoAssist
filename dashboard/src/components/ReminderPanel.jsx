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
      <form onSubmit={addReminder} className="flex gap-2 mb-4">
        <input
          className="min-w-0 flex-1 rounded-xl border border-slate-300 px-3 py-2"
          placeholder="Add reminder"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <button className="rounded-xl bg-slate-900 px-4 py-2 text-white">
          Add
        </button>
      </form>

      <div className="space-y-2">
        {reminders.length === 0 ? (
          <p className="text-slate-500">No reminders added yet.</p>
        ) : (
          reminders.map((reminder) => (
            <div key={reminder.id} className="rounded-xl border border-slate-200 p-3">
              <p className="font-medium text-slate-900">{reminder.title}</p>
              <p className="text-sm text-slate-500">{reminder.priority} priority</p>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
