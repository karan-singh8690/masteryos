import { describe, it, expect, beforeEach } from 'vitest'

import { useAuthStore } from '@/stores/auth-store'
import { useUIStore } from '@/stores/ui-store'
import { useNotificationStore } from '@/stores/notification-store'
import type { User } from '@/types/auth'

const mockUser: User = {
  id: 'user-1',
  email: 'test@example.com',
  status: 'active',
  mfaEnabled: false,
  emailVerifiedAt: '2024-01-01T00:00:00Z',
  createdAt: '2024-01-01T00:00:00Z',
}

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: true })
    localStorage.clear()
  })

  it('has correct initial state', () => {
    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(state.isLoading).toBe(true)
  })

  it('setUser updates user + isAuthenticated', () => {
    useAuthStore.getState().setUser(mockUser)
    const state = useAuthStore.getState()
    expect(state.user).toEqual(mockUser)
    expect(state.isAuthenticated).toBe(true)
  })

  it('setUser(null) clears auth', () => {
    useAuthStore.getState().setUser(mockUser)
    useAuthStore.getState().setUser(null)
    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('logout clears user + tokens', () => {
    useAuthStore.getState().setUser(mockUser)
    localStorage.setItem('mastery.access_token', 'token')
    localStorage.setItem('mastery.refresh_token', 'refresh')

    useAuthStore.getState().logout()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(localStorage.getItem('mastery.access_token')).toBeNull()
    expect(localStorage.getItem('mastery.refresh_token')).toBeNull()
  })

  it('updateProfile merges updates', () => {
    useAuthStore.getState().setUser(mockUser)
    useAuthStore.getState().updateProfile({ mfaEnabled: true })

    const state = useAuthStore.getState()
    expect(state.user?.mfaEnabled).toBe(true)
    expect(state.user?.email).toBe(mockUser.email) // Other fields preserved
  })
})

describe('useUIStore', () => {
  beforeEach(() => {
    useUIStore.setState({
      sidebarOpen: true,
      mobileNavOpen: false,
      commandPaletteOpen: false,
    })
  })

  it('has correct initial state', () => {
    const state = useUIStore.getState()
    expect(state.sidebarOpen).toBe(true)
    expect(state.mobileNavOpen).toBe(false)
    expect(state.commandPaletteOpen).toBe(false)
  })

  it('toggleSidebar flips sidebarOpen', () => {
    useUIStore.getState().toggleSidebar()
    expect(useUIStore.getState().sidebarOpen).toBe(false)
    useUIStore.getState().toggleSidebar()
    expect(useUIStore.getState().sidebarOpen).toBe(true)
  })

  it('setSidebarOpen sets value', () => {
    useUIStore.getState().setSidebarOpen(false)
    expect(useUIStore.getState().sidebarOpen).toBe(false)
  })

  it('toggleMobileNav flips mobileNavOpen', () => {
    useUIStore.getState().toggleMobileNav()
    expect(useUIStore.getState().mobileNavOpen).toBe(true)
  })

  it('toggleCommandPalette flips commandPaletteOpen', () => {
    useUIStore.getState().toggleCommandPalette()
    expect(useUIStore.getState().commandPaletteOpen).toBe(true)
  })
})

describe('useNotificationStore', () => {
  beforeEach(() => {
    useNotificationStore.setState({ unreadCount: 0 })
  })

  it('has correct initial state', () => {
    expect(useNotificationStore.getState().unreadCount).toBe(0)
  })

  it('setUnreadCount sets count', () => {
    useNotificationStore.getState().setUnreadCount(5)
    expect(useNotificationStore.getState().unreadCount).toBe(5)
  })

  it('incrementUnread adds 1', () => {
    useNotificationStore.getState().setUnreadCount(3)
    useNotificationStore.getState().incrementUnread()
    expect(useNotificationStore.getState().unreadCount).toBe(4)
  })

  it('decrementUnread subtracts 1 (not below 0)', () => {
    useNotificationStore.getState().setUnreadCount(2)
    useNotificationStore.getState().decrementUnread()
    expect(useNotificationStore.getState().unreadCount).toBe(1)

    useNotificationStore.getState().decrementUnread()
    expect(useNotificationStore.getState().unreadCount).toBe(0)

    useNotificationStore.getState().decrementUnread()
    expect(useNotificationStore.getState().unreadCount).toBe(0) // Stays at 0
  })

  it('reset sets count to 0', () => {
    useNotificationStore.getState().setUnreadCount(10)
    useNotificationStore.getState().reset()
    expect(useNotificationStore.getState().unreadCount).toBe(0)
  })
})
