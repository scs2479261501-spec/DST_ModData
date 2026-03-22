export default function EmptyState({ title, description, action = null }) {
  return (
    <div className="panel flex min-h-[240px] flex-col items-center justify-center gap-4 p-10 text-center">
      <div className="font-title text-lg font-semibold text-dst-text-title">{title}</div>
      <p className="max-w-xl font-hans text-sm leading-6 text-dst-text-dim">{description}</p>
      {action}
    </div>
  );
}
