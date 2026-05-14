import { useState, useEffect, useMemo } from 'react'
import api from '../api'
import './History.css'

function fmtPnl(n) {
  if (n == null) return '—'
  const s = n >= 0 ? '+' : ''
  return `${s}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function fmtDt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export default function History() {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)
  const [symFilter, setSymFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const load = () => {
    setLoading(true)
    api.post('/trades/history', null, {
      params: { limit: 500, symbol: symFilter || undefined, status: statusFilter || undefined },
    })
      .then((r) => setTrades(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const filtered = useMemo(() => trades.filter((t) => {
    if (symFilter && t.symbol !== symFilter) return false
    if (statusFilter && t.status !== statusFilter) return false
    return true
  }), [trades, symFilter, statusFilter])

  const symbols = useMemo(() => [...new Set(trades.map((t) => t.symbol))].sort(), [trades])

  return (
    <div className="page">
      <div className="page-title">Trade History</div>

      <div className="history-filters card" style={{ marginBottom: 12, padding: '12px 16px' }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label className="label">Symbol</label>
            <select value={symFilter} onChange={(e) => setSymFilter(e.target.value)} style={{ width: 120 }}>
              <option value="">All</option>
              {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Status</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ width: 120 }}>
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <button className="btn btn-blue" onClick={load} disabled={loading}>
            {loading ? <span className="spinner" /> : 'REFRESH'}
          </button>
          <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 'auto', alignSelf: 'center' }}>
            {filtered.length} trades
          </span>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center' }}><span className="spinner" /></div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>No trades</div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Symbol</th>
                  <th>Dir</th>
                  <th>Option</th>
                  <th>Entry $</th>
                  <th>Exit $</th>
                  <th>P&L</th>
                  <th>Ret%</th>
                  <th>VIX</th>
                  <th>Status</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr key={t.id}>
                    <td style={{ color: 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>{fmtDt(t.entry_time)}</td>
                    <td style={{ fontFamily: 'var(--font-display)', fontWeight: 700 }}>{t.symbol}</td>
                    <td>
                      <span className={'badge ' + (t.direction === 'CALL' ? 'badge-green' : 'badge-red')}>
                        {t.direction}
                      </span>
                    </td>
                    <td style={{ fontSize: 10, color: 'var(--text-muted)' }}>{t.option_code || '—'}</td>
                    <td>{t.entry_price != null ? `$${Number(t.entry_price).toFixed(2)}` : '—'}</td>
                    <td>{t.exit_price != null ? `$${Number(t.exit_price).toFixed(2)}` : '—'}</td>
                    <td className={t.pnl >= 0 ? 'val-green' : t.pnl < 0 ? 'val-red' : ''} style={{ fontWeight: 600 }}>
                      {fmtPnl(t.pnl)}
                    </td>
                    <td className={t.return_pct >= 0 ? 'val-green' : t.return_pct < 0 ? 'val-red' : 'val-muted'}>
                      {t.return_pct != null ? `${Number(t.return_pct).toFixed(1)}%` : '—'}
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>{t.vix != null ? Number(t.vix).toFixed(1) : '—'}</td>
                    <td>
                      <span className={'badge ' + (t.status === 'open' ? 'badge-blue' : 'badge-muted')}>
                        {t.status}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{t.exit_reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
