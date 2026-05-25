import Card from "./Card";

export default function StatusPanel({ status }) {
  const mode = status?.mode ?? "loading";
  const emotion = status?.current_emotion ?? "unknown";
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
            Source: {emotionSource}{confidence > 0 ? ` · ${Math.round(confidence * 100)}% confidence` : ""}
          </p>
        </div>
      </div>
    </Card>
  );
}
