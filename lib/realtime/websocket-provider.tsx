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

  // WebSocket is disabled — backend doesn't have a /ws endpoint yet.
  // Provider still renders so components don't crash, but no connection is attempted.
  const connect = React.useCallback(() => {
    // No-op: WebSocket not implemented on backend
    setStatus('disconnected')
  }, [])

  const scheduleReconnect = React.useCallback(() => {
    // No-op: WebSocket not implemented on backend
  }, [])

  const startHeartbeat = () => {
    // No-op: WebSocket not implemented on backend
  }

  const stopHeartbeat = () => {
    // No-op: WebSocket not implemented on backend
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
    // WebSocket is disabled — backend doesn't have a /ws endpoint yet.
    // No connection attempt on mount.
    return () => {}
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
