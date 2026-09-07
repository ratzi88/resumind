import { NavLink, Link, useNavigate } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useTheme } from '../theme.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

const links = [
  { to: '/resume', label: 'Resume' },
  { to: '/jobs',   label: 'Jobs' },
  { to: '/statistics', label: 'Your statistics' },
  { to: '/roadmap',label: 'Roadmap' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const accountRef = useRef(null)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!accountOpen) return

    const closeOnOutsideClick = (event) => {
      if (!accountRef.current?.contains(event.target)) setAccountOpen(false)
    }
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setAccountOpen(false)
    }

    document.addEventListener('mousedown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [accountOpen])

  const handleLogout = () => {
    setAccountOpen(false)
    logout()
    navigate('/login', { replace: true })
  }

  const restartOnboarding = () => {
    setAccountOpen(false)
    navigate('/onboarding')
  }

  return (
    <header className="sticky top-0 z-40 backdrop-blur-md bg-bg/80 border-b border-line">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <Logo />
          <span className="text-lg font-bold tracking-tight text-fg">
            Resu<span className="text-brand-400">Mind</span>
          </span>
        </Link>

        {user && (
          <div className="hidden lg:flex items-center gap-1">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? 'bg-surface-2 text-fg'
                      : 'text-muted hover:text-fg hover:bg-surface-2/60'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </div>
        )}

        <div className="hidden lg:flex items-center gap-2">
          <ThemeToggle />
          {user ? (
            <div ref={accountRef} className="relative">
              <button
                type="button"
                onClick={() => setAccountOpen((value) => !value)}
                aria-haspopup="menu"
                aria-expanded={accountOpen}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted hover:text-fg hover:bg-surface-2/60 transition"
              >
                <span className="max-w-[180px] truncate">{user.email}</span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className={`transition-transform ${accountOpen ? 'rotate-180' : ''}`}
                  aria-hidden="true"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </button>

              {accountOpen && (
                <div
                  role="menu"
                  className="absolute right-0 top-full mt-2 w-64 overflow-hidden rounded-xl border border-line bg-bg shadow-xl"
                >
                  <div className="border-b border-line px-4 py-3">
                    <p className="text-xs text-muted">Signed in as</p>
                    <p className="mt-1 truncate text-sm font-medium text-fg">{user.email}</p>
                  </div>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={restartOnboarding}
                    className="w-full px-4 py-3 text-left hover:bg-surface-2 transition"
                  >
                    <span className="block text-sm font-medium text-fg">Redo onboarding</span>
                    <span className="mt-0.5 block text-xs text-muted">Replace your CV and choose a new role</span>
                  </button>
                  <div className="border-t border-line" />
                  <button
                    type="button"
                    role="menuitem"
                    onClick={handleLogout}
                    className="w-full px-4 py-3 text-left text-sm text-muted hover:text-fg hover:bg-surface-2 transition"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link to="/login" className="btn-primary">
              Sign in
            </Link>
          )}
        </div>

        <div className="lg:hidden flex items-center gap-2">
          <ThemeToggle />
          <button
            aria-label="Toggle menu"
            className="btn-ghost px-3 py-2"
            onClick={() => setOpen((v) => !v)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {open ? (
                <path d="M6 6l12 12M6 18L18 6" />
              ) : (
                <>
                  <path d="M3 6h18" />
                  <path d="M3 12h18" />
                  <path d="M3 18h18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </nav>

      {open && (
        <div className="lg:hidden border-t border-line bg-bg/95">
          <div className="px-4 py-3 flex flex-col gap-1">
            {user && links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-lg text-sm font-medium ${
                    isActive ? 'bg-surface-2 text-fg' : 'text-muted hover:bg-surface-2/60'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
            {user ? (
              <>
                <p className="px-3 py-2 text-xs text-muted truncate">{user.email}</p>
                <Link
                  to="/onboarding"
                  onClick={() => setOpen(false)}
                  className="px-3 py-2 rounded-lg hover:bg-surface-2/60"
                >
                  <span className="block text-sm font-medium text-fg">Redo onboarding</span>
                  <span className="mt-0.5 block text-xs text-muted">Replace your CV and choose a new role</span>
                </Link>
                <button
                  onClick={() => { handleLogout(); setOpen(false) }}
                  className="btn-ghost mt-1 text-left"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link to="/login" onClick={() => setOpen(false)} className="btn-primary mt-2 text-center">
                Sign in
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  )
}

function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const isLight = theme === 'light'
  return (
    <button
      onClick={toggle}
      aria-label={`Switch to ${isLight ? 'dark' : 'light'} mode`}
      className="h-9 w-9 grid place-items-center rounded-lg border border-line bg-surface-2/60 text-muted hover:text-fg hover:bg-surface-2 transition"
      title={isLight ? 'Dark mode' : 'Light mode'}
    >
      {isLight ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      )}
    </button>
  )
}

function Logo() {
  return (
    <span className="grid place-items-center h-8 w-8 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 shadow-glow">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M6 4h9l3 3v13H6z" stroke="white" strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M9 11h6M9 14h6M9 17h4" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </span>
  )
}
