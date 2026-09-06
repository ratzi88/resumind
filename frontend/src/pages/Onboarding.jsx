import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext.jsx'

const ROLE_ICONS = {
  'backend':           '🖥️',
  'frontend':          '🎨',
  'full-stack':        '⚡',
  'devops':            '⚙️',
  'devsecops':         '🔒',
  'data-engineer':     '🗄️',
  'machine-learning':  '🤖',
  'cyber-security':    '🛡️',
  'ai-engineer':       '🧠',
  'data-analyst':      '📊',
  'qa':                '🔍',
  'software-architect':'🏗️',
  'mlops':             '🚀',
  'network-engineer':  '🌐',
  'android':           '📱',
  'ios':               '🍎',
}
const MAX_FILE_BYTES = 10 * 1024 * 1024

export default function Onboarding() {
  const { token, refreshUser } = useAuth()
  const navigate = useNavigate()

  const [step,    setStep]    = useState(1)   // 1 = upload, 2 = pick role
  const [file,    setFile]    = useState(null)
  const [role,    setRole]    = useState(null)
  const [roles,   setRoles]   = useState([])
  const [dragging,setDragging]= useState(false)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const acceptFile = (candidate) => {
    if (!candidate) return
    const validType = /\.(pdf|docx)$/i.test(candidate.name || '')
    if (!validType) {
      setError('Please choose a PDF or DOCX file.')
      return
    }
    if (candidate.size > MAX_FILE_BYTES) {
      setError('The resume must be smaller than 10 MB.')
      return
    }
    setError(null)
    setFile(candidate)
  }

  useEffect(() => {
    fetch('/api/roles')
      .then(r => r.json())
      .then(d => setRoles(d.roles || []))
      .catch(() => {})
  }, [])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    acceptFile(f)
  }

  const handleFile = (e) => {
    const f = e.target.files?.[0]
    acceptFile(f)
  }

  const submit = async () => {
    if (!file || !role) return
    setLoading(true)
    setError(null)
    try {
      const body = new FormData()
      body.append('file', file)
      body.append('role', role)
      const res  = await fetch('/api/onboarding', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Onboarding failed.')
      await refreshUser()
      navigate('/jobs', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl">
        {/* Progress */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <StepBadge n={1} active={step === 1} done={step > 1} label="Upload Resume" />
          <div className="h-px w-12 bg-line" />
          <StepBadge n={2} active={step === 2} done={false} label="Choose Role" />
        </div>

        {step === 1 && (
          <div className="card">
            <h1 className="text-2xl font-bold text-fg mb-1">Upload your resume</h1>
            <p className="text-muted text-sm mb-6">
              We'll analyse it to detect your current skills. PDF or DOCX, max 10 MB.
            </p>

            <div
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-10 text-center transition cursor-pointer
                ${dragging ? 'border-brand-400 bg-brand-400/5' : 'border-line hover:border-brand-400/50'}`}
            >
              <svg className="mx-auto mb-3 text-muted" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="12" y1="18" x2="12" y2="12" />
                <line x1="9" y1="15" x2="15" y2="15" />
              </svg>
              {file ? (
                <>
                  <p className="text-fg font-medium">{file.name}</p>
                  <p className="text-sm text-muted mt-1">{(file.size / 1024).toFixed(0)} KB</p>
                </>
              ) : (
                <>
                  <p className="text-muted">Drag &amp; drop your CV here, or</p>
                  <label className="mt-3 btn-ghost cursor-pointer inline-block">
                    <input type="file" accept=".pdf,.docx" className="hidden" onChange={handleFile} />
                    Browse files
                  </label>
                </>
              )}
            </div>

            {error && (
              <p className="mt-4 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            {file && (
              <button
                onClick={() => setStep(2)}
                className="btn-primary w-full mt-6"
              >
                Next: Choose role →
              </button>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="card">
            <div className="flex items-center gap-3 mb-1">
              <button onClick={() => setStep(1)} className="btn-ghost px-3 py-1.5 text-sm">← Back</button>
              <h1 className="text-2xl font-bold text-fg">What's your target role?</h1>
            </div>
            <p className="text-muted text-sm mb-6 ml-[60px]">
              We'll build your personal skill roadmap based on this.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {roles.map(r => (
                <button
                  key={r.slug}
                  onClick={() => setRole(r.slug)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border text-center transition
                    ${role === r.slug
                      ? 'border-brand-400 bg-brand-400/10 text-fg'
                      : 'border-line hover:border-brand-400/40 text-muted hover:text-fg'}`}
                >
                  <span className="text-2xl">{ROLE_ICONS[r.slug] || '💼'}</span>
                  <span className="text-xs font-medium leading-tight">{r.label}</span>
                </button>
              ))}
            </div>

            {error && (
              <p className="mt-4 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              onClick={submit}
              disabled={!role || loading}
              className="btn-primary w-full mt-6 disabled:opacity-60"
            >
              {loading ? 'Analysing your resume…' : 'Finish setup →'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function StepBadge({ n, active, done, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`grid place-items-center h-8 w-8 rounded-full text-sm font-bold transition
        ${done ? 'bg-emerald-400/20 text-emerald-400' : active ? 'bg-brand-400 text-white' : 'bg-surface-2 text-muted'}`}>
        {done ? '✓' : n}
      </span>
      <span className={`text-sm hidden sm:block ${active ? 'text-fg font-medium' : 'text-muted'}`}>{label}</span>
    </div>
  )
}
