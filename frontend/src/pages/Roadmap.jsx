import { useEffect, useState, useMemo, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { PageHeader } from './shared.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

const STAGE_LABELS = {
  1: 'Foundations',
  2: 'Core Tools',
  3: 'Advanced',
  4: 'Production',
}

function stageIsUnlocked(stage, byStage) {
  if (stage <= 1) return true
  const prev = byStage[stage - 1] || []
  if (!prev.length) return true
  return prev.filter(s => s.acquired).length / prev.length >= 0.5
}

async function readResponse(response) {
  const text = await response.text()
  let data
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error('The server returned an unexpected response. Please try again.')
  }
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not update your roadmap. Please try again.')
  }
  return data
}

export default function Roadmap() {
  const { token } = useAuth()
  const [searchParams] = useSearchParams()
  const jobId = searchParams.get('job_id')
  const [data,    setData]    = useState(null)
  const [skills,  setSkills]  = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [saveError, setSaveError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [reload, setReload] = useState(0)
  const saveController = useRef(null)
  const roadmapUrl = `/api/user/roadmap${jobId ? `?job_id=${encodeURIComponent(jobId)}` : ''}`

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setSaveError(null)
    setSaving(false)
    fetch(roadmapUrl, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal })
      .then(readResponse)
      .then(d => {
        if (controller.signal.aborted) return
        setData(d)
        setSkills(d.skills)
      })
      .catch(e => { if (!controller.signal.aborted) setError(e.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => {
      controller.abort()
      saveController.current?.abort()
      saveController.current = null
    }
  }, [token, roadmapUrl, reload])

  const { score, acquired, byStage, nextSkills } = useMemo(() => {
    const total   = skills.reduce((s, x) => s + x.impact, 0)
    const acquired = skills.filter(s => s.acquired)
    const earned  = acquired.reduce((s, x) => s + x.impact, 0)
    const score   = total ? Math.round((earned / total) * 100) : 0

    const byStage = {}
    for (const s of skills) {
      const st = s.stage ?? 1
      ;(byStage[st] = byStage[st] || []).push(s)
    }

    let nextSkills = []
    for (let st = 1; st <= 4; st++) {
      if (!stageIsUnlocked(st, byStage)) break
      const avail = (byStage[st] || []).filter(s => !s.acquired)
      if (avail.length) {
        nextSkills = avail.sort((a, b) => b.impact - a.impact).slice(0, 3)
        break
      }
    }

    return { score, acquired, byStage, nextSkills }
  }, [skills])

  const toggle = async (skillName, currentAcquired) => {
    if (saveController.current) return
    const controller = new AbortController()
    saveController.current = controller
    setSaving(true)
    setSaveError(null)
    const next = !currentAcquired
    let saved = false
    setSkills(prev => prev.map(s => s.skill_name === skillName ? { ...s, acquired: next } : s))
    try {
      const body = new URLSearchParams({ skill_name: skillName, acquired: String(next) })
      if (jobId) body.set('job_id', jobId)
      const res = await fetch('/api/user/skills/toggle', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
        signal: controller.signal,
      })
      await readResponse(res)
      saved = true
      const refreshed = await fetch(roadmapUrl, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      })
      const nextData = await readResponse(refreshed)
      if (!controller.signal.aborted) {
        setData(nextData)
        setSkills(nextData.skills)
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        if (!saved) setSkills(prev => prev.map(s => s.skill_name === skillName ? { ...s, acquired: currentAcquired } : s))
        setSaveError(saved ? 'Progress saved, but the roadmap could not refresh. Please reload it.' : e.message)
      }
    } finally {
      if (saveController.current === controller) {
        saveController.current = null
        setSaving(false)
      }
    }
  }

  if (loading) return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 text-center">
      <div className="inline-flex items-center gap-3 text-muted">
        <span className="h-5 w-5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
        <span>Loading your roadmap…</span>
      </div>
    </div>
  )

  if (error) return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 text-center space-y-4">
      <p role="alert" className="text-red-400">{error}</p>
      <button className="btn-primary" onClick={() => setReload(value => value + 1)}>Retry loading roadmap</button>
      <p><Link to="/onboarding" className="text-brand-500 underline">Update your resume or target role</Link></p>
    </div>
  )

  if (!data) return null

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Your roadmap"
        title={data.role_label}
        subtitle={data.target_job
          ? `A focused plan for ${data.target_job.title}${data.target_job.company ? ` at ${data.target_job.company}` : ''}.`
          : 'Follow the suggested stages, and mark any skills you already know.'}
      />

      {data.target_job && <>
        <Link to="/roadmap" className="mt-4 inline-block text-sm text-brand-500 underline">Back to my role roadmap</Link>
        <TargetJobPanel job={data.target_job} match={data.job_match} />
      </>}

      <p className="mt-5 text-sm text-muted">Open <span className="font-medium text-fg">Learn</span> under a skill you haven't learned yet for learning paths and guides. Marking it as learned hides its resources; unchecking it shows them again.</p>

      {saveError && <div role="alert" className="mt-6 rounded-xl border border-red-400/30 bg-red-500/5 p-4 text-sm text-red-400">
        {saveError} <button className="underline" onClick={() => setReload(value => value + 1)}>Reload roadmap</button>
      </div>}
      {saving && <p role="status" className="mt-4 text-sm text-muted">Saving skill progress…</p>}
      {!skills.length && <p className="mt-8 card text-muted">This posting does not contain enough recognizable skills to build a learning plan. Try another job or return to your role roadmap.</p>}

      {skills.length > 0 && <div className="mt-8 grid lg:grid-cols-4 gap-6 items-start">
        <div className="lg:col-span-3 min-w-0 space-y-4">
          {nextSkills.length > 0 && (
            <NextUpBanner skills={nextSkills} onToggle={toggle} saving={saving} />
          )}
          <StageMap byStage={byStage} onToggle={toggle} saving={saving} />
        </div>

      <ProgressPanel
        score={score}
          acquiredCount={acquired.length}
          total={skills.length}
          roleLabel={data.role_label}
          byStage={byStage}
        />
      </div>}
    </section>
  )
}

function NextUpBanner({ skills, onToggle, saving }) {
  return (
    <div className="card border-brand-400/20 bg-brand-500/5">
      <p className="text-xs uppercase tracking-wider text-brand-400 mb-3">Learn next</p>
      <div className="flex flex-wrap gap-2">
        {skills.map(s => (
          <button
            key={s.skill_name}
            disabled={saving}
            title={`Mark ${s.skill_name} as learned`}
            onClick={() => onToggle(s.skill_name, s.acquired)}
            className="chip border-brand-400/30 text-brand-500 dark:text-brand-200 hover:bg-brand-500/15 cursor-pointer transition"
          >
            → {s.skill_name}
          </button>
        ))}
      </div>
    </div>
  )
}

function StageMap({ byStage, onToggle, saving }) {
  return (
    <div className="overflow-x-auto pb-2 -mx-1 px-1">
      <div className="flex items-start gap-2 min-w-max">
        {[1, 2, 3, 4].map((stage, i) => {
          const stageSkills    = byStage[stage] || []
          const unlocked       = stageIsUnlocked(stage, byStage)
          const acquiredCount  = stageSkills.filter(s => s.acquired).length
          const nextUnlocked   = stageIsUnlocked(stage + 1, byStage)
          return (
            <div key={stage} className="flex items-start gap-2">
              <StageColumn
                stage={stage}
                label={STAGE_LABELS[stage]}
                skills={stageSkills}
                unlocked={unlocked}
                acquiredCount={acquiredCount}
                onToggle={onToggle}
                saving={saving}
              />
              {i < 3 && (
                <div className={`pt-[3.8rem] shrink-0 ${nextUnlocked ? 'text-brand-400' : 'text-line'}`}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M13 5l7 7-7 7" />
                  </svg>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function StageColumn({ stage, label, skills, unlocked, acquiredCount, onToggle, saving }) {
  const total  = skills.length
  const pct    = total ? Math.round((acquiredCount / total) * 100) : 0
  const allDone = total > 0 && acquiredCount === total

  return (
    <div className={`w-52 shrink-0 rounded-2xl border transition-colors ${
      allDone   ? 'border-emerald-400/30 bg-emerald-500/5' :
      unlocked  ? 'border-brand-400/20 bg-surface-1' :
                  'border-line/30 bg-surface-2/20'
    }`}>
      {/* Header */}
      <div className={`px-4 pt-4 pb-3 border-b ${allDone ? 'border-emerald-400/20' : 'border-line/30'}`}>
        <div className="flex items-center justify-between mb-0.5">
          <span className={`text-[10px] font-bold uppercase tracking-widest ${
            allDone ? 'text-emerald-400' : unlocked ? 'text-brand-400' : 'text-muted/40'
          }`}>
            Stage {stage}
          </span>
          <span className="text-xs text-muted tabular-nums">{acquiredCount}/{total}</span>
        </div>
        <p className={`text-sm font-semibold ${unlocked ? 'text-fg' : 'text-muted/50'}`}>{label}</p>
        <div className="mt-2 h-1 rounded-full bg-surface-2 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              allDone ? 'bg-emerald-400' : 'bg-gradient-to-r from-brand-400 to-brand-300'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Skills */}
      <ul className="p-3 space-y-1.5">
        {skills.map(s => (
          <SkillNode key={s.skill_name} skill={s} unlocked={unlocked} onToggle={onToggle} saving={saving} />
        ))}
        {!skills.length && (
          <li className="py-4 text-center text-xs text-subtle">—</li>
        )}
      </ul>
    </div>
  )
}

function SkillNode({ skill, unlocked, onToggle, saving }) {
  const { skill_name, acquired, impact } = skill
  return (
    <li>
      <button
        disabled={saving}
        aria-pressed={acquired}
        onClick={() => onToggle(skill_name, acquired)}
        title={acquired ? `Unmark ${skill_name}` : `Mark ${skill_name} as learned`}
        className={`w-full text-left flex items-center gap-2 px-2.5 py-2 rounded-xl border text-xs font-medium transition group ${
          acquired
            ? 'bg-emerald-500/10 border-emerald-400/30 text-emerald-600 dark:text-emerald-300 hover:bg-emerald-500/15'
            : unlocked
            ? 'bg-surface-2/60 border-line text-fg hover:border-brand-400/50 hover:bg-brand-500/5'
            : 'bg-transparent border-line/30 text-muted hover:border-brand-400/50 hover:bg-brand-500/5'
        }`}
      >
        <span className={`shrink-0 h-4 w-4 grid place-items-center rounded-full border text-[9px] font-bold transition ${
          acquired  ? 'border-emerald-400/60 bg-emerald-500/20 text-emerald-500' :
          unlocked  ? 'border-brand-400/40 bg-brand-500/10 text-brand-400 group-hover:border-brand-400' :
                      'border-line/30 bg-surface-2/30 text-transparent'
        }`}>
          {acquired ? '✓' : ''}
        </span>
        <span className="flex-1 break-words min-w-0 leading-tight">{skill_name}</span>
        <span className={`shrink-0 text-[9px] tabular-nums ${acquired ? 'text-emerald-500/70' : 'text-muted/40'}`}>
          +{impact}
        </span>
      </button>
      {!acquired && <SkillResources skill={skill} />}
    </li>
  )
}

function SkillResources({ skill }) {
  // Links come from a maintained server-side catalog, not model output. Keep
  // the browser guard too, so malformed responses never create executable URLs.
  const resources = (skill.learning_resources || []).filter(resource => {
    try {
      const url = new URL(resource.url)
      return url.protocol === 'https:' && !url.username && !url.password
    } catch {
      return false
    }
  })
  if (!resources.length) return null
  return (
    <details className="mt-1 mb-3 rounded-xl border border-line/50 bg-surface-2/30 p-2 group/resources">
      <summary
        aria-label={`Learning resources for ${skill.skill_name}`}
        className="cursor-pointer text-xs font-medium text-brand-500 dark:text-brand-200 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-400"
      >
        Learn <span className="text-muted font-normal">· {resources.length} resource{resources.length === 1 ? '' : 's'}</span>
      </summary>
      <ul className="mt-2 space-y-2">
        {resources.map(resource => (
          <li key={resource.url}>
            <a href={resource.url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer"
              className="block rounded-lg border border-line/60 p-2 hover:border-brand-400/50 hover:bg-brand-500/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-400"
              aria-label={`${resource.title} for ${skill.skill_name} (opens in a new tab)`}
            >
              <span className="block text-[10px] uppercase tracking-wide text-muted">{resource.kind}</span>
              <span className="mt-0.5 block text-xs leading-snug text-fg break-words">{resource.title} <span aria-hidden="true">↗</span></span>
              <span className="mt-1 block text-[10px] text-muted break-all">{resource.source}</span>
            </a>
          </li>
        ))}
      </ul>
      {resources.every(resource => resource.kind === 'Search') && <p className="mt-2 text-[10px] text-muted">No curated guide yet. These links search the web for this skill.</p>}
    </details>
  )
}

function ProgressPanel({ score, acquiredCount, total, roleLabel, byStage }) {
  return (
    <aside className="card lg:sticky lg:top-24 self-start space-y-5">
      <p className="chip">Progress</p>

      {/* Radial score ring */}
      <div className="relative h-32 w-32 mx-auto">
        <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
          <circle cx="18" cy="18" r="15.9155" fill="none" stroke="rgb(var(--surface-2))" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15.9155" fill="none"
            stroke="url(#rmgrad)" strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${score}, 100`}
            style={{ transition: 'stroke-dasharray 0.4s ease' }}
          />
          <defs>
            <linearGradient id="rmgrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#5d8eff" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <p className="text-3xl font-bold text-fg">{score}%</p>
            <p className="text-[10px] uppercase tracking-wider text-muted">Progress</p>
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <dl className="space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-muted">Role</dt>
          <dd className="text-fg font-medium text-right max-w-[110px] text-xs leading-snug">{roleLabel}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted">Skills done</dt>
          <dd className="text-fg font-medium">{acquiredCount} / {total}</dd>
        </div>
      </dl>

      {/* Per-stage mini bars */}
      <div className="space-y-2.5">
        {[1, 2, 3, 4].map(stage => {
          const stageSkills = byStage[stage] || []
          const done = stageSkills.filter(s => s.acquired).length
          const pct  = stageSkills.length ? Math.round((done / stageSkills.length) * 100) : 0
          const unlocked = stageIsUnlocked(stage, byStage)
          return (
            <div key={stage}>
              <div className="flex justify-between text-xs mb-1">
                <span className={unlocked ? 'text-muted' : 'text-muted/40'}>{STAGE_LABELS[stage]}</span>
                <span className="text-muted/60 tabular-nums">{done}/{stageSkills.length}</span>
              </div>
              <div className="h-1 rounded-full bg-surface-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    pct === 100 ? 'bg-emerald-400' : 'bg-gradient-to-r from-brand-400 to-emerald-400'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      <p className="text-xs text-muted leading-relaxed">
        Stages suggest a learning order. You can mark skills you already know in any stage; your choices are saved automatically.
      </p>
    </aside>
  )
}

function TargetJobPanel({ job, match }) {
  const matched = match?.matched_skills || []
  const missing = match?.missing_skills || []
  const hasJobSkills = matched.length + missing.length > 0
  return (
    <div className="mt-8 card border-brand-400/20 bg-brand-500/5">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <p className="chip">Target job</p>
          <h2 className="mt-3 text-xl font-semibold text-fg">{job.title}</h2>
          <p className="text-sm text-muted">{[job.company, job.location].filter(Boolean).join(' · ')}</p>
        </div>
        {match?.coverage_pct !== null && match?.coverage_pct !== undefined && (
          <div className="text-left sm:text-right">
            <p className="text-xs uppercase tracking-wider text-muted">Skill coverage</p>
            <p className="text-3xl font-bold text-fg">{match.coverage_pct}%</p>
          </div>
        )}
      </div>
      <div className="mt-5 grid md:grid-cols-2 gap-4">
        <SkillList title="Already covered" values={matched} tone="good" empty={hasJobSkills ? 'None of the detected job skills were found in your profile yet.' : 'This posting does not provide enough detail to compare skills.'} />
        <SkillList title="Prioritize next" values={missing} tone="warn" empty={hasJobSkills ? 'Your profile covers all skills detected in this posting.' : 'Skill gaps cannot be assessed from the available job information.'} />
      </div>
      {hasJobSkills && <p className="mt-3 text-xs text-muted">Based on skills mentioned in this job posting. Some may be preferred or optional.</p>}
    </div>
  )
}

function SkillList({ title, values, tone, empty }) {
  const colors = tone === 'good'
    ? 'border-emerald-400/20 bg-emerald-500/5 text-emerald-500 dark:text-emerald-300'
    : 'border-amber-400/20 bg-amber-500/5 text-amber-500 dark:text-amber-300'
  return (
    <div className={`rounded-xl border p-4 ${colors}`}>
      <p className="text-xs uppercase tracking-wider mb-2">{title}</p>
      {values.length > 0
        ? <div className="flex flex-wrap gap-1.5">{values.map(value => <span key={value} className="chip">{value}</span>)}</div>
        : <p className="text-xs text-muted">{empty}</p>}
    </div>
  )
}
