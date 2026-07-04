import { describe, it, expect } from 'vitest'
import type {
  WSMessage,
  WSMessageType,
} from '@/lib/realtime/websocket-provider'

describe('WebSocket Types', () => {
  it('WSMessageType has all expected types', () => {
    const types: WSMessageType[] = [
      'notification', 'dashboard_update', 'worker_metrics',
      'outbox_update', 'scheduler_event', 'security_incident',
      'session_warning', 'queue_update', 'study_progress',
      'achievement_unlocked', 'connection_ack', 'ping', 'pong',
    ]
    expect(types).toHaveLength(13)
  })

  it('WSMessage has all fields', () => {
    const msg: WSMessage = {
      type: 'notification',
      payload: { id: 'n1', title: 'Test' },
      timestamp: '2024-01-01T00:00:00Z',
      correlation_id: 'corr-1',
    }
    expect(msg.type).toBe('notification')
    expect(msg.payload).toEqual({ id: 'n1', title: 'Test' })
    expect(msg.correlation_id).toBe('corr-1')
  })

  it('WSMessage without correlation_id', () => {
    const msg: WSMessage = {
      type: 'ping',
      payload: {},
      timestamp: '2024-01-01T00:00:00Z',
    }
    expect(msg.correlation_id).toBeUndefined()
  })
})

describe('Realtime hooks exports', () => {
  it('hooks module exports all functions', async () => {
    const m = await import('@/lib/realtime/hooks')
    expect(m.useLiveNotifications).toBeDefined()
    expect(m.useLiveDashboard).toBeDefined()
    expect(m.useLiveAdminMetrics).toBeDefined()
    expect(m.useSessionExpirationWarning).toBeDefined()
    expect(m.useRealtimeUpdates).toBeDefined()
    expect(m.useConnectionStatus).toBeDefined()
  })
})

describe('Offline support exports', () => {
  it('offline module exports all functions', async () => {
    const m = await import('@/lib/offline/offline-provider')
    expect(m.OfflineProvider).toBeDefined()
    expect(m.useOffline).toBeDefined()
    expect(m.useOnlineStatus).toBeDefined()
    expect(m.useOfflineBanner).toBeDefined()
    expect(m.MAX_QUEUE_SIZE).toBe(50)
    expect(m.MAX_RETRIES).toBe(3)
  })

  it('QueuedMutation type has all fields', () => {
    const q: import('@/lib/offline/offline-provider').QueuedMutation = {
      id: 'm1',
      mutationKey: ['test'],
      variables: { data: 'test' },
      timestamp: '2024-01-01T00:00:00Z',
      retryCount: 0,
    }
    expect(q.id).toBe('m1')
    expect(q.retryCount).toBe(0)
  })
})

describe('Feature flags exports', () => {
  it('feature-flags module exports all', async () => {
    const m = await import('@/lib/production/feature-flags')
    expect(m.FeatureFlagProvider).toBeDefined()
    expect(m.useFeatureFlag).toBeDefined()
    expect(m.useFeatureFlags).toBeDefined()
    expect(m.FeatureFlag).toBeDefined()
  })
})

describe('Health checks exports', () => {
  it('health-checks module exports all', async () => {
    const m = await import('@/lib/production/health-checks')
    expect(m.checkHealth).toBeDefined()
    expect(m.checkLiveness).toBeDefined()
    expect(m.validateDeployment).toBeDefined()
  })
})

describe('Production providers exports', () => {
  it('production-providers module exports', async () => {
    const m = await import('@/providers/production-providers')
    expect(m.ProductionProviders).toBeDefined()
  })
})

describe('Realtime sync exports', () => {
  it('realtime-sync module exports', async () => {
    const m = await import('@/lib/realtime/realtime-sync')
    expect(m.RealtimeSync).toBeDefined()
  })
})

describe('Offline banner exports', () => {
  it('offline-banner component exports', async () => {
    const m = await import('@/components/production/offline-banner')
    expect(m.OfflineBanner).toBeDefined()
  })
})
