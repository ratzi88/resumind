import { NavLink, Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useTheme } from '../theme.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

const links = [
  { to: '/resume', label: 'Resume' },
  { to: '/jobs',   label: 'Jobs' },
  { to: '/roadmap',label: 'Roadmap' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
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
          <div className="hidden md:flex items-center gap-1">
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

        <div className="hidden md:flex items-center gap-2">
          <ThemeToggle />
          {user ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted max-w-[140px] truncate">{user.email}</span>
              <button onClick={handleLogout} className="btn-ghost text-sm px-3 py-1.5">
                Sign out
              </button>
            </div>
          ) : (
            <Link to="/login" className="btn-primary">
              Sign in
            </Link>
          )}
        </div>

        <div className="md:hidden flex items-center gap-2">
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
        <div className="md:hidden border-t border-line bg-bg/95">
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
