import { useEffect, useMemo, useState } from "react";
import { getJson, postJson } from "../lib/api";
import Card from "./Card";

function withCacheBuster(url, refreshKey) {
  if (!url) return "";
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}refresh=${refreshKey}`;
}

export default function MusicPanel({ status }) {
  const [music, setMusic] = useState(status?.music ?? null);
  const [refreshKey, setRefreshKey] = useState(Date.now());
  const currentEmotion = status?.current_emotion ?? "unknown";

  useEffect(() => {
    if (status?.music) {
      setMusic(status.music);
    }
  }, [status?.music]);

  useEffect(() => {
    getJson("/api/music/status").then(setMusic).catch(() => {});
  }, []);

  async function playForEmotion() {
    const result = await postJson("/api/music/play", { emotion: currentEmotion });
    setMusic(result);
    setRefreshKey(Date.now());
  }

  async function stopMusic() {
    const result = await postJson("/api/music/stop");
    setMusic(result);
  }

  async function refreshMusic() {
    const result = await postJson("/api/music/refresh");
    setMusic(result);
    setRefreshKey(Date.now());
  }

  const embedUrl = useMemo(
    () => withCacheBuster(music?.embed_url, refreshKey),
    [music?.embed_url, refreshKey]
  );
  const isPlaying = music?.status === "playing" && music?.embed_url;

  return (
    <Card title="Emotion-Aware Music">
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-indigo-50 p-4">
        <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Song playing window</p>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xl font-bold text-slate-900">
              {music?.title ?? "No playlist selected"}
            </p>
            <p className="text-sm capitalize text-slate-600">
              Current emotion: {currentEmotion} · Selected mood: {music?.emotion ?? "none"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={playForEmotion}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white"
            >
              Play by Emotion
            </button>
            <button
              onClick={refreshMusic}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800"
            >
              Refresh
            </button>
            <button
              onClick={stopMusic}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800"
            >
              Stop
            </button>
          </div>
        </div>

        <p className="mt-3 text-sm text-slate-600">
          {music?.description ?? "When the user asks JUNO to play music, the dashboard selects a Spotify playlist based on the latest emotion estimate. If the vision model is off, JUNO uses a neutral focus playlist."}
        </p>

        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-inner">
          {isPlaying ? (
            <iframe
              key={embedUrl}
              title="Spotify emotion-aware playlist"
              src={embedUrl}
              width="100%"
              height="352"
              allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
              loading="lazy"
              className="block"
            />
          ) : (
            <div className="flex min-h-56 flex-col items-center justify-center p-8 text-center">
              <p className="text-lg font-semibold text-slate-900">Music is ready when you are.</p>
              <p className="mt-2 max-w-md text-sm text-slate-500">
                Ask JUNO to play music or press “Play by Emotion” to load a playlist here.
              </p>
            </div>
          )}
        </div>

        {music?.external_url && (
          <a
            href={music.external_url}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex text-sm font-medium text-indigo-700 hover:text-indigo-900"
          >
            Open playlist in Spotify
          </a>
        )}
      </div>
    </Card>
  );
}
