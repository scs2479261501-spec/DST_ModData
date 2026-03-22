export default function StatCard({ label, value, hint }) {
  return (
    <div className="rounded-dst border-2 border-dst-border bg-dst-brown shadow-card-inset-sm transition-colors duration-300 hover:border-dst-gold" style={{ borderTop: '3px solid #e8b84b' }}>
      <div className="p-5">
        <div className="font-hans text-sm text-dst-text-dim">{label}</div>
        <div className="mt-3 font-mono text-3xl font-semibold text-dst-gold">{value}</div>
        {hint ? <div className="mt-2 font-hans text-sm text-dst-text-dim">{hint}</div> : null}
      </div>
    </div>
  );
}
