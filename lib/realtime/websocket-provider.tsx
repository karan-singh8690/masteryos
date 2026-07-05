/**
 * WebSocket Gateway — real-time communication with the backend.
 *
 * Connects to /ws on the backend and provides:
 * - Live notifications
 * - Dashboard updates
 * - Worker metrics
 * - Outbox backlog changes
 * - Scheduler events
 * - Security incidents
 * - Session expiration warnings
 * - Queue updates
 * - Study progress
 * - Achievement unlocks
 *
 * Automatically reconnects with exponential backoff.
 * Falls back gracefully when WebSocket is unavailable.
 */

'use client'

import * as React from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_URL = API_URL.replace('http', 'ws').replace('https', 'wss') + '/ws'

export type WSMessageType =
  | 'notification'
  | 'dashboard_update'
  | 'worker_metrics'
  | 'outbox_update'
  | 'scheduler_event'
  | 'security_incident'
  | 'session_warning'
  | 'queue_update'
  | 'study_progress'
  | 'achievement_unlocked'
  | 'connection_ack'
  | 'ping'
  | 'pong'

export interface WSMessage {
  type: WSMessageType
  payload: Record<string, unknown>
  timestamp: string
  correlation_id?: string
}

type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error'

interface WebSocketContextValue {
  status: WSStatus
  messages: WSMessage[]
  lastMessage: WSMessage | null
  send: (message: WSMessage) => void
  subscribe: (type: WSMessageType, handler: (msg: WSMessage) => void) => () => void
  reconnect: () => void
}

const WebSocketContext = React.createContext<WebSocketContextValue | null>(null)

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000]
const HEARTBEAT_INTERVAL = 30_000
const MAX_MESSAGES_BUFFER = 100

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<WSStatus>('disconnected')
  const [messages, setMessages] = React.useState<WSMessage[]>([])
  const [lastMessage, setLastMessage] = React.useState<WSMessage | null>(null)
  const wsRef = React.useRef<WebSocket | null>(null)
  const reconnectAttemptRef = React.useRef(0)
  const heartbeatRef = React.useRef<NodeJS.Timeout | null>(null)
  const subscribersRef = React.useRef<Map<WSMessageType, Set<(msg: WSMessage) => void>>>(new Map())
  const reconnectTimerRef = React.useRef<NodeJS.Timeout | null>(null)

  const connect = React.useCallback(() => {
    if (typeof window === 'undefined') return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    // Get token from localStorage
    const token = localStorage.getItem('mastery.access_token')
    if (!token) {
      setStatus('disconnected')
      return
    }

    try {
      setStatus(reconnectAttemptRef.current > 0 ? 'reconnecting' : 'connecting')
      const wsUrl = `${WS_URL}?token=${encodeURIComponent(token)}`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('connected')
        reconnectAttemptRef.current = 0
        startHeartbeat()
      }

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data)
          // Skip ping/pong
          if (msg.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }))
            return
          }
          setLastMessage(msg)
          setMessages((prev) => [...prev.slice(-MAX_MESSAGES_BUFFER + 1), msg])

          // Notify subscribers
          const subs = subscribersRef.current.get(msg.type)
          subs?.forEach((handler) => handler(msg))
          const allSubs = subscribersRef.current.get('*' as WSMessageType)
          allSubs?.forEach((handler) => handler(msg))
        } catch {
          // Ignore non-JSON
        }
      }

      ws.onerror = () => {
        setStatus('error')
      }

      ws.onclose = () => {
        setStatus('disconnected')
        stopHeartbeat()
        // Only reconnect if we haven't exceeded max attempts
        if (reconnectAttemptRef.current < RECONNECT_DELAYS.length) {
          scheduleReconnect()
        }
      }
    } catch {
      setStatus('error')
      scheduleReconnect()
    }
  }, [])

  const scheduleReconnect = React.useCallback(() => {
    if (reconnectTimerRef.current) return
    const delay = RECONNECT_DELAYS[Math.min(reconnectAttemptRef.current, RECONNECT_DELAYS.length - 1)]
    reconnectAttemptRef.current++
    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null
      connect()
    }, delay)
  }, [connect])

  const startHeartbeat = () => {
    stopHeartbeat()
    heartbeatRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }))
      }
    }, HEARTBEAT_INTERVAL)
  }

  const stopHeartbeat = () => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
    }
  }

  const send = React.useCallback((message: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const subscribe = React.useCallback(
    (type: WSMessageType, handler: (msg: WSMessage) => void) => {
      if (!subscribersRef.current.has(type)) {
        subscribersRef.current.set(type, new Set())
      }
      subscribersRef.current.get(type)!.add(handler)
      return () => {
        subscribersRef.current.get(type)?.delete(handler)
      }
    },
    [],
  )

  const reconnect = React.useCallback(() => {
    reconnectAttemptRef.current = 0
    if (wsRef.current) {
      wsRef.current.close()
    }
    connect()
  }, [connect])

  React.useEffect(() => {
    connect()
    return () => {
      stopHeartbeat()
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const value: WebSocketContextValue = {
    status,
    messages,
    lastMessage,
    send,
    subscribe,
    reconnect,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

export function useWebSocket() {
  const ctx = React.useContext(WebSocketContext)
  if (!ctx) throw new Error('useWebSocket must be used within WebSocketProvider')
  return ctx
}

/**
 * Subscribe to a specific message type and call handler when received.
 */
export function useWebSocketSubscription(
  type: WSMessageType,
  handler: (msg: WSMessage) => void,
) {
  const { subscribe } = useWebSocket()
  const handlerRef = React.useRef(handler)
  handlerRef.current = handler

  React.useEffect(() => {
    return subscribe(type, (msg) => handlerRef.current(msg))
  }, [type, subscribe])
}

/**
 * Connection status indicator.
 */
export function useWebSocketStatus(): WSStatus {
  const { status } = useWebSocket()
  return status
}
