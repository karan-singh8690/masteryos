'use client'

import * as React from 'react'

/**
 * setInterval as a hook. Pauses when delay is null.
 */
export function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = React.useRef(callback)

  React.useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  React.useEffect(() => {
    if (delay === null) return
    const id = setInterval(() => savedCallback.current(), delay)
    return () => clearInterval(id)
  }, [delay])
}
