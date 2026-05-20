import Card from "./Card";

export default function StatusPanel({ status }) {
  const mode = status?.mode ?? "loading";
  const emotion = status?.current_emotion ?? "unknown";

  return (
    <Card title="Robot Status">
      <div className="space-y-2">
        <p className="text-sm text-slate-600">Mode</p>
        <p className="text-2xl font-bold capitalize text-slate-900">{mode}</p>

        <p className="text-sm text-slate-600 pt-3">Current Emotion Estimate</p>
        <p className="text-2xl font-bold capitalize text-slate-900">{emotion}</p>

        <p className="text-sm text-slate-500 pt-3">
          Emotion is an estimate based on visible expression, not a diagnosis.
        </p>
      </div>
    </Card>
  );
}
