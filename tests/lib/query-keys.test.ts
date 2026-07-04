import { describe, it, expect } from 'vitest'

import { queryKey } from '@/lib/query-keys'

describe('queryKey', () => {
  describe('auth', () => {
    it('generates me key', () => {
      expect(queryKey.auth.me()).toEqual(['auth', 'me'])
    })

    it('generates session key', () => {
      expect(queryKey.auth.session()).toEqual(['auth', 'session'])
    })
  })

  describe('users', () => {
    it('generates me key', () => {
      expect(queryKey.users.me()).toEqual(['users', 'me'])
    })

    it('generates security key', () => {
      expect(queryKey.users.security()).toEqual(['users', 'me', 'security'])
    })

    it('generates detail key with ID', () => {
      expect(queryKey.users.detail('user-123')).toEqual(['users', 'user-123'])
    })
  })

  describe('notifications', () => {
    it('generates list key without filters', () => {
      expect(queryKey.notifications.list()).toEqual(['notifications', 'list', undefined])
    })

    it('generates list key with filters', () => {
      const key = queryKey.notifications.list({ status: 'unread' })
      expect(key).toEqual(['notifications', 'list', { status: 'unread' }])
    })

    it('generates detail key', () => {
      expect(queryKey.notifications.detail('notif-1')).toEqual(['notifications', 'notif-1'])
    })

    it('generates unread count key', () => {
      expect(queryKey.notifications.unreadCount()).toEqual(['notifications', 'unread-count'])
    })
  })

  describe('learning', () => {
    it('generates sessions key', () => {
      expect(queryKey.learning.sessions()).toEqual(['learning', 'sessions'])
    })

    it('generates adaptive queue key', () => {
      expect(queryKey.learning.adaptiveQueue('session-1')).toEqual([
        'learning',
        'sessions',
        'session-1',
        'adaptive-queue',
      ])
    })
  })

  describe('admin', () => {
    it('generates workers key', () => {
      expect(queryKey.admin.workers()).toEqual(['admin', 'workers'])
    })

    it('generates outbox key', () => {
      expect(queryKey.admin.outbox()).toEqual(['admin', 'outbox', undefined])
    })

    it('generates outbox key with filters', () => {
      expect(queryKey.admin.outbox({ status: 'pending' })).toEqual([
        'admin',
        'outbox',
        { status: 'pending' },
      ])
    })

    it('generates jobs key', () => {
      expect(queryKey.admin.jobs()).toEqual(['admin', 'jobs'])
    })
  })
})
