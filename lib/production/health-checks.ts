/**
 * Production health checks — validates backend connectivity and service health.
 */

import { apiClient } from '@/lib/api-client'

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'down'
  services: {
    database: ServiceHealth
    redis: ServiceHealth
    workers: ServiceHealth
    scheduler: ServiceHealth
  }
  version: string
  uptime_seconds: number
}

export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'down'
  latency_ms?: number
  last_check?: string
  details?: Record<string, unknown>
}

export async function checkHealth(): Promise<HealthStatus> {
  try {
    const result = await apiClient.get<HealthStatus>('/health/ready')
    return result
  } catch {
    return {
      status: 'down',
      services: {
        database: { status: 'down' },
        redis: { status: 'down' },
        workers: { status: 'down' },
        scheduler: { status: 'down' },
      },
      version: 'unknown',
      uptime_seconds: 0,
    }
  }
}

export async function checkLiveness(): Promise<boolean> {
  try {
    await apiClient.get('/health/live')
    return true
  } catch {
    return false
  }
}

/**
 * Production deployment validation — checks all required services.
 */
export interface DeploymentValidation {
  passed: boolean
  checks: {
    name: string
    passed: boolean
    message: string
  }[]
}

export async function validateDeployment(): Promise<DeploymentValidation> {
  const checks: DeploymentValidation['checks'] = []

  // Check API health
  const health = await checkHealth()
  checks.push({
    name: 'API Health',
    passed: health.status !== 'down',
    message: health.status === 'healthy' ? 'All services healthy' : `Status: ${health.status}`,
  })

  // Check database
  checks.push({
    name: 'Database',
    passed: health.services.database.status === 'healthy',
    message: health.services.database.status,
  })

  // Check Redis
  checks.push({
    name: 'Redis',
    passed: health.services.redis.status === 'healthy',
    message: health.services.redis.status,
  })

  // Check workers
  checks.push({
    name: 'Background Workers',
    passed: health.services.workers.status !== 'down',
    message: health.services.workers.status,
  })

  // Check scheduler
  checks.push({
    name: 'Scheduler',
    passed: health.services.scheduler.status !== 'down',
    message: health.services.scheduler.status,
  })

  const passed = checks.every((c) => c.passed)

  return { passed, checks }
}
