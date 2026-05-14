import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useWebSocket } from '../hooks/useWebSocket'
import './Layout.css'

const NAV = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/bot',       label: 'Bot' },
  { to: '/positions', label: 'Positions' },
  { to: '/history',   label: 'History' },
  { to: '/settings',  label: 'Settings' },
]

export default function Layout() {
  const { userId, token, logout } = useAuth()
  const { connected } = useWebSocket(userId, token)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-hex">⬡</span>
          <span className="brand-name">ORBIT</span>
          <span className="brand-sub">FABIO</span>
        </div>
        <nav className="topbar-nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="topbar-right">
          <span className={'ws-dot ' + (connected ? 'ws-on' : 'ws-off')} title={connected ? 'WS connected' : 'WS disconnected'} />
          <button className="btn btn-red" style={{ padding: '4px 12px', fontSize: 11 }} onClick={handleLogout}>
            LOGOUT
          </button>
        </div>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
