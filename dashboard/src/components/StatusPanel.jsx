import Card from "./Card";

export default function StatusPanel({ status }) {
  const mode = status?.mode ?? "loading";
  const emotion = status?.display_emotion ?? status?.current_emotion ?? "unknown";
  const rawEkmanEmotion = status?.raw_ekman_emotion ?? status?.current_emotion ?? "unknown";
  const junoEmotion = status?.juno_emotion ?? "unknown";
  const emotionMode = status?.vision_emotion_mode ?? "juno";
  const emotionSource = status?.emotion_source ?? "none";
  const confidence = Number(status?.emotion_confidence ?? 0);

  return (
    <Card title="Robot Status">
      <div className="space-y-4">
        <div className="soft-panel rounded-2xl p-4">
          <p className="text-sm text-slate-300/75">Mode</p>
          <p className="mt-1 text-3xl font-bold capitalize text-white">{mode}</p>
        </div>

        <div className="soft-panel rounded-2xl p-4">
          <p className="text-sm text-slate-300/75">Current Emotion Estimate</p>
          <p className="mt-1 text-3xl font-bold capitalize text-white">{emotion}</p>
          <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-300/70">
            Mode: {emotionMode}
          </p>
          <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-300/70">
            Source: {emotionSource} {confidence > 0 ? ` · ${Math.round(confidence * 100)}% confidence` : ""}
          </p>
          <p className="mt-2 text-xs text-slate-300/65">
            Raw Ekman: <span className="capitalize text-white/85">{rawEkmanEmotion}</span>
          </p>
          <p className="mt-2 text-xs text-slate-300/65">
            JUNO: <span className="capitalize text-white/85">{junoEmotion}</span>
          </p>
        </div>
      </div>
    </Card>
  );
}
