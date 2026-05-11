import Card from "./Card";

export default function SchedulePanel({ schedule }) {
  return (
    <Card title="Upcoming Schedule">
      <div className="space-y-3">
        {schedule.length === 0 ? (
          <p className="text-slate-500">No schedule items loaded.</p>
        ) : (
          schedule.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-200 p-3">
              <p className="font-semibold text-slate-900">{item.title}</p>
              <p className="text-sm text-slate-500">
                {item.date} · {item.time} · {item.priority} priority
              </p>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
