import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext.jsx'
import { PageHeader } from './shared.jsx'

export default function Statistics() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!token) return undefined
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetch('/api/user/statistics', { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal })
      .then(async response => {
        let body
        try { body = await response.json() } catch { throw new Error('The server returned an unexpected response.') }
        if (!response.ok) throw new Error(body.detail || 'Could not calculate your statistics.')
        setData(body)
      })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [token])

  return <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
    <PageHeader eyebrow="Market insights" title="Your statistics"
      subtitle="See which skills appear most often across all jobs currently recommended to your profile." />

    {loading && <div role="status" className="mt-10 card flex items-center gap-3 text-muted">
      <span className="h-5 w-5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
      Calculating statistics across your matched jobs…
    </div>}

    {error && <div className="mt-10 card text-center space-y-4">
      <p role="alert" className="text-red-400">{error}</p>
      <button className="btn-primary" onClick={() => window.location.reload()}>Try again</button>
    </div>}

    {!loading && data && data.total_jobs === 0 && <div className="mt-10 card text-center space-y-4">
      <h2 className="text-xl font-semibold">No matched-job statistics yet</h2>
      <p className="text-muted">Update your resume or target role to calculate new job matches.</p>
      <Link to="/onboarding" className="btn-primary">Redo onboarding</Link>
    </div>}

    {!loading && data && data.total_jobs > 0 && <StatisticsContent data={data} />}
  </section>
}

function StatisticsContent({ data }) {
  const topStrength = data.strongest_skills?.[0]
  const topGap = data.skills_to_strengthen?.[0]
  return <div className="mt-8 space-y-6">
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Metric label="Recommended jobs" value={data.total_jobs} note="Used for every percentage below" />
      <Metric label="Average estimated fit" value={data.average_fit == null ? '—' : `${data.average_fit}%`} note="Product score, not hiring probability" />
      <Metric label="Most useful strength" value={topStrength?.name || 'None detected'} note={topStrength ? `${formatPercent(topStrength.percentage)} of matched jobs` : 'No frequent profile skill found'} />
      <Metric label="Biggest opportunity" value={topGap?.name || 'None detected'} note={topGap ? `${formatPercent(topGap.percentage)} of matched jobs` : 'No frequent gap found'} />
    </div>

    <FitOverview data={data} />

    <div className="grid lg:grid-cols-2 gap-6 items-start">
      <SkillDemandCard title="Your strongest market skills"
        description="Skills found in your profile, ordered by how often matched jobs mention them."
        items={data.strongest_skills || []} total={data.total_jobs} tone="good"
        empty="No skills found in your profile overlap with the detected job skills yet." />
      <SkillDemandCard title="Skills most worth strengthening"
        description="Skills not found in your profile, ordered by demand across your matched jobs."
        items={data.skills_to_strengthen || []} total={data.total_jobs} tone="warn"
        empty="No common skill gaps were detected across your matched jobs." />
    </div>

    <AllSkills items={data.all_skills || []} total={data.total_jobs} />

    <div className="card text-sm text-muted leading-relaxed space-y-2">
      <h2 className="text-base font-semibold text-fg">How these numbers are calculated</h2>
      <p>Each job above the recommendation threshold is counted once. For each skill, the percentage is <span className="font-medium text-fg">jobs mentioning the skill ÷ {data.total_jobs} recommended jobs</span>.</p>
      <p>{data.jobs_with_detected_skills} of {data.total_jobs} jobs contained recognizable skill information. A mention may be mandatory, preferred, or descriptive—the source posting does not always distinguish them.</p>
      <p>The calculation is deterministic and does not use the chat model. Resume and roadmap skill evidence determine whether an item appears as a strength or a skill to strengthen.</p>
    </div>
  </div>
}

function Metric({ label, value, note }) {
  return <div className="card min-w-0">
    <p className="text-xs uppercase tracking-wider text-muted">{label}</p>
    <p className="mt-2 text-2xl font-bold text-fg break-words">{value}</p>
    <p className="mt-1 text-xs text-muted">{note}</p>
  </div>
}

function FitOverview({ data }) {
  const bands = data.fit_bands || {}
  const segments = [
    { label: 'Strong fit (80%+)', count: bands.strong || 0, color: 'bg-emerald-500' },
    { label: 'Good fit (65–79%)', count: bands.good || 0, color: 'bg-brand-400' },
    { label: 'Exploratory fit (<65%)', count: bands.exploratory || 0, color: 'bg-amber-400' },
  ]
  return <div className="card">
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
      <div><h2 className="text-lg font-semibold">Fit distribution</h2><p className="text-sm text-muted">How your recommended jobs are distributed by the displayed fit score.</p></div>
      <span className="chip">{data.score_method}</span>
    </div>
    <div className="mt-5 h-4 flex overflow-hidden rounded-full bg-surface-2" aria-label="Fit score distribution">
      {segments.map(segment => segment.count > 0 && <div key={segment.label} className={segment.color}
        style={{ width: `${segment.count / data.total_jobs * 100}%` }} title={`${segment.label}: ${segment.count}`} />)}
    </div>
    <div className="mt-4 grid sm:grid-cols-3 gap-3">
      {segments.map(segment => <div key={segment.label} className="flex items-center gap-2 text-sm">
        <span className={`h-2.5 w-2.5 rounded-full ${segment.color}`} /><span className="text-muted">{segment.label}</span><strong className="ml-auto">{segment.count}</strong>
      </div>)}
    </div>
  </div>
}

function SkillDemandCard({ title, description, items, total, tone, empty }) {
  const good = tone === 'good'
  return <section className="card">
    <h2 className="text-lg font-semibold">{title}</h2>
    <p className="mt-1 text-sm text-muted">{description}</p>
    {items.length ? <div className="mt-5 space-y-4">{items.map(item => <SkillBar key={item.name} item={item} total={total} good={good} />)}</div>
      : <p className="mt-5 rounded-xl border border-line bg-surface-2/40 p-4 text-sm text-muted">{empty}</p>}
  </section>
}

function SkillBar({ item, total, good }) {
  return <div>
    <div className="flex items-baseline justify-between gap-4">
      <p className="font-medium text-fg truncate">{item.name}</p>
      <p className={`text-sm font-semibold shrink-0 ${good ? 'text-emerald-500 dark:text-emerald-300' : 'text-amber-500 dark:text-amber-300'}`}>{formatPercent(item.percentage)}</p>
    </div>
    <div className="mt-1.5 h-2 rounded-full bg-surface-2 overflow-hidden">
      <div className={`h-full rounded-full ${good ? 'bg-emerald-500' : 'bg-amber-400'}`} style={{ width: `${Math.max(item.percentage, 1)}%` }} />
    </div>
    <p className="mt-1 text-xs text-muted">Mentioned in {item.job_count} of {total} matched jobs</p>
  </div>
}

function AllSkills({ items, total }) {
  return <section className="card">
    <h2 className="text-lg font-semibold">All detected skill demand</h2>
    <p className="mt-1 text-sm text-muted">The 50 most frequently mentioned skills across your matched jobs.</p>
    {items.length > 0 ? <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {items.map(item => <div key={item.name} className="rounded-xl border border-line bg-surface-2/30 p-3 min-w-0">
        <div className="flex items-start justify-between gap-2"><p className="font-medium truncate">{item.name}</p>
          <span className={`chip shrink-0 ${item.in_profile ? 'border-emerald-400/30 text-emerald-500 dark:text-emerald-300' : 'border-amber-400/30 text-amber-500 dark:text-amber-300'}`}>{item.in_profile ? 'In profile' : 'Gap'}</span></div>
        <p className="mt-2 text-sm text-muted">{formatPercent(item.percentage)} · {item.job_count} of {total} jobs</p>
      </div>)}
    </div> : <p className="mt-5 text-sm text-muted">No recognizable skills were found in the matched job postings.</p>}
  </section>
}

const formatPercent = value => `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`
