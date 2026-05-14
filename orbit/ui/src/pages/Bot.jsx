import { useState, useEffect, useRef } from 'react'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import { useWebSocket } from '../hooks/useWebSocket'
import './Bot.css'

function statusColor(s) {
  if (s === 'running') return 'badge-green'
  if (s === 'stopped') return 'badge-red'
  return 'badge-muted'
}

function EventRow({ ev }) {
  const ts = ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : ''
  const type = ev.event_type || ev.type || '?'
  const pay  = ev.payload ? JSON.stringify(ev.payload) : ''

  let color = 'var(--text-muted)'
  if (type === 'entry')    color = 'var(--accent-green)'
  if (type === 'exit')     color = 'var(--accent-red)'
  if (type === 'trim')     color = 'var(--accent-yellow)'
  if (type === 'eod')      color = 'var(--accent-blue)'
  if (type === 'day_init') color = 'var(--accent-blue)'

  return (
    <div className="ev-row">
      <span className="ev-ts">{ts}</span>
      <span className="ev-type" style={{ color }}>{type}</span>
      <span className="ev-pay">{pay}</span>
    </div>
  )
}

export default function Bot() {
  const { userId, token } = useAuth()
  const { events, connected } = useWebSocket(userId, token)
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const feedRef = useRef(null)

  useEffect(() => {
    api.get('/bot/status').then((r) => setSession(r.data)).finally(() => setLoading(false))
  }, [])

  const start = async () => {
    setActing(true)
    try { setSession((await api.post('/bot/start')).data) } finally { setActing(false) }
  }

  const stop = async () => {
    setActing(true)
    try { setSession((await api.post('/bot/stop')).data) } finally { setActing(false) }
  }

  const status = session?.status || 'idle'
  const isRunning = status === 'running'

  const regime = events.find((e) => e.event_type === 'day_init')?.payload
  const recentEvents = events.slice(0, 100)

  return (
    <div className="page">
      <div className="page-title">Bot Control</div>

      <div className="bot-top">
        <div className="card bot-status-card">
          <div className="stat-label" style={{ marginBottom: 10 }}>Status</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <span className={'badge ' + statusColor(status)} style={{ fontSize: 14, padding: '4px 12px' }}>
              {status.toUpperCase()}
            </span>
            <span className={'ws-indicator ' + (connected ? 'ws-on' : 'ws-off')}>
              {connected ? '● LIVE' : '○ OFFLINE'}
            </span>
          </div>
          {session?.started_at && (
            <div className="session-info">
              Started: {new Date(session.started_at).toLocaleString()}
            </div>
          )}
          {session?.stopped_at && (
            <div className="session-info">
              Stopped: {new Date(session.stopped_at).toLocaleString()}
            </div>
          )}
          {session?.symbols?.length > 0 && (
            <div className="session-info">
              Symbols: {session.symbols.join(', ')}
            </div>
          )}
          {session?.trd_env && (
            <div className="session-info">
              Mode: <span className={'badge ' + (session.trd_env === 'REAL' ? 'badge-red' : 'badge-blue')}>
                {session.trd_env}
              </span>
            </div>
          )}
          <div className="bot-actions">
            <button className="btn btn-green" onClick={start} disabled={acting || isRunning || loading}>
              {acting && !isRunning ? <span className="spinner" /> : '▶ START'}
            </button>
            <button className="btn btn-red" onClick={stop} disabled={acting || !isRunning || loading}>
              {acting && isRunning ? <span className="spinner" /> : '■ STOP'}
            </button>
          </div>
        </div>

        {regime && (
          <div className="card regime-card">
            <div className="stat-label" style={{ marginBottom: 10 }}>Today's Session</div>
            <div className="regime-grid">
              {regime.vix != null && (
                <div className="regime-item">
                  <div className="regime-key">VIX</div>
                  <div className="regime-val" style={{ color: regime.vix > 20 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                    {Number(regime.vix).toFixed(1)}
                  </div>
                </div>
              )}
              {regime.account != null && (
                <div className="regime-item">
                  <div className="regime-key">Account</div>
                  <div className="regime-val">${Number(regime.account).toLocaleString()}</div>
                </div>
              )}
              {regime.symbols && (
                <div className="regime-item" style={{ gridColumn: '1/-1' }}>
                  <div className="regime-key">Symbols</div>
                  <div className="regime-val">{Array.isArray(regime.symbols) ? regime.symbols.join(' · ') : regime.symbols}</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="card event-feed-card">
        <div className="event-feed-header">
          <div className="stat-label" style={{ margin: 0 }}>Live Event Feed</div>
          <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{recentEvents.length} events</span>
        </div>
        <div className="event-feed" ref={feedRef}>
          {recentEvents.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', padding: '16px 0', textAlign: 'center' }}>
              {connected ? 'Waiting for events...' : 'WebSocket disconnected'}
            </div>
          ) : (
            recentEvents.map((ev, i) => <EventRow key={ev.id ?? i} ev={ev} />)
          )}
        </div>
      </div>
    </div>
  )
}
