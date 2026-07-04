/**
 * UI store — manages sidebar state + mobile nav.
 */

import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  mobileNavOpen: boolean
  commandPaletteOpen: boolean

  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  toggleMobileNav: () => void
  setMobileNavOpen: (open: boolean) => void
  toggleCommandPalette: () => void
  setCommandPaletteOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>()((set) => ({
  sidebarOpen: true,
  mobileNavOpen: false,
  commandPaletteOpen: false,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleMobileNav: () => set((state) => ({ mobileNavOpen: !state.mobileNavOpen })),
  setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
  toggleCommandPalette: () =>
    set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
}))
