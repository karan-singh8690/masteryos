'use client'

import * as React from 'react'

/**
 * Returns the previous value of a prop or state.
 */
export function usePrevious<T>(value: T): T | undefined {
  const ref = React.useRef<T | undefined>(undefined)

  React.useEffect(() => {
    ref.current = value
  }, [value])

  return ref.current
}
