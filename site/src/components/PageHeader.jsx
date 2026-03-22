export default function PageHeader({ eyebrow, title, description, actions = null }) {
  return (
    <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        {eyebrow ? <p className="font-title text-xs uppercase tracking-[0.28em] text-dst-gold/70">{eyebrow}</p> : null}
        <h2 className="mt-2 font-title text-2xl font-semibold text-dst-text-title sm:text-3xl">{title}</h2>
        <p className="mt-3 max-w-3xl font-hans text-sm leading-6 text-dst-text-dim">{description}</p>
      </div>
      {actions ? <div>{actions}</div> : null}
    </div>
  );
}
