import { useEffect, useState } from "react";
import { getJson, postJson, statusSocket } from "./lib/api";
import StatusPanel from "./components/StatusPanel";
import CommandPanel from "./components/CommandPanel";
import SchedulePanel from "./components/SchedulePanel";
import TimerPanel from "./components/TimerPanel";
import DateTimePanel from "./components/DateTimePanel";
import ReminderPanel from "./components/ReminderPanel";
import CameraPanel from "./components/CameraPanel";
import MusicPanel from "./components/MusicPanel";
import FitnessPanel from "./components/FitnessPanel";
import FitnessGameModal, { openFitnessGameWindow } from "./components/FitnessGameModal";
import Card from "./components/Card";

export default function App() {
  const [status, setStatus] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [lastCommand, setLastCommand] = useState(null);
  const [dashboardClosing, setDashboardClosing] = useState(false);
  const [fitnessGameOpen, setFitnessGameOpen] = useState(false);
  const [fitnessRefreshKey, setFitnessRefreshKey] = useState(0);
  const [fitnessLaunchMessage, setFitnessLaunchMessage] = useState("");

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

  async function handleFitnessSessionSaved() {
    setFitnessRefreshKey((current) => current + 1);
  }

  function launchFitnessGame() {
    const openedPopup = openFitnessGameWindow();
    setFitnessLaunchMessage(
      openedPopup
        ? "Game opened in a separate popup window. Keep this dashboard open to save the final 6-7 score."
        : "A new game tab was requested because the browser may have blocked the popup. Keep this dashboard open to save the final 6-7 score."
    );
    setFitnessGameOpen(true);
  }

  useEffect(() => {
    if (!status?.dashboard_should_close) {
      setDashboardClosing(false);
      return;
    }

    setDashboardClosing(true);
    postJson("/api/dashboard/closed", {}).catch(() => {});

    const closeTimer = window.setTimeout(() => {
      try {
        window.open("", "_self");
        window.close();
      } catch (error) {
        // Browsers may block window.close() for tabs not opened by script.
        // The powered-off overlay below remains as the safe fallback.
      }
    }, 250);

    return () => window.clearTimeout(closeTimer);
  }, [status?.dashboard_should_close, status?.dashboard_session_id]);

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
      {dashboardClosing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/95 px-6 text-center text-white backdrop-blur-xl">
          <div className="max-w-lg rounded-[2rem] border border-white/15 bg-white/[0.08] p-8 shadow-2xl">
            <p className="section-kicker text-xs font-semibold">JUNO powered off</p>
            <h2 className="mt-3 text-3xl font-black">Closing dashboard</h2>
            <p className="mt-4 text-sm leading-6 text-slate-300">
              The robot has returned to sleep mode. If your browser blocks automatic tab closing, this page will stay here safely and will be reused when JUNO powers on again.
            </p>
          </div>
        </div>
      )}
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

      <DateTimePanel />

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
              onClick={launchFitnessGame}
              className="btn-primary px-5 py-2.5 text-sm font-semibold"
            >
              Play Fitness Game
            </button>
            <button
              onClick={sleepJuno}
              className="btn-secondary px-5 py-2.5 text-sm font-semibold"
            >
              Put JUNO to Sleep
            </button>
          </div>
          <p className="mt-3 text-sm text-slate-300/75">
            Use the fitness game for a quick movement break, or put JUNO back to sleep when the session is done.
          </p>
        </Card>
      </section>

      <section className="mt-5">
        <MusicPanel status={status} />
      </section>

      <section className="mt-5">
        <FitnessPanel refreshKey={fitnessRefreshKey} onProfileSaved={handleFitnessSessionSaved} />
      </section>

      <section className="mt-5 grid gap-5 lg:grid-cols-2">
        <SchedulePanel schedule={schedule} onScheduleChanged={loadSchedule} />
        <ReminderPanel />
      </section>

      <FitnessGameModal
        open={fitnessGameOpen}
        onClose={() => setFitnessGameOpen(false)}
        onSessionSaved={handleFitnessSessionSaved}
        launchMessage={fitnessLaunchMessage}
      />
    </main>
  );
}
