import { useState, useEffect, useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import './Dashboard.css'

function StatCard({ label, value, sub, color }) {
  return (
    <div className="card stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: color || 'var(--text-primary)' }}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

function fmtPnl(n) {
  if (n == null) return '—'
  const s = n >= 0 ? '+' : ''
  return `${s}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const val = payload[0].value
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', padding: '8px 12px', borderRadius: 4 }}>
      <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{label}</div>
      <div style={{ color: val >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 600 }}>
        {fmtPnl(val)}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { userId } = useAuth()
  const [trades, setTrades] = useState([])
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    Promise.all([
      api.post('/trades/history', null, { params: { limit: 500 } }),
      api.get('/users/me'),
    ]).then(([t, u]) => {
      if (!alive) return
      setTrades(t.data)
      setUser(u.data)
    }).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const stats = useMemo(() => {
    const closed = trades.filter((t) => t.status === 'closed')
    const open   = trades.filter((t) => t.status === 'open')
    const totalPnl = closed.reduce((s, t) => s + (t.pnl || 0), 0)
    const wins  = closed.filter((t) => (t.pnl || 0) > 0).length
    const wr    = closed.length ? Math.round((wins / closed.length) * 100) : null
    const avgPnl = closed.length ? totalPnl / closed.length : null
    return { closed, open, totalPnl, wins, wr, avgPnl }
  }, [trades])

  const chartData = useMemo(() => {
    const byDate = {}
    trades
      .filter((t) => t.status === 'closed' && t.entry_time)
      .forEach((t) => {
        const d = fmtDate(t.entry_time)
        byDate[d] = (byDate[d] || 0) + (t.pnl || 0)
      })
    let cum = 0
    return Object.entries(byDate).map(([date, pnl]) => {
      cum += pnl
      return { date, pnl: Math.round(cum) }
    })
  }, [trades])

  const recentTrades = useMemo(() =>
    trades.filter((t) => t.status === 'closed').slice(0, 8)
  , [trades])

  if (loading) return <div className="page" style={{ paddingTop: 40, textAlign: 'center' }}><span className="spinner" /></div>

  return (
    <div className="page">
      <div className="page-title">
        Dashboard
        {user && <span style={{ color: 'var(--text-muted)', fontSize: 13, fontFamily: 'var(--font-mono)', marginLeft: 14, textTransform: 'none', letterSpacing: 0 }}>{user.phone}</span>}
      </div>

      <div className="grid-4" style={{ marginBottom: 16 }}>
        <StatCard
          label="Total P&L"
          value={fmtPnl(stats.totalPnl)}
          color={stats.totalPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}
        />
        <StatCard
          label="Closed Trades"
          value={stats.closed.length}
          sub={`${stats.wins} wins`}
        />
        <StatCard
          label="Win Rate"
          value={stats.wr != null ? `${stats.wr}%` : '—'}
          color={stats.wr >= 50 ? 'var(--accent-green)' : stats.wr != null ? 'var(--accent-red)' : undefined}
        />
        <StatCard
          label="Avg P&L / Trade"
          value={stats.avgPnl != null ? fmtPnl(stats.avgPnl) : '—'}
          color={stats.avgPnl >= 0 ? 'var(--accent-green)' : stats.avgPnl != null ? 'var(--accent-red)' : undefined}
        />
      </div>

      <div className="dashboard-lower">
        <div className="card chart-card">
          <div className="card-title">Cumulative P&L</div>
          {chartData.length > 1 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                <defs>
                  <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="var(--accent-green)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--accent-green)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="pnl" stroke="var(--accent-green)" strokeWidth={2} fill="url(#pnlGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              No closed trades yet
            </div>
          )}
        </div>

        <div className="card recent-card">
          <div className="card-title">Recent Trades</div>
          {recentTrades.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', padding: '20px 0' }}>No trades yet</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Dir</th>
                  <th>P&L</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map((t) => (
                  <tr key={t.id}>
                    <td>{t.symbol}</td>
                    <td>
                      <span className={'badge ' + (t.direction === 'CALL' ? 'badge-green' : 'badge-red')}>
                        {t.direction}
                      </span>
                    </td>
                    <td className={t.pnl >= 0 ? 'val-green' : 'val-red'}>
                      {fmtPnl(t.pnl)}
                    </td>
                    <td className="val-muted">{fmtDate(t.entry_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
