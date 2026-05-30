import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader } from './shared.jsx'
import { toYaml } from '../lib/yaml.js'
// jsPDF is large (~600 KB) — lazy-load so it doesn't block the initial page
const loadPdfBuilder = () => import('../lib/generatePdf.js').then((m) => m.buildResumePdf)

export default function Resume() {
  const [mode, setMode] = useState('upload')
  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <PageHeader
        eyebrow="Flow 1"
        title="Your Resume"
        subtitle="Upload an existing CV or build a new one with our guided form. We convert it to YAML, then a clean PDF."
      />

      <div className="mt-8 inline-flex p-1 rounded-xl bg-surface-2/60 border border-line">
        <TabBtn active={mode === 'upload'} onClick={() => setMode('upload')}>
          Upload existing
        </TabBtn>
        <TabBtn active={mode === 'build'} onClick={() => setMode('build')}>
          Build from form
        </TabBtn>
      </div>

      {mode === 'upload' ? <UploadView /> : <BuildView />}
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

function UploadView() {
  const [drag, setDrag] = useState(false)
  const [file, setFile] = useState(null)

  return (
    <div className="mt-8 grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDrag(true)
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDrag(false)
            if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0])
          }}
          className={`card border-dashed text-center transition-colors ${
            drag ? 'border-brand-400 bg-brand-500/10' : ''
          }`}
        >
          <div className="mx-auto h-14 w-14 grid place-items-center rounded-2xl bg-brand-500/15 text-brand-500 dark:text-brand-300 border border-brand-400/20">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16V4M6 10l6-6 6 6" />
              <path d="M4 20h16" />
            </svg>
          </div>
          <h3 className="mt-4 text-xl font-semibold text-fg">Drop your CV here</h3>
          <p className="mt-1 text-sm text-muted">PDF or DOCX, up to 10MB</p>

          <label className="btn-primary mt-6 cursor-pointer">
            <input
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            Choose file
          </label>

          {file && (
            <div className="mt-6 inline-flex items-center gap-3 rounded-xl bg-surface-2 border border-line px-4 py-2">
              <span className="text-sm text-fg">{file.name}</span>
              <span className="chip">{(file.size / 1024).toFixed(0)} KB</span>
              <button onClick={() => setFile(null)} className="text-muted hover:text-fg text-sm">✕</button>
            </div>
          )}

          <p className="mt-6 text-xs text-subtle">
            Files are stored locally. Sensitive PII (IDs, addresses) is filtered out before indexing.
          </p>
        </div>

        {file && (
          <div className="card mt-6">
            <p className="chip">Detected from your file</p>
            <h3 className="mt-3 text-lg font-semibold text-fg">We extracted these skills</h3>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {['Python', 'PostgreSQL', 'Docker', 'REST APIs', 'Git', 'Linux'].map((s) => (
                <span key={s} className="chip border-brand-400/30 text-brand-500 dark:text-brand-200">{s}</span>
              ))}
            </div>
            <Link to="/jobs" className="btn-primary w-full justify-center mt-5">
              Find matching jobs →
            </Link>
          </div>
        )}
      </div>
      <UploadSidebar />
    </div>
  )
}

function UploadSidebar() {
  const items = [
    { t: 'PDF & DOCX support', d: 'We use pypdf and python-docx with OCR fallback for scanned PDFs.' },
    { t: 'PII filtered out', d: 'IDs, addresses, marital status — never indexed.' },
    { t: 'Stored locally', d: 'Files live on your machine. No cloud, no third parties.' },
  ]
  return (
    <aside className="card self-start">
      <p className="chip">What happens next</p>
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

const STEPS = ['Personal', 'Experience', 'Education', 'Projects', 'Skills', 'Review']

const EMPTY_FORM = {
  personal: { name: '', headline: '', email: '', phone: '', location: '', summary: '' },
  experience: [
    { title: '', company: '', from: '', to: '', description: '' },
  ],
  education: [{ degree: '', school: '', from: '', to: '' }],
  projects: [{ name: '', description: '', link: '' }],
  skills: { technical: '', tools: '', soft: '' },
}

function BuildView() {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(EMPTY_FORM)

  const update = (section, value) => setForm((f) => ({ ...f, [section]: value }))

  const yamlPayload = useMemo(() => {
    const splitSkills = (s) =>
      (s || '')
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
    return {
      name: form.personal.name,
      headline: form.personal.headline,
      contact: {
        email: form.personal.email,
        phone: form.personal.phone,
        location: form.personal.location,
      },
      summary: form.personal.summary,
      experience: form.experience
        .filter((e) => e.title || e.company)
        .map((e) => ({
          title: e.title,
          company: e.company,
          period: [e.from, e.to].filter(Boolean).join(' – '),
          description: e.description,
        })),
      education: form.education
        .filter((e) => e.degree || e.school)
        .map((e) => ({
          degree: e.degree,
          school: e.school,
          period: [e.from, e.to].filter(Boolean).join(' – '),
        })),
      projects: form.projects
        .filter((p) => p.name)
        .map((p) => ({ name: p.name, description: p.description, link: p.link })),
      skills: {
        technical: splitSkills(form.skills.technical),
        tools: splitSkills(form.skills.tools),
        soft: splitSkills(form.skills.soft),
      },
    }
  }, [form])

  const yamlText = useMemo(() => toYaml(yamlPayload), [yamlPayload])

  const next = () => setStep((s) => Math.min(STEPS.length - 1, s + 1))
  const prev = () => setStep((s) => Math.max(0, s - 1))

  const downloadYaml = () => {
    const blob = new Blob([yamlText + '\n'], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${(form.personal.name || 'resume').toLowerCase().replace(/\s+/g, '-')}.yaml`
    a.click()
    URL.revokeObjectURL(url)
  }

  const [pdfLoading, setPdfLoading] = useState(false)

  const downloadPdf = async () => {
    setPdfLoading(true)
    try {
      const buildResumePdf = await loadPdfBuilder()
      const pdf = buildResumePdf(yamlPayload)
      const filename = `${(form.personal.name || 'resume').toLowerCase().replace(/\s+/g, '-')}.pdf`
      pdf.save(filename)
    } catch (err) {
      console.error('PDF generation failed:', err)
      alert('Could not generate PDF. Check the browser console for details.')
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
          {step === 1 && (
            <ExperienceStep value={form.experience} onChange={(v) => update('experience', v)} />
          )}
          {step === 2 && (
            <EducationStep value={form.education} onChange={(v) => update('education', v)} />
          )}
          {step === 3 && (
            <ProjectsStep value={form.projects} onChange={(v) => update('projects', v)} />
          )}
          {step === 4 && <SkillsStep value={form.skills} onChange={(v) => update('skills', v)} />}
          {step === 5 && <ReviewStep payload={yamlPayload} />}

          <div className="mt-8 flex items-center justify-between gap-3 pt-6 border-t border-line">
            <button onClick={prev} className="btn-ghost" disabled={step === 0}>
              ← Back
            </button>
            <p className="text-xs text-subtle">
              Step {step + 1} of {STEPS.length}
            </p>
            {step < STEPS.length - 1 ? (
              <button onClick={next} className="btn-primary">
                Continue →
              </button>
            ) : (
              <button onClick={downloadPdf} disabled={pdfLoading} className="btn-primary disabled:opacity-60">
                {pdfLoading ? 'Generating…' : 'Generate PDF'}
              </button>
            )}
          </div>
        </div>
      </div>
      <YamlPreviewPanel yaml={yamlText} onDownloadYaml={downloadYaml} onDownloadPdf={downloadPdf} pdfLoading={pdfLoading} />
    </div>
  )
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
                  <span
                    className={`h-6 w-6 grid place-items-center rounded-full text-xs font-semibold ${
                      state === 'done'
                        ? 'bg-emerald-500 text-white'
                        : state === 'active'
                        ? 'bg-brand-500 text-white shadow-glow'
                        : 'bg-surface-2 text-muted border border-line'
                    }`}
                  >
                    {state === 'done' ? '✓' : i + 1}
                  </span>
                  <span
                    className={`text-xs font-medium ${
                      state === 'active' ? 'text-fg' : 'text-muted'
                    }`}
                  >
                    {label}
                  </span>
                </div>
                <div
                  className={`mt-2 h-1 rounded-full ${
                    state === 'todo' ? 'bg-surface-2' : 'bg-gradient-to-r from-brand-400 to-emerald-400'
                  }`}
                />
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
        <Field label="Full name">
          <input className="input" value={value.name} onChange={(e) => set('name', e.target.value)} placeholder="Jane Cohen" />
        </Field>
        <Field label="Headline">
          <input className="input" value={value.headline} onChange={(e) => set('headline', e.target.value)} placeholder="Backend Engineer · Python / PostgreSQL" />
        </Field>
        <Field label="Email">
          <input type="email" className="input" value={value.email} onChange={(e) => set('email', e.target.value)} placeholder="jane@example.com" />
        </Field>
        <Field label="Phone">
          <input className="input" value={value.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+972 50-000-0000" />
        </Field>
        <Field label="Location">
          <input className="input" value={value.location} onChange={(e) => set('location', e.target.value)} placeholder="Tel Aviv, IL" />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Professional summary" hint="One or two lines about who you are and what you do best.">
            <textarea
              rows={3}
              className="input"
              value={value.summary}
              onChange={(e) => set('summary', e.target.value)}
              placeholder="Backend engineer with 3 years of experience building production Python services."
            />
          </Field>
        </div>
      </div>
    </div>
  )
}

function RepeaterStep({ title, hint, value, onChange, template, render }) {
  const update = (i, patch) =>
    onChange(value.map((item, idx) => (idx === i ? { ...item, ...patch } : item)))
  const add = () => onChange([...value, template])
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i))

  return (
    <div>
      <StepHeader title={title} hint={hint} />
      <div className="space-y-4">
        {value.map((item, i) => (
          <div key={i} className="rounded-xl border border-line bg-surface-2/40 p-4 relative">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-muted">Entry {i + 1}</span>
              {value.length > 1 && (
                <button
                  onClick={() => remove(i)}
                  className="text-xs text-muted hover:text-red-400 transition"
                >
                  Remove
                </button>
              )}
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
    <RepeaterStep
      title="Experience"
      hint="Most recent roles first. Skip dates you don't remember exactly."
      value={value}
      onChange={onChange}
      template={{ title: '', company: '', from: '', to: '', description: '' }}
      render={(item, set) => (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Job title">
            <input className="input" value={item.title} onChange={(e) => set({ title: e.target.value })} placeholder="Backend Engineer" />
          </Field>
          <Field label="Company">
            <input className="input" value={item.company} onChange={(e) => set({ company: e.target.value })} placeholder="Acme Inc." />
          </Field>
          <Field label="From">
            <input className="input" value={item.from} onChange={(e) => set({ from: e.target.value })} placeholder="2022-01" />
          </Field>
          <Field label="To">
            <input className="input" value={item.to} onChange={(e) => set({ to: e.target.value })} placeholder="Present" />
          </Field>
          <div className="sm:col-span-2">
            <Field label="What you did">
              <textarea rows={3} className="input" value={item.description} onChange={(e) => set({ description: e.target.value })} placeholder="Built and shipped..." />
            </Field>
          </div>
        </div>
      )}
    />
  )
}

function EducationStep({ value, onChange }) {
  return (
    <RepeaterStep
      title="Education"
      hint="Degrees and significant certifications."
      value={value}
      onChange={onChange}
      template={{ degree: '', school: '', from: '', to: '' }}
      render={(item, set) => (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Degree / Program">
            <input className="input" value={item.degree} onChange={(e) => set({ degree: e.target.value })} placeholder="B.Sc. Computer Science" />
          </Field>
          <Field label="School / Institution">
            <input className="input" value={item.school} onChange={(e) => set({ school: e.target.value })} placeholder="Bar-Ilan University" />
          </Field>
          <Field label="From">
            <input className="input" value={item.from} onChange={(e) => set({ from: e.target.value })} placeholder="2022" />
          </Field>
          <Field label="To">
            <input className="input" value={item.to} onChange={(e) => set({ to: e.target.value })} placeholder="2025" />
          </Field>
        </div>
      )}
    />
  )
}

function ProjectsStep({ value, onChange }) {
  return (
    <RepeaterStep
      title="Projects"
      hint="Side projects, open source, course work that shows your stack."
      value={value}
      onChange={onChange}
      template={{ name: '', description: '', link: '' }}
      render={(item, set) => (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Project name">
            <input className="input" value={item.name} onChange={(e) => set({ name: e.target.value })} placeholder="ResuMind" />
          </Field>
          <Field label="Link (optional)">
            <input className="input" value={item.link} onChange={(e) => set({ link: e.target.value })} placeholder="https://github.com/…" />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Description">
              <textarea rows={2} className="input" value={item.description} onChange={(e) => set({ description: e.target.value })} placeholder="What it does and what you used to build it." />
            </Field>
          </div>
        </div>
      )}
    />
  )
}

function SkillsStep({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v })
  return (
    <div>
      <StepHeader title="Skills" hint="Comma-separated. We'll vectorize these against job descriptions." />
      <div className="grid gap-4">
        <Field label="Technical (languages, frameworks, databases)">
          <textarea rows={2} className="input" value={value.technical} onChange={(e) => set('technical', e.target.value)} placeholder="Python, FastAPI, PostgreSQL, React, TypeScript" />
        </Field>
        <Field label="Tools & infra">
          <textarea rows={2} className="input" value={value.tools} onChange={(e) => set('tools', e.target.value)} placeholder="Docker, Git, Linux, AWS, Datadog" />
        </Field>
        <Field label="Soft skills">
          <textarea rows={2} className="input" value={value.soft} onChange={(e) => set('soft', e.target.value)} placeholder="Mentoring, technical writing, cross-team collaboration" />
        </Field>
      </div>
    </div>
  )
}

function ReviewStep({ payload }) {
  return (
    <div>
      <StepHeader title="Review" hint="Last look before we generate the PDF. Edit any step from the stepper above." />
      <div className="space-y-4 text-sm">
        <ReviewRow label="Name" value={payload.name} />
        <ReviewRow label="Headline" value={payload.headline} />
        <ReviewRow label="Contact" value={[payload.contact.email, payload.contact.phone, payload.contact.location].filter(Boolean).join(' · ')} />
        <ReviewRow label="Summary" value={payload.summary} />
        <ReviewRow label="Experience" value={`${payload.experience.length} role${payload.experience.length === 1 ? '' : 's'}`} />
        <ReviewRow label="Education" value={`${payload.education.length} entr${payload.education.length === 1 ? 'y' : 'ies'}`} />
        <ReviewRow label="Projects" value={`${payload.projects.length} project${payload.projects.length === 1 ? '' : 's'}`} />
        <ReviewRow
          label="Skills"
          value={[
            ...(payload.skills.technical || []),
            ...(payload.skills.tools || []),
            ...(payload.skills.soft || []),
          ].join(', ') || '—'}
        />
      </div>
    </div>
  )
}

function ReviewRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line pb-3">
      <p className="text-muted text-xs uppercase tracking-wider w-32 shrink-0">{label}</p>
      <p className="text-fg flex-1">{value || <span className="text-subtle">—</span>}</p>
    </div>
  )
}

function YamlPreviewPanel({ yaml, onDownloadYaml, onDownloadPdf, pdfLoading }) {
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
      </div>
      <div className="card">
        <p className="chip">Pipeline</p>
        <ol className="mt-3 space-y-2 text-sm text-muted">
          <li>1. Form → structured YAML profile</li>
          <li>2. YAML → PDF via YAML Resume Docker image</li>
          <li>3. PDF stored locally, vectorized for matching</li>
        </ol>
      </div>
    </aside>
  )
}
