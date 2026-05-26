import { useEffect, useState } from "react";
import { getJson, postJson, statusSocket } from "./lib/api";
import StatusPanel from "./components/StatusPanel";
import CommandPanel from "./components/CommandPanel";
import SchedulePanel from "./components/SchedulePanel";
import TimerPanel from "./components/TimerPanel";
import ReminderPanel from "./components/ReminderPanel";
import CameraPanel from "./components/CameraPanel";
import MusicPanel from "./components/MusicPanel";
import Card from "./components/Card";

export default function App() {
  const [status, setStatus] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [lastCommand, setLastCommand] = useState(null);

  async function loadSchedule() {
    const scheduleData = await getJson("/api/schedule/today");
    setSchedule(scheduleData);
  }

  async function loadInitialData() {
    const [statusData, scheduleData] = await Promise.all([
      getJson("/api/status"),
      getJson("/api/schedule/today")
    ]);

    setStatus(statusData);
    setSchedule(scheduleData);
  }

  async function playMusic() {
    await postJson("/api/music/play", { emotion: status?.display_emotion ?? status?.current_emotion ?? "unknown" });
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

    // Voice-created schedule items arrive through the backend/ROS loop, not
    // through this component, so poll lightly to keep the dashboard current.
    const scheduleInterval = window.setInterval(loadSchedule, 4000);

    return () => {
      ws.close();
      window.clearInterval(scheduleInterval);
    };
  }, []);

  return (
    <main className="relative mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
      <header className="hero-shell mb-8 overflow-hidden rounded-[2.25rem] p-8 text-white">
        <div className="relative z-10 grid gap-6 lg:grid-cols-[1.4fr_0.6fr] lg:items-end">
          <div>
            <p className="section-kicker text-sm font-semibold">Personal Daily Assistant Robot</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-black tracking-tight sm:text-5xl lg:text-6xl">
              JUNO Assist Dashboard
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-200/85">
              Wake JUNO with “Hey, John”, confirm with “Yes”, then manage study schedules, reminders, timers, camera view, emotion-aware music, and break suggestions from one elegant control centre.
            </p>
          </div>
          <div className="glass-inner rounded-[2rem] p-4">
            <p className="text-sm font-medium text-slate-300">Current mode</p>
            <p className="mt-1 text-3xl font-bold capitalize text-white">{status?.mode ?? "loading"}</p>
            <p className="mt-3 text-sm text-slate-300">
              Emotion estimate: <span className="font-semibold capitalize text-white">{status?.display_emotion ?? status?.current_emotion ?? "unknown"}</span>
            </p>
          </div>
        </div>
      </header>

      <section className="grid gap-5 lg:grid-cols-3">
        <StatusPanel status={status} />
        <TimerPanel status={status} />
        <Card title="Most Recent Response from JUNO">
          <p className="text-slate-200/85">{status?.last_response ?? "Loading..."}</p>
          {lastCommand && (
            <p className="mt-3 text-sm text-slate-300/75">
              Last intent: {lastCommand.intent}
            </p>
          )}
        </Card>
      </section>

      <section className="mt-5">
        <CameraPanel status={status} />
      </section>

      <section className="mt-5 grid gap-5 lg:grid-cols-2">
        <CommandPanel onCommandResult={setLastCommand} />
        <Card title="Quick Actions">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={sleepJuno}
              className="btn-secondary px-5 py-2.5 text-sm font-semibold"
            >
              Put JUNO to Sleep
            </button>
          </div>
          <p className="mt-3 text-sm text-slate-300/75">
            Music selection follows the latest emotion estimate when the Vision Module is on; otherwise it falls back to a neutral study playlist.
          </p>
        </Card>
      </section>

      <section className="mt-5">
        <MusicPanel status={status} />
      </section>

      <section className="mt-5 grid gap-5 lg:grid-cols-2">
        <SchedulePanel schedule={schedule} onScheduleChanged={loadSchedule} />
        <ReminderPanel />
      </section>

    </main>
  );
}
