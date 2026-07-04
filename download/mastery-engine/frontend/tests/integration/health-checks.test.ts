import { describe, it, expect, vi } from 'vitest'
import { checkHealth, checkLiveness, validateDeployment, type HealthStatus } from '@/lib/production/health-checks'

// Mock the API client
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
  },
  ApiError: class extends Error {
    constructor(msg: string, public statusCode: number, public code: string) { super(msg) }
  },
}))

import { apiClient } from '@/lib/api-client'

describe('Health Checks', () => {
  describe('checkHealth', () => {
    it('returns healthy status from backend', async () => {
      const mockHealth: HealthStatus = {
        status: 'healthy',
        services: {
          database: { status: 'healthy' },
          redis: { status: 'healthy' },
          workers: { status: 'healthy' },
          scheduler: { status: 'healthy' },
        },
        version: '1.0.0',
        uptime_seconds: 3600,
      }
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockHealth)
      const result = await checkHealth()
      expect(result.status).toBe('healthy')
      expect(result.services.database.status).toBe('healthy')
    })

    it('returns down status on error', async () => {
      vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'))
      const result = await checkHealth()
      expect(result.status).toBe('down')
      expect(result.services.database.status).toBe('down')
    })
  })

  describe('checkLiveness', () => {
    it('returns true when API is live', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({})
      const result = await checkLiveness()
      expect(result).toBe(true)
    })

    it('returns false when API is down', async () => {
      vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'))
      const result = await checkLiveness()
      expect(result).toBe(false)
    })
  })

  describe('validateDeployment', () => {
    it('passes all checks when healthy', async () => {
      const mockHealth: HealthStatus = {
        status: 'healthy',
        services: {
          database: { status: 'healthy' },
          redis: { status: 'healthy' },
          workers: { status: 'healthy' },
          scheduler: { status: 'healthy' },
        },
        version: '1.0.0',
        uptime_seconds: 3600,
      }
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockHealth)
      const result = await validateDeployment()
      expect(result.passed).toBe(true)
      expect(result.checks).toHaveLength(5)
      expect(result.checks.every(c => c.passed)).toBe(true)
    })

    it('fails when database is down', async () => {
      const mockHealth: HealthStatus = {
        status: 'degraded',
        services: {
          database: { status: 'down' },
          redis: { status: 'healthy' },
          workers: { status: 'healthy' },
          scheduler: { status: 'healthy' },
        },
        version: '1.0.0',
        uptime_seconds: 3600,
      }
      vi.mocked(apiClient.get).mockResolvedValueOnce(mockHealth)
      const result = await validateDeployment()
      expect(result.passed).toBe(false)
      const dbCheck = result.checks.find(c => c.name === 'Database')
      expect(dbCheck?.passed).toBe(false)
    })

    it('fails when all services are down', async () => {
      vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'))
      const result = await validateDeployment()
      expect(result.passed).toBe(false)
      expect(result.checks.every(c => !c.passed)).toBe(true)
    })
  })
})
