import { useEffect, useState } from "react";
import { getJson, postJson, statusSocket } from "./lib/api";
import StatusPanel from "./components/StatusPanel";
import CommandPanel from "./components/CommandPanel";
import SchedulePanel from "./components/SchedulePanel";
import TimerPanel from "./components/TimerPanel";
import ReminderPanel from "./components/ReminderPanel";
import Card from "./components/Card";

export default function App() {
  const [status, setStatus] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [features, setFeatures] = useState([]);
  const [lastCommand, setLastCommand] = useState(null);

  async function loadInitialData() {
    const [statusData, scheduleData, featureData] = await Promise.all([
      getJson("/api/status"),
      getJson("/api/schedule/today"),
      getJson("/api/features")
    ]);

    setStatus(statusData);
    setSchedule(scheduleData);
    setFeatures(featureData);
  }

  async function playMusic() {
    await postJson("/api/music/play");
  }

  async function sleepJuno() {
    await postJson("/api/robot/sleep");
  }

  useEffect(() => {
    loadInitialData();

    const ws = statusSocket();
    ws.onmessage = (event) => {
      setStatus(JSON.parse(event.data));
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <main className="mx-auto max-w-7xl p-6">
      <header className="mb-8 rounded-3xl bg-slate-900 p-8 text-white shadow-sm">
        <p className="text-sm uppercase tracking-[0.25em] text-slate-300">Personal Daily Assistant Robot</p>
        <h1 className="mt-2 text-4xl font-bold">JUNO Assist Dashboard</h1>
        <p className="mt-3 max-w-3xl text-slate-300">
          Wake JUNO with “Hey, Jude”, confirm with “Yes”, then use the assistant to manage study schedules, reminders, timers, and emotion-aware break suggestions.
        </p>
      </header>

      <section className="grid gap-5 lg:grid-cols-3">
        <StatusPanel status={status} />
        <TimerPanel status={status} />
        <Card title="Last Response">
          <p className="text-slate-700">{status?.last_response ?? "Loading..."}</p>
          {lastCommand && (
            <p className="mt-3 text-sm text-slate-500">
              Last intent: {lastCommand.intent}
            </p>
          )}
        </Card>
      </section>

      <section className="mt-5 grid gap-5 lg:grid-cols-2">
        <CommandPanel onCommandResult={setLastCommand} />
        <Card title="Quick Actions">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={playMusic}
              className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white"
            >
              Play Soothing Music
            </button>
            <button
              onClick={sleepJuno}
              className="rounded-xl border border-slate-300 px-4 py-2 font-medium text-slate-800"
            >
              Put JUNO to Sleep
            </button>
          </div>
        </Card>
      </section>

      <section className="mt-5 grid gap-5 lg:grid-cols-2">
        <SchedulePanel schedule={schedule} />
        <ReminderPanel />
      </section>

      <section className="mt-5">
        <Card title="Available Features">
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.name} className="rounded-xl border border-slate-200 p-4">
                <p className="font-semibold text-slate-900">{feature.name}</p>
                <p className="mt-1 text-sm text-slate-500">{feature.description}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </main>
  );
}
