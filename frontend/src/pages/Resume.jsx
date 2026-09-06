import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { PageHeader } from './shared.jsx'
import { toYaml } from '../lib/yaml.js'
import { useAuth } from '../lib/AuthContext.jsx'

const loadPdfBuilder = () => import('../lib/generatePdf.js').then((m) => m.buildResumePdf)

export default function Resume() {
  const [mode, setMode] = useState('analyse')
  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Resume"
        title="Your CV"
        subtitle="Improve your CV for a roadmap role or fit it to a specific job posting."
      />

      <div className="mt-8 inline-flex p-1 rounded-xl bg-surface-2/60 border border-line">
        <TabBtn active={mode === 'analyse'} onClick={() => setMode('analyse')}>
          Analyse CV
        </TabBtn>
        <TabBtn active={mode === 'build'} onClick={() => setMode('build')}>
          Build from form
        </TabBtn>
      </div>

      {mode === 'analyse' ? <AnalyseView /> : <BuildView />}
    </section>
  )
}

function TabBtn({ active, children, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition ${
        active ? 'bg-brand-500 text-white shadow-glow' : 'text-muted hover:text-fg'
      }`}
    >
      {children}
    </button>
  )
}

// ── Analyse view ──────────────────────────────────────────────────────────────

function AnalyseView() {
  const { token, user } = useAuth()
  const [searchParams] = useSearchParams()
  const [roles, setRoles] = useState([])
  const [jobs, setJobs] = useState([])
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedJobId, setSelectedJobId] = useState(() => searchParams.get('job_id') || '')
  const [roleSuggestions, setRoleSuggestions] = useState(null)
  const [jobSuggestions, setJobSuggestions] = useState(null)
  const [roleLoading, setRoleLoading] = useState(false)
  const [jobLoading, setJobLoading] = useState(false)
  const [roleError, setRoleError] = useState(null)
  const [jobError, setJobError] = useState(null)
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobsLoadError, setJobsLoadError] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)

  const filename = user?.resume_filename
  const useUploadedResume = Boolean(uploadFile && (showUpload || !filename))
  const hasResume = useUploadedResume || Boolean(filename && !showUpload)
  const jobIdFromUrl = searchParams.get('job_id') || ''
  const jobTitleFromUrl = searchParams.get('job_title') || ''
  const companyFromUrl = searchParams.get('company') || ''
  const contextJob = useMemo(() => jobIdFromUrl ? {
    job_id: jobIdFromUrl,
    title: jobTitleFromUrl || 'Selected job',
    company: companyFromUrl,
  } : null, [companyFromUrl, jobIdFromUrl, jobTitleFromUrl])

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/roles', { signal: controller.signal })
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Could not load roadmap roles.')
        setRoles(data.roles || [])
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setRoleError(err.message)
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (selectedRole || roles.length === 0) return
    const preferred = roles.find(role => role.slug === user?.desired_role) || roles[0]
    if (preferred?.label) setSelectedRole(preferred.label)
  }, [roles, selectedRole, user?.desired_role])

  useEffect(() => {
    if (!token || !filename) {
      setJobs([])
      setJobsLoading(false)
      return undefined
    }

    const controller = new AbortController()
    setJobsLoading(true)
    setJobsLoadError(null)
    fetch('/api/user/jobs?page=1&limit=50&sort=score', {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Could not load matched jobs.')
        const loadedJobs = data.jobs || []
        const selectedIsLoaded = contextJob && loadedJobs.some(job => String(job.job_id) === String(contextJob.job_id))
        const jobsWithContext = contextJob && !selectedIsLoaded
          ? [contextJob, ...loadedJobs]
          : loadedJobs
        setJobs(jobsWithContext)
        setSelectedJobId(current => current || String(jobsWithContext[0]?.job_id || ''))
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setJobs([])
          setJobsLoadError(err.message)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setJobsLoading(false)
      })

    return () => controller.abort()
  }, [contextJob, filename, token])

  const selectableJobs = contextJob && !jobs.some(job => String(job.job_id) === String(contextJob.job_id))
    ? [contextJob, ...jobs]
    : jobs
  const selectedJob = selectableJobs.find(job => String(job.job_id) === selectedJobId) || null

  const requestSuggestions = async ({ jobTitle = '', jobId = '' }) => {
    let res
    if (useUploadedResume) {
      const body = new FormData()
      body.append('file', uploadFile)
      if (jobTitle) body.append('job_title', jobTitle)
      if (jobId) body.append('job_id', jobId)
      res = await fetch('/api/suggest', { method: 'POST', body })
    } else {
      const body = new URLSearchParams()
      if (jobTitle) body.set('job_title', jobTitle)
      if (jobId) body.set('job_id', jobId)
      res = await fetch('/api/user/suggest', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body,
      })
    }
    const contentType = res.headers.get('content-type') || ''
    const responseText = await res.text()
    let data = null
    if (contentType.includes('application/json')) {
      try {
        data = JSON.parse(responseText)
      } catch {
        throw new Error('The server returned an invalid response. Please try again.')
      }
    }
    if (!res.ok) {
      throw new Error(data?.detail || `The AI request failed (${res.status}). Please try again.`)
    }
    if (!data) {
      throw new Error('The AI server returned an unexpected response. Please try again.')
    }
    return data
  }

  const analyseRole = async () => {
    if (!selectedRole || !hasResume) return
    setRoleLoading(true)
    setRoleSuggestions(null)
    setRoleError(null)
    try {
      setRoleSuggestions(await requestSuggestions({ jobTitle: selectedRole }))
    } catch (err) {
      setRoleError(err.message)
    } finally {
      setRoleLoading(false)
    }
  }

  const analyseJob = async () => {
    if (!selectedJobId || !hasResume) return
    setJobLoading(true)
    setJobSuggestions(null)
    setJobError(null)
    try {
      setJobSuggestions(await requestSuggestions({
        jobTitle: selectedJob?.title || '',
        jobId: selectedJobId,
      }))
    } catch (err) {
      setJobError(err.message)
    } finally {
      setJobLoading(false)
    }
  }

  return (
    <div className="mt-8 space-y-6">
      {filename && !showUpload && (
        <div className="card flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="shrink-0 h-10 w-10 grid place-items-center rounded-xl bg-brand-500/15 border border-brand-400/20 text-brand-400">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 4h9l3 3v13H6z" strokeLinejoin="round" />
                <path d="M9 12h6M9 16h4" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted uppercase tracking-wider">Saved resume</p>
              <p className="text-sm font-medium text-fg truncate">{filename}</p>
            </div>
          </div>
          <button onClick={() => { setShowUpload(true); setRoleSuggestions(null); setJobSuggestions(null) }} className="btn-ghost text-xs shrink-0">
            Use a different file
          </button>
        </div>
      )}

      {(!filename || showUpload) && (
        <UploadArea
          file={uploadFile}
          onFile={(file) => { setUploadFile(file); setRoleSuggestions(null); setJobSuggestions(null) }}
          onCancel={filename ? () => { setShowUpload(false); setUploadFile(null) } : null}
        />
      )}

      {!hasResume && (
        <div className="card text-center py-6 text-muted text-sm">
          Choose a resume above, or{' '}
          <Link to="/onboarding" className="text-brand-400 hover:underline">complete onboarding</Link>.
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <RoleCoachCard
          roles={roles}
          selectedRole={selectedRole}
          onSelect={(role) => { setSelectedRole(role); setRoleSuggestions(null); setRoleError(null) }}
          onAnalyse={analyseRole}
          suggestions={roleSuggestions}
          loading={roleLoading}
          error={roleError}
          disabled={!hasResume}
        />

        <JobCoachCard
          jobs={selectableJobs}
          selectedJob={selectedJob}
          selectedJobId={selectedJobId}
          onSelect={(jobId) => { setSelectedJobId(jobId); setJobSuggestions(null); setJobError(null) }}
          onAnalyse={analyseJob}
          suggestions={jobSuggestions}
          loading={jobLoading}
          jobsLoading={jobsLoading}
          error={jobError || jobsLoadError}
          disabled={!hasResume}
        />
      </div>

      <AnalyseSidebar />
    </div>
  )
}

function RoleCoachCard({ roles, selectedRole, onSelect, onAnalyse, suggestions, loading, error, disabled }) {
  return (
    <div className="card space-y-5">
      <div>
        <p className="chip">Roadmap role coach</p>
        <h3 className="mt-3 text-xl font-semibold text-fg">Improve your CV for a role</h3>
        <p className="mt-1 text-sm text-muted">Choose a roadmap role to compare your resume with that role’s expected skills.</p>
      </div>
      <select
        aria-label="Roadmap role"
        className="input"
        value={selectedRole}
        onChange={e => onSelect(e.target.value)}
      >
        <option value="">Choose a roadmap role…</option>
        {roles.map(role => <option key={role.slug} value={role.label}>{role.label}</option>)}
      </select>
      <button
        onClick={onAnalyse}
        disabled={disabled || loading || !selectedRole}
        className="btn-primary w-full disabled:opacity-60"
      >
        {loading ? 'Analysing…' : 'Analyse CV for this role'}
      </button>
      <CoachStatus loading={loading} error={error} />
      {suggestions && <SuggestionsPanel data={suggestions} />}
    </div>
  )
}

function JobCoachCard({ jobs, selectedJob, selectedJobId, onSelect, onAnalyse, suggestions, loading, jobsLoading, error, disabled }) {
  const missing = selectedJob?.match_details?.missing_skills || []
  return (
    <div className="card space-y-5">
      <div>
        <p className="chip">Fit your CV</p>
        <h3 className="mt-3 text-xl font-semibold text-fg">Fit your CV to a specific job</h3>
        <p className="mt-1 text-sm text-muted">Choose a real matched job. Its description and requirements become the AI coach’s context.</p>
      </div>
      <select
        aria-label="Job to analyse resume against"
        className="input"
        value={selectedJobId}
        onChange={e => onSelect(e.target.value)}
        disabled={jobsLoading || jobs.length === 0}
      >
        <option value="">
          {jobsLoading ? 'Loading matched jobs…' : jobs.length ? 'Choose a job…' : 'No matched jobs available'}
        </option>
        {jobs.map(job => (
          <option key={job.job_id} value={job.job_id}>
            {[job.title, job.company].filter(Boolean).join(' · ')}
          </option>
        ))}
      </select>
      {selectedJob && (
        <div className="rounded-xl border border-brand-400/30 bg-brand-500/10 px-4 py-3">
          <p className="text-sm font-medium text-fg">{[selectedJob.title, selectedJob.company].filter(Boolean).join(' · ')}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {selectedJob.match_pct !== undefined && <span className="chip">{selectedJob.match_pct}% current match</span>}
            {missing.slice(0, 3).map(skill => <span key={skill} className="chip border-amber-400/30 text-amber-500 dark:text-amber-200">Gap: {skill}</span>)}
          </div>
        </div>
      )}
      <button
        onClick={onAnalyse}
        disabled={disabled || loading || !selectedJobId}
        className="btn-primary w-full disabled:opacity-60"
      >
        {loading ? 'Analysing…' : 'Fit CV to this job'}
      </button>
      <CoachStatus loading={loading} error={error} />
      {suggestions && <SuggestionsPanel data={suggestions} />}
      <div className="pt-2 border-t border-line">
        <Link to="/jobs" className="btn-ghost w-full justify-center">Browse matching jobs →</Link>
      </div>
    </div>
  )
}

function CoachStatus({ loading, error }) {
  return (
    <>
      {error && (
        <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}
      {loading && (
        <div className="flex items-center gap-3 text-sm text-muted">
          <span className="h-4 w-4 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
          Analysing your CV — this takes 30–60 seconds…
        </div>
      )}
    </>
  )
}

function UploadArea({ file, onFile, onCancel }) {
  const [drag, setDrag] = useState(false)
  const [error, setError] = useState(null)
  const acceptFile = (candidate) => {
    if (!candidate) return
    if (!/\.(pdf|docx)$/i.test(candidate.name || '')) {
      setError('Please choose a PDF or DOCX file.')
      return
    }
    if (candidate.size > 10 * 1024 * 1024) {
      setError('The CV must be smaller than 10 MB.')
      return
    }
    setError(null)
    onFile(candidate)
  }
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault(); setDrag(false)
        acceptFile(e.dataTransfer.files?.[0])
      }}
      className={`card border-dashed text-center transition-colors ${drag ? 'border-brand-400 bg-brand-500/10' : ''}`}
    >
      <div className="mx-auto h-12 w-12 grid place-items-center rounded-2xl bg-brand-500/15 text-brand-500 dark:text-brand-300 border border-brand-400/20">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 16V4M6 10l6-6 6 6" /><path d="M4 20h16" />
        </svg>
      </div>
      <h3 className="mt-3 text-base font-semibold text-fg">Drop your CV here</h3>
      <p className="mt-1 text-sm text-muted">PDF or DOCX, up to 10 MB</p>
      <label className="btn-primary mt-4 cursor-pointer">
        <input type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => acceptFile(e.target.files?.[0])} />
        Choose file
      </label>
      {file && (
        <div className="mt-4 inline-flex items-center gap-3 rounded-xl bg-surface-2 border border-line px-4 py-2">
          <span className="text-sm text-fg">{file.name}</span>
          <span className="chip">{(file.size / 1024).toFixed(0)} KB</span>
          <button onClick={() => onFile(null)} className="text-muted hover:text-fg text-sm">✕</button>
        </div>
      )}
      {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
      {onCancel && (
        <button onClick={onCancel} className="mt-3 text-xs text-muted hover:text-fg transition block mx-auto">
          ← Use my saved resume instead
        </button>
      )}
    </div>
  )
}

function AnalyseSidebar() {
  const items = [
    { t: 'Powered by your saved CV', d: 'We use the resume you uploaded during onboarding. No need to re-upload every time.' },
    { t: 'Contact PII redacted', d: 'Email addresses and phone numbers are removed before AI analysis.' },
    { t: 'AI coach in seconds', d: 'Strengths, gaps, keyword recommendations — all from one click.' },
  ]
  return (
    <aside className="card self-start">
      <p className="chip">How it works</p>
      <ul className="mt-4 space-y-4">
        {items.map((i) => (
          <li key={i.t}>
            <p className="text-sm font-semibold text-fg">{i.t}</p>
            <p className="text-xs text-muted mt-0.5">{i.d}</p>
          </li>
        ))}
      </ul>
    </aside>
  )
}

function SuggestionsPanel({ data }) {
  const { overall, strengths, gaps, improvements, keywords } = data
  return (
    <div className="space-y-4">
      {overall && (
        <div className="rounded-xl border border-brand-400/30 bg-brand-500/10 px-4 py-3">
          <p className="text-xs uppercase tracking-wider text-brand-400 mb-1">Overall</p>
          <p className="text-sm font-medium text-fg">{overall}</p>
        </div>
      )}
      <div className="grid sm:grid-cols-2 gap-4">
        {strengths?.length > 0 && (
          <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/5 p-4">
            <p className="text-xs uppercase tracking-wider text-emerald-500 dark:text-emerald-300 mb-2">Strengths</p>
            <ul className="space-y-1.5">
              {strengths.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-fg/90">
                  <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>{s}
                </li>
              ))}
            </ul>
          </div>
        )}
        {gaps?.length > 0 && (
          <div className="rounded-xl border border-amber-400/20 bg-amber-500/5 p-4">
            <p className="text-xs uppercase tracking-wider text-amber-500 dark:text-amber-300 mb-2">Skill gaps</p>
            <ul className="space-y-1.5">
              {gaps.map((g, i) => (
                <li key={i} className="flex gap-2 text-sm text-fg/90">
                  <span className="text-amber-500 mt-0.5 shrink-0">!</span>{g}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {improvements?.length > 0 && (
        <div className="rounded-xl border border-line bg-surface-2/40 p-4">
          <p className="text-xs uppercase tracking-wider text-muted mb-2">Improvements</p>
          <ul className="space-y-1.5">
            {improvements.map((imp, i) => (
              <li key={i} className="flex gap-2 text-sm text-fg/90">
                <span className="text-brand-400 mt-0.5 shrink-0">→</span>{imp}
              </li>
            ))}
          </ul>
        </div>
      )}
      {keywords?.length > 0 && (
        <div className="rounded-xl border border-line bg-surface-2/40 p-4">
          <p className="text-xs uppercase tracking-wider text-muted mb-2">Add these keywords</p>
          <div className="flex flex-wrap gap-1.5">
            {keywords.map((kw) => (
              <span key={kw} className="chip border-brand-400/30 text-brand-500 dark:text-brand-200">{kw}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Build from form view (unchanged) ─────────────────────────────────────────

const STEPS = ['Personal', 'Experience', 'Education', 'Projects', 'Skills', 'Review']

const EMPTY_FORM = {
  personal:   { name: '', headline: '', email: '', phone: '', location: '', summary: '' },
  experience: [{ title: '', company: '', from: '', to: '', description: '' }],
  education:  [{ degree: '', school: '', from: '', to: '' }],
  projects:   [{ name: '', description: '', link: '' }],
  skills:     { technical: '', tools: '', soft: '' },
}

function BuildView() {
  const { token, refreshUser } = useAuth()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saveState, setSaveState] = useState(null)
  const update = (section, value) => setForm((f) => ({ ...f, [section]: value }))

  const yamlPayload = useMemo(() => {
    const split = (s) => (s || '').split(',').map((x) => x.trim()).filter(Boolean)
    return {
      name: form.personal.name, headline: form.personal.headline,
      contact: { email: form.personal.email, phone: form.personal.phone, location: form.personal.location },
      summary: form.personal.summary,
      experience: form.experience.filter((e) => e.title || e.company).map((e) => ({
        title: e.title, company: e.company,
        period: [e.from, e.to].filter(Boolean).join(' – '), description: e.description,
      })),
      education: form.education.filter((e) => e.degree || e.school).map((e) => ({
        degree: e.degree, school: e.school, period: [e.from, e.to].filter(Boolean).join(' – '),
      })),
      projects: form.projects.filter((p) => p.name).map((p) => ({ name: p.name, description: p.description, link: p.link })),
      skills: { technical: split(form.skills.technical), tools: split(form.skills.tools), soft: split(form.skills.soft) },
    }
  }, [form])

  const yamlText = useMemo(() => toYaml(yamlPayload), [yamlPayload])
  const resumeText = useMemo(() => payloadToResumeText(yamlPayload), [yamlPayload])
  const next = () => setStep((s) => Math.min(STEPS.length - 1, s + 1))
  const prev = () => setStep((s) => Math.max(0, s - 1))

  const saveResume = async () => {
    setSaveState({ type: 'loading', message: 'Saving your resume…' })
    try {
      const body = new URLSearchParams({
        resume_text: resumeText,
        resume_filename: `${slugify(form.personal.name || 'resume')}-generated.txt`,
      })
      const res = await fetch('/api/user/resume', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Could not save resume.')
      await refreshUser()
      setSaveState({ type: 'success', message: data.onboarding_done ? 'Saved. Jobs and roadmap now use this resume.' : 'Saved. Complete onboarding to choose a target role.' })
    } catch (err) {
      setSaveState({ type: 'error', message: err.message })
    }
  }

  const downloadYaml = () => {
    const blob = new Blob([yamlText + '\n'], { type: 'text/yaml' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `${(form.personal.name || 'resume').toLowerCase().replace(/\s+/g, '-')}.yaml`; a.click()
    URL.revokeObjectURL(url)
  }

  const [pdfLoading, setPdfLoading] = useState(false)
  const downloadPdf = async () => {
    setPdfLoading(true)
    try {
      const build = await loadPdfBuilder()
      build(yamlPayload).save(`${(form.personal.name || 'resume').toLowerCase().replace(/\s+/g, '-')}.pdf`)
    } catch (err) {
      console.error(err)
      alert('Could not generate PDF.')
    } finally {
      setPdfLoading(false)
    }
  }

  return (
    <div className="mt-8 grid lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-6">
        <Stepper step={step} onJump={setStep} />
        <div className="card">
          {step === 0 && <PersonalStep value={form.personal} onChange={(v) => update('personal', v)} />}
          {step === 1 && <ExperienceStep value={form.experience} onChange={(v) => update('experience', v)} />}
          {step === 2 && <EducationStep value={form.education} onChange={(v) => update('education', v)} />}
          {step === 3 && <ProjectsStep value={form.projects} onChange={(v) => update('projects', v)} />}
          {step === 4 && <SkillsStep value={form.skills} onChange={(v) => update('skills', v)} />}
          {step === 5 && <ReviewStep payload={yamlPayload} />}
          <div className="mt-8 flex items-center justify-between gap-3 pt-6 border-t border-line">
            <button onClick={prev} className="btn-ghost" disabled={step === 0}>← Back</button>
            <p className="text-xs text-subtle">Step {step + 1} of {STEPS.length}</p>
            {step < STEPS.length - 1
              ? <button onClick={next} className="btn-primary">Continue →</button>
              : <button onClick={downloadPdf} disabled={pdfLoading} className="btn-primary disabled:opacity-60">
                  {pdfLoading ? 'Generating…' : 'Generate PDF'}
                </button>
            }
          </div>
        </div>
      </div>
      <YamlPreviewPanel
        yaml={yamlText}
        onDownloadYaml={downloadYaml}
        onDownloadPdf={downloadPdf}
        pdfLoading={pdfLoading}
        onSave={saveResume}
        saveState={saveState}
      />
    </div>
  )
}

function slugify(value) {
  return String(value).trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'resume'
}

function payloadToResumeText(payload) {
  const lines = []
  if (payload.name) lines.push(payload.name)
  if (payload.headline) lines.push(payload.headline)
  const contact = [payload.contact?.email, payload.contact?.phone, payload.contact?.location].filter(Boolean).join(' · ')
  if (contact) lines.push(contact)
  if (payload.summary) lines.push('\nSUMMARY\n' + payload.summary)
  if (payload.experience?.length) {
    lines.push('\nEXPERIENCE')
    payload.experience.forEach(item => {
      lines.push([item.title, item.company, item.period].filter(Boolean).join(' · '))
      if (item.description) lines.push(item.description)
    })
  }
  if (payload.education?.length) {
    lines.push('\nEDUCATION')
    payload.education.forEach(item => lines.push([item.degree, item.school, item.period].filter(Boolean).join(' · ')))
  }
  if (payload.projects?.length) {
    lines.push('\nPROJECTS')
    payload.projects.forEach(item => {
      lines.push(item.name)
      if (item.description) lines.push(item.description)
      if (item.link) lines.push(item.link)
    })
  }
  const skillGroups = [
    ['Technical skills', payload.skills?.technical],
    ['Tools and infrastructure', payload.skills?.tools],
    ['Soft skills', payload.skills?.soft],
  ].filter(([, values]) => values?.length)
  if (skillGroups.length) {
    lines.push('\nSKILLS')
    skillGroups.forEach(([label, values]) => lines.push(`${label}: ${values.join(', ')}`))
  }
  return lines.filter(Boolean).join('\n').trim()
}

function Stepper({ step, onJump }) {
  return (
    <div className="card">
      <ol className="flex items-center justify-between gap-2 overflow-x-auto">
        {STEPS.map((label, i) => {
          const state = i < step ? 'done' : i === step ? 'active' : 'todo'
          return (
            <li key={label} className="flex-1 min-w-[88px]">
              <button onClick={() => onJump(i)} className="w-full text-left group">
                <div className="flex items-center gap-2">
                  <span className={`h-6 w-6 grid place-items-center rounded-full text-xs font-semibold ${
                    state === 'done'   ? 'bg-emerald-500 text-white' :
                    state === 'active' ? 'bg-brand-500 text-white shadow-glow' :
                                         'bg-surface-2 text-muted border border-line'
                  }`}>
                    {state === 'done' ? '✓' : i + 1}
                  </span>
                  <span className={`text-xs font-medium ${state === 'active' ? 'text-fg' : 'text-muted'}`}>{label}</span>
                </div>
                <div className={`mt-2 h-1 rounded-full ${state === 'todo' ? 'bg-surface-2' : 'bg-gradient-to-r from-brand-400 to-emerald-400'}`} />
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-wider text-muted">{label}</span>
      <div className="mt-1.5">{children}</div>
      {hint && <p className="mt-1 text-xs text-subtle">{hint}</p>}
    </label>
  )
}

function StepHeader({ title, hint }) {
  return (
    <div className="mb-6">
      <h2 className="text-xl font-semibold text-fg">{title}</h2>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  )
}

function PersonalStep({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v })
  return (
    <div>
      <StepHeader title="Personal info" hint="The basics — name, headline, contact details." />
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="Full name"><input className="input" value={value.name} onChange={(e) => set('name', e.target.value)} placeholder="Jane Cohen" /></Field>
        <Field label="Headline"><input className="input" value={value.headline} onChange={(e) => set('headline', e.target.value)} placeholder="Backend Engineer · Python / PostgreSQL" /></Field>
        <Field label="Email"><input type="email" className="input" value={value.email} onChange={(e) => set('email', e.target.value)} placeholder="jane@example.com" /></Field>
        <Field label="Phone"><input className="input" value={value.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+972 50-000-0000" /></Field>
        <Field label="Location"><input className="input" value={value.location} onChange={(e) => set('location', e.target.value)} placeholder="Tel Aviv, IL" /></Field>
        <div className="sm:col-span-2">
          <Field label="Professional summary" hint="One or two lines about who you are.">
            <textarea rows={3} className="input" value={value.summary} onChange={(e) => set('summary', e.target.value)} placeholder="Backend engineer with 3 years building production Python services." />
          </Field>
        </div>
      </div>
    </div>
  )
}

function RepeaterStep({ title, hint, value, onChange, template, render }) {
  const update = (i, patch) => onChange(value.map((item, idx) => (idx === i ? { ...item, ...patch } : item)))
  const add    = () => onChange([...value, template])
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i))
  return (
    <div>
      <StepHeader title={title} hint={hint} />
      <div className="space-y-4">
        {value.map((item, i) => (
          <div key={i} className="rounded-xl border border-line bg-surface-2/40 p-4 relative">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-muted">Entry {i + 1}</span>
              {value.length > 1 && <button onClick={() => remove(i)} className="text-xs text-muted hover:text-red-400 transition">Remove</button>}
            </div>
            {render(item, (patch) => update(i, patch))}
          </div>
        ))}
        <button onClick={add} className="btn-ghost w-full justify-center">+ Add another</button>
      </div>
    </div>
  )
}

function ExperienceStep({ value, onChange }) {
  return (
    <RepeaterStep title="Experience" hint="Most recent roles first." value={value} onChange={onChange}
      template={{ title: '', company: '', from: '', to: '', description: '' }}
      render={(item, set) => (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Job title"><input className="input" value={item.title} onChange={(e) => set({ title: e.target.value })} placeholder="Backend Engineer" /></Field>
          <Field label="Company"><input className="input" value={item.company} onChange={(e) => set({ company: e.target.value })} placeholder="Acme Inc." /></Field>
          <Field label="From"><input className="input" value={item.from} onChange={(e) => set({ from: e.target.value })} placeholder="2022-01" /></Field>
          <Field label="To"><input className="input" value={item.to} onChange={(e) => set({ to: e.target.value })} placeholder="Present" /></Field>
          <div className="sm:col-span-2"><Field label="What you did"><textarea rows={3} className="input" value={item.description} onChange={(e) => set({ description: e.target.value })} placeholder="Built and shipped…" /></Field></div>
        </div>
      )}
    />
  )
}

function EducationStep({ value, onChange }) {
  return (
    <RepeaterStep title="Education" hint="Degrees and significant certifications." value={value} onChange={onChange}
      template={{ degree: '', school: '', from: '', to: '' }}
      render={(item, set) => (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Degree / Program"><input className="input" value={item.degree} onChange={(e) => set({ degree: e.target.value })} placeholder="B.Sc. Computer Science" /></Field>
          <Field label="School"><input className="input" value={item.school} onChange={(e) => set({ school: e.target.value })} placeholder="Bar-Ilan University" /></Field>
          <Field label="From"><input className="input" value={item.from} onChange={(e) => set({ from: e.target.value })} placeholder="2022" /></Field>
          <Field label="To"><input className="input" value={item.to} onChange={(e) => set({ to: e.target.value })} placeholder="2025" /></Field>
        </div>
      )}
    />
  )
}

function ProjectsStep({ value, onChange }) {
  return (
    <RepeaterStep title="Projects" hint="Side projects and open source work." value={value} onChange={onChange}
      template={{ name: '', description: '', link: '' }}
      render={(item, set) => (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Project name"><input className="input" value={item.name} onChange={(e) => set({ name: e.target.value })} placeholder="ResuMind" /></Field>
          <Field label="Link (optional)"><input className="input" value={item.link} onChange={(e) => set({ link: e.target.value })} placeholder="https://github.com/…" /></Field>
          <div className="sm:col-span-2"><Field label="Description"><textarea rows={2} className="input" value={item.description} onChange={(e) => set({ description: e.target.value })} placeholder="What it does and what you used to build it." /></Field></div>
        </div>
      )}
    />
  )
}

function SkillsStep({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v })
  return (
    <div>
      <StepHeader title="Skills" hint="Comma-separated." />
      <div className="grid gap-4">
        <Field label="Technical (languages, frameworks, databases)">
          <textarea rows={2} className="input" value={value.technical} onChange={(e) => set('technical', e.target.value)} placeholder="Python, FastAPI, PostgreSQL, React" />
        </Field>
        <Field label="Tools & infra">
          <textarea rows={2} className="input" value={value.tools} onChange={(e) => set('tools', e.target.value)} placeholder="Docker, Git, Linux, AWS" />
        </Field>
        <Field label="Soft skills">
          <textarea rows={2} className="input" value={value.soft} onChange={(e) => set('soft', e.target.value)} placeholder="Mentoring, technical writing" />
        </Field>
      </div>
    </div>
  )
}

function ReviewStep({ payload }) {
  return (
    <div>
      <StepHeader title="Review" hint="Last look before generating the PDF." />
      <div className="space-y-4 text-sm">
        {[
          ['Name', payload.name],
          ['Headline', payload.headline],
          ['Contact', [payload.contact.email, payload.contact.phone, payload.contact.location].filter(Boolean).join(' · ')],
          ['Summary', payload.summary],
          ['Experience', `${payload.experience.length} role${payload.experience.length === 1 ? '' : 's'}`],
          ['Education', `${payload.education.length} entr${payload.education.length === 1 ? 'y' : 'ies'}`],
          ['Projects', `${payload.projects.length} project${payload.projects.length === 1 ? '' : 's'}`],
          ['Skills', [...(payload.skills.technical||[]), ...(payload.skills.tools||[]), ...(payload.skills.soft||[])].join(', ') || '—'],
        ].map(([label, value]) => (
          <div key={label} className="flex items-start justify-between gap-4 border-b border-line pb-3">
            <p className="text-muted text-xs uppercase tracking-wider w-32 shrink-0">{label}</p>
            <p className="text-fg flex-1">{value || <span className="text-subtle">—</span>}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function YamlPreviewPanel({ yaml, onDownloadYaml, onDownloadPdf, pdfLoading, onSave, saveState }) {
  return (
    <aside className="lg:col-span-2 lg:sticky lg:top-24 self-start space-y-4">
      <div className="card">
        <div className="flex items-center justify-between">
          <p className="chip">resume.yaml</p>
          <span className="text-xs text-subtle">{yaml.split('\n').length} lines</span>
        </div>
        <pre className="mt-3 max-h-[60vh] overflow-auto rounded-xl bg-surface-2/60 border border-line p-4 text-xs leading-relaxed text-fg/90 font-mono">
          <code>{yaml || '# Fill the form to see your YAML here'}</code>
        </pre>
        <div className="mt-4 flex gap-2">
          <button onClick={onDownloadYaml} className="btn-ghost flex-1">Download YAML</button>
          <button onClick={onDownloadPdf} disabled={pdfLoading} className="btn-primary flex-1 disabled:opacity-60">
            {pdfLoading ? 'Generating…' : 'Download PDF'}
          </button>
        </div>
        <button onClick={onSave} disabled={saveState?.type === 'loading'} className="btn-ghost w-full mt-2 disabled:opacity-60">
          {saveState?.type === 'loading' ? 'Saving…' : 'Save to my profile'}
        </button>
        {saveState && <p className={`mt-2 text-xs ${saveState.type === 'error' ? 'text-red-400' : saveState.type === 'success' ? 'text-emerald-400' : 'text-muted'}`}>{saveState.message}</p>}
      </div>
    </aside>
  )
}
