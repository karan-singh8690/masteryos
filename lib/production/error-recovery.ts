/**
 * Error recovery — global retry policy, network recovery, graceful degradation.
 */

import { ApiError } from '@/lib/api-client'

export const MAX_RETRIES = 3
export const RETRY_DELAY_MS = 1000

export function isRetryableError(error: unknown): boolean {
  if (error instanceof ApiError) {
    // Retry on 5xx and 429 (rate limit)
    return error.statusCode >= 500 || error.statusCode === 429 || error.statusCode === 0
  }
  return true // Network errors
}

export function getRetryDelay(attempt: number): number {
  return RETRY_DELAY_MS * Math.pow(2, attempt)
}

/**
 * React Query retry function with custom logic.
 */
export function queryRetry(failureCount: number, error: unknown): boolean {
  if (!isRetryableError(error)) return false
  return failureCount < MAX_RETRIES
}

/**
 * Global error handler for unhandled errors.
 */
export function handleGlobalError(error: unknown): void {
  if (error instanceof ApiError) {
    if (error.statusCode === 0) {
      // Network error — offline banner handles this
      return
    }
    if (error.statusCode === 503) {
      // Maintenance mode
      if (typeof window !== 'undefined') {
        window.location.href = '/maintenance'
      }
      return
    }
  }
  // Log to monitoring service in production
  if (process.env.NODE_ENV === 'production') {
    // TODO: Send to Sentry/Datadog
  }
}

/**
 * Maintenance mode detector.
 */
export async function checkMaintenanceMode(): Promise<boolean> {
  try {
    const response = await fetch('/api/v1/health')
    if (response.status === 503) return true
    const data = await response.json()
    return data.maintenance === true
  } catch {
    return false
  }
}

/**
 * Token expiration detector — checks if the current token is about to expire.
 */
export function isTokenExpiring(token: string | null, thresholdMs: number = 60_000): boolean {
  if (!token) return false
  try {
    const payload = JSON.parse(atob(token.split('.')[1]!))
    const expiresAt = payload.exp * 1000
    return Date.now() + thresholdMs >= expiresAt
  } catch {
    return false
  }
}
