import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token,   setToken]   = useState(() => localStorage.getItem('rm_token'))
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async (t) => {
    if (!t) { setLoading(false); return }
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${t}` },
      })
      if (!res.ok) throw new Error('unauthorized')
      setUser(await res.json())
    } catch {
      localStorage.removeItem('rm_token')
      setToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUser(token) }, []) // eslint-disable-line

  const login = useCallback(async (t) => {
    localStorage.setItem('rm_token', t)
    setToken(t)
    setLoading(true)
    await loadUser(t)
  }, [loadUser])

  const logout = useCallback(() => {
    localStorage.removeItem('rm_token')
    setToken(null)
    setUser(null)
  }, [])

  const refreshUser = useCallback(() => loadUser(token), [token, loadUser])

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
