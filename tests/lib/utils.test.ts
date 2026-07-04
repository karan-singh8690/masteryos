import { describe, it, expect } from 'vitest'

import { cn } from '@/lib/cn'
import { calculatePasswordStrength } from '@/lib/validations'
import {
  formatDate,
  formatRelativeTime,
  formatNumber,
  truncate,
  capitalize,
  toTitleCase,
  getInitials,
  maskEmail,
  formatBytes,
} from '@/lib/format'

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes', () => {
    expect(cn('base', true && 'included', false && 'excluded')).toBe('base included')
  })

  it('deduplicates conflicting tailwind classes', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
  })

  it('handles undefined and null', () => {
    expect(cn('base', undefined, null, 'end')).toBe('base end')
  })
})

describe('formatDate', () => {
  it('formats a date string', () => {
    const result = formatDate('2024-01-15T10:00:00Z')
    expect(result).toMatch(/Jan/)
    expect(result).toMatch(/15/)
    expect(result).toMatch(/2024/)
  })

  it('returns dash for null/undefined', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate(undefined)).toBe('—')
  })

  it('returns dash for invalid date', () => {
    expect(formatDate('not-a-date')).toBe('—')
  })
})

describe('formatRelativeTime', () => {
  it('formats recent time as "ago"', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
    const result = formatRelativeTime(twoHoursAgo)
    expect(result).toMatch(/ago/i)
  })

  it('returns dash for null', () => {
    expect(formatRelativeTime(null)).toBe('—')
  })
})

describe('formatNumber', () => {
  it('formats thousands', () => {
    expect(formatNumber(1234567)).toMatch(/1,234,567/)
  })
})

describe('truncate', () => {
  it('truncates long strings', () => {
    expect(truncate('hello world', 5)).toBe('hell…')
  })

  it('does not truncate short strings', () => {
    expect(truncate('hi', 10)).toBe('hi')
  })
})

describe('capitalize', () => {
  it('capitalizes first letter', () => {
    expect(capitalize('hello')).toBe('Hello')
  })
})

describe('toTitleCase', () => {
  it('converts snake_case to Title Case', () => {
    expect(toTitleCase('hello_world')).toBe('Hello World')
  })

  it('converts kebab-case to Title Case', () => {
    expect(toTitleCase('hello-world')).toBe('Hello World')
  })
})

describe('getInitials', () => {
  it('returns initials for full name', () => {
    expect(getInitials('John Doe')).toBe('JD')
  })

  it('returns single initial for single name', () => {
    expect(getInitials('John')).toBe('J')
  })

  it('returns ? for empty string', () => {
    expect(getInitials('')).toBe('?')
  })
})

describe('maskEmail', () => {
  it('masks the local part', () => {
    expect(maskEmail('alice@example.com')).toBe('al***@example.com')
  })

  it('masks short local parts', () => {
    expect(maskEmail('ab@example.com')).toBe('a***@example.com')
  })
})

describe('formatBytes', () => {
  it('formats bytes', () => {
    expect(formatBytes(0)).toBe('0 B')
  })

  it('formats KB', () => {
    expect(formatBytes(1024)).toBe('1 KB')
  })

  it('formats MB', () => {
    expect(formatBytes(1024 * 1024)).toBe('1 MB')
  })
})

describe('calculatePasswordStrength', () => {
  it('returns 0 for empty password', () => {
    const result = calculatePasswordStrength('')
    expect(result.score).toBe(0)
    expect(result.percentage).toBe(0)
  })

  it('returns weak for short password', () => {
    const result = calculatePasswordStrength('abc')
    expect(result.score).toBeLessThanOrEqual(2)
  })

  it('returns strong for complex password', () => {
    const result = calculatePasswordStrength('Str0ng!Password#2024xyz')
    expect(result.score).toBe(4)
    expect(result.label).toBe('Strong')
  })
})
