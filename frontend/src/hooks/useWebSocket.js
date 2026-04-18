import { useRef, useEffect, useCallback } from 'react'
import { getToken, getRefreshToken, setTokens } from '../api'

const MAX_BACKOFF = 16000

async function tryRefresh() {
  const refresh_token = getRefreshToken()
  if (!refresh_token) return false
  try {
    const res = await fetch(`${window.location.origin}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    })
    if (!res.ok) return false
    const data = await res.json()
    if (!data?.access_token) return false
    setTokens(data)
    return true
  } catch (_) {
    return false
  }
}

export function useWebSocket({ docId, onMessage, onStatusChange, enabled = true }) {
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const backoffRef = useRef(1000)
  const docIdRef = useRef(docId)
  const onMessageRef = useRef(onMessage)
  const onStatusChangeRef = useRef(onStatusChange)
  const shouldReconnectRef = useRef(true)

  useEffect(() => { docIdRef.current = docId }, [docId])
  useEffect(() => { onMessageRef.current = onMessage }, [onMessage])
  useEffect(() => { onStatusChangeRef.current = onStatusChange }, [onStatusChange])

  const connect = useCallback(() => {
    if (!docIdRef.current || !enabled) return

    // Close existing socket before reconnecting
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }

    const token = getToken()
    if (!token) {
      window.dispatchEvent(new Event('session-expired'))
      return
    }

    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${wsProto}://${location.host}/ws/documents/${docIdRef.current}?token=${token}`
    const sock = new WebSocket(url)
    wsRef.current = sock
    onStatusChangeRef.current?.('connecting')

    sock.onopen = () => {
      backoffRef.current = 1000
      onStatusChangeRef.current?.('connected')
    }

    sock.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        onMessageRef.current?.(msg)
      } catch (_) {}
    }

    sock.onclose = async (evt) => {
      wsRef.current = null
      if (evt.code === 4001) {
        // Try silent refresh once; if it works, reconnect with the new access token.
        const refreshed = await tryRefresh()
        if (refreshed && shouldReconnectRef.current) {
          onStatusChangeRef.current?.('reconnecting')
          connect()
          return
        }
        window.dispatchEvent(new Event('session-expired'))
        return
      }
      if (evt.code === 4003) {
        onStatusChangeRef.current?.('no-permission')
        return
      }
      onStatusChangeRef.current?.('disconnected')
      if (shouldReconnectRef.current) {
        scheduleReconnect()
      }
    }

    sock.onerror = () => {
      onStatusChangeRef.current?.('error')
    }
  }, [enabled]) // eslint-disable-line react-hooks/exhaustive-deps

  const scheduleReconnect = useCallback(() => {
    clearTimeout(reconnectTimerRef.current)
    onStatusChangeRef.current?.('reconnecting')
    reconnectTimerRef.current = setTimeout(() => {
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF)
      connect()
    }, backoffRef.current)
  }, [connect])

  const send = useCallback((msg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false
    clearTimeout(reconnectTimerRef.current)
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!enabled || !docId) return
    shouldReconnectRef.current = true
    backoffRef.current = 1000
    connect()
    return () => {
      shouldReconnectRef.current = false
      clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [docId, enabled]) // eslint-disable-line react-hooks/exhaustive-deps

  return { send, disconnect }
}
