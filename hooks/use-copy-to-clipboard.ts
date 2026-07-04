'use client'

import * as React from 'react'

/**
 * Copy text to clipboard with a "copied" state.
 */
export function useCopyToClipboard(timeout = 2000) {
  const [copied, setCopied] = React.useState(false)

  const copy = React.useCallback(
    async (text: string) => {
      if (typeof navigator === 'undefined' || !navigator.clipboard) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea')
        textarea.value = text
        document.body.appendChild(textarea)
        textarea.select()
        try {
          document.execCommand('copy')
          setCopied(true)
        } catch {
          setCopied(false)
        }
        document.body.removeChild(textarea)
        return
      }
      try {
        await navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), timeout)
      } catch {
        setCopied(false)
      }
    },
    [timeout],
  )

  return { copied, copy }
}
