import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from './shared.jsx'
import { useAuth } from '../lib/AuthContext.jsx'
import WhyThisMatch from '../components/WhyThisMatch.jsx'
import JobDetailsDialog, { safeApplyUrl } from '../components/JobDetailsDialog.jsx'

const EXPERIENCE_OPTIONS = ['Internship', 'Entry level', 'Associate', 'Mid-Senior level', 'Director', 'Executive']
const WORK_TYPE_OPTIONS = ['Full-time', 'Part-time', 'Contract', 'Temporary', 'Volunteer', 'Internship']

export default function Jobs() {
  const { token } = useAuth()
  const [jobs, setJobs] = useState([])
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sort, setSort] = useState('score')
  const [filters, setFilters] = useState({ query: '', remote: '', workType: '', experience: '', industry: '', minSalary: '', maxSalary: '' })
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    if (!token) return undefined
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({ page: String(page), limit: '25', sort })
        if (filters.query.trim()) params.set('query', filters.query.trim())
        if (filters.remote) params.set('remote', filters.remote)
        if (filters.workType) params.set('work_type', filters.workType)
        if (filters.experience) params.set('experience_level', filters.experience)
        if (filters.industry.trim()) params.set('industry', filters.industry.trim())
        if (filters.minSalary) params.set('min_salary', filters.minSalary)
        if (filters.maxSalary) params.set('max_salary', filters.maxSalary)

        const res = await fetch(`/api/user/jobs?${params}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Could not load jobs.')
        setJobs(data.jobs || [])
        setTotal(data.total || 0)
        setHasMore(Boolean(data.has_more))
        setSelected(current => data.jobs?.find(j => j.job_id === current?.job_id) || data.jobs?.[0] || null)
      } catch (err) {
        if (err.name !== 'AbortError') setError(err.message)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }, 250)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [token, page, sort, filters])

  const updateFilter = (key, value) => {
    setPage(1)
    setFilters(current => ({ ...current, [key]: value }))
  }

  const clearFilters = () => {
    setPage(1)
    setFilters({ query: '', remote: '', workType: '', experience: '', industry: '', minSalary: '', maxSalary: '' })
  }

  const resultLabel = useMemo(() => {
    if (!total) return 'No matching roles'
    const start = (page - 1) * 25 + 1
    const end = Math.min(page * 25, total)
    return `Showing ${start}–${end} of ${total} matching roles`
  }, [page, total])

  if (error) return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 text-center">
      <p className="text-red-400 mb-4">{error}</p>
      <div className="flex justify-center gap-2">
        <button onClick={() => window.location.reload()} className="btn-primary">Try again</button>
        <a href="/onboarding" className="btn-ghost">Update resume</a>
      </div>
    </section>
  )

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Flow 2"
        title="Jobs that fit you"
        subtitle="Search the full job catalog and see exactly which skills support—or weaken—each match."
      />

      <div className="mt-8 card space-y-4">
        <div className="flex flex-col lg:flex-row gap-3">
          <label className="relative flex-1">
            <span className="sr-only">Search jobs</span>
            <input
              value={filters.query}
              onChange={e => updateFilter('query', e.target.value)}
              placeholder="Search by role, company or skill…"
              className="input pl-10"
            />
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" strokeLinecap="round" />
            </svg>
          </label>
          <select aria-label="Sort jobs" value={sort} onChange={e => { setPage(1); setSort(e.target.value) }} className="input lg:w-44">
            <option value="score">Highest fit first</option>
            <option value="title">Title A–Z</option>
          </select>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-7 gap-3">
          <select aria-label="Work arrangement" value={filters.remote} onChange={e => updateFilter('remote', e.target.value)} className="input">
            <option value="">Any arrangement</option>
            <option value="true">Remote</option>
            <option value="false">On-site</option>
          </select>
          <select aria-label="Work type" value={filters.workType} onChange={e => updateFilter('workType', e.target.value)} className="input">
            <option value="">Any work type</option>
            {WORK_TYPE_OPTIONS.map(option => <option key={option} value={option}>{option}</option>)}
          </select>
          <select aria-label="Experience level" value={filters.experience} onChange={e => updateFilter('experience', e.target.value)} className="input">
            <option value="">Any experience</option>
            {EXPERIENCE_OPTIONS.map(option => <option key={option} value={option}>{option}</option>)}
          </select>
          <input
            aria-label="Industry"
            value={filters.industry}
            onChange={e => updateFilter('industry', e.target.value)}
            placeholder="Industry"
            className="input"
          />
          <input
            aria-label="Minimum salary"
            type="number"
            min="0"
            value={filters.minSalary}
            onChange={e => updateFilter('minSalary', e.target.value)}
            placeholder="Min salary"
            className="input"
          />
          <input
            aria-label="Maximum salary"
            type="number"
            min="0"
            value={filters.maxSalary}
            onChange={e => updateFilter('maxSalary', e.target.value)}
            placeholder="Max salary"
            className="input"
          />
          <button onClick={clearFilters} className="btn-ghost">Clear filters</button>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3 text-xs text-muted">
        <span>{loading ? 'Refreshing matches…' : resultLabel}</span>
        <span className="hidden sm:block">Score = semantic similarity + explicit skill coverage</span>
      </div>

      <div className="mt-4 grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 min-w-0 space-y-3">
          {!loading && jobs.length === 0 && (
            <div className="card text-center text-muted space-y-3">
              <p>No jobs match these filters.</p>
              <button onClick={clearFilters} className="text-brand-400 hover:underline text-sm">Clear filters</button>
            </div>
          )}
          {jobs.map(job => (
            <JobRow
              key={job.job_id}
              job={job}
              active={selected?.job_id === job.job_id}
              onClick={() => setSelected(job)}
            />
          ))}
          {(page > 1 || hasMore) && (
            <div className="flex items-center justify-between pt-2">
              <button disabled={page === 1 || loading} onClick={() => setPage(value => value - 1)} className="btn-ghost disabled:opacity-40">← Previous</button>
              <span className="text-xs text-muted">Page {page}</span>
              <button disabled={!hasMore || loading} onClick={() => setPage(value => value + 1)} className="btn-ghost disabled:opacity-40">Next →</button>
            </div>
          )}
        </div>
        <ExplainPanel key={selected?.job_id || 'empty'} job={selected} />
      </div>
    </section>
  )
}

function JobRow({ job, active, onClick }) {
  const details = job.match_details || {}
  const skills = (details.matched_skills || []).slice(0, 3)
  const missing = (details.missing_skills || []).length

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => {
        if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onClick()
        }
      }}
      className={`w-full text-left card hover:border-brand-400/40 transition ${active ? 'border-brand-400/60 shadow-glow' : ''}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-fg truncate">{job.title}</h3>
          <p className="text-sm text-muted truncate">
            {[job.company, job.location].filter(Boolean).join(' · ') || 'Location not provided'}
            {job.remote && <span className="ml-2 chip border-emerald-400/30 text-emerald-500 dark:text-emerald-200">Remote</span>}
          </p>
        </div>
        <ScoreBadge score={job.match_pct} />
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {skills.map(skill => <span key={skill} className="chip border-emerald-400/30 text-emerald-500 dark:text-emerald-200">✓ {skill}</span>)}
        {missing > 0 && <span className="chip border-amber-400/30 text-amber-500 dark:text-amber-200">{missing} gap{missing === 1 ? '' : 's'}</span>}
        {job.experience_level && <span className="chip">{job.experience_level}</span>}
        {formatSalary(job) && <span className="chip">{formatSalary(job)}</span>}
      </div>
    </article>
  )
}

function ScoreBadge({ score }) {
  const color = score >= 80
    ? 'from-emerald-400 to-emerald-600'
    : score >= 65
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
  const [detailsOpen, setDetailsOpen] = useState(false)

  if (!job) {
    return <aside className="card lg:col-span-2 text-center text-muted">Select a job to see the evidence behind its score.</aside>
  }

  const details = job.match_details || {}
  const matched = details.matched_skills || []
  const missing = details.missing_skills || []
  const hasJobSkills = matched.length + missing.length > 0
  const applyUrl = safeApplyUrl(job.apply_url)

  return (
    <aside className="card lg:col-span-2 min-w-0 self-start space-y-5">
      <div>
        <p className="chip">Match details</p>
        <h3 className="mt-3 text-xl font-semibold text-fg">{job.title}</h3>
        <p className="text-sm text-muted">{[job.company, job.location].filter(Boolean).join(' · ')}</p>
      </div>

      <div>
        <div className="flex items-baseline justify-between">
          <p className="text-xs uppercase tracking-wider text-muted">Estimated fit</p>
          <p className="text-2xl font-bold text-fg">{job.match_pct}%</p>
        </div>
        <div className="mt-2 h-2 rounded-full bg-surface-2 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-brand-400 to-emerald-400 transition-all" style={{ width: `${job.match_pct}%` }} />
        </div>
        <p className="mt-2 text-xs text-muted">Semantic similarity: {Math.round((job.semantic_similarity || 0) * 100)}% · Skill coverage: {job.skill_coverage_pct == null ? 'Not available' : `${job.skill_coverage_pct}%`}</p>
      </div>

      <WhyThisMatch job={job} />

      {hasJobSkills && <p className="text-xs text-muted">Compared with skills mentioned in this job posting. Skills to strengthen are those not found in your CV or acquired roadmap skills; some may be optional.</p>}
      <SkillSection title="Skills found in your profile" skills={matched} tone="good" empty={hasJobSkills ? 'None of the detected job skills were found in your profile yet.' : 'This posting does not provide enough detail to compare skills.'} />
      <SkillSection title="Skills to strengthen" skills={missing} tone="warn" empty={hasJobSkills ? 'Your profile covers all skills detected in this posting.' : 'Skill gaps cannot be assessed from the available job information.'} />

      {(job.description_text || job.description) && <p className="text-sm text-muted leading-relaxed line-clamp-5">{job.description_text || job.description}</p>}
      {job.benefits?.length > 0 && <p className="text-xs text-muted"><span className="font-semibold text-fg">Benefits:</span> {job.benefits.join(' · ')}</p>}

      <div className="grid grid-cols-2 gap-2 pt-1">
        <button onClick={() => navigate(resumeCoachPath(job))} className="btn-primary flex-1">Fit your CV →</button>
        <button onClick={() => navigate(`/roadmap?job_id=${encodeURIComponent(job.job_id)}`)} className="btn-ghost flex-1">Build roadmap →</button>
        {applyUrl ? <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="btn-ghost text-center">Apply</a> : <button disabled className="btn-ghost opacity-50" title="No valid application link was provided">Apply unavailable</button>}
        <button onClick={() => setDetailsOpen(true)} className="btn-ghost" aria-haspopup="dialog">Full job details</button>
      </div>
      {detailsOpen && <JobDetailsDialog job={job} onClose={() => setDetailsOpen(false)} />}
    </aside>
  )
}

function SkillSection({ title, skills, tone, empty }) {
  const toneClass = tone === 'good'
    ? 'text-emerald-500 dark:text-emerald-300 border-emerald-400/20 bg-emerald-500/5'
    : 'text-amber-500 dark:text-amber-300 border-amber-400/20 bg-amber-500/5'
  return (
    <div className={`rounded-xl border p-4 ${toneClass}`}>
      <p className="text-xs uppercase tracking-wider mb-2">{title}</p>
      {skills.length > 0
        ? <div className="flex flex-wrap gap-1.5">{skills.map(skill => <span key={skill} className="chip">{skill}</span>)}</div>
        : <p className="text-xs text-muted">{empty}</p>}
    </div>
  )
}

function formatSalary(job) {
  const value = job.med_salary ?? job.max_salary ?? job.min_salary
  if (value === null || value === undefined || value === '') return ''
  const currency = job.currency || '$'
  const period = job.pay_period ? `/${String(job.pay_period).toLowerCase()}` : ''
  return `${currency} ${Math.round(Number(value)).toLocaleString()}${period}`
}

function resumeCoachPath(job) {
  const params = new URLSearchParams({ job_id: String(job.job_id) })
  if (job.title) params.set('job_title', job.title)
  if (job.company) params.set('company', job.company)
  return `/resume?${params.toString()}`
}
