'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

interface HealthResponse {
  status: string
  app: string
  version: string
  timestamp: number
}

interface ReadinessCheck {
  name: string
  status: string
  latency_ms: number | null
  details: Record<string, string> | null
}

interface ReadinessResponse {
  status: string
  checks: ReadinessCheck[]
}

export default function HealthPage() {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.get<HealthResponse>('/api/v1/health'),
    refetchInterval: 5000,
  })

  const readinessQuery = useQuery({
    queryKey: ['readiness'],
    queryFn: () => apiClient.get<ReadinessResponse>('/api/v1/health/ready'),
    refetchInterval: 10000,
  })

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="mb-8 text-3xl font-bold text-gray-900">Health Check</h1>

      {/* Liveness */}
      <section className="mb-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">Liveness</h2>
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
              healthQuery.isLoading
                ? 'bg-gray-100 text-gray-600'
                : healthQuery.isError
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
            }`}
          >
            {healthQuery.isLoading
              ? 'Checking...'
              : healthQuery.isError
                ? 'Unhealthy'
                : 'Healthy'}
          </span>
        </div>
        {healthQuery.data && (
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">App</dt>
              <dd className="font-mono font-semibold">{healthQuery.data.app}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Version</dt>
              <dd className="font-mono font-semibold">{healthQuery.data.version}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Status</dt>
              <dd className="font-mono font-semibold">{healthQuery.data.status}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Timestamp</dt>
              <dd className="font-mono font-semibold">
                {new Date(healthQuery.data.timestamp * 1000).toISOString()}
              </dd>
            </div>
          </dl>
        )}
      </section>

      {/* Readiness */}
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">Readiness</h2>
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
              readinessQuery.isLoading
                ? 'bg-gray-100 text-gray-600'
                : readinessQuery.isError
                  ? 'bg-red-100 text-red-700'
                  : readinessQuery.data?.status === 'ready'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-yellow-100 text-yellow-700'
            }`}
          >
            {readinessQuery.isLoading
              ? 'Checking...'
              : readinessQuery.isError
                ? 'Error'
                : readinessQuery.data?.status === 'ready'
                  ? 'Ready'
                  : 'Not Ready'}
          </span>
        </div>
        {readinessQuery.data && (
          <div className="space-y-3">
            {readinessQuery.data.checks.map((check) => (
              <div
                key={check.name}
                className="flex items-center justify-between border-b border-gray-100 pb-3 last:border-0 last:pb-0"
              >
                <div>
                  <p className="font-semibold text-gray-700">{check.name}</p>
                  {check.latency_ms !== null && (
                    <p className="text-xs text-gray-500">{check.latency_ms}ms</p>
                  )}
                </div>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    check.status === 'pass'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {check.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
