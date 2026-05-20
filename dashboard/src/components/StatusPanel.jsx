import Card from "./Card";

export default function StatusPanel({ status }) {
  const mode = status?.mode ?? "loading";
  const emotion = status?.current_emotion ?? "unknown";

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
        </div>

        <p className="text-sm leading-6 text-slate-300/75">
          Emotion is an estimate based on visible expression, not a diagnosis.
        </p>
      </div>
    </Card>
  );
}
