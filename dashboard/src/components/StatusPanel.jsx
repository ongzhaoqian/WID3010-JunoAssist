import Card from "./Card";

const EMOTION_VISUALS = {
  stress: {
    labels: new Set(["stress", "stressed", "fear", "fearful", "scared", "anger", "angry", "frustrated", "frustration", "disgust", "disgusted"]),
    colour: "#ef4444",
    label: "Stress-class",
  },
  lowEnergy: {
    labels: new Set(["tired", "sad", "sadness", "sleepy", "fatigued", "exhausted", "drained"]),
    colour: "#60a5fa",
    label: "Low-energy",
  },
  positive: {
    labels: new Set(["happy", "happiness", "calm", "focused", "focus", "relaxed", "motivated"]),
    colour: "#4ade80",
    label: "Positive/focused",
  },
};

function normaliseEmotion(value) {
  return String(value ?? "unknown").trim().toLowerCase().replaceAll("_", "-");
}

function formatEmotionLabel(value) {
  const normalised = normaliseEmotion(value).replaceAll("-", " ");
  if (!normalised || normalised === "unknown") return "Unknown";
  return normalised
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function getEmotionVisualState(...values) {
  const labels = values.map(normaliseEmotion);
  if (labels.some((label) => EMOTION_VISUALS.stress.labels.has(label))) {
    return EMOTION_VISUALS.stress;
  }
  if (labels.some((label) => EMOTION_VISUALS.lowEnergy.labels.has(label))) {
    return EMOTION_VISUALS.lowEnergy;
  }
  if (labels.some((label) => EMOTION_VISUALS.positive.labels.has(label))) {
    return EMOTION_VISUALS.positive;
  }
  return { colour: "#94a3b8", label: "Neutral/unknown" };
}

export function isStressClassEmotion(...values) {
  return values.map(normaliseEmotion).some((label) => EMOTION_VISUALS.stress.labels.has(label));
}

export default function StatusPanel({ status }) {
  const mode = status?.mode ?? "loading";
  const emotion = status?.display_emotion ?? status?.current_emotion ?? "unknown";
  const rawEkmanEmotion = status?.raw_ekman_emotion ?? status?.current_emotion ?? "unknown";
  const junoEmotion = status?.juno_emotion ?? "unknown";
  const emotionMode = status?.vision_emotion_mode ?? "juno";
  const emotionSource = status?.emotion_source ?? "none";
  const confidence = Number(status?.emotion_confidence ?? 0);
  const breakSuggested = Boolean(status?.break_suggested);
  const stressActive = breakSuggested || isStressClassEmotion(emotion, rawEkmanEmotion, junoEmotion);
  const visualState = getEmotionVisualState(emotion, rawEkmanEmotion, junoEmotion);
  const badgeStyle = {
    color: visualState.colour,
    borderColor: `${visualState.colour}cc`,
    backgroundColor: `${visualState.colour}22`,
    boxShadow: `0 0 40px ${visualState.colour}33`,
  };

  return (
    <Card title="Robot Status" className={stressActive ? "ring-2 ring-[#ef4444]/45" : ""}>
      <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr] lg:items-stretch">
        <div className="soft-panel flex min-h-[15rem] flex-col items-center justify-center rounded-[2rem] p-6 text-center">
          <p className="section-kicker text-xs font-semibold">Current emotion estimate</p>
          <div
            className={`mt-4 inline-flex min-w-[16rem] items-center justify-center rounded-[2rem] border px-8 py-5 text-[clamp(2.75rem,6vw,5rem)] font-black leading-none tracking-tight ${stressActive ? "animate-pulse" : ""}`}
            style={badgeStyle}
            aria-live="polite"
          >
            {formatEmotionLabel(emotion)}
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-sm text-slate-300/80">
            <span className="rounded-full border border-white/15 bg-white/[0.08] px-3 py-1 font-semibold text-white">
              {visualState.label}
            </span>
            <span className="rounded-full border border-white/15 bg-white/[0.08] px-3 py-1 uppercase tracking-[0.16em]">
              {emotionMode} mode
            </span>
            <span className="rounded-full border border-white/15 bg-white/[0.08] px-3 py-1">
              {emotionSource}{confidence > 0 ? ` · ${Math.round(confidence * 100)}% confidence` : ""}
            </span>
          </div>
          {stressActive && (
            <p className="mt-4 max-w-2xl rounded-2xl border border-[#ef4444]/40 bg-[#ef4444]/15 px-4 py-3 text-sm font-semibold text-red-100">
              Stress-class emotion detected. JUNO can recommend a short movement break to help reset focus.
            </p>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
          <div className="soft-panel rounded-2xl p-4">
            <p className="text-sm text-slate-300/75">Mode</p>
            <p className="mt-1 text-3xl font-bold capitalize text-white">{mode}</p>
          </div>
          <div className="soft-panel rounded-2xl p-4">
            <p className="text-sm text-slate-300/75">Raw Ekman</p>
            <p className="mt-1 text-2xl font-bold text-white">{formatEmotionLabel(rawEkmanEmotion)}</p>
          </div>
          <div className="soft-panel rounded-2xl p-4">
            <p className="text-sm text-slate-300/75">JUNO Label</p>
            <p className="mt-1 text-2xl font-bold text-white">{formatEmotionLabel(junoEmotion)}</p>
          </div>
          <div className="soft-panel rounded-2xl p-4">
            <p className="text-sm text-slate-300/75">Break Prompt</p>
            <p className="mt-1 text-2xl font-bold text-white">{breakSuggested ? "Suggested" : "Not active"}</p>
          </div>
        </div>
      </div>
    </Card>
  );
}
