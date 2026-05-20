import { useState } from "react";
import { postJson } from "../lib/api";
import Card from "./Card";

function formatSeconds(seconds = 0) {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

export default function TimerPanel({ status }) {
  const [minutes, setMinutes] = useState(25);

  async function startTimer() {
    await postJson("/api/timer/start", { minutes: Number(minutes) });
  }

  return (
    <Card title="Study Timer">
      <p className="text-4xl font-bold text-slate-900">
        {formatSeconds(status?.timer_remaining_seconds ?? 0)}
      </p>
      <p className="text-sm text-slate-500 mt-1">
        {status?.active_timer_label ?? "No active timer"}
      </p>

      <div className="mt-4 flex gap-2">
        <input
          type="number"
          min="1"
          max="180"
          className="w-24 rounded-xl border border-slate-300 px-3 py-2"
          value={minutes}
          onChange={(event) => setMinutes(event.target.value)}
        />
        <button
          onClick={startTimer}
          className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white"
        >
          Start
        </button>
      </div>
    </Card>
  );
}
