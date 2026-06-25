import { useEffect, useState, useMemo } from 'react'
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

export default function Roadmap() {
  const { token } = useAuth()
  const [data,    setData]    = useState(null)
  const [skills,  setSkills]  = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    if (!token) return
    fetch('/api/user/roadmap', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.detail || 'Could not load roadmap.')
        setData(d)
        setSkills(d.skills)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [token])

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
    const next = !currentAcquired
    setSkills(prev => prev.map(s => s.skill_name === skillName ? { ...s, acquired: next } : s))
    const body = new URLSearchParams({ skill_name: skillName, acquired: String(next) })
    const res = await fetch('/api/user/skills/toggle', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!res.ok) {
      setSkills(prev => prev.map(s => s.skill_name === skillName ? { ...s, acquired: currentAcquired } : s))
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
      <p className="text-red-400">{error}</p>
      <a href="/onboarding" className="btn-primary inline-block">Complete onboarding first</a>
    </div>
  )

  if (!data) return null

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Your roadmap"
        title={data.role_label}
        subtitle="Work through each stage in order — stages unlock as you progress. Click any skill to mark it learned."
      />

      <div className="mt-8 grid lg:grid-cols-4 gap-6 items-start">
        <div className="lg:col-span-3 space-y-4">
          {nextSkills.length > 0 && (
            <NextUpBanner skills={nextSkills} onToggle={toggle} />
          )}
          <StageMap byStage={byStage} onToggle={toggle} />
        </div>

        <ProgressPanel
          score={score}
          acquiredCount={acquired.length}
          total={skills.length}
          roleLabel={data.role_label}
          byStage={byStage}
        />
      </div>
    </section>
  )
}

function NextUpBanner({ skills, onToggle }) {
  return (
    <div className="card border-brand-400/20 bg-brand-500/5">
      <p className="text-xs uppercase tracking-wider text-brand-400 mb-3">Learn next</p>
      <div className="flex flex-wrap gap-2">
        {skills.map(s => (
          <button
            key={s.skill_name}
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

function StageMap({ byStage, onToggle }) {
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

function StageColumn({ stage, label, skills, unlocked, acquiredCount, onToggle }) {
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
          <SkillNode key={s.skill_name} skill={s} unlocked={unlocked} onToggle={onToggle} />
        ))}
        {!skills.length && (
          <li className="py-4 text-center text-xs text-subtle">—</li>
        )}
      </ul>
    </div>
  )
}

function SkillNode({ skill, unlocked, onToggle }) {
  const { skill_name, acquired, impact } = skill
  return (
    <li>
      <button
        onClick={() => onToggle(skill_name, acquired)}
        title={acquired ? 'Click to unmark' : 'Click to mark as learned'}
        className={`w-full text-left flex items-center gap-2 px-2.5 py-2 rounded-xl border text-xs font-medium transition group ${
          acquired
            ? 'bg-emerald-500/10 border-emerald-400/30 text-emerald-600 dark:text-emerald-300 hover:bg-emerald-500/15'
            : unlocked
            ? 'bg-surface-2/60 border-line text-fg hover:border-brand-400/50 hover:bg-brand-500/5'
            : 'bg-transparent border-line/20 text-muted/50 hover:border-line/40'
        }`}
      >
        <span className={`shrink-0 h-4 w-4 grid place-items-center rounded-full border text-[9px] font-bold transition ${
          acquired  ? 'border-emerald-400/60 bg-emerald-500/20 text-emerald-500' :
          unlocked  ? 'border-brand-400/40 bg-brand-500/10 text-brand-400 group-hover:border-brand-400' :
                      'border-line/30 bg-surface-2/30 text-transparent'
        }`}>
          {acquired ? '✓' : ''}
        </span>
        <span className="flex-1 truncate leading-tight">{skill_name}</span>
        <span className={`shrink-0 text-[9px] tabular-nums ${acquired ? 'text-emerald-500/70' : 'text-muted/40'}`}>
          +{impact}
        </span>
      </button>
    </li>
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
            <p className="text-[10px] uppercase tracking-wider text-muted">Match</p>
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
        Stages unlock at 50% completion. Click any skill — even locked ones — to mark it acquired.
      </p>
    </aside>
  )
}
