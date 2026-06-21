import Card from "./Card";

export default function FitnessPanel({ onPlayGame }) {
  return (
    <Card title="Movement Break">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-3xl text-sm leading-6 text-slate-300/80">
          A short movement break helps reset focus and reduce stress. Play the destress game for a quick reset.
        </p>
        {onPlayGame && (
          <button onClick={onPlayGame} className="btn-primary shrink-0 px-5 py-2.5 text-sm font-semibold" type="button">
            Play Destress Game
          </button>
        )}
      </div>
    </Card>
  );
}
