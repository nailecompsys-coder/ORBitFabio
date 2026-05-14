import { useState, useEffect, useRef, useCallback } from 'react'

export function useWebSocket(userId, token) {
  const [events, setEvents] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const retryRef = useRef(null)

  const connect = useCallback(() => {
    if (!userId || !token) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const url = `${proto}://${host}/ws/${userId}?token=${token}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'ping') return
        setEvents((prev) => [msg, ...prev].slice(0, 500))
      } catch {}
    }

    ws.onclose = () => {
      setConnected(false)
      retryRef.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => ws.close()
  }, [userId, token])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const clear = useCallback(() => setEvents([]), [])

  return { events, connected, clear }
}
