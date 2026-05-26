import { useEffect, useMemo, useState } from "react";
import { postJson } from "../lib/api";

const GAME_URL = "https://67speed.com/";

function extractScoreFromMessage(data) {
  if (data == null) return null;

  if (typeof data === "number" && Number.isFinite(data)) {
    return Math.max(0, Math.floor(data));
  }

  if (typeof data === "string") {
    const scoreMatch = data.match(/(?:score|count|67|six\s*seven|six-seven|reps?)\D{0,12}(\d{1,5})/i)
      || data.match(/\b(\d{1,5})\b/);
    return scoreMatch ? Math.max(0, Number(scoreMatch[1])) : null;
  }

  if (typeof data === "object") {
    const possibleKeys = [
      "score67",
      "score_67",
      "sixSevenCount",
      "six_seven_count",
      "number67",
      "count67",
      "score",
      "count",
      "reps",
      "moves",
    ];
    for (const key of possibleKeys) {
      const value = data[key];
      if (typeof value === "number" && Number.isFinite(value)) {
        return Math.max(0, Math.floor(value));
      }
      if (typeof value === "string" && /^\d+$/.test(value.trim())) {
        return Math.max(0, Number(value.trim()));
      }
    }
  }

  return null;
}

export default function FitnessGameModal({ open, onClose, onSessionSaved }) {
  const [score, setScore] = useState("");
  const [durationSeconds, setDurationSeconds] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [iframeFailed, setIframeFailed] = useState(false);
  const iframeSrc = useMemo(() => `${GAME_URL}?juno=1`, []);

  useEffect(() => {
    if (!open) return undefined;

    function handleMessage(event) {
      // The game is third-party. If it emits postMessage score data, capture it;
      // otherwise the manual input remains the reliable path.
      if (!String(event.origin || "").includes("67speed.com")) return;
      const detectedScore = extractScoreFromMessage(event.data);
      if (detectedScore == null) return;
      setScore(String(detectedScore));
      setMessage(`Detected score from game message: ${detectedScore}`);
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [open]);

  if (!open) return null;

  function openPopupWindow() {
    const popup = window.open(
      GAME_URL,
      "juno-67-speed-game",
      "popup=yes,width=520,height=820,menubar=no,toolbar=no,location=yes,status=no,scrollbars=yes,resizable=yes"
    );
    if (!popup) {
      setMessage("Your browser blocked the popup. Please allow popups or use the embedded game panel.");
      return;
    }
    popup.focus?.();
    setMessage("Game popup opened. Enter the 6-7 score here after the round if it is not auto-detected.");
  }

  async function saveScore() {
    const numericScore = Number(score);
    if (!Number.isFinite(numericScore) || numericScore < 0) {
      setMessage("Enter a valid 6-7 score before saving.");
      return;
    }
    const numericDuration = durationSeconds ? Number(durationSeconds) : null;
    if (numericDuration != null && (!Number.isFinite(numericDuration) || numericDuration <= 0)) {
      setMessage("Duration must be empty or a positive number of seconds.");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        score_67: Math.floor(numericScore),
        source: "dashboard_game",
      };
      if (numericDuration) payload.duration_seconds = Math.floor(numericDuration);
      const session = await postJson("/api/fitness/sessions", payload);
      setMessage(`Saved ${session.score_67} six-seven motions.`);
      setScore("");
      setDurationSeconds("");
      await onSessionSaved?.(session);
    } catch (error) {
      setMessage(error.message || "Could not save the fitness score.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6 backdrop-blur-xl">
      <div className="glass-card relative flex max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-[2rem] text-slate-100">
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-5">
          <div>
            <p className="section-kicker text-xs font-semibold">Fitness Game</p>
            <h2 className="mt-1 text-2xl font-black text-white">Play 6-7 Speed Challenge</h2>
            <p className="mt-1 text-sm text-slate-300/75">
              Play the game, then save your 6-7 count for one-off or cumulative fitness statistics.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={openPopupWindow} className="btn-secondary px-4 py-2 text-sm font-semibold" type="button">
              Open Game Popup
            </button>
            <button onClick={onClose} className="btn-secondary px-4 py-2 text-sm font-semibold" type="button">
              Close
            </button>
          </div>
        </div>

        <div className="relative z-10 grid min-h-0 flex-1 gap-4 p-5 lg:grid-cols-[1.5fr_0.7fr]">
          <div className="min-h-[520px] overflow-hidden rounded-[1.5rem] border border-white/15 bg-slate-950/55">
            {!iframeFailed ? (
              <iframe
                title="67 Speed fitness game"
                src={iframeSrc}
                className="h-full min-h-[520px] w-full"
                allow="clipboard-read; clipboard-write; fullscreen; autoplay"
                loading="lazy"
                onError={() => setIframeFailed(true)}
              />
            ) : (
              <div className="flex h-full min-h-[520px] flex-col items-center justify-center p-8 text-center">
                <p className="text-xl font-bold text-white">Embedded game could not load.</p>
                <p className="mt-2 max-w-md text-sm text-slate-300/75">
                  Some third-party sites block iframe embedding. Use the popup button to play the game in a separate window.
                </p>
                <button onClick={openPopupWindow} className="btn-primary mt-4 px-5 py-2.5 text-sm font-semibold" type="button">
                  Open Game Popup
                </button>
              </div>
            )}
          </div>

          <aside className="space-y-4 rounded-[1.5rem] border border-white/15 bg-white/[0.08] p-4">
            <div>
              <p className="text-lg font-bold text-white">Record Game Result</p>
              <p className="mt-1 text-sm leading-6 text-slate-300/75">
                Automatic extraction is attempted through browser messages from the game. If the game does not share its score, enter the final 6-7 count manually after one round.
              </p>
            </div>

            <label className="block text-sm font-medium text-slate-200">
              Number of 6-7 motions completed
              <input
                type="number"
                min="0"
                max="10000"
                className="input-glass mt-1 w-full rounded-2xl px-3 py-2"
                placeholder="e.g. 67"
                value={score}
                onChange={(event) => setScore(event.target.value)}
              />
            </label>

            <label className="block text-sm font-medium text-slate-200">
              Duration in seconds, optional
              <input
                type="number"
                min="1"
                max="600"
                className="input-glass mt-1 w-full rounded-2xl px-3 py-2"
                placeholder="Leave blank for automatic estimate"
                value={durationSeconds}
                onChange={(event) => setDurationSeconds(event.target.value)}
              />
            </label>

            <button
              onClick={saveScore}
              disabled={saving}
              className="btn-primary w-full px-5 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
              type="button"
            >
              {saving ? "Saving..." : "Save Fitness Score"}
            </button>

            {message && (
              <p className="rounded-2xl border border-white/15 bg-white/[0.08] p-3 text-sm text-slate-200">
                {message}
              </p>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
