export default function Card({ title, children, className = "", headerAction }) {
  return (
    <section className={`glass-card overflow-hidden rounded-[2rem] p-5 text-slate-100 ${className}`}>
      <div className="relative z-10">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {headerAction}
        </div>
        {children}
      </div>
    </section>
  );
}
