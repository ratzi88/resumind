import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from './shared.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

export default function Jobs() {
  const { token } = useAuth()
  const [jobs,    setJobs]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [sort,    setSort]    = useState('score')
  const [query,   setQuery]   = useState('')
  const [selected,setSelected]= useState(null)

  useEffect(() => {
    if (!token) return
    fetch('/api/user/jobs', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.detail || 'Could not load jobs.')
        setJobs(d.jobs)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

  const filtered = useMemo(() => {
    if (!jobs) return []
    const q = query.trim().toLowerCase()
    const list = jobs.filter(j =>
      !q ||
      j.title?.toLowerCase().includes(q) ||
      j.company?.toLowerCase().includes(q) ||
      j.skills_desc?.toLowerCase().includes(q)
    )
    return [...list].sort((a, b) =>
      sort === 'score'
        ? b.match_pct - a.match_pct
        : a.title.localeCompare(b.title)
    )
  }, [jobs, query, sort])

  if (loading) return <LoadingState />

  if (error) return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 text-center">
      <p className="text-red-400 mb-4">{error}</p>
      <a href="/onboarding" className="btn-primary">Re-run onboarding</a>
    </section>
  )

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Flow 2"
        title="Jobs that fit you"
        subtitle="Roles matched to your resume using semantic similarity. Each score is normalised for readability."
      />

      <div className="mt-8 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search by role, company or skill…"
            className="input pl-10"
          />
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" strokeLinecap="round" />
          </svg>
        </div>
        <select value={sort} onChange={e => setSort(e.target.value)} className="input sm:w-auto">
          <option value="score">Sort: Match score</option>
          <option value="title">Sort: Title (A-Z)</option>
        </select>
      </div>

      <div className="mt-6 grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 space-y-3">
          {filtered.length === 0 && jobs?.length === 0 && (
            <div className="card text-center text-muted">
              <p>No matches found for your resume.</p>
              <a href="/onboarding" className="text-brand-400 hover:underline text-sm mt-2 block">
                Update your resume in onboarding
              </a>
            </div>
          )}
          {filtered.length === 0 && jobs?.length > 0 && (
            <div className="card text-center text-muted">No results for "{query}"</div>
          )}
          {filtered.map(j => (
            <JobRow key={j.job_id} job={j} active={selected?.job_id === j.job_id} onClick={() => setSelected(j)} />
          ))}
        </div>
        <ExplainPanel job={selected} />
      </div>
    </section>
  )
}

function JobRow({ job, active, onClick }) {
  const skills = job.skills_desc
    ? job.skills_desc.split(/[,;]/).map(s => s.trim()).filter(Boolean).slice(0, 4)
    : []

  return (
    <button
      onClick={onClick}
      className={`w-full text-left card hover:border-brand-400/40 transition ${active ? 'border-brand-400/60 shadow-glow' : ''}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-fg">{job.title}</h3>
          <p className="text-sm text-muted">
            {[job.company, job.location].filter(Boolean).join(' · ')}
            {job.remote && <span className="ml-2 chip border-emerald-400/30 text-emerald-500 dark:text-emerald-200">Remote</span>}
          </p>
        </div>
        <ScoreBadge score={job.match_pct} />
      </div>
      {skills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {skills.map(s => (
            <span key={s} className="chip border-brand-400/30 text-brand-500 dark:text-brand-200">{s}</span>
          ))}
          {job.experience_level && (
            <span className="chip">{job.experience_level}</span>
          )}
        </div>
      )}
    </button>
  )
}

function ScoreBadge({ score }) {
  const color = score >= 90
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
  const navigate = useNavigate()

  if (!job) {
    return (
      <aside className="card lg:col-span-2 text-center text-muted">
        Select a job to see details and get your roadmap.
      </aside>
    )
  }

  const skills = job.skills_desc
    ? job.skills_desc.split(/[,;]/).map(s => s.trim()).filter(Boolean)
    : []

  return (
    <aside className="card lg:col-span-2 lg:sticky lg:top-24 self-start space-y-5">
      <div>
        <p className="chip">Match details</p>
        <h3 className="mt-3 text-xl font-semibold text-fg">{job.title}</h3>
        <p className="text-sm text-muted">{[job.company, job.location].filter(Boolean).join(' · ')}</p>
      </div>

      <div>
        <div className="flex items-baseline justify-between">
          <p className="text-xs uppercase tracking-wider text-muted">Match score</p>
          <p className="text-2xl font-bold text-fg">{job.match_pct}%</p>
        </div>
        <div className="mt-2 h-2 rounded-full bg-surface-2 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-brand-400 to-emerald-400" style={{ width: `${job.match_pct}%` }} />
        </div>
      </div>

      {skills.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-wider text-emerald-500 dark:text-emerald-300 mb-2">Required skills</p>
          <div className="flex flex-wrap gap-1.5">
            {skills.slice(0, 10).map(s => (
              <span key={s} className="chip border-emerald-400/30 text-emerald-500 dark:text-emerald-200">{s}</span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <button onClick={() => navigate('/roadmap')} className="btn-primary flex-1">
          View roadmap →
        </button>
        {job.apply_url && (
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="btn-ghost flex-1 text-center">
            Apply
          </a>
        )}
      </div>
    </aside>
  )
}

function LoadingState() {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 text-center">
      <div className="inline-flex items-center gap-3 text-muted">
        <span className="h-5 w-5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
        <span>Finding your best matches…</span>
      </div>
    </div>
  )
}
