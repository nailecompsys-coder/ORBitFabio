import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { authed } = useAuth()
  return authed ? children : <Navigate to="/login" replace />
}
