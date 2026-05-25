export default function Card({ title, children, className = "" }) {
  return (
    <section className={`glass-card overflow-hidden rounded-[2rem] p-5 text-slate-100 ${className}`}>
      <div className="relative z-10">
        <h2 className="mb-3 text-lg font-semibold text-white">{title}</h2>
        {children}
      </div>
    </section>
  );
}
