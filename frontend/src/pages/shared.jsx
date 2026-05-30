export function PageHeader({ eyebrow, title, subtitle }) {
  return (
    <div>
      {eyebrow && <span className="chip">{eyebrow}</span>}
      <h1 className="mt-3 text-3xl sm:text-4xl font-bold tracking-tight text-fg">{title}</h1>
      {subtitle && <p className="mt-2 text-muted max-w-2xl">{subtitle}</p>}
    </div>
  )
}
