export default function Panel({ title, subtitle, action, className = '', children }) {
  return (
    <section className={`panel p-6 ${className}`.trim()}>
      {(title || subtitle || action) && (
        <div className="mb-5 flex flex-col gap-3 border-b border-dashed border-dst-border pb-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            {title ? <h2 className="font-title text-lg font-semibold text-dst-gold">{title}</h2> : null}
            {subtitle ? <p className="mt-1 font-hans text-sm text-dst-text-dim">{subtitle}</p> : null}
          </div>
          {action ? <div>{action}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}
