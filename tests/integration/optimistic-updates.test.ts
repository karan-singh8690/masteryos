import { describe, it, expect } from 'vitest'
import {
  optimisticListUpdate,
  optimisticToggle,
  optimisticNotificationRead,
  optimisticAnswerSubmit,
  optimisticFeatureFlagToggle,
} from '@/lib/optimistic/optimistic-updates'

// Mock query client
const mockQueryClient = {
  cancelQueries: vi.fn().mockResolvedValue(undefined),
  getQueryData: vi.fn(),
  setQueryData: vi.fn(),
  invalidateQueries: vi.fn(),
} as any

describe('Optimistic Updates', () => {
  describe('optimisticListUpdate', () => {
    it('creates config for add operation', () => {
      const config = optimisticListUpdate(mockQueryClient, ['test'], 'add', { id: '1' })
      expect(config.onMutate).toBeDefined()
      expect(config.onError).toBeDefined()
      expect(config.onSettled).toBeDefined()
    })
    it('creates config for update operation', () => {
      const config = optimisticListUpdate(mockQueryClient, ['test'], 'update', { id: '1' })
      expect(config.onMutate).toBeDefined()
    })
    it('creates config for remove operation', () => {
      const config = optimisticListUpdate(mockQueryClient, ['test'], 'remove', { id: '1' })
      expect(config.onMutate).toBeDefined()
    })
  })

  describe('optimisticToggle', () => {
    it('creates config with field name and new value', () => {
      const config = optimisticToggle(mockQueryClient, ['test'], 'enabled', true)
      expect(config.onMutate).toBeDefined()
      expect(config.onError).toBeDefined()
      expect(config.onSettled).toBeDefined()
    })
  })

  describe('optimisticNotificationRead', () => {
    it('creates config for marking notification as read', () => {
      const config = optimisticNotificationRead(mockQueryClient, 'notif-1')
      expect(config.onMutate).toBeDefined()
      expect(config.onError).toBeDefined()
      expect(config.onSettled).toBeDefined()
    })
  })

  describe('optimisticAnswerSubmit', () => {
    it('creates config for answer submission', () => {
      const config = optimisticAnswerSubmit(mockQueryClient, 'q-1')
      expect(config.onMutate).toBeDefined()
      expect(config.onError).toBeDefined()
      expect(config.onSettled).toBeDefined()
    })
  })

  describe('optimisticFeatureFlagToggle', () => {
    it('creates config for feature flag toggle', () => {
      const config = optimisticFeatureFlagToggle(mockQueryClient, 'flag-1', true)
      expect(config.onMutate).toBeDefined()
      expect(config.onError).toBeDefined()
      expect(config.onSettled).toBeDefined()
    })
  })

  describe('onMutate callbacks', () => {
    it('cancelQueries is called in list update', async () => {
      const config = optimisticListUpdate(mockQueryClient, ['test'], 'add', { id: '1' })
      await config.onMutate()
      expect(mockQueryClient.cancelQueries).toHaveBeenCalledWith({ queryKey: ['test'] })
    })

    it('cancelQueries is called in toggle', async () => {
      const config = optimisticToggle(mockQueryClient, ['test'], 'enabled', true)
      await config.onMutate()
      expect(mockQueryClient.cancelQueries).toHaveBeenCalledWith({ queryKey: ['test'] })
    })

    it('invalidateQueries is called in onSettled', () => {
      const config = optimisticListUpdate(mockQueryClient, ['test'], 'add', { id: '1' })
      config.onSettled()
      expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['test'] })
    })
  })

  describe('onError rollback', () => {
    it('restores previous data on error', () => {
      const config = optimisticListUpdate(mockQueryClient, ['test'], 'add', { id: '1' })
      const context = { previous: [{ id: 'old' }] }
      config.onError(new Error('test'), null, context)
      expect(mockQueryClient.setQueryData).toHaveBeenCalledWith(['test'], [{ id: 'old' }])
    })

    it('does not throw when context is undefined', () => {
      const config = optimisticListUpdate(mockQueryClient, ['test'], 'add', { id: '1' })
      expect(() => config.onError(new Error('test'), null, undefined)).not.toThrow()
    })
  })
})
