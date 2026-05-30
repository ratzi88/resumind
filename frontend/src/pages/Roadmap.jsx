import { useMemo, useState } from 'react'
import { PageHeader } from './shared.jsx'

const INITIAL_SKILLS = [
  { id: 's1', name: 'Python', impact: 18, acquired: true, category: 'Foundations' },
  { id: 's2', name: 'PostgreSQL', impact: 14, acquired: true, category: 'Foundations' },
  { id: 's3', name: 'Docker', impact: 12, acquired: true, category: 'Foundations' },
  { id: 's4', name: 'REST APIs', impact: 10, acquired: true, category: 'Foundations' },
  { id: 's5', name: 'Kubernetes', impact: 12, acquired: false, category: 'Infrastructure' },
  { id: 's6', name: 'Terraform', impact: 8, acquired: false, category: 'Infrastructure' },
  { id: 's7', name: 'GraphQL', impact: 7, acquired: false, category: 'APIs' },
  { id: 's8', name: 'Redis', impact: 5, acquired: false, category: 'Performance' },
  { id: 's9', name: 'System Design', impact: 9, acquired: false, category: 'Engineering' },
  { id: 's10', name: 'CI/CD pipelines', impact: 6, acquired: false, category: 'Infrastructure' },
]

const TARGET_ROLE = 'Senior Backend Engineer'

export default function Roadmap() {
  const [skills, setSkills] = useState(INITIAL_SKILLS)

  const score = useMemo(() => {
    const total = skills.reduce((sum, s) => sum + s.impact, 0)
    const earned = skills.filter((s) => s.acquired).reduce((sum, s) => sum + s.impact, 0)
    return Math.round((earned / total) * 100)
  }, [skills])

  const acquiredCount = skills.filter((s) => s.acquired).length

  const grouped = useMemo(() => {
    const remaining = skills.filter((s) => !s.acquired).sort((a, b) => b.impact - a.impact)
    const byCat = {}
    for (const s of remaining) {
      ;(byCat[s.category] = byCat[s.category] || []).push(s)
    }
    return byCat
  }, [skills])

  const acquired = skills.filter((s) => s.acquired)

  const toggle = (id) =>
    setSkills((prev) => prev.map((s) => (s.id === id ? { ...s, acquired: !s.acquired } : s)))

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Flow 3"
        title="Your career roadmap"
        subtitle={`Targeting: ${TARGET_ROLE}. Check off a skill as you learn it — your CV updates and jobs re-rank automatically.`}
      />

      <div className="mt-8 grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {Object.entries(grouped).map(([cat, items]) => (
            <CategoryGroup key={cat} category={cat} items={items} onToggle={toggle} />
          ))}
          {Object.keys(grouped).length === 0 && (
            <div className="card text-center">
              <p className="text-fg font-semibold">You did it. 🎉</p>
              <p className="text-muted text-sm mt-1">Every skill on this roadmap is checked off.</p>
            </div>
          )}

          {acquired.length > 0 && (
            <div className="card">
              <p className="text-xs uppercase tracking-wider text-emerald-500 dark:text-emerald-300">Already on your CV</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {acquired.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => toggle(s.id)}
                    className="chip border-emerald-400/30 text-emerald-500 dark:text-emerald-200 hover:bg-surface-2"
                    title="Remove from CV"
                  >
                    ✓ {s.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <ProgressPanel score={score} acquiredCount={acquiredCount} total={skills.length} />
      </div>
    </section>
  )
}

function CategoryGroup({ category, items, onToggle }) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-fg">{category}</h3>
        <span className="chip">{items.length} skill{items.length === 1 ? '' : 's'}</span>
      </div>
      <ul className="mt-4 divide-y divide-line">
        {items.map((s) => (
          <li key={s.id} className="py-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-fg font-medium">{s.name}</p>
              <p className="text-xs text-muted">+{s.impact}% predicted match boost</p>
            </div>
            <button
              onClick={() => onToggle(s.id)}
              className="btn-ghost text-xs px-3 py-1.5 hover:border-emerald-400/40 hover:text-emerald-500 dark:hover:text-emerald-200"
            >
              I acquired this →
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function ProgressPanel({ score, acquiredCount, total }) {
  return (
    <aside className="card lg:sticky lg:top-24 self-start">
      <p className="chip">Progress</p>
      <div className="mt-4">
        <div className="relative h-32 w-32 mx-auto">
          <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
            <circle cx="18" cy="18" r="15.9155" fill="none" stroke="rgb(var(--surface-2))" strokeWidth="3" />
            <circle
              cx="18"
              cy="18"
              r="15.9155"
              fill="none"
              stroke="url(#grad)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={`${score}, 100`}
            />
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#5d8eff" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 grid place-items-center">
            <div className="text-center">
              <p className="text-3xl font-bold text-fg">{score}%</p>
              <p className="text-[10px] uppercase tracking-wider text-muted">Match</p>
            </div>
          </div>
        </div>
      </div>

      <dl className="mt-6 space-y-3 text-sm">
        <div className="flex justify-between">
          <dt className="text-muted">Target role</dt>
          <dd className="text-fg font-medium">{TARGET_ROLE}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted">Skills acquired</dt>
          <dd className="text-fg font-medium">
            {acquiredCount} / {total}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted">Jobs re-ranked</dt>
          <dd className="text-emerald-500 dark:text-emerald-300 font-medium">+{Math.round(score / 10)} new matches</dd>
        </div>
      </dl>

      <p className="mt-6 text-xs text-subtle leading-relaxed">
        When you mark a skill acquired, ResuMind updates your CV in storage and re-runs the matching
        engine. New jobs may surface above the 80% threshold.
      </p>
    </aside>
  )
}
