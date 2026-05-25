import { useEffect, useRef, useState } from "react";
import { postJson } from "../lib/api";
import Card from "./Card";

function formatSeconds(seconds = 0) {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

function playBellSound() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;

  const context = new AudioContextClass();
  const now = context.currentTime;
  const masterGain = context.createGain();
  masterGain.gain.setValueAtTime(0.0001, now);
  masterGain.gain.exponentialRampToValueAtTime(0.35, now + 0.02);
  masterGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.4);
  masterGain.connect(context.destination);

  [880, 1320, 1760].forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const start = now + index * 0.12;
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.28, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.55);
    oscillator.connect(gain);
    gain.connect(masterGain);
    oscillator.start(start);
    oscillator.stop(start + 0.65);
  });

  window.setTimeout(() => context.close?.(), 1800);
}

export default function TimerPanel({ status }) {
  const [minutes, setMinutes] = useState(25);
  const [seconds, setSeconds] = useState(0);
  const previousCompletionCounter = useRef(null);

  async function startTimer() {
    await postJson("/api/timer/start", {
      minutes: Number(minutes) || 0,
      seconds: Number(seconds) || 0
    });
  }

  const awaitingDuration = Boolean(status?.awaiting_timer_duration);
  const completedCounter = status?.timer_completed_counter ?? 0;

  useEffect(() => {
    if (previousCompletionCounter.current === null) {
      previousCompletionCounter.current = completedCounter;
      return;
    }

    if (completedCounter > previousCompletionCounter.current) {
      playBellSound();
    }
    previousCompletionCounter.current = completedCounter;
  }, [completedCounter]);

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
        {status?.last_timer_completed_label && (
          <p className="mt-1 text-xs text-slate-400">
            Last completed: {status.last_timer_completed_label}
          </p>
        )}
      </div>

      {awaitingDuration && (
        <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-3 text-sm text-amber-100">
          JUNO is waiting for your answer. Say “25 minutes”, “one minute thirty”, “1 30”, “half an hour”, “2:30”, or “cancel” to exit timer setup.
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
