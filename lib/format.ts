/**
 * Formatting utilities for dates, numbers, strings, etc.
 */

import { format, formatDistanceToNow, isToday, isYesterday } from 'date-fns'

/**
 * Format a date string/Date into a human-readable format.
 */
export function formatDate(
  date: string | Date | null | undefined,
  formatStr: string = 'MMM d, yyyy',
): string {
  if (!date) return '—'
  const d = typeof date === 'string' ? new Date(date) : date
  if (Number.isNaN(d.getTime())) return '—'
  return format(d, formatStr)
}

/**
 * Format a date with time.
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  return formatDate(date, 'MMM d, yyyy h:mm a')
}

/**
 * Format a date as a relative time (e.g., "2 hours ago").
 */
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return '—'
  const d = typeof date === 'string' ? new Date(date) : date
  if (Number.isNaN(d.getTime())) return '—'
  return formatDistanceToNow(d, { addSuffix: true })
}

/**
 * Format a date with smart display: "Today", "Yesterday", or full date.
 */
export function formatSmartDate(date: string | Date | null | undefined): string {
  if (!date) return '—'
  const d = typeof date === 'string' ? new Date(date) : date
  if (Number.isNaN(d.getTime())) return '—'
  if (isToday(d)) return `Today at ${format(d, 'h:mm a')}`
  if (isYesterday(d)) return `Yesterday at ${format(d, 'h:mm a')}`
  return formatDateTime(d)
}

/**
 * Format a number with thousands separators.
 */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat().format(n)
}

/**
 * Format a percentage (0-100 → "0%").
 */
export function formatPercent(n: number, decimals = 0): string {
  return `${n.toFixed(decimals)}%`
}

/**
 * Format a duration in seconds as "Mm Ss".
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  if (m < 60) return `${m}m ${s}s`
  const h = Math.floor(m / 60)
  const remM = m % 60
  return `${h}h ${remM}m`
}

/**
 * Truncate a string to maxLen, adding an ellipsis.
 */
export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen - 1) + '…'
}

/**
 * Capitalize the first letter of a string.
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * Convert a string to title case (e.g., "hello_world" → "Hello World").
 */
export function toTitleCase(str: string): string {
  return str
    .replace(/[_-]/g, ' ')
    .split(' ')
    .map((word) => capitalize(word.toLowerCase()))
    .join(' ')
}

/**
 * Format an email for display (lowercase).
 */
export function normalizeEmail(email: string): string {
  return (email || '').trim().toLowerCase()
}

/**
 * Get initials from a display name (max 2 characters).
 */
export function getInitials(name: string | undefined | null): string {
  if (!name || typeof name !== 'string') return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 0 || parts[0] === '') return '?'
  if (parts.length === 1) return parts[0]!.charAt(0).toUpperCase()
  return (parts[0]!.charAt(0) + parts[parts.length - 1]!.charAt(0)).toUpperCase()
}

/**
 * Mask an email for privacy (e.g., "a***@example.com").
 */
export function maskEmail(email: string): string {
  const [local, domain] = email.split('@')
  if (!local || !domain) return email
  if (local.length <= 2) return `${local[0]}***@${domain}`
  return `${local.slice(0, 2)}***@${domain}`
}

/**
 * Format a byte count as a human-readable size.
 */
export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`
}
