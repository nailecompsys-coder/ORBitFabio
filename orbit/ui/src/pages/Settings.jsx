import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/AuthContext'

export default function Settings() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/users/me').then((r) => setUser(r.data)).finally(() => setLoading(false))
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) return <div className="page" style={{ paddingTop: 40, textAlign: 'center' }}><span className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-title">Settings</div>

      <div className="grid-2" style={{ maxWidth: 640 }}>
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div style={{ marginBottom: 16, fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Account
          </div>
          {user && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Row label="Phone"   value={user.phone} />
              <Row label="User ID" value={user.id} mono />
              <Row label="Role"    value={<span className={'badge ' + (user.role === 'admin' ? 'badge-yellow' : 'badge-muted')}>{user.role}</span>} />
              <Row label="Status"  value={<span className={'badge ' + (user.is_active ? 'badge-green' : 'badge-red')}>{user.is_active ? 'active' : 'inactive'}</span>} />
              <Row label="Joined"  value={user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'} />
            </div>
          )}
        </div>

        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div style={{ marginBottom: 16, fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Trading Mode
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span className="badge badge-blue" style={{ fontSize: 13, padding: '4px 14px' }}>PAPER / SIMULATE</span>
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Live trading not yet enabled</span>
          </div>
        </div>

        <div className="card" style={{ gridColumn: '1/-1' }}>
          <button className="btn btn-red" onClick={handleLogout} style={{ width: '100%', justifyContent: 'center' }}>
            LOGOUT
          </button>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, mono }) {
  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
      <div style={{ width: 80, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-display)', fontWeight: 600, flexShrink: 0 }}>
        {label}
      </div>
      <div style={{ fontFamily: mono ? 'var(--font-mono)' : undefined, fontSize: mono ? 11 : 13, wordBreak: 'break-all' }}>
        {value}
      </div>
    </div>
  )
}
