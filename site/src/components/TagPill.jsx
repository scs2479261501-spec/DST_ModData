export default function TagPill({ children, className = '', style = undefined }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm border border-dst-gold/30 bg-dst-gold/15 px-3 py-1 text-xs text-dst-gold ${className}`.trim()}
      style={style}
    >
      {children}
    </span>
  );
}
