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
}

const AuthContext = React.createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const { user, isAuthenticated, setUser, setLoading, logout: storeLogout } = useAuthStore()
  const [hasToken, setHasToken] = React.useState(false)

  // Check for existing token on mount
  React.useEffect(() => {
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
      setUser(currentUser.user)
      setLoading(false)
    } else if (!isLoading && hasToken) {
      // Token exists but user fetch failed — logout
      storeLogout()
    }
  }, [currentUser, isLoading, hasToken, setUser, setLoading, storeLogout])

  const login = React.useCallback(
    async (email: string, password: string, mfaCode?: string) => {
      const response = await authApi.login({ email, password, mfaCode })
      if (response.requiresMfa) {
        // Return MFA challenge — caller handles
        throw new MfaRequiredError(response.mfaSessionToken || '')
      }
      tokenStorage.setAccessToken(response.accessToken)
      if (response.refreshToken) {
        tokenStorage.setRefreshToken(response.refreshToken)
      }
      setUser(response.user)
      setHasToken(true)
      // Invalidate user query to refetch
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
    user: currentUser ?? null,
    isLoading: isLoading || (hasToken && !currentUser),
    isAuthenticated: !!currentUser,
    login,
    logout,
    refresh,
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
