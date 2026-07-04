/**
 * Notification store — manages in-app toast notifications + unread count.
 *
 * Uses sonner for toasts. This store tracks the unread count for the
 * notification badge in the header.
 */

import { create } from 'zustand'

interface NotificationState {
  unreadCount: number
  setUnreadCount: (count: number) => void
  incrementUnread: () => void
  decrementUnread: () => void
  reset: () => void
}

export const useNotificationStore = create<NotificationState>()((set) => ({
  unreadCount: 0,
  setUnreadCount: (count) => set({ unreadCount: count }),
  incrementUnread: () => set((state) => ({ unreadCount: state.unreadCount + 1 })),
  decrementUnread: () =>
    set((state) => ({ unreadCount: Math.max(0, state.unreadCount - 1) })),
  reset: () => set({ unreadCount: 0 }),
}))
