import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('orbit_token'))
  const [userId, setUserId] = useState(() => localStorage.getItem('orbit_user_id'))

  const login = useCallback((tok, uid) => {
    localStorage.setItem('orbit_token', tok)
    localStorage.setItem('orbit_user_id', uid)
    setToken(tok)
    setUserId(uid)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('orbit_token')
    localStorage.removeItem('orbit_user_id')
    setToken(null)
    setUserId(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, userId, login, logout, authed: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
