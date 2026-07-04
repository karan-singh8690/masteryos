/**
 * Feature flag integration — dynamically enable/disable UI elements.
 *
 * Flags are fetched from the backend and cached in React Query.
 * Components use <FeatureFlag> or useFeatureFlag() to conditionally render.
 */

'use client'

import * as React from 'react'
import { useQuery } from '@tanstack/react-query'

import { featureFlagApi } from '@/lib/admin-api'
import { queryKey } from '@/lib/query-keys'

interface FeatureFlagContextValue {
  flags: Map<string, boolean>
  isEnabled: (key: string) => boolean
  isLoading: boolean
}

const FeatureFlagContext = React.createContext<FeatureFlagContextValue | null>(null)

export function FeatureFlagProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useQuery({
    queryKey: queryKey.admin.featureFlags(),
    queryFn: () => featureFlagApi.list(),
    staleTime: 60_000, // 1 minute
    refetchInterval: 120_000, // Refetch every 2 minutes
  })

  const flags = React.useMemo(() => {
    const map = new Map<string, boolean>()
    if (data) {
      data.forEach((flag) => {
        map.set(flag.key, flag.enabled)
      })
    }
    return map
  }, [data])

  const isEnabled = React.useCallback(
    (key: string) => flags.get(key) ?? false,
    [flags],
  )

  const value: FeatureFlagContextValue = { flags, isEnabled, isLoading }

  return <FeatureFlagContext.Provider value={value}>{children}</FeatureFlagContext.Provider>
}

export function useFeatureFlag(key: string): boolean {
  const ctx = React.useContext(FeatureFlagContext)
  if (!ctx) return false
  return ctx.isEnabled(key)
}

export function useFeatureFlags() {
  const ctx = React.useContext(FeatureFlagContext)
  if (!ctx) {
    return { flags: new Map<string, boolean>(), isEnabled: () => false, isLoading: false }
  }
  return ctx
}

/**
 * Conditionally render children based on a feature flag.
 */
export function FeatureFlag({
  flag,
  fallback = null,
  children,
}: {
  flag: string
  fallback?: React.ReactNode
  children: React.ReactNode
}) {
  const enabled = useFeatureFlag(flag)
  if (!enabled) return <>{fallback}</>
  return <>{children}</>
}
