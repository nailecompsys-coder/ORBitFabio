import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import './Login.css'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const sendOtp = async (e) => {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      await api.post('/auth/request-otp', { phone })
      setStep(2)
    } catch (ex) {
      setErr(ex.response?.data?.detail || 'Failed to send code')
    } finally {
      setLoading(false)
    }
  }

  const verifyOtp = async (e) => {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/verify-otp', { phone, code })
      login(data.token, data.user_id)
      navigate('/dashboard')
    } catch (ex) {
      setErr(ex.response?.data?.detail || 'Invalid code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-logo">
          <span className="login-hex">⬡</span>
          <div>
            <div className="login-brand">ORBIT</div>
            <div className="login-sub">FABIO TRADING SYSTEM</div>
          </div>
        </div>

        {step === 1 ? (
          <form onSubmit={sendOtp}>
            <div className="form-group">
              <label className="label">Phone number</label>
              <input
                type="tel"
                placeholder="+1 555 000 0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                autoFocus
              />
            </div>
            {err && <div className="err-msg">{err}</div>}
            <button className="btn btn-green login-btn" disabled={loading || !phone}>
              {loading ? <span className="spinner" /> : 'SEND CODE'}
            </button>
          </form>
        ) : (
          <form onSubmit={verifyOtp}>
            <div className="login-phone-display">{phone}</div>
            <div className="form-group">
              <label className="label">6-digit code</label>
              <input
                type="text"
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                required
                autoFocus
                style={{ fontSize: 22, letterSpacing: '0.2em', textAlign: 'center' }}
              />
            </div>
            {err && <div className="err-msg">{err}</div>}
            <button className="btn btn-green login-btn" disabled={loading || code.length < 6}>
              {loading ? <span className="spinner" /> : 'VERIFY'}
            </button>
            <button
              type="button"
              className="btn login-btn"
              style={{ marginTop: 8 }}
              onClick={() => { setStep(1); setCode(''); setErr('') }}
            >
              BACK
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
