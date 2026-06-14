import { useEffect, useState } from "react";
import { getJson, postJson } from "../lib/api";
import Card from "./Card";

function formatCalories(value) {
  if (value == null || Number.isNaN(Number(value))) return "Add weight to estimate";
  return `${Number(value).toFixed(2)} kcal`;
}

function formatDate(value) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default function FitnessPanel({ refreshKey = 0, onProfileSaved }) {
  const [scope, setScope] = useState("latest");
  const [stats, setStats] = useState(null);
  const [profile, setProfile] = useState({ height_m: "", weight_kg: "" });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function loadFitnessData(selectedScope = scope) {
    const [profileData, statsData] = await Promise.all([
      getJson("/api/fitness/profile"),
      getJson(`/api/fitness/stats?scope=${selectedScope}`),
    ]);
    setProfile({
      height_m: profileData.height_m ?? "",
      weight_kg: profileData.weight_kg ?? "",
    });
    setStats(statsData);
  }

  useEffect(() => {
    loadFitnessData().catch((error) => setMessage(error.message || "Could not load fitness data."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  async function changeScope(nextScope) {
    setScope(nextScope);
    await loadFitnessData(nextScope);
  }

  async function saveProfile(event) {
    event.preventDefault();
    const height = profile.height_m === "" ? null : Number(profile.height_m);
    const weight = profile.weight_kg === "" ? null : Number(profile.weight_kg);
    if (height != null && (!Number.isFinite(height) || height <= 0)) {
      setMessage("Enter a valid height in metres.");
      return;
    }
    if (weight != null && (!Number.isFinite(weight) || weight <= 0)) {
      setMessage("Enter a valid weight in kilogrammes.");
      return;
    }
    setSaving(true);
    try {
      await postJson("/api/fitness/profile", { height_m: height, weight_kg: weight });
      setMessage("Fitness profile saved. Calorie estimates have been refreshed.");
      await loadFitnessData(scope);
      await onProfileSaved?.();
    } catch (error) {
      setMessage(error.message || "Could not save fitness profile.");
    } finally {
      setSaving(false);
    }
  }

  const latestSession = stats?.latest_session;

  return (
    <Card title="Fitness Game Statistics">
      <div className="grid gap-4 lg:grid-cols-[1fr_0.8fr]">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => changeScope("latest")}
              className={`${scope === "latest" ? "btn-primary" : "btn-secondary"} px-4 py-2 text-sm font-semibold`}
              type="button"
            >
              One-off Stats
            </button>
            <button
              onClick={() => changeScope("cumulative")}
              className={`${scope === "cumulative" ? "btn-primary" : "btn-secondary"} px-4 py-2 text-sm font-semibold`}
              type="button"
            >
              Cumulative Stats
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="soft-panel rounded-2xl p-4">
              <p className="text-sm text-slate-300/75">6-7 Count</p>
              <p className="mt-1 text-3xl font-black text-white">{stats?.score_67 ?? 0}</p>
            </div>
            <div className="soft-panel rounded-2xl p-4">
              <p className="text-sm text-slate-300/75">Calories Burnt</p>
              <p className="mt-1 text-2xl font-black text-white">{formatCalories(stats?.calories_burned)}</p>
            </div>
            <div className="soft-panel rounded-2xl p-4">
              <p className="text-sm text-slate-300/75">Sessions</p>
              <p className="mt-1 text-3xl font-black text-white">{stats?.session_count ?? 0}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-white/15 bg-white/[0.08] p-4 text-sm text-slate-300/80">
            <p className="font-semibold text-white">Latest game</p>
            <p className="mt-1">{latestSession ? `${latestSession.score_67} six-seven motions · ${formatDate(latestSession.created_at)}` : "No fitness game saved yet."}</p>
            <p className="mt-2 text-xs leading-5 text-slate-400">
              Calories are rough activity estimates based on weight and estimated movement duration. They are for dashboard feedback only.
            </p>
          </div>
        </div>

        <form onSubmit={saveProfile} className="space-y-3 rounded-[1.5rem] border border-white/15 bg-white/[0.08] p-4">
          <div>
            <p className="text-lg font-bold text-white">Fitness Profile</p>
            <p className="mt-1 text-sm text-slate-300/75">Enter height and weight to estimate calories burnt after each 6-7 game.</p>
          </div>
          <label className="block text-sm font-medium text-slate-200">
            Height in metres
            <input
              type="number"
              min="0.5"
              max="2.5"
              step="0.01"
              className="input-glass mt-1 w-full rounded-2xl px-3 py-2"
              placeholder="e.g. 1.70"
              value={profile.height_m}
              onChange={(event) => setProfile((current) => ({ ...current, height_m: event.target.value }))}
            />
          </label>
          <label className="block text-sm font-medium text-slate-200">
            Weight in kilogrammes
            <input
              type="number"
              min="20"
              max="250"
              step="0.1"
              className="input-glass mt-1 w-full rounded-2xl px-3 py-2"
              placeholder="e.g. 60"
              value={profile.weight_kg}
              onChange={(event) => setProfile((current) => ({ ...current, weight_kg: event.target.value }))}
            />
          </label>
          <button disabled={saving} className="btn-primary w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50" type="submit">
            {saving ? "Saving..." : "Save Profile"}
          </button>
          {message && <p className="text-sm text-slate-300/80">{message}</p>}
        </form>
      </div>
    </Card>
  );
}
