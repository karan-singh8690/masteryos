'use client'

import * as React from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { authApi, tokenStorage, userApi } from '@/lib/api-client'
import { queryKey } from '@/lib/query-keys'
import { useAuthStore } from '@/stores/auth-store'
import type { CurrentUser } from '@/types/auth'

interface AuthContextValue {
  user: CurrentUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string, mfaCode?: string) => Promise<void>
  logout: (allDevices?: boolean) => Promise<void>
  refresh: () => void
  setUser: (user: CurrentUser | null) => void
}

const AuthContext = React.createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const { user, isAuthenticated, setUser, setLoading, logout: storeLogout } = useAuthStore()
  // Start with false on both server and client to avoid hydration mismatch.
  // The useEffect below sets the real value after mount.
  const [hasToken, setHasToken] = React.useState(false)
  // Track whether we've mounted on the client (to avoid hydration mismatch
  // when reading from the persisted zustand store).
  const [mounted, setMounted] = React.useState(false)

  // Check for existing token on mount
  React.useEffect(() => {
    setMounted(true)
    const token = tokenStorage.getAccessToken()
    setHasToken(!!token)
    if (!token) {
      setLoading(false)
    }
  }, [setLoading])

  // Fetch current user if we have a token
  const { data: currentUser, isLoading } = useQuery({
    queryKey: queryKey.users.me(),
    queryFn: () => userApi.me(),
    enabled: hasToken,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Update store when user data changes
  React.useEffect(() => {
    if (currentUser) {
      setUser(currentUser)
      setLoading(false)
    } else if (!isLoading && hasToken) {
      // Token exists but user fetch failed — logout
      storeLogout()
    }
  }, [currentUser, isLoading, hasToken, setUser, setLoading, storeLogout])

  const login = React.useCallback(
    async (email: string, password: string, mfaCode?: string) => {
      const response = await authApi.login({ email, password, mfa_code: mfaCode })
      if (response.requires_mfa) {
        // Return MFA challenge — caller handles
        throw new MfaRequiredError(response.mfa_session_token || '')
      }
      tokenStorage.setAccessToken(response.access_token)
      if (response.refresh_token) {
        tokenStorage.setRefreshToken(response.refresh_token)
      }
      setHasToken(true)
      // Don't setUser with bare User — auth provider's useQuery will fetch
      // the full CurrentUser (with profile + roles + permissions) automatically.
      queryClient.invalidateQueries({ queryKey: queryKey.users.me() })
    },
    [setUser, queryClient],
  )

  const logout = React.useCallback(
    async (allDevices = false) => {
      try {
        if (allDevices) {
          await authApi.logoutAll()
        } else {
          const refreshToken = tokenStorage.getRefreshToken()
          await authApi.logout(refreshToken || undefined)
        }
      } catch {
        // Ignore errors on logout
      } finally {
        tokenStorage.clear()
        // Also clear legacy keys
        if (typeof window !== 'undefined') {
          localStorage.removeItem('mastery-token')
          // Clear auth cookies
          document.cookie = 'mastery-authenticated=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
          document.cookie = 'mastery-role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
        }
        setUser(null)
        setHasToken(false)
        queryClient.clear()
        // Redirect to login
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
    },
    [setUser, queryClient],
  )

  const refresh = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: queryKey.users.me() })
  }, [queryClient])

  const value: AuthContextValue = {
    // Use query result if available, otherwise fall back to persisted store user.
    // Before mount, user is null (avoids hydration mismatch with SSR).
    user: currentUser ?? (mounted ? user : null) ?? null,
    // Loading if: query is loading, OR we haven't mounted yet (checking token),
    // OR we have a token but query hasn't returned.
    isLoading: !mounted || isLoading || (hasToken && !currentUser),
    // Authenticated if: query returned a user, OR (after mount) we have a
    // persisted user from a previous session.
    isAuthenticated: !!currentUser || (mounted && !!user),
    login,
    logout,
    refresh,
    setUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = React.useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Custom error for MFA challenge
export class MfaRequiredError extends Error {
  constructor(public readonly mfaSessionToken: string) {
    super('MFA required')
    this.name = 'MfaRequiredError'
  }
}
