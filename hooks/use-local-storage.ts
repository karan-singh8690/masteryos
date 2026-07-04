'use client'

import * as React from 'react'

/**
 * Persist state to localStorage.
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((val: T) => T)) => void] {
  const [stored, setStored] = React.useState<T>(() => {
    if (typeof window === 'undefined') return initialValue
    try {
      const item = window.localStorage.getItem(key)
      return item ? (JSON.parse(item) as T) : initialValue
    } catch {
      return initialValue
    }
  })

  const setValue = React.useCallback(
    (value: T | ((val: T) => T)) => {
      setStored((prev) => {
        const next = value instanceof Function ? value(prev) : value
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, JSON.stringify(next))
        }
        return next
      })
    },
    [key],
  )

  return [stored, setValue]
}
