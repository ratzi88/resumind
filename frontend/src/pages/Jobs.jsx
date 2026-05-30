import { useMemo, useState } from 'react'
import { PageHeader } from './shared.jsx'

const MOCK_JOBS = [
  {
    id: 1,
    title: 'Backend Engineer',
    company: 'Stripe',
    location: 'Remote · EU',
    score: 87,
    matched: ['Python', 'PostgreSQL', 'Docker', 'REST APIs'],
    gaps: ['Kubernetes', 'GraphQL'],
    reason: 'Strong Python and database background. Missing container orchestration experience.',
  },
  {
    id: 2,
    title: 'Full-Stack Developer',
    company: 'Wix',
    location: 'Tel Aviv · Hybrid',
    score: 91,
    matched: ['React', 'Node.js', 'TypeScript', 'PostgreSQL'],
    gaps: ['Redis'],
    reason: 'Excellent React/Node alignment. Light caching layer experience would close the gap.',
  },
  {
    id: 3,
    title: 'Data Engineer',
    company: 'Monday.com',
    location: 'Remote',
    score: 83,
    matched: ['Python', 'SQL', 'Airflow'],
    gaps: ['Spark', 'dbt'],
    reason: 'Solid pipelines foundation. Distributed processing skills would strengthen the fit.',
  },
  {
    id: 4,
    title: 'ML Engineer',
    company: 'AI21 Labs',
    location: 'Jerusalem',
    score: 82,
    matched: ['Python', 'PyTorch', 'Transformers'],
    gaps: ['MLOps', 'Kubernetes'],
    reason: 'Strong modeling background. Production deployment skills are the next step.',
  },
  {
    id: 5,
    title: 'DevOps Engineer',
    company: 'Lightricks',
    location: 'Jerusalem',
    score: 80,
    matched: ['Docker', 'Linux', 'CI/CD'],
    gaps: ['Terraform', 'AWS'],
    reason: 'Containerization fundamentals match. Infra-as-code experience would lift this much higher.',
  },
]

export default function Jobs() {
  const [sort, setSort] = useState('score')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(MOCK_JOBS[0])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = MOCK_JOBS.filter(
      (j) =>
        !q ||
        j.title.toLowerCase().includes(q) ||
        j.company.toLowerCase().includes(q) ||
        j.matched.some((s) => s.toLowerCase().includes(q))
    )
    return [...list].sort((a, b) =>
      sort === 'score' ? b.score - a.score : a.title.localeCompare(b.title)
    )
  }, [query, sort])

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Flow 2"
        title="Jobs that fit you"
        subtitle="Vector-matched roles above 80% similarity. Every score comes with a transparent explanation."
      />

      <div className="mt-8 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by role, company or skill…"
            className="input pl-10"
          />
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" strokeLinecap="round" />
          </svg>
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="input sm:w-auto"
        >
          <option value="score">Sort: Match score</option>
          <option value="title">Sort: Title (A-Z)</option>
        </select>
      </div>

      <div className="mt-6 grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 space-y-3">
          {filtered.map((j) => (
            <JobRow
              key={j.id}
              job={j}
              active={selected?.id === j.id}
              onClick={() => setSelected(j)}
            />
          ))}
          {filtered.length === 0 && (
            <div className="card text-center text-muted">No matches above the 80% threshold.</div>
          )}
        </div>
        <ExplainPanel job={selected} />
      </div>
    </section>
  )
}

function JobRow({ job, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left card hover:border-brand-400/40 transition ${
        active ? 'border-brand-400/60 shadow-glow' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-fg">{job.title}</h3>
          <p className="text-sm text-muted">
            {job.company} · {job.location}
          </p>
        </div>
        <ScoreBadge score={job.score} />
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {job.matched.slice(0, 4).map((s) => (
          <span key={s} className="chip border-emerald-400/30 text-emerald-500 dark:text-emerald-200">{s}</span>
        ))}
        {job.gaps.slice(0, 2).map((s) => (
          <span key={s} className="chip border-amber-400/30 text-amber-600 dark:text-amber-200">−{s}</span>
        ))}
      </div>
    </button>
  )
}

function ScoreBadge({ score }) {
  const color =
    score >= 90
      ? 'from-emerald-400 to-emerald-600'
      : score >= 85
      ? 'from-brand-300 to-brand-500'
      : 'from-brand-500 to-brand-700'
  return (
    <div className={`shrink-0 grid place-items-center h-14 w-14 rounded-2xl bg-gradient-to-br ${color} text-white shadow-glow`}>
      <span className="text-lg font-bold">{score}<span className="text-sm">%</span></span>
    </div>
  )
}

function ExplainPanel({ job }) {
  if (!job) {
    return (
      <aside className="card lg:col-span-2 text-center text-muted">
        Select a job to see the explanation.
      </aside>
    )
  }
  return (
    <aside className="card lg:col-span-2 lg:sticky lg:top-24 self-start">
      <p className="chip">Contrastive explanation</p>
      <h3 className="mt-3 text-xl font-semibold text-fg">{job.title}</h3>
      <p className="text-sm text-muted">{job.company} · {job.location}</p>

      <div className="mt-5">
        <div className="flex items-baseline justify-between">
          <p className="text-xs uppercase tracking-wider text-muted">Match score</p>
          <p className="text-2xl font-bold text-fg">{job.score}%</p>
        </div>
        <div className="mt-2 h-2 rounded-full bg-surface-2 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand-400 to-emerald-400"
            style={{ width: `${job.score}%` }}
          />
        </div>
      </div>

      <p className="mt-5 text-sm text-muted">{job.reason}</p>

      <div className="mt-5 space-y-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-emerald-500 dark:text-emerald-300">Why you matched</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {job.matched.map((s) => (
              <span key={s} className="chip border-emerald-400/30 text-emerald-500 dark:text-emerald-200">✓ {s}</span>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider text-amber-600 dark:text-amber-300">What's holding you back</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {job.gaps.map((s) => (
              <span key={s} className="chip border-amber-400/30 text-amber-600 dark:text-amber-200">! {s}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex gap-2">
        <button className="btn-primary flex-1">Apply</button>
        <button className="btn-ghost flex-1">Save</button>
      </div>
    </aside>
  )
}
