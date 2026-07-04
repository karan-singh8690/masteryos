import { describe, it, expect } from 'vitest'

// Test types at runtime (type-level tests would fail to compile if types are wrong)
import type { User, AuthResponse, CurrentUser, SecurityDashboard, Notification, NotificationPreferences } from '@/types/auth'
import type { UUID, ISO8601, PaginatedResponse, PaginationParams, ApiErrorResponse, NotificationPriority, NotificationChannel, UserRole, UserStatus } from '@/types/common'

describe('Type definitions', () => {
  it('User type has all required fields', () => {
    const user: User = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      email: 'test@example.com',
      status: 'active',
      mfaEnabled: false,
      emailVerifiedAt: null,
      createdAt: '2024-01-01T00:00:00Z',
    }
    expect(user.id).toBeDefined()
    expect(user.email).toBeDefined()
    expect(user.status).toBeDefined()
    expect(user.mfaEnabled).toBeDefined()
    expect(user.emailVerifiedAt).toBeDefined()
    expect(user.createdAt).toBeDefined()
  })

  it('User status accepts all values', () => {
    const statuses: UserStatus[] = [
      'pending_verification',
      'active',
      'suspended',
      'deactivated',
      'pending_deletion',
      'anonymized',
    ]
    statuses.forEach((s) => expect(s).toBeDefined())
  })

  it('AuthResponse has tokens + user', () => {
    const response: AuthResponse = {
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      expiresIn: 900,
      tokenType: 'Bearer',
      user: {
        id: '123',
        email: 'test@example.com',
        status: 'active',
        mfaEnabled: false,
        emailVerifiedAt: null,
        createdAt: '2024-01-01T00:00:00Z',
      },
    }
    expect(response.accessToken).toBeDefined()
    expect(response.refreshToken).toBeDefined()
    expect(response.expiresIn).toBeDefined()
    expect(response.tokenType).toBeDefined()
    expect(response.user).toBeDefined()
  })

  it('CurrentUser includes profile + roles + permissions', () => {
    const user: CurrentUser = {
      user: {
        id: '123',
        email: 'test@example.com',
        status: 'active',
        mfaEnabled: false,
        emailVerifiedAt: null,
        createdAt: '2024-01-01T00:00:00Z',
      },
      profile: {
        displayName: 'Test User',
        timezone: 'UTC',
        locale: 'en-US',
        avatarUrl: null,
        preferences: {},
      },
      roles: ['learner'],
      permissions: ['identity:user:read_self'],
    }
    expect(user.user).toBeDefined()
    expect(user.profile).toBeDefined()
    expect(user.roles).toBeDefined()
    expect(user.permissions).toBeDefined()
  })

  it('SecurityDashboard has all fields', () => {
    const dashboard: SecurityDashboard = {
      mfaEnabled: false,
      emailVerified: true,
      passwordLastChangedAt: null,
      activeSessions: [],
      recoveryCodesRemaining: 0,
      recentSecurityEvents: [],
    }
    expect(dashboard.mfaEnabled).toBeDefined()
    expect(dashboard.emailVerified).toBeDefined()
    expect(dashboard.activeSessions).toBeDefined()
    expect(dashboard.recoveryCodesRemaining).toBeDefined()
  })

  it('Notification has all fields', () => {
    const notif: Notification = {
      id: '123',
      userId: '456',
      notificationType: 'test',
      channel: 'in_app',
      priority: 'normal',
      status: 'queued',
      title: 'Test',
      body: 'Body',
      payload: {},
      scheduledAt: '2024-01-01T00:00:00Z',
      sentAt: null,
      deliveredAt: null,
      openedAt: null,
      dismissedAt: null,
      createdAt: '2024-01-01T00:00:00Z',
    }
    expect(notif.id).toBeDefined()
    expect(notif.title).toBeDefined()
    expect(notif.body).toBeDefined()
  })

  it('NotificationPreferences has all toggles', () => {
    const prefs: NotificationPreferences = {
      emailEnabled: true,
      inAppEnabled: true,
      pushEnabled: false,
      smsEnabled: false,
      securityNotificationsEnabled: true,
      achievementNotificationsEnabled: true,
      marketingNotificationsEnabled: false,
      reminderNotificationsEnabled: true,
      digestFrequency: 'immediate',
      quietHoursStart: null,
      quietHoursEnd: null,
      timezone: 'UTC',
    }
    expect(prefs.emailEnabled).toBeDefined()
    expect(prefs.securityNotificationsEnabled).toBe(true)
    expect(prefs.digestFrequency).toBe('immediate')
  })

  it('NotificationPriority has all values', () => {
    const priorities: NotificationPriority[] = ['low', 'normal', 'high', 'urgent']
    expect(priorities).toHaveLength(4)
  })

  it('NotificationChannel has all values', () => {
    const channels: NotificationChannel[] = ['in_app', 'email', 'push', 'sms']
    expect(channels).toHaveLength(4)
  })

  it('UserRole has all values', () => {
    const roles: UserRole[] = [
      'learner',
      'instructor',
      'content_editor',
      'organization_admin',
      'administrator',
      'system_admin',
    ]
    expect(roles).toHaveLength(6)
  })

  it('PaginatedResponse has pagination fields', () => {
    const response: PaginatedResponse<string> = {
      items: ['a', 'b'],
      total: 2,
      page: 1,
      pageSize: 20,
      hasNext: false,
      hasPrev: false,
    }
    expect(response.items).toHaveLength(2)
    expect(response.hasNext).toBe(false)
  })

  it('ApiErrorResponse has detail with code + message', () => {
    const error: ApiErrorResponse = {
      detail: {
        code: 'TEST_ERROR',
        message: 'Test error message',
      },
    }
    expect(error.detail.code).toBe('TEST_ERROR')
    expect(error.detail.message).toBe('Test error message')
  })
})
