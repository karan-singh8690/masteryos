/**
 * Auth store — manages JWT tokens + current user.
 *
 * Only stores the bare minimum (tokens + user). Everything else (profile,
 * sessions, security dashboard) is fetched via React Query.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { CurrentUser, User } from '@/types/auth'
import { tokenStorage } from '@/lib/api-client'

interface AuthState {
  // State
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean

  // Actions
  setUser: (user: User | null) => void
  setCurrentUser: (user: CurrentUser | null) => void
  setAuthenticated: (authenticated: boolean) => void
  setLoading: (loading: boolean) => void
  logout: () => void
  updateProfile: (profile: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: user !== null,
        }),

      setCurrentUser: (currentUser) =>
        set({
          user: currentUser?.user ?? null,
          isAuthenticated: currentUser !== null,
        }),

      setAuthenticated: (authenticated) =>
        set({ isAuthenticated: authenticated }),

      setLoading: (loading) => set({ isLoading: loading }),

      logout: () => {
        tokenStorage.clear()
        set({ user: null, isAuthenticated: false, isLoading: false })
      },

      updateProfile: (profile) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...profile } : null,
        })),
    }),
    {
      name: 'mastery-auth',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)
