import { describe, it, expect } from 'vitest'
import {
  isRetryableError,
  getRetryDelay,
  queryRetry,
  isTokenExpiring,
} from '@/lib/production/error-recovery'
import { ApiError } from '@/lib/api-client'

describe('Error Recovery', () => {
  describe('isRetryableError', () => {
    it('returns true for 500 errors', () => {
      const error = new ApiError('Server error', 500, 'SERVER_ERROR')
      expect(isRetryableError(error)).toBe(true)
    })
    it('returns true for 502 errors', () => {
      const error = new ApiError('Bad gateway', 502, 'BAD_GATEWAY')
      expect(isRetryableError(error)).toBe(true)
    })
    it('returns true for 503 errors', () => {
      const error = new ApiError('Service unavailable', 503, 'UNAVAILABLE')
      expect(isRetryableError(error)).toBe(true)
    })
    it('returns true for 429 rate limit', () => {
      const error = new ApiError('Rate limited', 429, 'RATE_LIMITED')
      expect(isRetryableError(error)).toBe(true)
    })
    it('returns true for network errors (status 0)', () => {
      const error = new ApiError('Network error', 0, 'NETWORK_ERROR')
      expect(isRetryableError(error)).toBe(true)
    })
    it('returns false for 400 bad request', () => {
      const error = new ApiError('Bad request', 400, 'BAD_REQUEST')
      expect(isRetryableError(error)).toBe(false)
    })
    it('returns false for 401 unauthorized', () => {
      const error = new ApiError('Unauthorized', 401, 'UNAUTHORIZED')
      expect(isRetryableError(error)).toBe(false)
    })
    it('returns false for 404 not found', () => {
      const error = new ApiError('Not found', 404, 'NOT_FOUND')
      expect(isRetryableError(error)).toBe(false)
    })
    it('returns false for 422 validation error', () => {
      const error = new ApiError('Validation failed', 422, 'VALIDATION_FAILED')
      expect(isRetryableError(error)).toBe(false)
    })
    it('returns true for generic errors', () => {
      expect(isRetryableError(new Error('Generic error'))).toBe(true)
    })
  })

  describe('getRetryDelay', () => {
    it('returns base delay for attempt 0', () => {
      expect(getRetryDelay(0)).toBe(1000)
    })
    it('returns 2x delay for attempt 1', () => {
      expect(getRetryDelay(1)).toBe(2000)
    })
    it('returns 4x delay for attempt 2', () => {
      expect(getRetryDelay(2)).toBe(4000)
    })
    it('returns 8x delay for attempt 3', () => {
      expect(getRetryDelay(3)).toBe(8000)
    })
  })

  describe('queryRetry', () => {
    it('returns true for retryable error under max retries', () => {
      expect(queryRetry(0, new ApiError('Server error', 500, 'SERVER_ERROR'))).toBe(true)
    })
    it('returns false for retryable error at max retries', () => {
      expect(queryRetry(3, new ApiError('Server error', 500, 'SERVER_ERROR'))).toBe(false)
    })
    it('returns false for non-retryable error', () => {
      expect(queryRetry(0, new ApiError('Bad request', 400, 'BAD_REQUEST'))).toBe(false)
    })
  })

  describe('isTokenExpiring', () => {
    it('returns false for null token', () => {
      expect(isTokenExpiring(null)).toBe(false)
    })
    it('returns false for invalid token', () => {
      expect(isTokenExpiring('invalid')).toBe(false)
    })
    it('returns true for token expiring within threshold', () => {
      // Create a JWT with exp 30 seconds from now
      const payload = { exp: Math.floor(Date.now() / 1000) + 30 }
      const token = `header.${btoa(JSON.stringify(payload))}.signature`
      expect(isTokenExpiring(token, 60_000)).toBe(true)
    })
    it('returns false for token not expiring soon', () => {
      const payload = { exp: Math.floor(Date.now() / 1000) + 3600 }
      const token = `header.${btoa(JSON.stringify(payload))}.signature`
      expect(isTokenExpiring(token, 60_000)).toBe(false)
    })
  })
})
