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
      <div className="rounded-[1.75rem] border border-white/20 bg-slate-950/60 p-5 text-white shadow-inner">
        <p className="section-kicker text-xs font-semibold">Focus countdown</p>
        <p className="mt-2 text-5xl font-black tabular-nums">
          {formatSeconds(status?.timer_remaining_seconds ?? 0)}
        </p>
        <p className="mt-2 text-sm text-slate-300/80">
          {status?.active_timer_label ?? (awaitingDuration ? "Waiting for voice duration" : "No active timer")}
        </p>
      </div>

      {awaitingDuration && (
        <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-3 text-sm text-amber-100">
          JUNO is waiting for your answer. Say a duration such as “25 minutes” or “1 minute 30 seconds”.
        </div>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <label className="text-sm font-medium text-slate-200">
          Minutes
          <input
            type="number"
            min="0"
            max="180"
            className="input-glass mt-1 w-full rounded-2xl px-3 py-2"
            value={minutes}
            onChange={(event) => setMinutes(event.target.value)}
          />
        </label>
        <label className="text-sm font-medium text-slate-200">
          Seconds
          <input
            type="number"
            min="0"
            max="59"
            className="input-glass mt-1 w-full rounded-2xl px-3 py-2"
            value={seconds}
            onChange={(event) => setSeconds(event.target.value)}
          />
        </label>
        <button
          onClick={startTimer}
          className="btn-primary self-end px-5 py-2.5 text-sm font-semibold"
        >
          Start
        </button>
      </div>
    </Card>
  );
}
