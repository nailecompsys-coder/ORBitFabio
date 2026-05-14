import { useMemo } from 'react'
import { useAuth } from '../context/AuthContext'
import { useWebSocket } from '../hooks/useWebSocket'

function fmtPnl(n) {
  if (n == null) return '—'
  const s = n >= 0 ? '+' : ''
  return `${s}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

export default function Positions() {
  const { userId, token } = useAuth()
  const { events, connected } = useWebSocket(userId, token)

  const positions = useMemo(() => {
    const map = {}
    events.forEach((ev) => {
      if (ev.event_type === 'entry' && ev.payload?.symbol) {
        const p = ev.payload
        map[p.symbol] = {
          symbol:       p.symbol,
          direction:    p.direction,
          option_code:  p.option_code,
          entry_price:  p.entry_price,
          vix:          p.vix,
          risk_pct:     p.risk_pct,
          entered_at:   ev.created_at,
        }
      }
      if (ev.event_type === 'exit' && ev.payload?.symbol) {
        delete map[ev.payload.symbol]
      }
    })
    return Object.values(map)
  }, [events])

  return (
    <div className="page">
      <div className="page-title">
        Open Positions
        <span style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--font-mono)', marginLeft: 12, textTransform: 'none', letterSpacing: 0 }}>
          {connected ? '● live' : '○ offline'}
        </span>
      </div>

      {positions.length === 0 ? (
        <div className="card" style={{ padding: '40px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
          No open positions
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Direction</th>
                <th>Option</th>
                <th>Entry $</th>
                <th>VIX</th>
                <th>Risk %</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.symbol}>
                  <td style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>{p.symbol}</td>
                  <td>
                    <span className={'badge ' + (p.direction === 'CALL' ? 'badge-green' : 'badge-red')}>
                      {p.direction}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{p.option_code || '—'}</td>
                  <td>{p.entry_price != null ? `$${Number(p.entry_price).toFixed(2)}` : '—'}</td>
                  <td style={{ color: p.vix > 20 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                    {p.vix != null ? Number(p.vix).toFixed(1) : '—'}
                  </td>
                  <td>{p.risk_pct != null ? `${(p.risk_pct * 100).toFixed(0)}%` : '—'}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    {p.entered_at ? new Date(p.entered_at).toLocaleTimeString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: 16, color: 'var(--text-muted)', fontSize: 11 }}>
        Derived from WebSocket event stream. Refreshes in real-time.
      </div>
    </div>
  )
}
