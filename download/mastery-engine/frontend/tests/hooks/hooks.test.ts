import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'

import { useLocalStorage } from '@/hooks/use-local-storage'
import { useDebounce } from '@/hooks/use-debounce'
import { usePrevious } from '@/hooks/use-previous'

describe('useLocalStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns initial value when no stored value', () => {
    const { result } = renderHook(() => useLocalStorage('test', 'initial'))
    expect(result.current[0]).toBe('initial')
  })

  it('returns stored value when available', () => {
    localStorage.setItem('test', JSON.stringify('stored'))
    const { result } = renderHook(() => useLocalStorage('test', 'initial'))
    expect(result.current[0]).toBe('stored')
  })

  it('updates value + localStorage', () => {
    const { result } = renderHook(() => useLocalStorage('test', 'initial'))
    act(() => {
      result.current[1]('updated')
    })
    expect(result.current[0]).toBe('updated')
    expect(JSON.parse(localStorage.getItem('test')!)).toBe('updated')
  })

  it('supports functional updates', () => {
    const { result } = renderHook(() => useLocalStorage('count', 0))
    act(() => {
      result.current[1]((prev) => prev + 1)
    })
    expect(result.current[0]).toBe(1)
  })
})

describe('useDebounce', () => {
  it('returns value immediately on first render', () => {
    const { result } = renderHook(() => useDebounce('initial', 100))
    expect(result.current).toBe('initial')
  })

  it('debounces value changes', async () => {
    const { result, rerender } = renderHook(({ value }) => useDebounce(value, 100), {
      initialProps: { value: 'first' },
    })

    rerender({ value: 'second' })
    expect(result.current).toBe('first') // Still old value

    await new Promise((r) => setTimeout(r, 150))
    expect(result.current).toBe('second') // Now updated
  })
})

describe('usePrevious', () => {
  it('returns undefined on first render', () => {
    const { result } = renderHook(() => usePrevious('first'))
    expect(result.current).toBeUndefined()
  })

  it('returns previous value after update', () => {
    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: 'first' },
    })

    rerender({ value: 'second' })
    expect(result.current).toBe('first')
  })
})
