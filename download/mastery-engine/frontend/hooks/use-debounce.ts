'use client'

import * as React from 'react'

/**
 * Debounce a value — returns the value after `delay` ms of no changes.
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debounced, setDebounced] = React.useState<T>(value)

  React.useEffect(() => {
    const handler = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(handler)
  }, [value, delay])

  return debounced
}
