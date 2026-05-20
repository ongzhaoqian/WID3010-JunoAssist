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
  const [seconds, setSeconds] = useState(0);

  async function startTimer() {
    await postJson("/api/timer/start", {
      minutes: Number(minutes) || 0,
      seconds: Number(seconds) || 0
    });
  }

  const awaitingDuration = Boolean(status?.awaiting_timer_duration);

  return (
    <Card title="Study Timer">
      <div className="rounded-2xl bg-slate-950 p-5 text-white">
        <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Focus countdown</p>
        <p className="mt-2 text-5xl font-bold tabular-nums">
          {formatSeconds(status?.timer_remaining_seconds ?? 0)}
        </p>
        <p className="mt-2 text-sm text-slate-300">
          {status?.active_timer_label ?? (awaitingDuration ? "Waiting for voice duration" : "No active timer")}
        </p>
      </div>

      {awaitingDuration && (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          JUNO is waiting for your answer. Say a duration such as “25 minutes” or “1 minute 30 seconds”.
        </div>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <label className="text-sm font-medium text-slate-700">
          Minutes
          <input
            type="number"
            min="0"
            max="180"
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
            value={minutes}
            onChange={(event) => setMinutes(event.target.value)}
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Seconds
          <input
            type="number"
            min="0"
            max="59"
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
            value={seconds}
            onChange={(event) => setSeconds(event.target.value)}
          />
        </label>
        <button
          onClick={startTimer}
          className="self-end rounded-xl bg-slate-900 px-4 py-2 font-medium text-white"
        >
          Start
        </button>
      </div>
    </Card>
  );
}
