import { useEffect, useMemo, useState } from "react";
import { getJson, postJson } from "../lib/api";
import Card from "./Card";

function withCacheBuster(url, refreshKey) {
  if (!url) return "";
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}refresh=${refreshKey}`;
}

const GENRE_BUTTONS = [
  {
    label: "Focus",
    genre: "focus",
    emoji: "🎯",
    title: "Deep Focus Mix",
    description: "Lo-fi and instrumental tracks for distraction-free study.",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DWZeKCadgRdKQ?utm_source=generator",
  },
  {
    label: "Calm",
    genre: "calm",
    emoji: "😌",
    title: "Calm Study Mix",
    description: "Gentle, slow-paced music to help you study with ease.",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DWWQRwui0ExPn?utm_source=generator",
  },
  {
    label: "Happy",
    genre: "happy",
    emoji: "😊",
    title: "Positive Focus Mix",
    description: "Upbeat, feel-good songs to keep your study session lively.",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DXdPec7aLTmlC?utm_source=generator",
  },
  {
    label: "Gentle",
    genre: "gentle",
    emoji: "🌿",
    title: "Gentle Reset Mix",
    description: "Soft acoustic and ambient tracks for quiet study time.",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DX4sWSpwq3LiO?utm_source=generator",
  },
  {
    label: "Cool Down",
    genre: "cool down",
    emoji: "❄️",
    title: "Cool-Down Mix",
    description: "Laid-back beats to help you slow down and take a break.",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DX4WYpdgoIcn6?utm_source=generator",
  },
];

export default function MusicPanel({ status }) {
  const [music, setMusic] = useState(status?.music ?? null);
  const [activeGenreButton, setActiveGenreButton] = useState(null);
  const [refreshKey, setRefreshKey] = useState(Date.now());
  // currentEmotion not used for music selection — genre buttons drive playlist choice.
  // const currentEmotion = status?.display_emotion ?? status?.current_emotion ?? "unknown";

  useEffect(() => {
    if (!status?.music) return;
    setMusic(status.music);
    // A backend-side stop (e.g. via voice) should clear an active genre button
    // too, so the panel doesn't stay stuck showing "playing" after a stop.
    if (status.music.status === "stopped" && activeGenreButton) {
      setActiveGenreButton(null);
    }
  }, [status?.music, activeGenreButton]);

  useEffect(() => {
    getJson("/api/music/status").then(setMusic).catch(() => {});
  }, []);

  // Emotion-based play disabled — genre buttons replace this.
  // async function playForEmotion() {
  //   const result = await postJson("/api/music/play", { emotion: currentEmotion });
  //   setMusic(result);
  //   setActiveGenreButton(null);
  //   setRefreshKey(Date.now());
  // }

  function playForGenre(btn) {
    // Set iframe directly from the button's hardcoded URL — no backend emotion lookup.
    setActiveGenreButton(btn);
    setRefreshKey(Date.now());
    // Speak the genre name explicitly so TTS is not driven by emotion detection.
    postJson("/api/robot/speak", { text: `Playing ${btn.title} for you.` }).catch(() => {});
    // Notify backend for state tracking (fire and forget).
    postJson("/api/music/play", { genre: btn.genre }).catch(() => {});
  }

  async function stopMusic() {
    const result = await postJson("/api/music/stop");
    setMusic(result);
    setActiveGenreButton(null);
  }

  async function refreshMusic() {
    if (activeGenreButton) {
      setRefreshKey(Date.now());
    } else {
      const result = await postJson("/api/music/refresh");
      setMusic(result);
      setRefreshKey(Date.now());
    }
  }

  // Genre button active: use its hardcoded embed URL. Otherwise use backend music state.
  const embedUrl = useMemo(() => {
    const base = activeGenreButton ? activeGenreButton.embedUrl : music?.embed_url;
    return base ? withCacheBuster(base, refreshKey) : "";
  }, [activeGenreButton, music?.embed_url, refreshKey]);

  const isPlaying = activeGenreButton != null || (music?.status === "playing" && music?.embed_url);
  const displayTitle = activeGenreButton ? activeGenreButton.title : (music?.title ?? "No playlist selected");
  const displayDesc = activeGenreButton ? activeGenreButton.description : music?.description;

  return (
    <Card title="Music Player">
      <div className="rounded-[1.75rem] border border-white/20 bg-gradient-to-br from-white/[0.12] via-fuchsia-400/[0.08] to-cyan-400/[0.08] p-4">
        <p className="section-kicker text-xs font-semibold">Song playing window</p>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xl font-bold text-white">{displayTitle}</p>
            <p className="text-sm capitalize text-slate-300/80">
              {activeGenreButton ? `Genre: ${activeGenreButton.label}` : "Pick a mood below or ask JUNO by voice"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {/* Play by Emotion button removed — genre buttons drive playlist choice. */}
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
          {displayDesc ?? "Ask JUNO to play music by voice, or pick a mood below."}
        </p>

        <div className="mt-3">
          <p className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wide">Pick a mood</p>
          <div className="flex flex-wrap gap-2">
            {GENRE_BUTTONS.map((btn) => (
              <button
                key={btn.genre}
                onClick={() => playForGenre(btn)}
                className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  activeGenreButton?.genre === btn.genre
                    ? "bg-fuchsia-500 text-white"
                    : "bg-white/10 text-slate-200 hover:bg-white/20"
                }`}
              >
                <span>{btn.emoji}</span>
                {btn.label}
              </button>
            ))}
          </div>
        </div>

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
                Pick a mood below or say &quot;play calm music&quot; to get started.
              </p>
            </div>
          )}
        </div>

        {(activeGenreButton?.embedUrl || music?.external_url) && (
          <a
            href={activeGenreButton ? activeGenreButton.embedUrl.replace("/embed/", "/") : music.external_url}
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
