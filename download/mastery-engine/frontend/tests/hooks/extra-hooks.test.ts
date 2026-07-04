import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

import { useCopyToClipboard } from '@/hooks/use-copy-to-clipboard'
import { useInterval } from '@/hooks/use-interval'
import { useMediaQuery, useIsMobile } from '@/hooks/use-media-query'
import { renderHook, act } from '@testing-library/react'

describe('useCopyToClipboard', () => {
  it('starts with copied = false', () => {
    const { result } = renderHook(() => useCopyToClipboard())
    expect(result.current.copied).toBe(false)
  })

  it('sets copied to true after copy', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: { writeText },
    })

    const { result } = renderHook(() => useCopyToClipboard())
    await act(async () => {
      await result.current.copy('test text')
    })
    expect(result.current.copied).toBe(true)
    expect(writeText).toHaveBeenCalledWith('test text')
  })

  it('handles clipboard errors gracefully', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('Not allowed'))
    Object.assign(navigator, {
      clipboard: { writeText },
    })

    const { result } = renderHook(() => useCopyToClipboard())
    await act(async () => {
      await result.current.copy('test')
    })
    expect(result.current.copied).toBe(false)
  })
})

describe('useInterval', () => {
  beforeAll(() => {
    vi.useFakeTimers()
  })

  afterAll(() => {
    vi.useRealTimers()
  })

  it('calls callback at interval', () => {
    const callback = vi.fn()
    renderHook(() => useInterval(callback, 1000))

    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(callback).toHaveBeenCalledTimes(3)
  })

  it('does not call callback when delay is null', () => {
    const callback = vi.fn()
    renderHook(() => useInterval(callback, null))

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(callback).not.toHaveBeenCalled()
  })

  it('clears interval on unmount', () => {
    const callback = vi.fn()
    const { unmount } = renderHook(() => useInterval(callback, 1000))

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(callback).toHaveBeenCalledTimes(1)

    unmount()

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(callback).toHaveBeenCalledTimes(1) // Not called after unmount
  })
})

describe('useMediaQuery', () => {
  it('returns false for non-matching query', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({
        matches: false,
        media: '(max-width: 768px)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'))
    expect(result.current).toBe(false)
  })

  it('returns true for matching query', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({
        matches: true,
        media: '(max-width: 768px)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })

    const { result } = renderHook(() => useMediaQuery('(max-width: 768px)'))
    expect(result.current).toBe(true)
  })
})

describe('useIsMobile', () => {
  it('returns boolean', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({
        matches: false,
        media: '(max-width: 768px)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })

    const { result } = renderHook(() => useIsMobile())
    expect(typeof result.current).toBe('boolean')
  })
})
