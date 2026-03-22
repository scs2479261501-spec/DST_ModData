export default function LoadingState({ label = '正在加载数据…' }) {
  return (
    <div className="panel flex min-h-[240px] items-center justify-center p-10">
      <div className="flex items-center gap-3 text-dst-text-dim">
        <span className="h-3 w-3 animate-pulse rounded-sm bg-dst-gold" />
        <span className="font-hans">{label}</span>
      </div>
    </div>
  );
}
