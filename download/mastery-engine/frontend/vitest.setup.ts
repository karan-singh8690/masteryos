import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, vi } from 'vitest'
import * as React from 'react'

// Polyfill for TextEncoder/TextDecoder (needed by some libs in jsdom)
import { TextEncoder, TextDecoder } from 'util'

global.TextEncoder = TextEncoder as typeof global.TextEncoder
global.TextDecoder = TextDecoder as typeof global.TextDecoder

// Mock matchMedia (needed for next-themes + useMediaQuery)
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })

  // Mock IntersectionObserver
  Object.defineProperty(window, 'IntersectionObserver', {
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    })),
  })

  // Mock ResizeObserver
  Object.defineProperty(window, 'ResizeObserver', {
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    })),
  })

  // Mock scrollTo
  window.scrollTo = vi.fn()
})

// Auto cleanup after each test
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  localStorage.clear()
  sessionStorage.clear()
})

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  redirect: vi.fn(),
}))

// Mock next-themes
vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: vi.fn(),
    themes: ['light', 'dark', 'system'],
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Re-export React for JSX
export { React }
