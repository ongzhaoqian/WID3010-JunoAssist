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
      <div className="rounded-[1.75rem] border border-white/20 bg-gradient-to-br from-white/[0.12] via-fuchsia-400/[0.08] to-cyan-400/[0.08] p-4">
        <p className="section-kicker text-xs font-semibold">Song playing window</p>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xl font-bold text-white">
              {music?.title ?? "No playlist selected"}
            </p>
            <p className="text-sm capitalize text-slate-300/80">
              Current emotion: {currentEmotion} · Selected mood: {music?.emotion ?? "none"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={playForEmotion}
              className="btn-primary px-5 py-2.5 text-sm font-semibold"
            >
              Play by Emotion
            </button>
            <button
              onClick={refreshMusic}
              className="btn-secondary px-5 py-2.5 text-sm font-semibold"
            >
              Refresh
            </button>
            <button
              onClick={stopMusic}
              className="btn-secondary px-5 py-2.5 text-sm font-semibold"
            >
              Stop
            </button>
          </div>
        </div>

        <p className="mt-3 text-sm leading-6 text-slate-300/80">
          {music?.description ?? "When the user asks JUNO to play music, the dashboard selects a Spotify playlist based on the latest emotion estimate. If the vision model is off, JUNO uses a neutral focus playlist."}
        </p>

        <div className="mt-4 overflow-hidden rounded-[1.5rem] border border-white/20 bg-slate-950/45 shadow-inner">
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
              <p className="text-lg font-semibold text-white">Music is ready when you are.</p>
              <p className="mt-2 max-w-md text-sm text-slate-300/75">
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
            className="mt-3 inline-flex text-sm font-medium text-cyan-200 hover:text-white"
          >
            Open playlist in Spotify
          </a>
        )}
      </div>
    </Card>
  );
}
