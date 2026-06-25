import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext.jsx'

export default function Login() {
  const { token, login } = useAuth()
  const navigate = useNavigate()

  const [mode,    setMode]    = useState('login')
  const [email,   setEmail]   = useState('')
  const [pass,    setPass]    = useState('')
  const [error,   setError]   = useState(null)
  const [loading, setLoading] = useState(false)

  if (token) return <Navigate to="/jobs" replace />

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const body = new URLSearchParams({ email, password: pass })
      const res  = await fetch(`/api/auth/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Something went wrong.')

      // For existing logins, check onboarding status before navigating
      let destination = '/jobs'
      if (mode === 'register') {
        destination = '/onboarding'
      } else {
        const meRes = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${data.token}` },
        })
        if (meRes.ok) {
          const me = await meRes.json()
          destination = me.onboarding_done ? '/jobs' : '/onboarding'
        }
      }

      await login(data.token)
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="card w-full max-w-sm">
        <div className="flex justify-center mb-6">
          <span className="grid place-items-center h-12 w-12 rounded-2xl bg-gradient-to-br from-brand-400 to-brand-700 shadow-glow">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M6 4h9l3 3v13H6z" stroke="white" strokeWidth="1.8" strokeLinejoin="round" />
              <path d="M9 11h6M9 14h6M9 17h4" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </span>
        </div>

        <h1 className="text-2xl font-bold text-fg text-center">
          {mode === 'login' ? 'Welcome back' : 'Create your account'}
        </h1>
        <p className="text-sm text-muted text-center mt-1 mb-7">
          {mode === 'login'
            ? 'Sign in to your ResuMind account'
            : 'AI-powered career coaching starts here'}
        </p>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-wider text-muted mb-1.5 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              className="input w-full"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wider text-muted mb-1.5 block">Password</label>
            <input
              type="password"
              value={pass}
              onChange={e => setPass(e.target.value)}
              placeholder="••••••••"
              required
              minLength={8}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              className="input w-full"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full disabled:opacity-60 mt-2"
          >
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign in →' : 'Create account →'}
          </button>
        </form>

        <p className="mt-6 text-sm text-muted text-center">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            onClick={() => { setMode(m => m === 'login' ? 'register' : 'login'); setError(null) }}
            className="text-brand-400 hover:underline font-medium"
          >
            {mode === 'login' ? 'Create one' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}
